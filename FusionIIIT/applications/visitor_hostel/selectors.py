# selectors.py
# All database queries for the visitor_hostel module.
# Fixes: V-02, V-03, V-04, V-16, V-19, R-05, R-06, 5B-4

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


# ---------------------------------------------------------------------------
# R-05: Parametric base query builder
# ---------------------------------------------------------------------------

def _get_bookings(statuses=None, user=None, prefetch=None, order='booking_from',
                  descending=False, require_future=False, check_out_past=False):
    """
    R-05: Single parametric builder replacing 15+ individual booking selectors.
    Eliminates duplication across intender/staff selector pairs.
    """
    qs = BookingDetail.objects.select_related(*BOOKING_SELECT_RELATED)
    if prefetch:
        qs = qs.prefetch_related(*prefetch)
    if statuses:
        q_filter = Q()
        for s in statuses:
            q_filter |= Q(status=s)
        qs = qs.filter(q_filter)
    if user is not None:
        qs = qs.filter(intender=user)
    if require_future:
        qs = qs.filter(booking_to__gte=datetime.datetime.today())
    if check_out_past:
        qs = qs.filter(check_out__lt=datetime.datetime.today())
    if order:
        order_field = f'-{order}' if descending else order
        qs = qs.order_by(order_field)
    return qs


# ---------------------------------------------------------------------------
# Single-booking selectors
# ---------------------------------------------------------------------------

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
# Dashboard booking queries  (R-01, R-05)
# ---------------------------------------------------------------------------

def get_pending_bookings_for_intender(user):
    """Pending + Forward bookings for an intender."""
    return _get_bookings(['Pending', 'Forward'], user=user, require_future=True)


def get_active_bookings_for_intender(user):
    """CheckedIn bookings for an intender."""
    return _get_bookings(
        ['CheckedIn'], user=user, prefetch=['rooms', 'visitor'], require_future=True)


def get_dashboard_bookings_for_intender(user):
    """Dashboard bookings for an intender."""
    return _get_bookings(
        ['Pending', 'Forward', 'Confirmed', 'Rejected'],
        user=user, prefetch=['visitor'], require_future=True)


def get_complete_bookings_for_intender(user):
    return _get_bookings(user=user, check_out_past=True, descending=True)


def get_canceled_bookings_for_intender(user):
    return _get_bookings(['Canceled'], user=user)


def get_rejected_bookings_for_intender(user):
    return _get_bookings(['Rejected'], user=user)


def get_cancel_requested_bookings_for_intender(user, future_only=False):
    """R-06: Consolidated cancel-requested selector with optional future filter."""
    return _get_bookings(['CancelRequested'], user=user, require_future=future_only)


# --- Staff-side dashboard queries ---

def get_pending_bookings_all():
    """Pending + Forward bookings for staff."""
    return _get_bookings(['Pending', 'Forward'], require_future=True)


def get_active_bookings_all():
    """Confirmed + CheckedIn bookings for staff."""
    return _get_bookings(
        ['Confirmed', 'CheckedIn'], prefetch=['rooms', 'visitor'], require_future=True)


def get_cancel_requests_all():
    return _get_bookings(['CancelRequested'], require_future=True)


def get_dashboard_bookings_all():
    return _get_bookings(
        ['Pending', 'Forward', 'Confirmed'], prefetch=['visitor'], require_future=True)


def get_forwarded_bookings():
    return _get_bookings(['Forward'], require_future=True)


def get_complete_bookings_all():
    return _get_bookings(
        ['Canceled', 'Complete'], check_out_past=True, descending=True)


def get_canceled_bookings_all():
    return _get_bookings(['Canceled'])


def get_rejected_bookings_all():
    return _get_bookings(['Rejected'])


def get_all_bookings():
    return _get_bookings()


def get_booking_requests_pending():
    return _get_bookings(['Pending'], order=None)


def get_active_bookings_confirmed():
    return _get_bookings(['Confirmed'], order=None)


def get_inactive_bookings():
    """5B-4: Fixed typo 'Cancelled' → 'Canceled' to match model choices."""
    return _get_bookings(['Canceled', 'Rejected', 'Complete'], order=None)


# ---------------------------------------------------------------------------
# Room selectors  (V-16)
# ---------------------------------------------------------------------------

def get_overlapping_bookings(date1, date2, statuses):
    """
    R-03: Unified query for bookings overlapping a date range with given statuses.
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
    """V-16: Optimized — uses values_list instead of O(n×m) Python loop."""
    statuses = ["Confirmed", "Forward", "CheckedIn"]
    overlapping = get_overlapping_bookings(date1, date2, statuses)
    booked_room_ids = list(overlapping.values_list('rooms__id', flat=True))
    return RoomDetail.objects.exclude(id__in=booked_room_ids)


def get_forwarded_booking_rooms(date1, date2):
    """Rooms allocated to forwarded bookings in the date range."""
    statuses_forward = ["Forward"]
    forwarded_bookings = get_overlapping_bookings(date1, date2, statuses_forward)
    room_ids = list(forwarded_bookings.values_list('rooms__id', flat=True))
    return RoomDetail.objects.filter(id__in=room_ids)


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
    """Bill range query."""
    overlapping = get_overlapping_bookings(
        date1, date2, ["Confirmed", "Forward", "CheckedIn", "Complete", "Canceled"])
    booking_ids = list(overlapping.values_list('id', flat=True))
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
# User selectors  (V-02, V-03, V-04, V-19)
# ---------------------------------------------------------------------------

def get_all_intenders():
    """V-02, V-03: Moved User.objects.all() out of views."""
    return User.objects.all()


def get_user_by_id(user_id):
    """V-04: Moved User.objects.get() out of views."""
    return User.objects.get(id=user_id)


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
    """V-19: Fixed — returns first incharge instead of fragile [1] index."""
    hd = HoldsDesignation.objects.select_related(
        'user', 'working', 'designation'
    ).filter(designation__name="VhIncharge").first()
    if hd is None:
        return None
    return hd.user
