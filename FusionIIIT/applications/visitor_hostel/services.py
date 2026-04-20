import datetime
from collections import defaultdict

from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Q

from applications.globals.models import HoldsDesignation
from notification.views import visitors_hostel_notif

from .models import Bill, BookingDetail, Inventory, InventoryBill, MealRecord, VisitorDetail
from .selectors import (
    CARETAKER_ROLE,
    INCHARGE_ROLE,
    get_available_rooms_between,
    get_bills_queryset,
    get_booking_detail,
    get_booking_range_bills,
    get_dashboard_base_queryset,
    get_forwarded_booking_rooms_between,
    get_inventory_bills_queryset,
    get_inventory_queryset,
    get_meal_records_for_bookings,
    get_room_by_number,
    get_user_designation,
)


ROLE_NAMES = {
    "student": "student",
    CARETAKER_ROLE: CARETAKER_ROLE,
    INCHARGE_ROLE: INCHARGE_ROLE,
}
VISITOR_COSTS = {"A": 0, "B": 500, "C": 800, "D": 1400}
ROOM_RATE_CARD = {
    "B": {"SingleBed": 400, "DoubleBed": 500, "VIP": 500},
    "C": {"SingleBed": 800, "DoubleBed": 1000, "VIP": 1000},
    "D": {"SingleBed": 1400, "DoubleBed": 1600, "VIP": 1600},
}
MEAL_RATE_CARD = {
    "morning_tea": 10,
    "eve_tea": 10,
    "breakfast": 50,
    "lunch": 100,
    "dinner": 100,
}


def _get_designation_holder(designation_name, index=0):
    designations = HoldsDesignation.objects.select_related("user", "working", "designation").filter(
        designation__name=designation_name,
    )
    if not designations.exists():
        return None
    ordered_designations = list(designations)
    if index < len(ordered_designations):
        return ordered_designations[index]
    return ordered_designations[0]


def get_designation_user(designation_name, index=0):
    holder = _get_designation_holder(designation_name, index=index)
    return holder.user if holder else None


def create_booking_request(validated_data, user):
    care_taker_user = get_designation_user(CARETAKER_ROLE)
    if not care_taker_user:
        raise ValueError("Caretaker not found")

    visitor = VisitorDetail.objects.create(
        visitor_name=validated_data["visitor_name"],
        visitor_email=validated_data.get("visitor_email", ""),
        visitor_phone=validated_data["visitor_phone"],
        visitor_organization=validated_data.get("visitor_organization", ""),
        visitor_address=validated_data.get("visitor_address", ""),
        nationality=validated_data.get("nationality", ""),
    )

    booking = BookingDetail.objects.create(
        caretaker=care_taker_user,
        purpose=validated_data["purpose_of_visit"],
        intender=user,
        booking_from=validated_data["booking_from"],
        booking_to=validated_data["booking_to"],
        visitor_category=validated_data["category"],
        modified_visitor_category=validated_data["category"],
        person_count=validated_data["person_count"],
        arrival_time=validated_data.get("booking_from_time"),
        departure_time=validated_data.get("booking_to_time"),
        number_of_rooms=validated_data["number_of_rooms"],
        bill_to_be_settled_by=validated_data["bill_to_be_settled_by"],
        remark=validated_data.get("remarks_during_booking_request"),
    )
    booking.visitor.set([visitor])
    return booking


def update_expired_pending_bookings(current_date=None):
    current_date = current_date or datetime.date.today()
    return BookingDetail.objects.filter(status="Pending", booking_to__lt=current_date).update(status="Expired")


def assign_rooms_to_booking(booking, rooms, clear_existing=True):
    if clear_existing:
        booking.rooms.clear()
    for room in rooms:
        room_object = get_room_by_number(room)
        booking.rooms.add(room_object)
    booking.number_of_rooms_alloted = len(rooms)
    booking.save()
    return booking


def forward_booking(booking_id, modified_category, rooms, remarks, request_user, notify_index=0):
    booking = get_booking_detail(booking_id)
    booking.status = "Forward"
    booking.modified_visitor_category = modified_category
    booking.remark = remarks
    booking.save()
    assign_rooms_to_booking(booking, rooms, clear_existing=True)

    incharge_user = get_designation_user(INCHARGE_ROLE, index=notify_index)
    if not incharge_user:
        raise ValueError("VhIncharge not found")
    visitors_hostel_notif(request_user, incharge_user, "booking_forwarded")
    return booking


