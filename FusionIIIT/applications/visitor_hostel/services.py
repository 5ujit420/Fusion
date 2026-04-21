# services.py
# All business logic for the visitor_hostel module.
# Fixes: V-02, V-05–V-13, V-14–V-16, V-43–V-44, R-02, R-04, R-06, R-08, R-09
# Refactoring: T-02, T-03, T-06, T-09, T-10a, T-11b, T-12, T-13a, T-16,
#              T-17, T-19, T-20, T-21, T-22b, T-23b, T-24, T-30b

import datetime
import logging
import os

from .exceptions import BookingError, InventoryError  # T-15
from .notifications import send_vh_notification       # T-11b
from .models import (
    BookingDetail, Bill, Inventory, InventoryBill,
    MealRecord, RoomDetail, VisitorDetail,
    ROOM_RATES, MEAL_RATES, ROOM_BILL_BASE,
)
from . import selectors

logger = logging.getLogger(__name__)


# === User Role ===================================================================

def get_user_designation(user):
    """Determine the VH role for a user."""
    return selectors.get_user_role(user)


# === Visitor Creation ============================================================

def create_visitor(visitor_name, visitor_phone, visitor_email='',
                   visitor_address='', visitor_organization='', nationality=''):
    """R-06: consolidated visitor creation."""
    if visitor_organization == '':
        visitor_organization = ' '
    return VisitorDetail.objects.create(
        visitor_phone=visitor_phone,
        visitor_name=visitor_name,
        visitor_email=visitor_email,
        visitor_address=visitor_address,
        visitor_organization=visitor_organization,
        nationality=nationality,
    )


# === Room Assignment =============================================================

def assign_rooms_to_booking(booking, room_numbers):
    """T-13a: Batch room lookup — one query for all rooms, not one per room (N+1 fix)."""
    rooms_map = selectors.batch_get_rooms_by_numbers(room_numbers)
    count = 0
    for room_number in room_numbers:
        room_obj = rooms_map.get(room_number)
        if room_obj is not None:
            booking.rooms.add(room_obj)
            count += 1
    booking.number_of_rooms_alloted = count
    booking.save()
    return count


# === Bill Creation ===============================================================

def create_bill(booking, meal_bill, room_bill, caretaker, payment_status=True, bill_date=None):
    """R-09: Consolidated bill creation."""
    if bill_date is None:
        bill_date = datetime.date.today()
    return Bill.objects.create(
        booking=booking,
        meal_bill=int(meal_bill),
        room_bill=int(room_bill),
        caretaker=caretaker,
        payment_status=payment_status,
        bill_date=bill_date,
    )


# === Booking Lifecycle ===========================================================

def _update_booking_status(booking_id, status, remark=''):
    """T-06: Private helper — replaces 4 duplicated BookingDetail.filter.update() blocks."""
    BookingDetail.objects.select_related('intender', 'caretaker').filter(
        id=booking_id
    ).update(status=status, remark=remark)


def create_booking(intender_user, category, person_count, purpose, booking_from,
                   booking_to, arrival_time, departure_time, number_of_rooms,
                   bill_to_be_settled_by):
    """V-06: Extract booking creation from request_booking view.
    T-09: Added date-range guard.
    """
    # T-09: Date-range validation at service layer
    if booking_from and booking_to and booking_from > booking_to:
        raise BookingError("booking_from must be on or before booking_to")

    care_taker = selectors.get_caretaker_user()
    if care_taker is None:
        raise BookingError("No VhCaretaker designation found")

    booking_obj = BookingDetail.objects.create(
        caretaker=care_taker,
        purpose=purpose,
        intender=intender_user,
        booking_from=booking_from,
        booking_to=booking_to,
        visitor_category=category,
        person_count=person_count,
        arrival_time=arrival_time,
        departure_time=departure_time,
        number_of_rooms=number_of_rooms,
        bill_to_be_settled_by=bill_to_be_settled_by,
    )
    return booking_obj


