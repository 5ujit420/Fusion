import datetime

from django.contrib.auth.models import User
from django.test import TestCase

from applications.globals.models import Designation, HoldsDesignation
from applications.visitor_hostel.models import Bill, BookingDetail, Inventory, InventoryBill, RoomDetail
from applications.visitor_hostel.selectors import (
    get_available_rooms_between,
    get_user_designation,
)
from applications.visitor_hostel.services import (
    add_inventory_item_and_bill,
    build_booking_bill_response,
    create_booking_request,
)
from applications.visitor_hostel.urls import urlpatterns


class VisitorHostelServiceTests(TestCase):
    def setUp(self):
        self.intender = User.objects.create_user(username="intender", password="pass")
        self.caretaker = User.objects.create_user(username="caretaker", password="pass")
        self.incharge = User.objects.create_user(username="incharge", password="pass")

        self.caretaker_designation = Designation.objects.create(
            name="VhCaretaker",
            full_name="Visitor Hostel Caretaker",
            type="administrative",
        )
        self.incharge_designation = Designation.objects.create(
            name="VhIncharge",
            full_name="Visitor Hostel Incharge",
            type="administrative",
        )

        HoldsDesignation.objects.create(
            user=self.caretaker,
            working=self.caretaker,
            designation=self.caretaker_designation,
        )
        HoldsDesignation.objects.create(
            user=self.incharge,
            working=self.incharge,
            designation=self.incharge_designation,
        )

    def test_get_user_designation_returns_expected_role(self):
        self.assertEqual(get_user_designation(self.intender), "Intender")
        self.assertEqual(get_user_designation(self.caretaker), "VhCaretaker")
        self.assertEqual(get_user_designation(self.incharge), "VhIncharge")

    def test_booking_request_service_creates_related_models_atomically(self):
        booking = create_booking_request(
            {
                "category": "C",
                "person_count": 2,
                "purpose_of_visit": "Official visit",
                "booking_from": datetime.date(2026, 4, 21),
                "booking_to": datetime.date(2026, 4, 22),
                "booking_from_time": "10:00",
                "booking_to_time": "11:00",
                "remarks_during_booking_request": "Need projector",
                "bill_to_be_settled_by": "Intender",
                "number_of_rooms": 1,
                "visitor_name": "Guest One",
                "visitor_email": "guest@example.com",
                "visitor_phone": "9999999999",
                "visitor_organization": "Fusion",
                "visitor_address": "Campus",
                "nationality": "Indian",
            },
            self.intender,
        )

        self.assertEqual(booking.intender, self.intender)
        self.assertEqual(booking.caretaker, self.caretaker)
        self.assertEqual(booking.visitor.count(), 1)
        self.assertEqual(booking.visitor.first().visitor_name, "Guest One")

    def test_inventory_service_updates_existing_item_by_name(self):
        add_inventory_item_and_bill(
            {
                "item_name": "Blanket",
                "bill_number": "B-1",
                "quantity": 2,
                "cost": 300,
                "consumable": False,
            }
        )
        add_inventory_item_and_bill(
            {
                "item_name": "Blanket",
                "bill_number": "B-2",
                "quantity": 5,
                "cost": 450,
                "consumable": True,
            }
        )

        inventory = Inventory.objects.get(item_name="Blanket")
        self.assertEqual(Inventory.objects.count(), 1)
        self.assertEqual(inventory.quantity, 5)
        self.assertTrue(inventory.consumable)
        self.assertEqual(InventoryBill.objects.filter(item_name=inventory).count(), 2)

    def test_get_all_bills_bill_builder_is_idempotent(self):
        booking = BookingDetail.objects.create(
            intender=self.intender,
            caretaker=self.caretaker,
            visitor_category="B",
            modified_visitor_category="B",
            person_count=1,
            purpose="Visit",
            booking_from=datetime.date(2026, 4, 21),
            booking_to=datetime.date(2026, 4, 22),
            status="Confirmed",
        )

        first = build_booking_bill_response(booking)
        second = build_booking_bill_response(BookingDetail.objects.get(id=booking.id))

        self.assertEqual(Bill.objects.filter(booking=booking).count(), 1)
        self.assertEqual(first["bill_id"], second["bill_id"])


class VisitorHostelSelectorTests(TestCase):
    def setUp(self):
        self.intender = User.objects.create_user(username="selector", password="pass")
        self.caretaker = User.objects.create_user(username="caretaker2", password="pass")
        self.room_one = RoomDetail.objects.create(
            room_number="101",
            room_type="SingleBed",
            room_floor="GroundFloor",
            room_status="Available",
        )
        self.room_two = RoomDetail.objects.create(
            room_number="102",
            room_type="DoubleBed",
            room_floor="GroundFloor",
            room_status="Available",
        )
        booking = BookingDetail.objects.create(
            intender=self.intender,
            caretaker=self.caretaker,
            visitor_category="C",
            modified_visitor_category="C",
            person_count=1,
            purpose="Visit",
            booking_from=datetime.date(2026, 4, 21),
            booking_to=datetime.date(2026, 4, 23),
            status="Confirmed",
        )
        booking.rooms.add(self.room_one)

    def test_overlap_selector_matches_existing_edge_cases(self):
        available_rooms = list(
            get_available_rooms_between(
                datetime.date(2026, 4, 22),
                datetime.date(2026, 4, 24),
            ).values_list("room_number", flat=True)
        )
        self.assertEqual(available_rooms, ["102"])


class VisitorHostelUrlTests(TestCase):
    def test_urlpatterns_are_unique(self):
        patterns = [pattern.pattern.regex.pattern for pattern in urlpatterns]
        self.assertEqual(len(patterns), len(set(patterns)))

    def test_inventory_detail_route_is_registered(self):
        patterns = [pattern.pattern.regex.pattern for pattern in urlpatterns]
        self.assertIn("^inventory/(?P<pk>\\d+)/$", patterns)
