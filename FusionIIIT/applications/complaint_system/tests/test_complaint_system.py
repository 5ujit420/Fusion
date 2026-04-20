# tests/test_complaint_system.py
# Provides unit tests for services.py and selectors.py functions.
# Each test validates a T-xx refactoring task from the audit plan.

from datetime import date, timedelta, datetime
from unittest.mock import MagicMock, patch

from django.test import TestCase

from applications.complaint_system.services import (
    calculate_new_rating,
    compute_complaint_deadline,
    resolve_caretaker_designation,
    determine_user_role,
    LOCATION_DESIGNATION_MAP,
    ROLE_URLS,
)


# ---------------------------------------------------------------------------
# T-02 / T-10: services.compute_complaint_deadline
# ---------------------------------------------------------------------------
class ComputeComplaintDeadlineTests(TestCase):
    def test_electricity_gives_2_days(self):
        result = compute_complaint_deadline('Electricity')
        expected = (datetime.now() + timedelta(days=2)).date()
        self.assertEqual(result, expected)

    def test_internet_gives_4_days(self):
        result = compute_complaint_deadline('internet')
        expected = (datetime.now() + timedelta(days=4)).date()
        self.assertEqual(result, expected)

    def test_garbage_gives_1_day(self):
        result = compute_complaint_deadline('garbage')
        expected = (datetime.now() + timedelta(days=1)).date()
        self.assertEqual(result, expected)

    def test_other_gives_3_days(self):
        result = compute_complaint_deadline('other')
        expected = (datetime.now() + timedelta(days=3)).date()
        self.assertEqual(result, expected)

    def test_unknown_type_defaults_to_2_days(self):
        result = compute_complaint_deadline('unknown_type')
        expected = (datetime.now() + timedelta(days=2)).date()
        self.assertEqual(result, expected)

    def test_returns_date_not_datetime(self):
        result = compute_complaint_deadline('Electricity')
        self.assertIsInstance(result, date)

    def test_carpenter_capitalised_variant(self):
        """Preserves existing behaviour: 'Carpenter' (buggy input) still gives 2 days."""
        result = compute_complaint_deadline('Carpenter')
        expected = (datetime.now() + timedelta(days=2)).date()
        self.assertEqual(result, expected)


# ---------------------------------------------------------------------------
# T-02 / CS-12: services.resolve_caretaker_designation
# ---------------------------------------------------------------------------
class ResolveCaretakerDesignationTests(TestCase):
    def test_hall1_maps_correctly(self):
        self.assertEqual(resolve_caretaker_designation('hall-1'), 'hall1caretaker')

    def test_hall3_maps_correctly(self):
        self.assertEqual(resolve_caretaker_designation('hall-3'), 'hall3caretaker')

    def test_msa_hostel_maps_correctly(self):
        self.assertEqual(
            resolve_caretaker_designation('Maa Saraswati Hostel'), 'mshcaretaker'
        )

    def test_cc1_maps_correctly(self):
        self.assertEqual(resolve_caretaker_designation('CC1'), 'cc1convener')

    def test_unknown_location_defaults_to_rewa(self):
        self.assertEqual(resolve_caretaker_designation('unknown'), 'rewacaretaker')

    def test_all_mapped_locations_present(self):
        """Every key in LOCATION_DESIGNATION_MAP resolves without hitting the default."""
        for loc, expected_dsgn in LOCATION_DESIGNATION_MAP.items():
            self.assertEqual(resolve_caretaker_designation(loc), expected_dsgn)


# ---------------------------------------------------------------------------
# T-10 / CS-13: services.calculate_new_rating
# ---------------------------------------------------------------------------
class CalculateNewRatingTests(TestCase):
    def test_zero_existing_returns_new(self):
        self.assertEqual(calculate_new_rating(0, 4), 4)

    def test_nonzero_existing_returns_average(self):
        self.assertEqual(calculate_new_rating(3, 5), 4)

    def test_average_truncated_to_int(self):
        self.assertIsInstance(calculate_new_rating(3, 4), int)

    def test_same_value_stays_same(self):
        self.assertEqual(calculate_new_rating(3, 3), 3)