def create_booking_with_visitor(intender_user, booking_data, visitor_data, uploaded_file=None):
    """T-02: Unified booking+visitor creation — replaces duplicated blocks in views and api/views.

    Args:
        intender_user: User instance for the intender.
        booking_data:  dict with keys matching create_booking kwargs.
        visitor_data:  dict with keys matching create_visitor kwargs.
        uploaded_file: optional uploaded file for attachment.

    Returns:
        The created BookingDetail instance.
    """
    booking = create_booking(
        intender_user=intender_user,
        category=booking_data.get('category'),
        person_count=booking_data.get('person_count'),
        purpose=booking_data.get('purpose'),
        booking_from=booking_data.get('booking_from'),
        booking_to=booking_data.get('booking_to'),
        arrival_time=booking_data.get('arrival_time', ''),
        departure_time=booking_data.get('departure_time', ''),
        number_of_rooms=booking_data.get('number_of_rooms'),
        bill_to_be_settled_by=booking_data.get('bill_to_be_settled_by'),
    )
    handle_booking_attachment(booking, uploaded_file)
    visitor = create_visitor(**visitor_data)
    booking.visitor.add(visitor)
    booking.save()
    return booking


def handle_booking_attachment(booking_obj, uploaded_file):
    """V-06, V-43, V-44: Fixed file upload — uses os.makedirs instead of shell command."""
    if uploaded_file is None:
        return
    from Fusion import settings
    try:
        filename, file_extension = os.path.splitext(uploaded_file.name)
        full_path = os.path.join(settings.MEDIA_ROOT, "VhImage")
        os.makedirs(full_path, exist_ok=True)
        from django.core.files.storage import FileSystemStorage
        url = settings.MEDIA_URL + filename + file_extension
        fs = FileSystemStorage(full_path, url)
        fs.save(filename + file_extension, uploaded_file)
        uploaded_file_url = "/media/online_cms/" + filename + file_extension
        booking_obj.image = uploaded_file_url
        booking_obj.save()
    except Exception as e:
        logger.error(f"Error handling booking attachment: {e}")


def update_booking(booking_id, person_count, number_of_rooms, booking_from,
                   booking_to, purpose):
    """V-07: Business logic extracted from update_booking view.
    T-10a: Simplified person_count guard — uses 'or 1' instead of if/else.
    """
    booking = selectors.get_booking_by_id(booking_id)
    booking.person_count = person_count or 1  # T-10a: model clean() enforces >= 1
    booking.number_of_rooms = number_of_rooms
    booking.booking_from = booking_from
    booking.booking_to = booking_to
    booking.purpose = purpose
    booking.save()
    return booking


def confirm_booking(booking_id, rooms_list, category, requesting_user):
    """V-08: Extracted from confirm_booking view."""
    bd = selectors.get_booking_by_id(booking_id)
    bd.status = 'Confirmed'
    bd.category = category
    bd.save()
    assign_rooms_to_booking(bd, rooms_list)
    send_vh_notification(requesting_user, bd.intender, 'booking_confirmation')  # T-11b
    return bd


def cancel_booking(booking_id, remark, charges, caretaker_user):
    """V-09: Extracted from cancel_booking view.
    T-06: Uses _update_booking_status helper.
    T-24: Renamed x → zero_meal_bill.
    T-30b: Standardised create_bill call with keyword args.
    """
    _update_booking_status(booking_id, 'Canceled', remark)  # T-06
    booking = selectors.get_booking_by_id(booking_id)
    zero_meal_bill = 0  # T-24: renamed from x
    create_bill(
        booking,
        meal_bill=zero_meal_bill,
        room_bill=int(charges) if charges else zero_meal_bill,  # T-30b
        caretaker=caretaker_user,
    )
    send_vh_notification(caretaker_user, booking.intender, 'booking_cancellation_request_accepted')
    return booking


