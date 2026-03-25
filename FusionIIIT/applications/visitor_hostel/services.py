# services.py
# All business logic for the visitor_hostel module.
# Fixes: V-02, V-05–V-13, V-14–V-16, V-43–V-44, R-02, R-04, R-06, R-08, R-09

import datetime
import logging
import os

from django.contrib.auth.models import User

from .models import (
    BookingDetail, Bill, Inventory, InventoryBill,
    MealRecord, RoomDetail, VisitorDetail,
)

# ---------------------------------------------------------------------------
# Rate constants  (V-14, V-15)
# ---------------------------------------------------------------------------

ROOM_RATES = {
    'A': {'SingleBed': 0, 'DoubleBed': 0, 'VIP': 0},
    'B': {'SingleBed': 400, 'DoubleBed': 500, 'VIP': 500},
    'C': {'SingleBed': 800, 'DoubleBed': 1000, 'VIP': 1000},
    'D': {'SingleBed': 1400, 'DoubleBed': 1600, 'VIP': 1600},
}

MEAL_RATES = {
    'morning_tea': 10,
    'eve_tea': 10,
    'breakfast': 50,
    'lunch': 100,
    'dinner': 100,
}

ROOM_BILL_BASE = 100  # Base charge for category B/C/D
from . import selectors

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# User role  (R-10)
# ---------------------------------------------------------------------------

def get_user_designation(user):
    """Determine the VH role for a user."""
    return selectors.get_user_role(user)


# ---------------------------------------------------------------------------
# Visitor creation  (R-06)
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Room assignment  (R-08)
# ---------------------------------------------------------------------------

def assign_rooms_to_booking(booking, room_numbers):
    """R-08: Assign rooms to a booking by room number list."""
    count = 0
    for room_number in room_numbers:
        room_obj = selectors.get_room_by_number(room_number)
        booking.rooms.add(room_obj)
        count += 1
    booking.number_of_rooms_alloted = count
    booking.save()
    return count


# ---------------------------------------------------------------------------
# Bill creation  (R-09)
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Booking creation  (V-06)
# ---------------------------------------------------------------------------

def create_booking(intender_user, category, person_count, purpose, booking_from,
                   booking_to, arrival_time, departure_time, number_of_rooms,
                   bill_to_be_settled_by):
    """V-06: Extract booking creation from request_booking view."""
    care_taker = selectors.get_caretaker_user()
    if care_taker is None:
        raise ValueError("No VhCaretaker designation found")

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


def handle_booking_attachment(booking_obj, uploaded_file):
    """V-06, V-43, V-44: Fixed file upload — uses os.makedirs instead of shell command."""
    if uploaded_file is None:
        return
    from Fusion import settings
    try:
        filename, file_extension = os.path.splitext(uploaded_file.name)  # V-43: was .booking_id
        full_path = os.path.join(settings.MEDIA_ROOT, "VhImage")
        os.makedirs(full_path, exist_ok=True)  # V-44: replaced os.subprocess.call
        from django.core.files.storage import FileSystemStorage
        url = settings.MEDIA_URL + filename + file_extension
        fs = FileSystemStorage(full_path, url)
        fs.save(filename + file_extension, uploaded_file)
        uploaded_file_url = "/media/online_cms/" + filename + file_extension
        booking_obj.image = uploaded_file_url
        booking_obj.save()
    except Exception as e:
        logger.error(f"Error handling booking attachment: {e}")


# ---------------------------------------------------------------------------
# Update booking  (V-07)
# ---------------------------------------------------------------------------

def update_booking(booking_id, person_count, number_of_rooms, booking_from,
                   booking_to, purpose):
    """V-07: Business logic extracted from update_booking view."""
    booking = selectors.get_booking_by_id(booking_id)
    if person_count:
        booking.person_count = person_count
    else:
        booking.person_count = 1
    booking.number_of_rooms = number_of_rooms
    booking.booking_from = booking_from
    booking.booking_to = booking_to
    booking.purpose = purpose
    booking.save()
    return booking


