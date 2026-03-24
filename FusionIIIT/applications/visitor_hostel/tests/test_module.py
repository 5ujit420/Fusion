# tests/test_module.py
# Comprehensive test suite for the visitor_hostel module.
# Covers: selectors, services, serializer validation, and API integration.

import datetime
from django.test import TestCase, RequestFactory
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework import status
from rest_framework.authtoken.models import Token

from applications.globals.models import ExtraInfo, Designation, HoldsDesignation, Department
from applications.visitor_hostel.models import (
    BookingDetail, RoomDetail, VisitorDetail, MealRecord,
    Bill, Inventory, InventoryBill,
    ROOM_RATES, MEAL_RATES, ROOM_BILL_BASE,
)
from applications.visitor_hostel import services
from applications.visitor_hostel import selectors
from applications.visitor_hostel.api.serializers import (
    BookingRequestInputSerializer, CheckOutInputSerializer,
    AddInventoryInputSerializer, ForwardBookingInputSerializer,
    ConfirmBookingInputSerializer, RecordMealInputSerializer,
    RoomAvailabilityInputSerializer, BillDateRangeInputSerializer,
)


class BaseTestCase(TestCase):
    """Common setup for all visitor_hostel tests."""

    @classmethod
    def setUpTestData(cls):
        cls.department = Department.objects.create(name='CSE: Computer Science')

        cls.des_caretaker = Designation.objects.create(name='VhCaretaker')
        cls.des_incharge = Designation.objects.create(name='VhIncharge')
        cls.des_intender = Designation.objects.create(name='Intender')

        cls.user_intender = User.objects.create_user(username='intender1', password='testpass123')
        cls.user_caretaker = User.objects.create_user(username='caretaker1', password='testpass123')
        cls.user_incharge = User.objects.create_user(username='incharge1', password='testpass123')

        cls.ei_intender = ExtraInfo.objects.create(
            user=cls.user_intender, id='INT001', department=cls.department)
        cls.ei_caretaker = ExtraInfo.objects.create(
            user=cls.user_caretaker, id='CT001', department=cls.department)
        cls.ei_incharge = ExtraInfo.objects.create(
            user=cls.user_incharge, id='IN001', department=cls.department)

        HoldsDesignation.objects.create(user=cls.user_caretaker, designation=cls.des_caretaker)
        HoldsDesignation.objects.create(user=cls.user_incharge, designation=cls.des_incharge)
        # Create a second incharge to match the [1] indexing pattern
        cls.user_incharge2 = User.objects.create_user(username='incharge2', password='testpass123')
        cls.ei_incharge2 = ExtraInfo.objects.create(
            user=cls.user_incharge2, id='IN002', department=cls.department)
        HoldsDesignation.objects.create(user=cls.user_incharge2, designation=cls.des_incharge)

        cls.room1 = RoomDetail.objects.create(
            room_number='101', room_type='SingleBed', room_floor='GroundFloor')
        cls.room2 = RoomDetail.objects.create(
            room_number='201', room_type='DoubleBed', room_floor='FirstFloor')

        cls.today = datetime.date.today()
        cls.tomorrow = cls.today + datetime.timedelta(days=1)
        cls.next_week = cls.today + datetime.timedelta(days=7)


# ===========================================================================
# Selector Tests
# ===========================================================================