# ---------------------------------------------------------------------------
# T-04 / CS-03: services.determine_user_role
# ---------------------------------------------------------------------------
class DetermineUserRoleTests(TestCase):
    def _make_extra_info(self, user_type='student'):
        ei = MagicMock()
        ei.user_type = user_type
        return ei

    @patch('applications.complaint_system.services.selectors')
    def test_service_provider_role(self, mock_selectors):
        mock_selectors.is_service_provider.return_value = True
        mock_selectors.is_complaint_admin.return_value = False
        mock_selectors.is_caretaker.return_value = False
        mock_selectors.is_warden.return_value = False
        result = determine_user_role(self._make_extra_info())
        self.assertEqual(result['role'], 'service_provider')
        self.assertEqual(result['next_url'], ROLE_URLS['service_provider'])

    @patch('applications.complaint_system.services.selectors')
    def test_student_role(self, mock_selectors):
        mock_selectors.is_service_provider.return_value = False
        mock_selectors.is_complaint_admin.return_value = False
        mock_selectors.is_caretaker.return_value = False
        mock_selectors.is_warden.return_value = False
        result = determine_user_role(self._make_extra_info(user_type='student'))
        self.assertEqual(result['role'], 'student')
        self.assertEqual(result['next_url'], '/complaint/user/')

    @patch('applications.complaint_system.services.selectors')
    def test_unknown_user_type_returns_none(self, mock_selectors):
        mock_selectors.is_service_provider.return_value = False
        mock_selectors.is_complaint_admin.return_value = False
        mock_selectors.is_caretaker.return_value = False
        mock_selectors.is_warden.return_value = False
        result = determine_user_role(self._make_extra_info(user_type='alien'))
        self.assertIsNone(result)


# ---------------------------------------------------------------------------
# T-09 / CS-17: FeedbackSerializer.validate_rating
# ---------------------------------------------------------------------------
class FeedbackSerializerValidationTests(TestCase):
    def _get_serializer(self, rating):
        from applications.complaint_system.serializers import FeedbackSerializer
        return FeedbackSerializer(data={'feedback': 'ok', 'rating': rating})

    def test_valid_rating_5_passes(self):
        self.assertTrue(self._get_serializer(5).is_valid())

    def test_valid_rating_1_passes(self):
        self.assertTrue(self._get_serializer(1).is_valid())

    def test_rating_zero_fails(self):
        ser = self._get_serializer(0)
        self.assertFalse(ser.is_valid())
        self.assertIn('rating', ser.errors)

    def test_rating_six_fails(self):
        ser = self._get_serializer(6)
        self.assertFalse(ser.is_valid())
        self.assertIn('rating', ser.errors)

    def test_string_rating_fails(self):
        ser = self._get_serializer('abc')
        self.assertFalse(ser.is_valid())
        self.assertIn('rating', ser.errors)


# ---------------------------------------------------------------------------
# T-11 / CS-23: TextChoices in models
# ---------------------------------------------------------------------------
class TextChoicesTests(TestCase):
    def test_area_textchoices_hall1_value(self):
        from applications.complaint_system.models import Area
        self.assertEqual(Area.HALL_1, 'hall-1')

    def test_complaint_type_textchoices_electricity(self):
        from applications.complaint_system.models import ComplaintType
        self.assertEqual(ComplaintType.ELECTRICITY, 'Electricity')

    def test_complaint_type_internet(self):
        from applications.complaint_system.models import ComplaintType
        self.assertEqual(ComplaintType.INTERNET, 'internet')

    def test_status_constants(self):
        from applications.complaint_system.models import (
            COMPLAINT_STATUS_PENDING, COMPLAINT_STATUS_ASSIGNED,
            COMPLAINT_STATUS_RESOLVED, COMPLAINT_STATUS_DECLINED,
        )
        self.assertEqual(COMPLAINT_STATUS_PENDING, 0)
        self.assertEqual(COMPLAINT_STATUS_ASSIGNED, 1)
        self.assertEqual(COMPLAINT_STATUS_RESOLVED, 2)
        self.assertEqual(COMPLAINT_STATUS_DECLINED, 3)