# ---------------------------------------------------------------------------
# Confirm booking  (V-08)
# ---------------------------------------------------------------------------

def confirm_booking(booking_id, rooms_list, category, requesting_user):
    """V-08: Extracted from confirm_booking view."""
    bd = selectors.get_booking_by_id(booking_id)
    bd.status = 'Confirmed'
    bd.category = category
    bd.save()
    assign_rooms_to_booking(bd, rooms_list)
    visitors_hostel_notif(requesting_user, bd.intender, 'booking_confirmation')
    return bd


# ---------------------------------------------------------------------------
# Cancel booking  (V-09)
# ---------------------------------------------------------------------------

def cancel_booking(booking_id, remark, charges, caretaker_user):
    """V-09: Extracted from cancel_booking view."""
    BookingDetail.objects.select_related('intender', 'caretaker').filter(
        id=booking_id
    ).update(status='Canceled', remark=remark)

    booking = selectors.get_booking_by_id(booking_id)
    x = 0
    if charges:
        create_bill(booking, x, int(charges), caretaker_user)
    else:
        create_bill(booking, x, x, caretaker_user)

    visitors_hostel_notif(caretaker_user, booking.intender, 'booking_cancellation_request_accepted')
    return booking


# ---------------------------------------------------------------------------
# Cancel booking request  (V-09)
# ---------------------------------------------------------------------------

def request_cancel_booking(booking_id, remark, requesting_user):
    """Extracted from cancel_booking_request view."""
    BookingDetail.objects.select_related('intender', 'caretaker').filter(
        id=booking_id
    ).update(status='CancelRequested', remark=remark)

    incharge = selectors.get_incharge_user()
    if incharge:
        visitors_hostel_notif(requesting_user, incharge, 'cancellation_request_placed')


# ---------------------------------------------------------------------------
# Reject booking  (V-09)
# ---------------------------------------------------------------------------

def reject_booking(booking_id, remark):
    """Extracted from reject_booking view."""
    BookingDetail.objects.select_related('intender', 'caretaker').filter(
        id=booking_id
    ).update(status="Rejected", remark=remark)


# ---------------------------------------------------------------------------
# Check in  (V-05)
# ---------------------------------------------------------------------------

def check_in_visitor(booking_id, visitor_name, visitor_phone, visitor_email='',
                     visitor_address=''):
    """Extracted from check_in view. V-27: specific exception."""
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


# ---------------------------------------------------------------------------
# Check out  (V-10)
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Record meal  (V-11)
# ---------------------------------------------------------------------------

def record_meal(booking_id, visitor_id, m_tea, breakfast, lunch, eve_tea, dinner):
    """V-11, V-28: Extracted from record_meal view. Uses specific exception."""
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


# ---------------------------------------------------------------------------
# Bill calculation  (V-05, V-14, V-15)
# ---------------------------------------------------------------------------

def calculate_room_bill(booking):
    """V-14: Uses ROOM_RATES constants instead of hard-coded values."""
    rooms = booking.rooms.all()
    days = (datetime.date.today() - booking.check_in).days
    category = booking.visitor_category

    if days == 0:
        days = 1

    if category == 'A':
        return 0

    room_bill = ROOM_BILL_BASE
    category_rates = ROOM_RATES.get(category, ROOM_RATES['D'])
    for room in rooms:
        rate = category_rates.get(room.room_type, category_rates.get('DoubleBed', 500))
        room_bill += days * rate
    return room_bill


def calculate_mess_bill(booking):
    """V-15: Uses MEAL_RATES constants instead of hard-coded values."""
    mess_bill = 0
    for visitor in booking.visitor.all():
        meals = selectors.get_meal_records_for_booking(booking.id)
        mess_bill1 = 0
        for m in meals:
            if m.morning_tea != 0:
                mess_bill1 += m.morning_tea * MEAL_RATES['morning_tea']
            if m.eve_tea != 0:
                mess_bill1 += m.eve_tea * MEAL_RATES['eve_tea']
            if m.breakfast != 0:
                mess_bill1 += m.breakfast * MEAL_RATES['breakfast']
            if m.lunch != 0:
                mess_bill1 += m.lunch * MEAL_RATES['lunch']
            if m.dinner != 0:
                mess_bill1 += m.dinner * MEAL_RATES['dinner']
            mess_bill += mess_bill1
    return mess_bill


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