class SelectorTests(BaseTestCase):

    def test_get_user_role_intender(self):
        role = selectors.get_user_role(self.user_intender)
        self.assertEqual(role, 'Intender')

    def test_get_user_role_caretaker(self):
        role = selectors.get_user_role(self.user_caretaker)
        self.assertEqual(role, 'VhCaretaker')

    def test_get_user_role_incharge(self):
        role = selectors.get_user_role(self.user_incharge)
        self.assertEqual(role, 'VhIncharge')

    def test_get_caretaker_user(self):
        user = selectors.get_caretaker_user()
        self.assertEqual(user, self.user_caretaker)

    def test_get_incharge_user(self):
        user = selectors.get_incharge_user()
        self.assertIn(user, [self.user_incharge, self.user_incharge2])

    def test_get_booking_by_id(self):
        booking = BookingDetail.objects.create(
            intender=self.user_intender, caretaker=self.user_caretaker,
            booking_from=self.today, booking_to=self.next_week)
        result = selectors.get_booking_by_id(booking.id)
        self.assertEqual(result.id, booking.id)

    def test_get_available_rooms_all_free(self):
        rooms = selectors.get_available_rooms(self.today, self.next_week)
        self.assertIn(self.room1, rooms)
        self.assertIn(self.room2, rooms)

    def test_get_available_rooms_with_booking(self):
        booking = BookingDetail.objects.create(
            intender=self.user_intender, caretaker=self.user_caretaker,
            booking_from=self.today, booking_to=self.next_week, status='Confirmed')
        booking.rooms.add(self.room1)
        rooms = selectors.get_available_rooms(self.today, self.next_week)
        self.assertNotIn(self.room1, rooms)
        self.assertIn(self.room2, rooms)

    def test_get_pending_bookings_for_intender(self):
        BookingDetail.objects.create(
            intender=self.user_intender, caretaker=self.user_caretaker,
            booking_from=self.today, booking_to=self.next_week, status='Pending')
        result = selectors.get_pending_bookings_for_intender(self.user_intender)
        self.assertEqual(result.count(), 1)

    def test_get_pending_bookings_all(self):
        BookingDetail.objects.create(
            intender=self.user_intender, caretaker=self.user_caretaker,
            booking_from=self.today, booking_to=self.next_week, status='Pending')
        result = selectors.get_pending_bookings_all()
        self.assertTrue(result.count() >= 1)

    def test_get_meal_record_for_visitor_date_none(self):
        visitor = VisitorDetail.objects.create(visitor_name='TestV', visitor_phone='1234567890')
        booking = BookingDetail.objects.create(
            intender=self.user_intender, caretaker=self.user_caretaker,
            booking_from=self.today, booking_to=self.next_week)
        result = selectors.get_meal_record_for_visitor_date(visitor, booking, self.today)
        self.assertIsNone(result)


# ===========================================================================
# Service Tests
# ===========================================================================

class ServiceUserTests(BaseTestCase):

    def test_get_user_designation(self):
        self.assertEqual(services.get_user_designation(self.user_intender), 'Intender')
        self.assertEqual(services.get_user_designation(self.user_caretaker), 'VhCaretaker')


class ServiceVisitorTests(BaseTestCase):

    def test_create_visitor(self):
        visitor = services.create_visitor('John', '1234567890', 'john@test.com')
        self.assertEqual(visitor.visitor_name, 'John')
        self.assertEqual(visitor.visitor_phone, '1234567890')

    def test_create_visitor_empty_org(self):
        visitor = services.create_visitor('Jane', '9999999999', visitor_organization='')
        self.assertEqual(visitor.visitor_organization, ' ')


class ServiceBookingTests(BaseTestCase):

    def test_create_booking(self):
        booking = services.create_booking(
            intender_user=self.user_intender, category='B',
            person_count=2, purpose='Meeting',
            booking_from=self.today, booking_to=self.next_week,
            arrival_time='10:00', departure_time='18:00',
            number_of_rooms=1, bill_to_be_settled_by='Intender',
        )
        self.assertIsNotNone(booking.id)
        self.assertEqual(booking.intender, self.user_intender)
        self.assertEqual(booking.caretaker, self.user_caretaker)
        self.assertEqual(booking.status, 'Pending')

    def test_update_booking(self):
        booking = services.create_booking(
            self.user_intender, 'B', 2, 'Old purpose',
            self.today, self.next_week, '', '', 1, 'Intender')
        updated = services.update_booking(
            booking.id, 3, 2, self.today, self.next_week, 'New purpose')
        self.assertEqual(updated.person_count, '3')
        self.assertEqual(updated.purpose, 'New purpose')

    def test_confirm_booking(self):
        booking = services.create_booking(
            self.user_intender, 'B', 2, 'Test',
            self.today, self.next_week, '', '', 1, 'Intender')
        services.confirm_booking(booking.id, ['101'], 'B', self.user_incharge)
        booking.refresh_from_db()
        self.assertEqual(booking.status, 'Confirmed')
        self.assertTrue(booking.rooms.filter(room_number='101').exists())

    def test_reject_booking(self):
        booking = services.create_booking(
            self.user_intender, 'B', 1, 'Test',
            self.today, self.next_week, '', '', 1, 'Intender')
        services.reject_booking(booking.id, 'Not valid')
        booking.refresh_from_db()
        self.assertEqual(booking.status, 'Rejected')
        self.assertEqual(booking.remark, 'Not valid')

    def test_cancel_booking(self):
        booking = services.create_booking(
            self.user_intender, 'B', 1, 'Test',
            self.today, self.next_week, '', '', 1, 'Intender')
        services.cancel_booking(booking.id, 'Cancel reason', None, self.user_caretaker)
        booking.refresh_from_db()
        self.assertEqual(booking.status, 'Canceled')
        self.assertTrue(Bill.objects.filter(booking=booking).exists())

    def test_request_cancel_booking(self):
        booking = services.create_booking(
            self.user_intender, 'B', 1, 'Test',
            self.today, self.next_week, '', '', 1, 'Intender')
        services.request_cancel_booking(booking.id, 'Please cancel', self.user_intender)
        booking.refresh_from_db()
        self.assertEqual(booking.status, 'CancelRequested')


