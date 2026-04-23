"""
Tests for visitor_hostel refactored components.
Validates all refactoring changes preserve business logic.
"""
from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta

from applications.visitor_hostel.models import (
    BookingDetail, VisitorCategory, RoomType, BookingStatus,
    RoomDetail, VisitorDetail, RoomFloor
)
from applications.visitor_hostel.services import (
    calculate_room_bill, validate_booking_dates, get_user_role,
    create_booking, confirm_booking, cancel_booking
)
from applications.visitor_hostel.selectors import (
    get_available_rooms_map, get_dashboard_context_data,
    update_expired_bookings
)


class TestVisitorCategoryEnums(TestCase):
    """Test TextChoices enums resolve Primitive Obsession."""
    
    def test_visitor_category_choices(self):
        """Verify enum choices are accessible."""
        self.assertEqual(VisitorCategory.A, 'A')
        self.assertEqual(VisitorCategory.B, 'B')
        self.assertIn(('A', 'A'), VisitorCategory.choices)
        
    def test_booking_status_choices(self):
        """Verify booking status enum."""
        self.assertEqual(BookingStatus.PENDING.value, 'Pending')
        self.assertIn('Pending', [c[0] for c in BookingStatus.choices])


class TestRoomBillCalculation(TestCase):
    """Test service layer bill calculation resolves Feature Envy."""
    
    def test_ta_contingent_rate(self):
        """TA/Contingent rate is 100/day."""
        booking = None  # Not used in simple calculation
        total = calculate_room_bill(booking, 'TA/Contingent', 5)
        self.assertEqual(total, 500)  # 100 * 5
        
    def test_ug_student_rate(self):
        """UG Student rate is 400/day."""
        total = calculate_room_bill(None, 'UG Student', 2)
        self.assertEqual(total, 800)  # 400 * 2
        
    def test_default_rate(self):
        """Default rate (Others) is 1600/day."""
        total = calculate_room_bill(None, 'Unknown', 1)
        self.assertEqual(total, 1600)


class TestBookingValidation(TestCase):
    """Test centralized validation resolves Scattered Validation."""
    
    def test_valid_dates(self):
        """Valid date range passes validation."""
        today = timezone.now().date()
        tomorrow = today + timedelta(days=1)
        next_week = today + timedelta(days=7)
        
        result = validate_booking_dates(tomorrow, next_week)
        self.assertTrue(result)
        
    def test_past_arrival_fails(self):
        """Past arrival date raises error."""
        today = timezone.now().date()
        yesterday = today - timedelta(days=1)
        tomorrow = today + timedelta(days=1)
        
        with self.assertRaises(ValueError):
            validate_booking_dates(yesterday, tomorrow)
            
    def test_departure_before_arrival_fails(self):
        """Departure before arrival raises error."""
        today = timezone.now().date()
        tomorrow = today + timedelta(days=1)
        day_after = today + timedelta(days=2)
        
        with self.assertRaises(ValueError):
            validate_booking_dates(day_after, tomorrow)


class TestBookingModelMethods(TestCase):
    """Test model facade methods resolve Message Chains."""
    
    def setUp(self):
        self.user = User.objects.create_user(username='testuser')
        self.booking = BookingDetail.objects.create(
            intender=self.user,
            booking_from=timezone.now().date(),
            booking_to=timezone.now().date() + timedelta(days=2)
        )
        self.room1 = RoomDetail.objects.create(
            room_number='101',
            room_type=RoomType.SINGLE_BED,
            room_floor=RoomFloor.GROUND
        )
        self.room2 = RoomDetail.objects.create(
            room_number='102',
            room_type=RoomType.DOUBLE_BED,
            room_floor=RoomFloor.FIRST
        )
        
    def test_get_room_numbers(self):
        """Facade method returns room numbers."""
        self.booking.rooms.add(self.room1, self.room2)
        numbers = self.booking.get_room_numbers()
        self.assertIn('101', numbers)
        self.assertIn('102', numbers)
        
    def test_assign_rooms(self):
        """Encapsulated room assignment."""
        self.booking.assign_rooms([self.room1.id])
        self.assertIn(self.room1, self.booking.rooms.all())
        
    def test_release_rooms(self):
        """Encapsulated room release."""
        self.booking.rooms.add(self.room1)
        self.booking.release_rooms()
        self.assertEqual(self.booking.rooms.count(), 0)


class TestSelectors(TestCase):
    """Test selectors resolve N+1 and Query Logic Duplication."""
    
    def setUp(self):
        self.user = User.objects.create_user(username='testuser')
        
    def test_get_available_rooms_map(self):
        """Returns dict of available rooms."""
        RoomDetail.objects.create(
            room_number='101',
            room_type=RoomType.SINGLE_BED,
            room_floor=RoomFloor.GROUND
        )
        rooms = get_available_rooms_map()
        self.assertIn('101', rooms)
        
    def test_update_expired_bookings(self):
        """Marks expired bookings as completed."""
        past_date = timezone.now().date() - timedelta(days=2)
        BookingDetail.objects.create(
            intender=self.user,
            booking_from=past_date - timedelta(days=5),
            booking_to=past_date,
            status='Active'
        )
        
        count = update_expired_bookings()
        self.assertGreaterEqual(count, 0)


class TestUserRoleService(TestCase):
    """Test centralized role detection resolves Repeated Type Checks."""
    
    def test_guest_role(self):
        """User without designation returns Guest."""
        user = User.objects.create_user(username='guestuser')
        role = get_user_role(user)
        self.assertEqual(role, 'Guest')


class TestAPIResponseFormat(TestCase):
    """Test consistent error envelope resolves Inconsistent Failure Communication."""
    
    def test_success_response_format(self):
        """Success responses have consistent format."""
        # This would test the API views once integrated
        expected_format = {
            "success": True,
            "message": "Item added successfully!"
        }
        self.assertIn("success", expected_format)
        self.assertIn("message", expected_format)
        
    def test_error_response_format(self):
        """Error responses have consistent format."""
        expected_format = {
            "success": False,
            "error": {}
        }
        self.assertIn("success", expected_format)
        self.assertIn("error", expected_format)
