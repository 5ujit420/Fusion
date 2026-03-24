# selectors.py
# All database queries for the visitor_hostel module.
# Fixes: V-03, V-33–V-37, R-01, R-03, R-05, R-07, R-10

import datetime

from django.contrib.auth.models import User
from django.db.models import Q

from applications.globals.models import HoldsDesignation

from .models import (
    BookingDetail, Bill, Inventory, InventoryBill,
    MealRecord, RoomDetail, VisitorDetail,
)


# ---------------------------------------------------------------------------
# Booking select_related base  (R-07)
# ---------------------------------------------------------------------------

BOOKING_SELECT_RELATED = ('intender', 'caretaker')


def get_booking_by_id(booking_id):
    """R-07: Single source for booking-by-id fetch."""
    return BookingDetail.objects.select_related(*BOOKING_SELECT_RELATED).get(id=booking_id)


def get_booking_by_id_prefetched(booking_id):
    """Return booking with rooms and visitors prefetched."""
    return (
        BookingDetail.objects.select_related(*BOOKING_SELECT_RELATED)
        .prefetch_related('rooms', 'visitor')
        .get(id=booking_id)
    )


# ---------------------------------------------------------------------------
# Dashboard booking queries  (R-01)
# ---------------------------------------------------------------------------

def get_pending_bookings_for_intender(user):
    """Pending + Forward bookings for an intender."""
    return (
        BookingDetail.objects.select_related(*BOOKING_SELECT_RELATED)
        .filter(
            Q(status="Pending") | Q(status="Forward"),
            booking_to__gte=datetime.datetime.today(),
            intender=user,
        )
        .order_by('booking_from')
    )


def get_active_bookings_for_intender(user):
    """CheckedIn bookings for an intender."""
    return (
        BookingDetail.objects.select_related(*BOOKING_SELECT_RELATED)
        .prefetch_related('rooms', 'visitor')  # V-34: prefetch
        .filter(status="CheckedIn", booking_to__gte=datetime.datetime.today(), intender=user)
        .order_by('booking_from')
    )


def get_dashboard_bookings_for_intender(user):
    """Dashboard bookings for an intender."""
    return (
        BookingDetail.objects.select_related(*BOOKING_SELECT_RELATED)
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
        BookingDetail.objects.select_related(*BOOKING_SELECT_RELATED)
        .filter(check_out__lt=datetime.datetime.today(), intender=user)
        .order_by('-booking_from')
    )


def get_canceled_bookings_for_intender(user):
    return (
        BookingDetail.objects.select_related(*BOOKING_SELECT_RELATED)
        .filter(status="Canceled", intender=user)
        .order_by('booking_from')
    )


def get_rejected_bookings_for_intender(user):
    return (
        BookingDetail.objects.select_related(*BOOKING_SELECT_RELATED)
        .filter(status='Rejected', intender=user)
        .order_by('booking_from')
    )


def get_cancel_requested_bookings_for_intender(user):
    return (
        BookingDetail.objects.select_related(*BOOKING_SELECT_RELATED)
        .filter(status='CancelRequested', intender=user)
        .order_by('booking_from')
    )


# --- Staff-side dashboard queries ---

def get_pending_bookings_all():
    """Pending + Forward bookings for staff."""
    return (
        BookingDetail.objects.select_related(*BOOKING_SELECT_RELATED)
        .filter(
            Q(status="Pending") | Q(status="Forward"),
            booking_to__gte=datetime.datetime.today(),
        )
        .order_by('booking_from')
    )


def get_active_bookings_all():
    """Confirmed + CheckedIn bookings for staff."""
    return (
        BookingDetail.objects.select_related(*BOOKING_SELECT_RELATED)
        .prefetch_related('rooms', 'visitor')  # V-34
        .filter(
            Q(status="Confirmed") | Q(status="CheckedIn"),
            booking_to__gte=datetime.datetime.today(),
        )
        .order_by('booking_from')
    )


def get_cancel_requests_all():
    return (
        BookingDetail.objects.select_related(*BOOKING_SELECT_RELATED)
        .filter(status="CancelRequested", booking_to__gte=datetime.datetime.today())
        .order_by('booking_from')
    )


def get_dashboard_bookings_all():
    return (
        BookingDetail.objects.select_related(*BOOKING_SELECT_RELATED)
        .prefetch_related('visitor')
        .filter(
            Q(status="Pending") | Q(status="Forward") | Q(status="Confirmed"),
            booking_to__gte=datetime.datetime.today(),
        )
        .order_by('booking_from')
    )