def confirm_booking(booking_id, modified_category, rooms, remarks, action, request_user):
    booking = get_booking_detail(booking_id)
    if action == "accept":
        booking.status = "Confirmed"
    elif action == "reject":
        booking.status = "Rejected"
    booking.modified_visitor_category = modified_category
    booking.remark = remarks
    booking.save()
    assign_rooms_to_booking(booking, rooms, clear_existing=True)
    notification_name = "booking_confirmation" if action == "accept" else "booking_rejection"
    visitors_hostel_notif(request_user, booking.intender, notification_name)
    return booking


def update_booking_details(booking_id, validated_data, request_user):
    booking = get_booking_detail(booking_id)
    booking.modified_visitor_category = validated_data["modified_category"]
    booking.remark = validated_data.get("remarks")
    booking.bill_to_be_settled_by = validated_data.get("bill_to_be_settled_by")
    booking.purpose = validated_data.get("purpose")
    booking.number_of_rooms = validated_data.get("number_of_rooms")
    booking.person_count = validated_data.get("person_count")

    for visitor in booking.visitor.all():
        visitor.visitor_organization = validated_data["visitor_organization"]
        visitor.visitor_phone = validated_data["visitor_phone"]
        visitor.visitor_email = validated_data["visitor_email"]
        visitor.visitor_name = validated_data["visitor_name"]
        visitor.visitor_address = validated_data["visitor_address"]
        visitor.save()

    booking.save()
    assign_rooms_to_booking(booking, validated_data.get("rooms", []), clear_existing=True)

    incharge_user = get_designation_user(INCHARGE_ROLE)
    if not incharge_user:
        raise ValueError("VhIncharge not found")
    visitors_hostel_notif(request_user, incharge_user, "booking_forwarded")
    return booking


def update_inventory_item(inventory_id, quantity):
    if quantity < 0:
        quantity = 1
    if quantity == 0:
        Inventory.objects.filter(id=inventory_id).delete()
        return None
    Inventory.objects.filter(id=inventory_id).update(quantity=quantity)
    return Inventory.objects.filter(id=inventory_id).first()


def add_inventory_item_and_bill(validated_data):
    item_name = validated_data["item_name"]
    quantity = int(validated_data["quantity"])
    consumable = validated_data.get("consumable", False)
    bill_number = validated_data["bill_number"]
    cost = int(validated_data["cost"])

    inventory_item = Inventory.objects.filter(item_name=item_name).first()
    if inventory_item:
        inventory_item.quantity = quantity
        inventory_item.consumable = consumable
        inventory_item.save()
    else:
        inventory_item = Inventory.objects.create(
            item_name=item_name,
            quantity=quantity,
            consumable=consumable,
        )

    InventoryBill.objects.create(
        item_name=inventory_item,
        bill_number=bill_number,
        cost=cost,
    )
    return inventory_item


def add_checkout_inventory_items(booking_id, inventory_items):
    for item in inventory_items:
        item_name = item.get("name")
        quantity = int(item.get("quantity", 0))
        cost = int(item.get("cost", 0))
        inventory_item = Inventory.objects.filter(item_name=item_name).first()
        if inventory_item:
            inventory_item.quantity += quantity
            inventory_item.save()
        else:
            inventory_item = Inventory.objects.create(
                item_name=item_name,
                quantity=quantity,
                consumable=True,
                total_usable=cost,
            )
        InventoryBill.objects.create(
            item_name=inventory_item,
            bill_number=f"INV-{booking_id}-{item_name[:3].upper()}",
            cost=cost,
        )


def check_in_booking(booking_id, validated_data):
    visitor = VisitorDetail.objects.create(
        visitor_phone=validated_data["visitor_phone"],
        visitor_name=validated_data["visitor_name"],
        visitor_email=validated_data.get("visitor_email", ""),
        visitor_address=validated_data.get("visitor_address", ""),
    )
    booking = get_booking_detail(booking_id)
    booking.status = "CheckedIn"
    booking.check_in = datetime.date.today()
    booking.check_in_time = validated_data.get("check_in_time")
    booking.visitor.add(visitor)
    booking.save()
    return booking


def check_out_booking(booking_id, check_out_time):
    booking = get_booking_detail(booking_id)
    booking.status = "Complete"
    booking.check_out = datetime.date.today()
    booking.check_out_time = check_out_time
    booking.save()
    return booking