class ServiceCheckInOutTests(BaseTestCase):

    def test_check_in_visitor(self):
        booking = services.create_booking(
            self.user_intender, 'B', 1, 'Test',
            self.today, self.next_week, '', '', 1, 'Intender')
        services.check_in_visitor(booking.id, 'Visitor1', '1234567890')
        booking.refresh_from_db()
        self.assertEqual(booking.status, 'CheckedIn')
        self.assertEqual(booking.check_in, datetime.date.today())
        self.assertTrue(booking.visitor.exists())

    def test_check_out_booking(self):
        booking = services.create_booking(
            self.user_intender, 'B', 1, 'Test',
            self.today, self.next_week, '', '', 1, 'Intender')
        services.check_in_visitor(booking.id, 'V1', '1234567890')
        services.check_out_booking(booking.id, 100, 200, self.user_caretaker)
        booking.refresh_from_db()
        self.assertEqual(booking.status, 'Complete')
        bill = Bill.objects.get(booking=booking)
        self.assertEqual(bill.meal_bill, 100)
        self.assertEqual(bill.room_bill, 200)


class ServiceMealTests(BaseTestCase):

    def test_record_meal_new(self):
        booking = services.create_booking(
            self.user_intender, 'B', 1, 'Test',
            self.today, self.next_week, '', '', 1, 'Intender')
        visitor = services.create_visitor('MealV', '5555555555')
        booking.visitor.add(visitor)
        services.record_meal(booking.id, visitor.id, 1, 1, 1, 1, 1)
        meal = MealRecord.objects.filter(booking=booking, visitor=visitor).first()
        self.assertIsNotNone(meal)
        self.assertEqual(meal.morning_tea, 1)
        self.assertEqual(meal.dinner, 1)


class ServiceBillCalculationTests(BaseTestCase):

    def test_calculate_room_bill_category_A(self):
        booking = BookingDetail.objects.create(
            intender=self.user_intender, caretaker=self.user_caretaker,
            booking_from=self.today, booking_to=self.next_week,
            visitor_category='A', check_in=self.today, status='CheckedIn')
        booking.rooms.add(self.room1)
        bill = services.calculate_room_bill(booking)
        self.assertEqual(bill, 0)

    def test_calculate_room_bill_category_B(self):
        booking = BookingDetail.objects.create(
            intender=self.user_intender, caretaker=self.user_caretaker,
            booking_from=self.today, booking_to=self.next_week,
            visitor_category='B', check_in=self.today, status='CheckedIn')
        booking.rooms.add(self.room1)
        # day 0 → days = 1, SingleBed rate = 400
        expected = ROOM_BILL_BASE + 1 * 400
        bill = services.calculate_room_bill(booking)
        self.assertEqual(bill, expected)

    def test_calculate_room_bill_category_C_double(self):
        booking = BookingDetail.objects.create(
            intender=self.user_intender, caretaker=self.user_caretaker,
            booking_from=self.today, booking_to=self.next_week,
            visitor_category='C', check_in=self.today, status='CheckedIn')
        booking.rooms.add(self.room2)  # DoubleBed
        expected = ROOM_BILL_BASE + 1 * 1000
        bill = services.calculate_room_bill(booking)
        self.assertEqual(bill, expected)


class ServiceRoomAssignmentTests(BaseTestCase):

    def test_assign_rooms_to_booking(self):
        booking = BookingDetail.objects.create(
            intender=self.user_intender, caretaker=self.user_caretaker,
            booking_from=self.today, booking_to=self.next_week)
        count = services.assign_rooms_to_booking(booking, ['101', '201'])
        self.assertEqual(count, 2)
        self.assertEqual(booking.rooms.count(), 2)
        self.assertEqual(booking.number_of_rooms_alloted, 2)


