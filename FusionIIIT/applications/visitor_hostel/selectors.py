# selectors.py
# All database queries for the visitor_hostel module.
# Fixes: V-03, V-33–V-37, R-01, R-03, R-05, R-07, R-10
# Refactoring: T-01, T-04, T-05, T-08, T-13b, T-14, T-18, T-23, T-29, T-30a

import datetime
from itertools import chain

from django.contrib.auth.models import User
from django.db.models import Q

from applications.globals.models import HoldsDesignation

from .models import (
    BookingDetail, Bill, Inventory, InventoryBill,
    MealRecord, RoomDetail, VisitorDetail,
)


# ---------------------------------------------------------------------------
# Module-level query constants  (T-04)
# ---------------------------------------------------------------------------

BOOKING_SELECT_RELATED = ('intender', 'caretaker')

# T-04: Centralised Pending+Forward filter — replaces 4 duplicated Q expressions.
_PENDING_FORWARD_Q = Q(status="Pending") | Q(status="Forward")


# ---------------------------------------------------------------------------
# Base queryset helper  (T-05)
# ---------------------------------------------------------------------------

def _base_booking_qs():
    """T-05: Single source for the standard booking queryset with select_related."""
    return BookingDetail.objects.select_related(*BOOKING_SELECT_RELATED)


# ---------------------------------------------------------------------------
# Overlap predicate helper  (T-18)
# ---------------------------------------------------------------------------

def _overlap_q(d1, d2, status):
    """T-18: Named predicate for a date-range overlap with a given status.
    Replaces the inline triple-Q-OR inside get_overlapping_bookings.
    """
    return (
        Q(booking_from__lte=d1, booking_to__gte=d1, status=status) |
        Q(booking_from__gte=d1, booking_to__lte=d2, status=status) |
        Q(booking_from__lte=d2, booking_to__gte=d2, status=status)
    )


# ---------------------------------------------------------------------------
# Booking single-item fetch
# ---------------------------------------------------------------------------

def get_booking_by_id(booking_id):
    """R-07: Single source for booking-by-id fetch."""
    return _base_booking_qs().get(id=booking_id)


def get_booking_by_id_prefetched(booking_id):
    """Return booking with rooms and visitors prefetched."""
    return (
        _base_booking_qs()
        .prefetch_related('rooms', 'visitor')
        .get(id=booking_id)
    )


# ---------------------------------------------------------------------------
# Dashboard booking queries  (R-01)
# ---------------------------------------------------------------------------

def get_pending_bookings_for_intender(user):
    """Pending + Forward bookings for an intender."""
    return (
        _base_booking_qs()
        .filter(
            _PENDING_FORWARD_Q,  # T-04
            booking_to__gte=datetime.datetime.today(),
            intender=user,
        )
        .order_by('booking_from')
    )


def get_active_bookings_for_intender(user):
    """CheckedIn bookings for an intender."""
    return (
        _base_booking_qs()
        .prefetch_related('rooms', 'visitor')  # T-14: ensure rooms prefetched
        .filter(status="CheckedIn", booking_to__gte=datetime.datetime.today(), intender=user)
        .order_by('booking_from')
    )


def get_dashboard_bookings_for_intender(user):
    """Dashboard bookings for an intender."""
    return (
        _base_booking_qs()
        .prefetch_related('visitor')
        .filter(
            Q(status="Pending") | Q(status="Forward") | Q(status="Confirmed") | Q(status='Rejected'),
            booking_to__gte=datetime.datetime.today(),
            intender=user,
        )
        .order_by('booking_from')
    )


def get_complete_bookings_for_intender(user):
    return (
        _base_booking_qs()
        .filter(check_out__lt=datetime.datetime.today(), intender=user)
        .order_by('-booking_from')
    )


def get_canceled_bookings_for_intender(user):
    return (
        _base_booking_qs()
        .filter(status="Canceled", intender=user)
        .order_by('booking_from')
    )


def get_rejected_bookings_for_intender(user):
    return (
        _base_booking_qs()
        .filter(status='Rejected', intender=user)
        .order_by('booking_from')
    )


def get_cancel_requested_bookings_for_intender(user):
    return (
        _base_booking_qs()
        .filter(status='CancelRequested', intender=user)
        .order_by('booking_from')
    )