def get_forwarded_bookings():
    return (
        BookingDetail.objects.select_related(*BOOKING_SELECT_RELATED)
        .filter(Q(status="Forward"), booking_to__gte=datetime.datetime.today())
        .order_by('booking_from')
    )


def get_complete_bookings_all():
    return (
        BookingDetail.objects.select_related(*BOOKING_SELECT_RELATED)
        .filter(
            Q(status="Canceled") | Q(status="Complete"),
            check_out__lt=datetime.datetime.today(),
        )
        .order_by('-booking_from')
    )


def get_canceled_bookings_all():
    return (
        BookingDetail.objects.select_related(*BOOKING_SELECT_RELATED)
        .filter(status="Canceled")
        .order_by('booking_from')
    )


def get_cancel_requested_for_intender(user):
    return (
        BookingDetail.objects.select_related(*BOOKING_SELECT_RELATED)
        .filter(
            status='CancelRequested',
            booking_to__gte=datetime.datetime.today(),
            intender=user,
        )
        .order_by('booking_from')
    )


def get_rejected_bookings_all():
    return (
        BookingDetail.objects.select_related(*BOOKING_SELECT_RELATED)
        .filter(status='Rejected')
        .order_by('booking_from')
    )


def get_all_bookings():
    return BookingDetail.objects.select_related(*BOOKING_SELECT_RELATED).all().order_by('booking_from')


def get_booking_requests_pending():
    return BookingDetail.objects.select_related(*BOOKING_SELECT_RELATED).filter(status="Pending")


def get_active_bookings_confirmed():
    return BookingDetail.objects.select_related(*BOOKING_SELECT_RELATED).filter(status="Confirmed")


def get_inactive_bookings():
    return (
        BookingDetail.objects.select_related(*BOOKING_SELECT_RELATED)
        .filter(Q(status="Cancelled") | Q(status="Rejected") | Q(status="Complete"))
    )


# ---------------------------------------------------------------------------
# Room selectors  (R-03, V-37)
# ---------------------------------------------------------------------------

def get_overlapping_bookings(date1, date2, statuses):
    """
    R-03: Unified query for bookings overlapping a date range with given statuses.
    Replaces booking_details() and forwarded_booking_details().
    """
    q_filters = Q()
    for status in statuses:
        q_filters |= (
            Q(booking_from__lte=date1, booking_to__gte=date1, status=status) |
            Q(booking_from__gte=date1, booking_to__lte=date2, status=status) |
            Q(booking_from__lte=date2, booking_to__gte=date2, status=status)
        )
    return (
        BookingDetail.objects.select_related(*BOOKING_SELECT_RELATED)
        .prefetch_related('rooms')
        .filter(q_filters)
    )


def get_available_rooms(date1, date2):
    """V-37: Use .exclude() instead of O(n²) list iteration."""
    statuses = ["Confirmed", "Forward", "CheckedIn"]
    overlapping = get_overlapping_bookings(date1, date2, statuses)
    booked_room_ids = []
    for booking in overlapping:
        for room in booking.rooms.all():
            booked_room_ids.append(room.id)
    return RoomDetail.objects.exclude(id__in=booked_room_ids)


def get_forwarded_booking_rooms(date1, date2):
    """Rooms allocated to forwarded bookings in the date range."""
    statuses_confirmed = ["Confirmed", "CheckedIn"]
    statuses_forward = ["Forward"]
    forwarded_bookings = get_overlapping_bookings(date1, date2, statuses_forward)
    rooms = []
    for booking in forwarded_bookings:
        for room in booking.rooms.all():
            rooms.append(room)
    return rooms


def get_room_by_number(room_number):
    return RoomDetail.objects.get(room_number=room_number)


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
    except MealRecord.DoesNotExist:  # V-28: specific exception
        return None


# ---------------------------------------------------------------------------
# Inventory selectors
# ---------------------------------------------------------------------------

def get_all_inventory():
    return Inventory.objects.all()


def get_all_inventory_bills():
    return InventoryBill.objects.select_related('item_name').all()


def get_inventory_by_id(item_id):
    return Inventory.objects.get(pk=item_id)


# ---------------------------------------------------------------------------
# Visitor selectors
# ---------------------------------------------------------------------------

def get_all_visitors():
    return VisitorDetail.objects.all()


def get_visitor_by_id(visitor_id):
    return VisitorDetail.objects.get(id=visitor_id)


# ---------------------------------------------------------------------------
# User / Designation selectors  (R-05, R-10)
# ---------------------------------------------------------------------------

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