class ServiceInventoryTests(BaseTestCase):

    def test_add_inventory_item(self):
        item = services.add_inventory_item('Towels', 10, 500, 'BILL001', 'true')
        self.assertTrue(item.consumable)
        self.assertEqual(item.quantity, 10)
        bill = InventoryBill.objects.get(item_name=item)
        self.assertEqual(bill.cost, 500)

    def test_update_inventory_item_zero_deletes(self):
        item = Inventory.objects.create(item_name='Soap', quantity=5)
        services.update_inventory_item(item.id, 0)
        self.assertFalse(Inventory.objects.filter(id=item.id).exists())

    def test_update_inventory_item_negative_sets_one(self):
        item = Inventory.objects.create(item_name='Soap', quantity=5)
        services.update_inventory_item(item.id, -1)
        item.refresh_from_db()
        self.assertEqual(item.quantity, 1)


class ServiceForwardTests(BaseTestCase):

    def test_forward_booking(self):
        booking = services.create_booking(
            self.user_intender, 'B', 1, 'Test',
            self.today, self.next_week, '', '', 1, 'Intender')
        services.forward_booking(booking.id, 'C', ['101'], 'Forwarding', self.user_caretaker)
        booking.refresh_from_db()
        self.assertEqual(booking.status, 'Forward')
        self.assertEqual(booking.modified_visitor_category, 'C')
        self.assertTrue(booking.rooms.filter(room_number='101').exists())


class ServiceBalanceTests(BaseTestCase):

    def test_calculate_current_balance(self):
        completed_bills, balance = services.calculate_current_balance()
        self.assertIsInstance(completed_bills, dict)
        self.assertIsInstance(balance, (int, float))


# ===========================================================================
# Serializer Validation Tests
# ===========================================================================

class SerializerValidationTests(TestCase):

    def test_booking_request_valid(self):
        data = {
            'intender': 1, 'category': 'B', 'number_of_people': 2,
            'purpose_of_visit': 'Meeting', 'booking_from': '2026-04-01',
            'booking_to': '2026-04-05', 'number_of_rooms': 1,
            'bill_settlement': 'Intender', 'name': 'John', 'phone': '1234567890',
        }
        s = BookingRequestInputSerializer(data=data)
        self.assertTrue(s.is_valid(), s.errors)

    def test_booking_request_invalid_dates(self):
        data = {
            'intender': 1, 'category': 'B', 'number_of_people': 2,
            'purpose_of_visit': 'Meeting', 'booking_from': '2026-04-05',
            'booking_to': '2026-04-01', 'number_of_rooms': 1,
            'bill_settlement': 'Intender', 'name': 'John', 'phone': '1234567890',
        }
        s = BookingRequestInputSerializer(data=data)
        self.assertFalse(s.is_valid())

    def test_booking_request_invalid_category(self):
        data = {
            'intender': 1, 'category': 'Z', 'number_of_people': 2,
            'purpose_of_visit': 'Meeting', 'booking_from': '2026-04-01',
            'booking_to': '2026-04-05', 'number_of_rooms': 1,
            'bill_settlement': 'Intender', 'name': 'John', 'phone': '123',
        }
        s = BookingRequestInputSerializer(data=data)
        self.assertFalse(s.is_valid())
        self.assertIn('category', s.errors)

    def test_booking_request_missing_required(self):
        s = BookingRequestInputSerializer(data={})
        self.assertFalse(s.is_valid())
        self.assertIn('intender', s.errors)
        self.assertIn('name', s.errors)

    def test_checkout_valid(self):
        s = CheckOutInputSerializer(data={'id': 1, 'mess_bill': 100, 'room_bill': 200})
        self.assertTrue(s.is_valid())

    def test_checkout_negative_bill(self):
        s = CheckOutInputSerializer(data={'id': 1, 'mess_bill': -1, 'room_bill': 0})
        self.assertFalse(s.is_valid())

    def test_add_inventory_valid(self):
        s = AddInventoryInputSerializer(data={
            'item_name': 'Towels', 'bill_number': 'B001', 'quantity': 10, 'cost': 500})
        self.assertTrue(s.is_valid())

    def test_add_inventory_missing_fields(self):
        s = AddInventoryInputSerializer(data={})
        self.assertFalse(s.is_valid())

    def test_confirm_booking_valid(self):
        s = ConfirmBookingInputSerializer(data={
            'booking_id': 1, 'category': 'A', 'rooms': ['101', '201']})
        self.assertTrue(s.is_valid())

    def test_record_meal_valid(self):
        s = RecordMealInputSerializer(data={
            'pk': 1, 'booking': 1, 'm_tea': 1, 'breakfast': 0,
            'lunch': 1, 'eve_tea': 0, 'dinner': 1})
        self.assertTrue(s.is_valid())

    def test_room_availability_valid(self):
        s = RoomAvailabilityInputSerializer(data={
            'start_date': '2026-04-01', 'end_date': '2026-04-05'})
        self.assertTrue(s.is_valid())

    def test_forward_booking_valid(self):
        s = ForwardBookingInputSerializer(data={
            'id': 1, 'modified_category': 'C', 'rooms': ['101']})
        self.assertTrue(s.is_valid())