def record_meal_for_visitor(booking_id, visitor_id, meal_payload):
    booking = get_booking_detail(booking_id)
    visitor = VisitorDetail.objects.get(id=visitor_id)
    meal_date = datetime.datetime.today()
    try:
        meal = MealRecord.objects.select_related("booking__intender", "booking__caretaker", "visitor").get(
            visitor=visitor,
            booking=booking,
            meal_date=meal_date,
        )
    except MealRecord.DoesNotExist:
        meal = None

    if meal:
        meal.morning_tea += int(meal_payload.get("m_tea", 0))
        meal.eve_tea += int(meal_payload.get("eve_tea", 0))
        meal.breakfast += int(meal_payload.get("breakfast", 0))
        meal.lunch += int(meal_payload.get("lunch", 0))
        meal.dinner += int(meal_payload.get("dinner", 0))
        meal.save()
        return meal

    return MealRecord.objects.create(
        visitor=visitor,
        booking=booking,
        morning_tea=meal_payload.get("m_tea", 0),
        eve_tea=meal_payload.get("eve_tea", 0),
        meal_date=meal_date,
        breakfast=meal_payload.get("breakfast", 0),
        lunch=meal_payload.get("lunch", 0),
        dinner=meal_payload.get("dinner", 0),
        persons=1,
    )


def get_bill_between_dates(date1, date2):
    return get_booking_range_bills(date1, date2)


def calculate_room_bill_for_dashboard(booking):
    if booking.status != "CheckedIn":
        return 0

    rooms = list(booking.rooms.all())
    days = (datetime.date.today() - booking.check_in).days
    if days == 0:
        days = 1

    category = booking.visitor_category
    if category == "A":
        return 0

    room_bill = 100
    if category in ROOM_RATE_CARD:
        for room in rooms:
            room_bill += days * ROOM_RATE_CARD[category].get(room.room_type, ROOM_RATE_CARD[category]["DoubleBed"])
    return room_bill


def calculate_meal_bill_for_dashboard(booking, meal_records):
    mess_bill = 0
    for _visitor in booking.visitor.all():
        mess_bill1 = 0
        for meal in meal_records:
            mess_bill1 += int(meal.morning_tea) * MEAL_RATE_CARD["morning_tea"]
            mess_bill1 += int(meal.eve_tea) * MEAL_RATE_CARD["eve_tea"]
            mess_bill1 += int(meal.breakfast) * MEAL_RATE_CARD["breakfast"]
            mess_bill1 += int(meal.lunch) * MEAL_RATE_CARD["lunch"]
            mess_bill1 += int(meal.dinner) * MEAL_RATE_CARD["dinner"]
            mess_bill += mess_bill1
    return mess_bill