# --- Staff-side dashboard queries ---

def get_pending_bookings_all():
    """Pending + Forward bookings for staff."""
    return (
        _base_booking_qs()
        .filter(
            _PENDING_FORWARD_Q,  # T-04
            booking_to__gte=datetime.datetime.today(),
        )
        .order_by('booking_from')
    )


def get_active_bookings_all():
    """Confirmed + CheckedIn bookings for staff."""
    return (
        _base_booking_qs()
        .prefetch_related('rooms', 'visitor')
        .filter(
            Q(status="Confirmed") | Q(status="CheckedIn"),
            booking_to__gte=datetime.datetime.today(),
        )
        .order_by('booking_from')
    )


def get_cancel_requests_all():
    return (
        _base_booking_qs()
        .filter(status="CancelRequested", booking_to__gte=datetime.datetime.today())
        .order_by('booking_from')
    )


def get_dashboard_bookings_all():
    return (
        _base_booking_qs()
        .prefetch_related('visitor')
        .filter(
            Q(status="Pending") | Q(status="Forward") | Q(status="Confirmed"),
            booking_to__gte=datetime.datetime.today(),
        )
        .order_by('booking_from')
    )


def get_forwarded_bookings():
    return (
        _base_booking_qs()
        .filter(Q(status="Forward"), booking_to__gte=datetime.datetime.today())
        .order_by('booking_from')
    )


def get_complete_bookings_all():
    return (
        _base_booking_qs()
        .filter(
            Q(status="Canceled") | Q(status="Complete"),
            check_out__lt=datetime.datetime.today(),
        )
        .order_by('-booking_from')
    )


def get_canceled_bookings_all():
    return (
        _base_booking_qs()
        .filter(status="Canceled")
        .order_by('booking_from')
    )


def get_cancel_requested_for_intender(user):
    return (
        _base_booking_qs()
        .filter(
            status='CancelRequested',
            booking_to__gte=datetime.datetime.today(),
            intender=user,
        )
        .order_by('booking_from')
    )


def get_rejected_bookings_all():
    return (
        _base_booking_qs()
        .filter(status='Rejected')
        .order_by('booking_from')
    )


def get_all_bookings():
    return _base_booking_qs().all().order_by('booking_from')


def get_booking_requests_pending():
    return _base_booking_qs().filter(status="Pending")


def get_active_bookings_confirmed():
    return _base_booking_qs().filter(status="Confirmed")


def get_inactive_bookings():
    # T-08: Fixed typo 'Cancelled' → 'Canceled' (was returning 0 rows)
    return (
        _base_booking_qs()
        .filter(Q(status="Canceled") | Q(status="Rejected") | Q(status="Complete"))
    )


# ---------------------------------------------------------------------------
# Room selectors  (R-03, V-37)
# ---------------------------------------------------------------------------

def get_overlapping_bookings(date1, date2, statuses):
    """
    R-03: Unified query for bookings overlapping a date range with given statuses.
    T-18: Uses _overlap_q() helper — replaces inline triple-Q per status.
    """
    q_filters = Q()
    for status in statuses:
        q_filters |= _overlap_q(date1, date2, status)  # T-18
    return (
        _base_booking_qs()
        .prefetch_related('rooms')
        .filter(q_filters)
    )


def get_available_rooms(date1, date2):
    """T-29: Use chain.from_iterable instead of nested loop — more Pythonic."""
    statuses = ["Confirmed", "Forward", "CheckedIn"]
    overlapping = get_overlapping_bookings(date1, date2, statuses)
    booked_room_ids = list(
        chain.from_iterable(
            b.rooms.values_list('id', flat=True) for b in overlapping
        )
    )
    return RoomDetail.objects.exclude(id__in=booked_room_ids)


def get_forwarded_booking_rooms(date1, date2):
    """T-29: Use chain.from_iterable and values_list for room id collection."""
    statuses_forward = ["Forward"]
    forwarded_bookings = get_overlapping_bookings(date1, date2, statuses_forward)
    room_ids = list(
        chain.from_iterable(
            b.rooms.values_list('id', flat=True) for b in forwarded_bookings
        )
    )
    return list(RoomDetail.objects.filter(id__in=room_ids))