# ===========================================================================
# API Integration Tests
# ===========================================================================

class APIIntegrationTests(BaseTestCase):

    def setUp(self):
        self.client = APIClient()
        self.token_intender, _ = Token.objects.get_or_create(user=self.user_intender)
        self.token_caretaker, _ = Token.objects.get_or_create(user=self.user_caretaker)
        self.token_incharge, _ = Token.objects.get_or_create(user=self.user_incharge)

    def _auth_as(self, token):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + token.key)

    def test_dashboard_requires_auth(self):
        response = self.client.get('/visitorhostel/api/dashboard/')
        self.assertIn(response.status_code,
                      [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])

    def test_dashboard_as_intender(self):
        self._auth_as(self.token_intender)
        response = self.client.get('/visitorhostel/api/dashboard/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['user_designation'], 'Intender')

    def test_dashboard_as_caretaker(self):
        self._auth_as(self.token_caretaker)
        response = self.client.get('/visitorhostel/api/dashboard/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['user_designation'], 'VhCaretaker')

    def test_request_booking_api(self):
        self._auth_as(self.token_intender)
        response = self.client.post('/visitorhostel/api/request-booking/', {
            'intender': self.user_intender.id, 'category': 'B',
            'number_of_people': 2, 'purpose_of_visit': 'API Test',
            'booking_from': str(self.today), 'booking_to': str(self.next_week),
            'number_of_rooms': 1, 'bill_settlement': 'Intender',
            'name': 'API Visitor', 'phone': '1234567890',
        })
        self.assertIn(response.status_code,
                      [status.HTTP_201_CREATED, status.HTTP_400_BAD_REQUEST])

    def test_request_booking_invalid_input(self):
        self._auth_as(self.token_intender)
        response = self.client.post('/visitorhostel/api/request-booking/', {})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_confirm_booking_requires_incharge(self):
        """V-17: Intenders cannot confirm bookings."""
        self._auth_as(self.token_intender)
        response = self.client.post('/visitorhostel/api/confirm-booking/', {
            'booking_id': 1, 'category': 'A', 'rooms': ['101']})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_reject_booking_requires_incharge(self):
        """V-19: Only VhIncharge can reject."""
        self._auth_as(self.token_intender)
        response = self.client.post('/visitorhostel/api/reject-booking/', {
            'booking_id': 1, 'remark': 'No'})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_add_inventory_requires_staff(self):
        """V-20: Only VhCaretaker/VhIncharge can add inventory."""
        self._auth_as(self.token_intender)
        response = self.client.post('/visitorhostel/api/add-to-inventory/', {
            'item_name': 'Sheets', 'quantity': 5, 'cost': 100, 'bill_number': 'B1'})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_add_inventory_as_caretaker(self):
        """V-20: VhCaretaker can add inventory."""
        self._auth_as(self.token_caretaker)
        response = self.client.post('/visitorhostel/api/add-to-inventory/', {
            'item_name': 'Sheets', 'quantity': 5, 'cost': 100, 'bill_number': 'B1'})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_room_availability_api(self):
        self._auth_as(self.token_intender)
        response = self.client.post('/visitorhostel/api/room-availability/', {
            'start_date': str(self.today), 'end_date': str(self.next_week)})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)

    def test_edit_room_status_requires_staff(self):
        """V-22: Only staff can change room status."""
        self._auth_as(self.token_intender)
        response = self.client.post('/visitorhostel/api/edit-room-status/', {
            'room_number': '101', 'room_status': 'UnderMaintenance'})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


# ===========================================================================
# Model Constants Tests (V-14, V-15)
# ===========================================================================

class ModelConstantsTests(TestCase):

    def test_room_rates_structure(self):
        self.assertIn('A', ROOM_RATES)
        self.assertIn('D', ROOM_RATES)
        self.assertEqual(ROOM_RATES['A']['SingleBed'], 0)
        self.assertEqual(ROOM_RATES['B']['SingleBed'], 400)
        self.assertEqual(ROOM_RATES['C']['DoubleBed'], 1000)

    def test_meal_rates_structure(self):
        self.assertEqual(MEAL_RATES['morning_tea'], 10)
        self.assertEqual(MEAL_RATES['breakfast'], 50)
        self.assertEqual(MEAL_RATES['lunch'], 100)

    def test_room_bill_base(self):
        self.assertEqual(ROOM_BILL_BASE, 100)