def build_dashboard_context(user):
    intenders = User.objects.all()
    user_designation = get_user_designation(user)
    available_rooms = {}
    forwarded_rooms = {}
    cancel_booking_request = []

    if user_designation == "Intender":
        all_bookings = get_dashboard_base_queryset().all().order_by("booking_from")
        pending_bookings = get_dashboard_base_queryset().filter(
            Q(status="Pending") | Q(status="Forward"),
            booking_to__gte=datetime.datetime.today(),
            intender=user,
        ).order_by("booking_from")
        active_bookings = get_dashboard_base_queryset().filter(
            status="CheckedIn",
            booking_to__gte=datetime.datetime.today(),
            intender=user,
        ).order_by("booking_from")
        dashboard_bookings = get_dashboard_base_queryset().filter(
            Q(status="Pending") | Q(status="Forward") | Q(status="Confirmed") | Q(status="Rejected"),
            booking_to__gte=datetime.datetime.today(),
            intender=user,
        ).order_by("booking_from")
        complete_bookings = get_dashboard_base_queryset().filter(
            check_out__lt=datetime.datetime.today(),
            intender=user,
        ).order_by("booking_from").reverse()
        canceled_bookings = get_dashboard_base_queryset().filter(status="Canceled", intender=user).order_by("booking_from")
        rejected_bookings = get_dashboard_base_queryset().filter(status="Rejected", intender=user).order_by("booking_from")
        cancel_booking_requested = get_dashboard_base_queryset().filter(
            status="CancelRequested",
            intender=user,
        ).order_by("booking_from")
    else:
        all_bookings = get_dashboard_base_queryset().all().order_by("booking_from")
        pending_bookings = get_dashboard_base_queryset().filter(
            Q(status="Pending") | Q(status="Forward"),
            booking_to__gte=datetime.datetime.today(),
        ).order_by("booking_from")
        active_bookings = get_dashboard_base_queryset().filter(
            Q(status="Confirmed") | Q(status="CheckedIn"),
            booking_to__gte=datetime.datetime.today(),
        ).order_by("booking_from")
        cancel_booking_request = get_dashboard_base_queryset().filter(
            status="CancelRequested",
            booking_to__gte=datetime.datetime.today(),
        ).order_by("booking_from")
        dashboard_bookings = get_dashboard_base_queryset().filter(
            Q(status="Pending") | Q(status="Forward") | Q(status="Confirmed"),
            booking_to__gte=datetime.datetime.today(),
        ).order_by("booking_from")
        c_bookings = get_dashboard_base_queryset().filter(
            Q(status="Forward"),
            booking_to__gte=datetime.datetime.today(),
        ).order_by("booking_from")
        complete_bookings = get_dashboard_base_queryset().filter(
            Q(status="Canceled") | Q(status="Complete"),
            check_out__lt=datetime.datetime.today(),
        ).order_by("booking_from").reverse()
        canceled_bookings = get_dashboard_base_queryset().filter(status="Canceled").order_by("booking_from")
        cancel_booking_requested = get_dashboard_base_queryset().filter(
            status="CancelRequested",
            booking_to__gte=datetime.datetime.today(),
            intender=user,
        ).order_by("booking_from")
        rejected_bookings = get_dashboard_base_queryset().filter(status="Rejected").order_by("booking_from")

        for booking in pending_bookings:
            available_rooms[booking.id] = get_available_rooms_between(booking.booking_from, booking.booking_to)

        for booking in c_bookings:
            forwarded_rooms[booking.id] = get_forwarded_booking_rooms_between(booking.booking_from, booking.booking_to)

    visitors = {}
    rooms = {}
    for booking in active_bookings:
        visitors[booking.id] = range(2, booking.person_count + 1)
        for _room_no in booking.rooms.all():
            start_range = 1 if user_designation == "Intender" else 2
            end_range = booking.number_of_rooms_alloted if user_designation == "Intender" else booking.number_of_rooms_alloted + 1
            rooms[booking.id] = range(start_range, end_range)

    inventory = get_inventory_queryset()
    inventory_bill = get_inventory_bills_queryset()
    completed_booking_bills = {}
    current_balance = 0

    for bill in get_bills_queryset():
        completed_booking_bills[bill.id] = {
            "intender": str(bill.booking.intender),
            "booking_from": str(bill.booking.booking_from),
            "booking_to": str(bill.booking.booking_to),
            "total_bill": str(bill.meal_bill + bill.room_bill),
            "bill_date": str(bill.bill_date),
        }
        current_balance += bill.meal_bill + bill.room_bill

    for inv_bill in inventory_bill:
        current_balance -= inv_bill.cost

    active_visitors = {}
    for booking in active_bookings:
        if booking.status == "CheckedIn":
            for visitor in booking.visitor.all():
                active_visitors[booking.id] = visitor

    previous_visitors = VisitorDetail.objects.all()
    bills = {}
    meal_records_by_booking = defaultdict(list)
    for meal_record in get_meal_records_for_bookings(active_bookings.values_list("id", flat=True)):
        meal_records_by_booking[meal_record.booking_id].append(meal_record)

    for booking in active_bookings:
        if booking.status == "CheckedIn":
            room_bill = calculate_room_bill_for_dashboard(booking)
            mess_bill = calculate_meal_bill_for_dashboard(booking, meal_records_by_booking.get(booking.id, []))
            bills[booking.id] = {
                "mess_bill": mess_bill,
                "room_bill": room_bill,
                "total_bill": mess_bill + room_bill,
            }

    return {
        "all_bookings": all_bookings,
        "complete_bookings": complete_bookings,
        "pending_bookings": pending_bookings,
        "active_bookings": active_bookings,
        "canceled_bookings": canceled_bookings,
        "dashboard_bookings": dashboard_bookings,
        "bills": bills,
        "available_rooms": available_rooms,
        "forwarded_rooms": forwarded_rooms,
        "inventory": inventory,
        "inventory_bill": inventory_bill,
        "active_visitors": active_visitors,
        "intenders": intenders,
        "user": user,
        "visitors": visitors,
        "rooms": rooms,
        "previous_visitors": previous_visitors,
        "completed_booking_bills": completed_booking_bills,
        "current_balance": current_balance,
        "rejected_bookings": rejected_bookings,
        "cancel_booking_request": cancel_booking_request,
        "cancel_booking_requested": cancel_booking_requested,
        "user_designation": user_designation,
    }


def build_booking_bill_response(booking):
    num_days = (booking.booking_to - booking.booking_from).days + 1
    per_day_cost = VISITOR_COSTS.get(booking.visitor_category, 900)
    room_bill = num_days * per_day_cost
    with transaction.atomic():
        if hasattr(booking, "bill") and booking.bill:
            bill = booking.bill
            total_bill = bill.meal_bill + room_bill
        else:
            bill = Bill.objects.create(
                booking=booking,
                meal_bill=0,
                room_bill=room_bill,
                payment_status=False,
                bill_date=booking.booking_to,
                caretaker=booking.caretaker,
            )
            booking.refresh_from_db()
            total_bill = bill.room_bill
    return {
        "intender_name": booking.intender.username,
        "booking_from": booking.booking_from,
        "booking_to": booking.booking_to,
        "total_bill": total_bill,
        "bill_id": bill.id,
        "bill_date": bill.bill_date,
    }