def request_cancel_booking(booking_id, remark, requesting_user):
    """Extracted from cancel_booking_request view. T-06: Uses _update_booking_status."""
    _update_booking_status(booking_id, 'CancelRequested', remark)  # T-06
    incharge = selectors.get_incharge_user()
    send_vh_notification(requesting_user, incharge, 'cancellation_request_placed')  # T-11b (None guard in adapter)


def reject_booking(booking_id, remark):
    """Extracted from reject_booking view. T-06: Uses _update_booking_status."""
    _update_booking_status(booking_id, 'Rejected', remark)  # T-06


def check_in_visitor(booking_id, visitor_name, visitor_phone, visitor_email='',
                     visitor_address=''):
    """Extracted from check_in view."""
    visitor = create_visitor(
        visitor_name=visitor_name,
        visitor_phone=visitor_phone,
        visitor_email=visitor_email,
        visitor_address=visitor_address,
    )
    bd = selectors.get_booking_by_id(booking_id)
    bd.status = "CheckedIn"
    bd.check_in = datetime.date.today()
    bd.visitor.add(visitor)
    bd.save()
    return bd


def check_out_booking(booking_id, meal_bill, room_bill, caretaker_user):
    """V-10: Extracted from check_out view."""
    checkout_date = datetime.date.today()
    BookingDetail.objects.select_related('intender', 'caretaker').filter(
        id=booking_id
    ).update(check_out=datetime.datetime.today(), status="Complete")
    booking = selectors.get_booking_by_id(booking_id)
    create_bill(booking, meal_bill, room_bill, caretaker_user,
                payment_status=True, bill_date=checkout_date)
    return booking


def forward_booking(booking_id, modified_category, rooms_list, remark, requesting_user):
    """V-13: Extracted from forward_booking view. T-06: Uses _update_booking_status."""
    _update_booking_status(booking_id, 'Forward', remark)  # T-06
    bd = selectors.get_booking_by_id(booking_id)
    bd.modified_visitor_category = modified_category
    bd.save()
    assign_rooms_to_booking(bd, rooms_list)
    incharge = selectors.get_incharge_user()
    send_vh_notification(requesting_user, incharge, 'booking_forwarded')  # T-11b
    return bd


# === Meal Recording ==============================================================

def record_meal(booking_id, visitor_id, m_tea, breakfast, lunch, eve_tea, dinner):
    """V-11, V-28: Extracted from record_meal view."""
    booking = selectors.get_booking_by_id(booking_id)
    visitor = selectors.get_visitor_by_id(visitor_id)
    date_1 = datetime.datetime.today()
    person = 1

    meal = selectors.get_meal_record_for_visitor_date(visitor, booking, date_1)

    if meal:
        meal.morning_tea += int(m_tea)
        meal.eve_tea += int(eve_tea)
        meal.breakfast += int(breakfast)
        meal.lunch += int(lunch)
        meal.dinner += int(dinner)
        meal.save()
    else:
        MealRecord.objects.create(
            visitor=visitor,
            booking=booking,
            morning_tea=m_tea,
            eve_tea=eve_tea,
            meal_date=date_1,
            breakfast=breakfast,
            lunch=lunch,
            dinner=dinner,
            persons=person,
        )


# === Billing =====================================================================

# T-16: Named field map and cost helper replace repeated if-guards in calculate_mess_bill.
MEAL_FIELD_MAP = [
    ('morning_tea', 'morning_tea'),
    ('eve_tea', 'eve_tea'),
    ('breakfast', 'breakfast'),
    ('lunch', 'lunch'),
    ('dinner', 'dinner'),
]


def _meal_cost(meal_record):
    """T-16: Compute the cost of a single MealRecord using MEAL_RATES."""
    return sum(
        getattr(meal_record, field) * MEAL_RATES[rate_key]
        for rate_key, field in MEAL_FIELD_MAP
    )