def get_room_by_number(room_number):
    return RoomDetail.objects.get(room_number=room_number)


def batch_get_rooms_by_numbers(room_numbers):
    """T-13b: Batch room lookup — one DB hit for all rooms, not one per room."""
    return {
        room.room_number: room
        for room in RoomDetail.objects.filter(room_number__in=room_numbers)
    }


def get_all_rooms():
    return RoomDetail.objects.all()


# ---------------------------------------------------------------------------
# Bill selectors
# ---------------------------------------------------------------------------

def get_all_bills():
    return Bill.objects.select_related('booking__intender', 'booking__caretaker', 'caretaker').all()


def get_bills_for_date_range(date1, date2):
    """Bill range query (from views.py L900-919)."""
    overlapping = get_overlapping_bookings(date1, date2, ["Confirmed", "Forward", "CheckedIn", "Complete", "Canceled"])
    booking_ids = [b.id for b in overlapping]
    return Bill.objects.select_related('caretaker', 'booking__intender').filter(booking__pk__in=booking_ids)


def get_meal_records_for_booking(booking_id):
    return MealRecord.objects.select_related(
        'booking__intender', 'booking__caretaker', 'visitor'
    ).filter(booking_id=booking_id)


def get_meal_record_for_visitor_date(visitor, booking, meal_date):
    """Return meal record or None."""
    try:
        return MealRecord.objects.select_related(
            'booking__intender', 'booking__caretaker', 'visitor'
        ).get(visitor=visitor, booking=booking, meal_date=meal_date)
    except MealRecord.DoesNotExist:
        return None


# ---------------------------------------------------------------------------
# Inventory selectors  (T-30a: add mutation selectors)
# ---------------------------------------------------------------------------

def get_all_inventory():
    return Inventory.objects.all()


def get_all_inventory_bills():
    return InventoryBill.objects.select_related('item_name').all()


def get_inventory_by_id(item_id):
    return Inventory.objects.get(pk=item_id)


def update_inventory_quantity(item_id, quantity):
    """T-30a: Route inventory update through selector layer."""
    Inventory.objects.filter(id=item_id).update(quantity=quantity)


def delete_inventory_item(item_id):
    """T-30a: Route inventory deletion through selector layer."""
    Inventory.objects.filter(id=item_id).delete()


# ---------------------------------------------------------------------------
# Visitor selectors
# ---------------------------------------------------------------------------

def get_all_visitors():
    return VisitorDetail.objects.all()


def get_visitor_by_id(visitor_id):
    return VisitorDetail.objects.get(id=visitor_id)


def get_first_visitor_per_booking(bookings):
    """T-23: Returns list of first visitor for each booking that has visitors.
    Extracted from services.get_visitor_list_from_dashboard.
    """
    visitor_list = []
    for booking in bookings:
        first = booking.visitor.first()
        if first is not None:
            visitor_list.append(first)
    return visitor_list


# ---------------------------------------------------------------------------
# User / Designation selectors  (R-05, R-10)
# ---------------------------------------------------------------------------

def get_all_users():
    """T-01: Centralised User.objects.all() — replaces ORM calls in views."""
    return User.objects.all()


def get_user_by_id(pk):
    """T-01: Centralised User.objects.get — replaces ORM calls in views/api."""
    return User.objects.get(id=pk)


def get_user_role(user):
    """R-10: Determine user's VH designation."""
    if user.holds_designations.filter(designation__name='VhIncharge').exists():
        return 'VhIncharge'
    elif user.holds_designations.filter(designation__name='VhCaretaker').exists():
        return 'VhCaretaker'
    else:
        return 'Intender'


def get_caretaker_user():
    """R-05: Safe access to caretaker user (avoids hard-coded index)."""
    hd = HoldsDesignation.objects.select_related(
        'user', 'working', 'designation'
    ).filter(designation__name="VhCaretaker").first()
    if hd is None:
        return None
    return hd.user


def get_incharge_user():
    """R-05, V-26: Safe access to incharge user (replaces unsafe [1])."""
    hds = HoldsDesignation.objects.select_related(
        'user', 'working', 'designation'
    ).filter(designation__name="VhIncharge")
    if hds.count() >= 2:
        return hds[1].user
    elif hds.exists():
        return hds.first().user
    return None
