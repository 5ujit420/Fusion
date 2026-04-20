import datetime

from django.db.models import Prefetch, Q

from .models import Bill, BookingDetail, Inventory, InventoryBill, MealRecord, RoomDetail


INTENDER_ROLE = "Intender"
CARETAKER_ROLE = "VhCaretaker"
INCHARGE_ROLE = "VhIncharge"


def get_user_designation(user):
    if user.holds_designations.filter(designation__name=INCHARGE_ROLE).exists():
        return INCHARGE_ROLE
    if user.holds_designations.filter(designation__name=CARETAKER_ROLE).exists():
        return CARETAKER_ROLE
    return INTENDER_ROLE


def get_dashboard_base_queryset():
    return BookingDetail.objects.select_related("intender", "caretaker").prefetch_related(
        "rooms",
        "visitor",
    )


def get_inventory_queryset():
    return Inventory.objects.all()


def get_inventory_bills_queryset():
    return InventoryBill.objects.select_related("item_name").all()


def get_bills_queryset():
    return Bill.objects.select_related("booking", "booking__intender", "caretaker").prefetch_related("room")


def get_booking_requests_queryset(user):
    queryset = get_dashboard_base_queryset().order_by("booking_from")
    if get_user_designation(user) in [INCHARGE_ROLE, CARETAKER_ROLE]:
        return queryset
    return queryset.filter(intender=user)


def get_active_bookings_queryset(user):
    statuses = ["Forward", "CheckedIn", "Pending", "Confirmed"]
    queryset = get_dashboard_base_queryset().filter(
        Q(status="Forward") | Q(status="CheckedIn") | Q(status="Pending") | Q(status="Confirmed"),
        booking_to__gte=datetime.date.today(),
    )
    if get_user_designation(user) in [INCHARGE_ROLE, CARETAKER_ROLE]:
        return queryset
    return queryset.filter(intender=user)


def get_inactive_bookings_queryset(user):
    queryset = get_dashboard_base_queryset().filter(Q(status="Canceled") | Q(status="Rejected"))
    if get_user_designation(user) in [INCHARGE_ROLE, CARETAKER_ROLE]:
        return queryset
    return queryset.filter(intender=user)


def get_completed_bookings_queryset(user):
    queryset = get_dashboard_base_queryset().select_related("intender")
    current_date = datetime.date.today()
    if get_user_designation(user) in [INCHARGE_ROLE, CARETAKER_ROLE]:
        return queryset.filter(status="CheckedOut", booking_to__lt=current_date)
    return queryset.filter(intender=user, status="CheckedOut", booking_to__lt=current_date)


def get_api_completed_bookings_queryset(user):
    queryset = get_dashboard_base_queryset().select_related("intender").filter(
        Q(status="Confirmed") | Q(status="Complete"),
    )
    if get_user_designation(user) in [INCHARGE_ROLE, CARETAKER_ROLE]:
        return queryset
    return queryset.filter(intender=user)


def get_booking_detail(booking_id):
    return get_dashboard_base_queryset().get(id=booking_id)


def get_available_rooms_queryset():
    return RoomDetail.objects.filter(room_status="Available").order_by("room_number")


def get_room_by_number(room_number):
    return RoomDetail.objects.get(room_number=room_number)


def get_inventory_item(inventory_id):
    return Inventory.objects.get(id=inventory_id)


def get_inventory_bill(bill_id):
    return InventoryBill.objects.select_related("item_name").get(id=bill_id)


def get_overlapping_bookings(date1, date2, statuses):
    overlap_filter = (
        Q(booking_from__lte=date1, booking_to__gte=date1)
        | Q(booking_from__gte=date1, booking_to__lte=date2)
        | Q(booking_from__lte=date2, booking_to__gte=date2)
    )
    return (
        get_dashboard_base_queryset()
        .filter(overlap_filter, status__in=list(statuses))
        .order_by("booking_from")
    )


def get_available_rooms_between(date1, date2):
    booked_room_ids = set()
    bookings = get_overlapping_bookings(date1, date2, ["Confirmed", "Forward", "CheckedIn"])
    for booking in bookings:
        booked_room_ids.update(room.id for room in booking.rooms.all())
    return RoomDetail.objects.exclude(id__in=booked_room_ids).order_by("room_number")


def get_forwarded_booking_rooms_between(date1, date2):
    forwarded_bookings = get_overlapping_bookings(date1, date2, ["Forward"])
    room_ids = []
    for booking in forwarded_bookings:
        room_ids.extend(room.id for room in booking.rooms.all())
    return RoomDetail.objects.filter(id__in=room_ids).order_by("room_number")


def get_overlapping_room_bookings(room_id, start_date, end_date):
    return (
        BookingDetail.objects.filter(
            rooms__id=room_id,
            booking_from__lt=end_date,
            booking_to__gt=start_date,
            status__in=["Confirmed", "CheckedIn"],
        )
        .order_by("booking_from")
    )


def get_booking_range_bills(date1, date2):
    bookings = get_overlapping_bookings(
        date1,
        date2,
        ["Confirmed", "Forward", "CheckedIn", "Pending", "Rejected", "Canceled", "Complete"],
    )
    bills = []
    for booking in bookings:
        bill = Bill.objects.select_related("caretaker").filter(booking__pk=booking.id).first()
        if bill:
            bills.append(bill)
    return bills


def get_meal_records_for_bookings(booking_ids):
    return (
        MealRecord.objects.select_related("booking__intender", "booking__caretaker", "visitor")
        .filter(booking_id__in=list(booking_ids))
        .order_by("booking_id")
    )