def calculate_room_bill(booking):
    """V-14: Uses ROOM_RATES constants.
    T-19: Guard-clause refactor — early returns first.
    """
    # T-19: Guard clauses at top
    category = booking.visitor_category
    if category == 'A':
        return 0

    days = (datetime.date.today() - booking.check_in).days
    if days == 0:
        days = 1

    rooms = booking.rooms.all()
    room_bill = ROOM_BILL_BASE
    category_rates = ROOM_RATES.get(category, ROOM_RATES['D'])
    for room in rooms:
        rate = category_rates.get(room.room_type, category_rates.get('DoubleBed', 500))
        room_bill += days * rate
    return room_bill


def calculate_mess_bill(booking):
    """T-12: Uses prefetched mealrecord_set (no per-visitor N+1 query).
    T-16: Uses _meal_cost() helper — no repeated if-guards.
    """
    meals = booking.mealrecord_set.all()  # T-12: prefetched by caller
    return sum(_meal_cost(m) for m in meals)


def calculate_active_bills(active_bookings):
    """V-05: Calculate bills for all checked-in bookings."""
    bills = {}
    for booking in active_bookings:
        if booking.status == 'CheckedIn':
            room_bill = calculate_room_bill(booking)
            mess_bill = calculate_mess_bill(booking)
            total_bill = mess_bill + room_bill
            bills[booking.id] = {
                'mess_bill': mess_bill,
                'room_bill': room_bill,
                'total_bill': total_bill,
            }
    return bills


def _build_bill_entry(bill):
    """T-17: Private helper — extracts dict construction out of calculate_current_balance.
    T-22b: Delegates to Bill.to_summary_dict() (feature envy fix).
    """
    return bill.to_summary_dict()


def calculate_current_balance():
    """V-05: Extract balance calculation from dashboard view.
    T-17: Uses _build_bill_entry() helper — method body shortened.
    """
    all_bills = selectors.get_all_bills()
    inventory_bills = selectors.get_all_inventory_bills()

    completed_booking_bills = {
        bill.id: _build_bill_entry(bill)   # T-17, T-22b
        for bill in all_bills
    }
    bill_total = sum(bill.meal_bill + bill.room_bill for bill in all_bills)
    current_balance = bill_total - sum(inv_bill.cost for inv_bill in inventory_bills)

    return completed_booking_bills, current_balance


# === Visitor / Room Counts for Dashboard =========================================

def get_visitor_and_room_counts(active_bookings):
    """R-02: Consolidated visitor and room iteration."""
    visitors = {}
    rooms = {}
    for booking in active_bookings:
        visitors[booking.id] = range(2, booking.person_count + 1)
        for room_no in booking.rooms.all():
            rooms[booking.id] = range(2, booking.number_of_rooms_alloted + 1)
    return visitors, rooms


def get_active_visitor_map(active_bookings):
    """Map booking_id → first visitor for checked-in bookings."""
    active_visitors = {}
    for booking in active_bookings:
        if booking.status == 'CheckedIn':
            for visitor in booking.visitor.all():
                active_visitors[booking.id] = visitor
    return active_visitors


def get_visitor_list_from_dashboard(dashboard_bookings):
    """T-23b: Delegates to selectors.get_first_visitor_per_booking (misplaced logic fix)."""
    return selectors.get_first_visitor_per_booking(dashboard_bookings)


# === Room Availability ===========================================================

def _build_booking_to_result_map(bookings, selector_fn):
    """T-21: Generic helper — builds {booking.id: result} map from a selector function.
    Replaces the near-duplicate compute_room_availability and compute_forwarded_rooms.
    """
    return {booking.id: selector_fn(booking.booking_from, booking.booking_to)
            for booking in bookings}


def compute_room_availability(pending_bookings):
    """R-04: Compute available rooms for each pending booking. T-21: Uses generic helper."""
    return _build_booking_to_result_map(pending_bookings, selectors.get_available_rooms)