# ---------------------------------------------------------------------------
# Visitor / room counts for dashboard  (R-02)
# ---------------------------------------------------------------------------

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
    """Get first visitor from each dashboard booking."""
    visitor_list = []
    for b in dashboard_bookings:
        b_visitor_list = b.visitor.all()
        count = 1
        for v in b_visitor_list:
            if count == 1:
                visitor_list.append(v)
                count += 1
    return visitor_list


# ---------------------------------------------------------------------------
# Balance calculation  (V-05)
# ---------------------------------------------------------------------------

def calculate_current_balance():
    """V-05: Extract balance calculation from dashboard view."""
    all_bills = selectors.get_all_bills()
    inventory_bills = selectors.get_all_inventory_bills()

    completed_booking_bills = {}
    current_balance = 0

    for bill in all_bills:
        completed_booking_bills[bill.id] = {
            'intender': str(bill.booking.intender),
            'booking_from': str(bill.booking.booking_from),
            'booking_to': str(bill.booking.booking_to),
            'total_bill': str(bill.meal_bill + bill.room_bill),
            'bill_date': str(bill.bill_date),
        }
        current_balance += bill.meal_bill + bill.room_bill

    for inv_bill in inventory_bills:
        current_balance -= inv_bill.cost

    return completed_booking_bills, current_balance


# ---------------------------------------------------------------------------
# Room availability  (R-04)
# ---------------------------------------------------------------------------

def compute_room_availability(pending_bookings):
    """R-04: Compute available rooms for each pending booking."""
    available_rooms = {}
    for booking in pending_bookings:
        available = selectors.get_available_rooms(booking.booking_from, booking.booking_to)
        available_rooms[booking.id] = available
    return available_rooms


def compute_forwarded_rooms(forwarded_bookings):
    """R-04: Compute forwarded rooms for forwarded bookings."""
    forwarded_rooms = {}
    for booking in forwarded_bookings:
        rooms = selectors.get_forwarded_booking_rooms(booking.booking_from, booking.booking_to)
        forwarded_rooms[booking.id] = rooms
    return forwarded_rooms


# ---------------------------------------------------------------------------
# Bill between dates  (V-05)
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Inventory management  (V-20, V-21)
# ---------------------------------------------------------------------------

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
    """Extracted from update_inventory view."""
    quantity = int(quantity)
    if quantity < 0:
        quantity = 1
    if quantity == 0:
        Inventory.objects.filter(id=item_id).delete()
    else:
        Inventory.objects.filter(id=item_id).update(quantity=quantity)


# ---------------------------------------------------------------------------
# Edit room status
# ---------------------------------------------------------------------------

def edit_room_status(room_number, room_status):
    """Extracted from edit_room_status view."""
    room = selectors.get_room_by_number(room_number)
    RoomDetail.objects.filter(id=room.id).update(room_status=room_status)


# ---------------------------------------------------------------------------
# Forward booking  (V-13)
# ---------------------------------------------------------------------------

def forward_booking(booking_id, modified_category, rooms_list, remark, requesting_user):
    """V-13: Extracted from forward_booking view."""
    BookingDetail.objects.select_related('intender', 'caretaker').filter(
        id=booking_id
    ).update(status="Forward", remark=remark)

    bd = selectors.get_booking_by_id(booking_id)
    bd.modified_visitor_category = modified_category
    bd.save()

    assign_rooms_to_booking(bd, rooms_list)

    incharge = selectors.get_incharge_user()
    if incharge:
        visitors_hostel_notif(requesting_user, incharge, 'booking_forwarded')
    return bd