def compute_forwarded_rooms(forwarded_bookings):
    """R-04: Compute forwarded rooms for forwarded bookings. T-21: Uses generic helper."""
    return _build_booking_to_result_map(forwarded_bookings, selectors.get_forwarded_booking_rooms)


# === Dashboard Data ==============================================================

def get_dashboard_data(user, role):
    """T-03: Centralised dashboard data assembly — replaces duplicated if/else blocks
    in views.py:visitorhostel and api/views.py:DashboardView.
    Returns a plain dict with all selector results.
    """
    available_rooms = {}
    forwarded_rooms = {}
    cancel_booking_request = []

    if role == "Intender":
        pending_bookings = selectors.get_pending_bookings_for_intender(user)
        active_bookings = selectors.get_active_bookings_for_intender(user)
        dashboard_bookings = selectors.get_dashboard_bookings_for_intender(user)
        complete_bookings = selectors.get_complete_bookings_for_intender(user)
        canceled_bookings = selectors.get_canceled_bookings_for_intender(user)
        rejected_bookings = selectors.get_rejected_bookings_for_intender(user)
        cancel_booking_requested = selectors.get_cancel_requested_bookings_for_intender(user)
    else:
        pending_bookings = selectors.get_pending_bookings_all()
        active_bookings = selectors.get_active_bookings_all()
        dashboard_bookings = selectors.get_dashboard_bookings_all()
        cancel_booking_request = selectors.get_cancel_requests_all()
        complete_bookings = selectors.get_complete_bookings_all()
        canceled_bookings = selectors.get_canceled_bookings_all()
        rejected_bookings = selectors.get_rejected_bookings_all()
        cancel_booking_requested = selectors.get_cancel_requested_for_intender(user)
        c_bookings = selectors.get_forwarded_bookings()
        available_rooms = compute_room_availability(pending_bookings)
        forwarded_rooms = compute_forwarded_rooms(c_bookings)

    return {
        'pending_bookings': pending_bookings,
        'active_bookings': active_bookings,
        'dashboard_bookings': dashboard_bookings,
        'complete_bookings': complete_bookings,
        'canceled_bookings': canceled_bookings,
        'rejected_bookings': rejected_bookings,
        'cancel_booking_request': cancel_booking_request,
        'cancel_booking_requested': cancel_booking_requested,
        'available_rooms': available_rooms,
        'forwarded_rooms': forwarded_rooms,
    }


# === Bill Report =================================================================

def get_bill_report(date1, date2):
    """Extracted from bill_between_dates view."""
    bills = selectors.get_bills_for_date_range(date1, date2)
    meal_total = 0
    room_total = 0
    individual_total = []

    for bill in bills:
        meal_total += bill.meal_bill
        room_total += bill.room_bill
        individual_total.append(bill.meal_bill + bill.room_bill)

    total_bill = meal_total + room_total
    return bills, meal_total, room_total, total_bill, individual_total


# === Inventory Management ========================================================

def add_inventory_item(item_name, quantity, cost, bill_number, consumable):
    """Extracted from add_to_inventory view."""
    is_consumable = consumable != 'false'
    item = Inventory.objects.create(
        item_name=item_name, quantity=int(quantity), consumable=is_consumable
    )
    InventoryBill.objects.create(
        bill_number=bill_number, cost=int(cost), item_name=item
    )
    return item


def update_inventory_item(item_id, quantity):
    """Extracted from update_inventory view.
    T-30b: Routes ORM mutations through selector layer.
    """
    quantity = int(quantity)
    if quantity < 0:
        quantity = 1
    if quantity == 0:
        selectors.delete_inventory_item(item_id)  # T-30b
    else:
        selectors.update_inventory_quantity(item_id, quantity)  # T-30b


# === Room Status =================================================================

def edit_room_status(room_number, room_status):
    """Extracted from edit_room_status view."""
    room = selectors.get_room_by_number(room_number)
    RoomDetail.objects.filter(id=room.id).update(room_status=room_status)
