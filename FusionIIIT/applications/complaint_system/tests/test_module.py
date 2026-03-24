# tests/test_module.py
# Comprehensive tests for the complaint_system module.
# Fixes: V-03

import datetime
from unittest.mock import patch, MagicMock

from django.test import TestCase, RequestFactory
from django.contrib.auth.models import User
from rest_framework.test import APIClient, APITestCase
from rest_framework import status

from applications.globals.models import ExtraInfo
from applications.complaint_system.models import (
    Caretaker, Warden, StudentComplain, ServiceProvider,
    Complaint_Admin, ServiceAuthority, Workers, SectionIncharge,
    Constants, COMPLAINT_TYPE_DAYS, LOCATION_DESIGNATION_MAP,
    DEFAULT_FINISH_DAYS, DEFAULT_DESIGNATION,
)
from applications.complaint_system import selectors, services


# ===================================================================
#  MODEL / CONSTANT TESTS
# ===================================================================

class ConstantsTest(TestCase):
    """Test that lookup dicts match original if/elif logic."""

    def test_complaint_type_days_electricity(self):
        self.assertEqual(COMPLAINT_TYPE_DAYS.get('Electricity', DEFAULT_FINISH_DAYS), 2)

    def test_complaint_type_days_garbage(self):
        self.assertEqual(COMPLAINT_TYPE_DAYS.get('garbage', DEFAULT_FINISH_DAYS), 1)
        self.assertEqual(COMPLAINT_TYPE_DAYS.get('Garbage', DEFAULT_FINISH_DAYS), 1)

    def test_complaint_type_days_internet(self):
        self.assertEqual(COMPLAINT_TYPE_DAYS.get('internet', DEFAULT_FINISH_DAYS), 4)
        self.assertEqual(COMPLAINT_TYPE_DAYS.get('Internet', DEFAULT_FINISH_DAYS), 4)

    def test_complaint_type_days_other(self):
        self.assertEqual(COMPLAINT_TYPE_DAYS.get('other', DEFAULT_FINISH_DAYS), 3)
        self.assertEqual(COMPLAINT_TYPE_DAYS.get('Other', DEFAULT_FINISH_DAYS), 3)

    def test_complaint_type_days_default(self):
        self.assertEqual(COMPLAINT_TYPE_DAYS.get('unknown', DEFAULT_FINISH_DAYS), 2)

    def test_location_designation_map_hall1(self):
        self.assertEqual(LOCATION_DESIGNATION_MAP.get('hall-1', DEFAULT_DESIGNATION), 'hall1caretaker')

    def test_location_designation_map_cc1(self):
        self.assertEqual(LOCATION_DESIGNATION_MAP.get('CC1', DEFAULT_DESIGNATION), 'cc1convener')

    def test_location_designation_map_default(self):
        self.assertEqual(LOCATION_DESIGNATION_MAP.get('unknown', DEFAULT_DESIGNATION), DEFAULT_DESIGNATION)

    def test_all_areas_accounted(self):
        """All expected locations should be in the map."""
        expected = [
            'hall-1', 'hall-3', 'hall-4', 'CC1', 'CC2', 'core_lab',
            'LHTC', 'NR2', 'Maa Saraswati Hostel', 'Nagarjun Hostel', 'Panini Hostel',
        ]
        for loc in expected:
            self.assertIn(loc, LOCATION_DESIGNATION_MAP)


# ===================================================================
#  SERVICE TESTS
# ===================================================================

class CalculateComplaintFinishDateTest(TestCase):
    """Test the complaint finish date calculation service."""

    def test_electricity_type(self):
        finish = services.calculate_complaint_finish_date('Electricity')
        expected = (datetime.datetime.now() + datetime.timedelta(days=2)).date()
        self.assertEqual(finish, expected)

    def test_garbage_type(self):
        finish = services.calculate_complaint_finish_date('garbage')
        expected = (datetime.datetime.now() + datetime.timedelta(days=1)).date()
        self.assertEqual(finish, expected)

    def test_internet_type(self):
        finish = services.calculate_complaint_finish_date('internet')
        expected = (datetime.datetime.now() + datetime.timedelta(days=4)).date()
        self.assertEqual(finish, expected)

    def test_other_type(self):
        finish = services.calculate_complaint_finish_date('other')
        expected = (datetime.datetime.now() + datetime.timedelta(days=3)).date()
        self.assertEqual(finish, expected)

    def test_unknown_type_uses_default(self):
        finish = services.calculate_complaint_finish_date('nonexistent')
        expected = (datetime.datetime.now() + datetime.timedelta(days=DEFAULT_FINISH_DAYS)).date()
        self.assertEqual(finish, expected)


class ResolveLocationToDesignationTest(TestCase):
    """Test the location-to-designation mapping service."""

    def test_hall_1(self):
        self.assertEqual(services.resolve_location_to_designation('hall-1'), 'hall1caretaker')

    def test_cc2(self):
        self.assertEqual(services.resolve_location_to_designation('CC2'), 'CC2 convener')

    def test_unknown_location_uses_default(self):
        self.assertEqual(services.resolve_location_to_designation('unknown'), DEFAULT_DESIGNATION)


class UpdateCaretakerRatingTest(TestCase):
    """Test the caretaker rating update logic."""

    def setUp(self):
        self.user = User.objects.create_user(username='caretaker_test', password='test')
        self.extra = ExtraInfo.objects.create(
            user=self.user, id='CT001', user_type='staff'
        )
        self.caretaker = Caretaker.objects.create(
            staff_id=self.extra, area='hall-1', rating=0
        )

    def test_first_rating_sets_value(self):
        services._update_caretaker_rating(self.caretaker, 4)
        self.caretaker.refresh_from_db()
        self.assertEqual(self.caretaker.rating, 4)

    def test_subsequent_rating_averages(self):
        self.caretaker.rating = 4
        self.caretaker.save()
        services._update_caretaker_rating(self.caretaker, 2)
        self.caretaker.refresh_from_db()
        self.assertEqual(self.caretaker.rating, int((2 + 4) / 2))


class DetermineUserTypeTest(TestCase):
    """Test user type determination."""

    def setUp(self):
        self.student_user = User.objects.create_user(username='student1', password='test')
        self.student_extra = ExtraInfo.objects.create(
            user=self.student_user, id='STU001', user_type='student'
        )

    def test_student_user(self):
        user_type, url = services.determine_user_type(self.student_user)
        self.assertEqual(user_type, 'student')
        self.assertEqual(url, '/complaint/user/')

    def test_caretaker_user(self):
        user = User.objects.create_user(username='care1', password='test')
        extra = ExtraInfo.objects.create(user=user, id='CR001', user_type='staff')
        Caretaker.objects.create(staff_id=extra, area='hall-1')
        user_type, url = services.determine_user_type(user)
        self.assertEqual(user_type, 'caretaker')
        self.assertEqual(url, '/complaint/caretaker/')

    def test_service_provider_user(self):
        user = User.objects.create_user(username='sp1', password='test')
        extra = ExtraInfo.objects.create(user=user, id='SP001', user_type='staff')
        ServiceProvider.objects.create(ser_pro_id=extra, type='Electricity')
        user_type, url = services.determine_user_type(user)
        self.assertEqual(user_type, 'service_provider')
        self.assertEqual(url, '/complaint/service_provider/')

    def test_complaint_admin_user(self):
        user = User.objects.create_user(username='admin1', password='test')
        extra = ExtraInfo.objects.create(user=user, id='AD001', user_type='staff')
        Complaint_Admin.objects.create(sup_id=extra)
        user_type, url = services.determine_user_type(user)
        self.assertEqual(user_type, 'complaint_admin')
        self.assertEqual(url, '/complaint/complaint_admin/')

    def test_warden_user(self):
        user = User.objects.create_user(username='warden1', password='test')
        extra = ExtraInfo.objects.create(user=user, id='WD001', user_type='staff')
        Warden.objects.create(staff_id=extra, area='hall-1')
        user_type, url = services.determine_user_type(user)
        self.assertEqual(user_type, 'warden')
        self.assertEqual(url, '/complaint/warden/')


class ChangeComplaintStatusTest(TestCase):
    """Test complaint status change service."""

    def setUp(self):
        self.user = User.objects.create_user(username='status_test', password='test')
        self.extra = ExtraInfo.objects.create(
            user=self.user, id='ST001', user_type='student'
        )
        self.complaint = StudentComplain.objects.create(
            complainer=self.extra,
            complaint_type='internet',
            location='hall-1',
            details='Test complaint',
            status=0,
        )

    def test_change_to_resolved(self):
        services.change_complaint_status(self.complaint.id, '2')
        self.complaint.refresh_from_db()
        self.assertEqual(self.complaint.status, '2')
        self.assertIsNone(self.complaint.worker_id)

    def test_change_to_normal_status(self):
        services.change_complaint_status(self.complaint.id, '1')
        self.complaint.refresh_from_db()
        self.assertEqual(self.complaint.status, '1')


class DeleteComplaintTest(TestCase):
    """Test complaint deletion with ownership check (V-26)."""

    def setUp(self):
        self.owner = User.objects.create_user(username='owner', password='test')
        self.other = User.objects.create_user(username='other', password='test')
        self.owner_extra = ExtraInfo.objects.create(
            user=self.owner, id='OW001', user_type='student'
        )
        self.other_extra = ExtraInfo.objects.create(
            user=self.other, id='OT001', user_type='student'
        )
        self.complaint = StudentComplain.objects.create(
            complainer=self.owner_extra,
            complaint_type='internet',
            location='hall-1',
            details='Test complaint',
            status=0,
        )

    def test_owner_can_delete(self):
        success, msg = services.delete_complaint(self.complaint.id, self.owner)
        self.assertTrue(success)
        self.assertFalse(StudentComplain.objects.filter(id=self.complaint.id).exists())

    def test_non_owner_cannot_delete(self):
        success, msg = services.delete_complaint(self.complaint.id, self.other)
        self.assertFalse(success)
        self.assertTrue(StudentComplain.objects.filter(id=self.complaint.id).exists())

    def test_caretaker_can_delete(self):
        caretaker_user = User.objects.create_user(username='care_del', password='test')
        care_extra = ExtraInfo.objects.create(
            user=caretaker_user, id='CD001', user_type='staff'
        )
        Caretaker.objects.create(staff_id=care_extra, area='hall-1')
        success, msg = services.delete_complaint(self.complaint.id, caretaker_user)
        self.assertTrue(success)


class RemoveWorkerTest(TestCase):
    """Test worker removal logic."""

    def setUp(self):
        self.sec = SectionIncharge.objects.create(
            staff_id=ExtraInfo.objects.create(
                user=User.objects.create_user(username='sec1', password='test'),
                id='SE001', user_type='staff'
            ),
            work_type='Electricity',
        )
        self.worker = Workers.objects.create(
            secincharge_id=self.sec, name='Worker1', age='30', phone=1234567890
        )

    def test_remove_unassigned_worker(self):
        success, msg = services.remove_worker(self.worker.id)
        self.assertTrue(success)
        self.assertFalse(Workers.objects.filter(id=self.worker.id).exists())

    def test_cannot_remove_assigned_worker(self):
        user = User.objects.create_user(username='w_test', password='test')
        extra = ExtraInfo.objects.create(user=user, id='WT001', user_type='student')
        StudentComplain.objects.create(
            complainer=extra, complaint_type='Electricity',
            location='hall-1', details='test', worker_id=self.worker
        )
        success, msg = services.remove_worker(self.worker.id)
        self.assertFalse(success)


class SubmitComplaintFeedbackTest(TestCase):
    """Test feedback submission + caretaker rating update (V-07, R-03)."""

    def setUp(self):
        user = User.objects.create_user(username='fb_test', password='test')
        extra = ExtraInfo.objects.create(user=user, id='FB001', user_type='student')
        self.complaint = StudentComplain.objects.create(
            complainer=extra, complaint_type='internet',
            location='hall-1', details='Feedback test', status=2,
        )
        care_user = User.objects.create_user(username='fb_care', password='test')
        care_extra = ExtraInfo.objects.create(user=care_user, id='FC001', user_type='staff')
        self.caretaker = Caretaker.objects.create(
            staff_id=care_extra, area='hall-1', rating=0
        )

    def test_feedback_updates_complaint(self):
        services.submit_complaint_feedback(self.complaint.id, 'Great work', 4)
        self.complaint.refresh_from_db()
        self.assertEqual(self.complaint.feedback, 'Great work')
        self.assertEqual(self.complaint.flag, 4)

    def test_feedback_updates_caretaker_rating(self):
        services.submit_complaint_feedback(self.complaint.id, 'Good', 5)
        self.caretaker.refresh_from_db()
        self.assertEqual(self.caretaker.rating, 5)  # first rating set directly


# ===================================================================
#  SELECTOR TESTS
# ===================================================================

class SelectorTests(TestCase):
    """Test selector functions."""

    def setUp(self):
        self.user = User.objects.create_user(username='sel_test', password='test')
        self.extra = ExtraInfo.objects.create(
            user=self.user, id='SL001', user_type='student'
        )
        self.complaint = StudentComplain.objects.create(
            complainer=self.extra, complaint_type='internet',
            location='hall-1', details='Selector test', status=0,
        )

    def test_get_extrainfo_by_user(self):
        result = selectors.get_extrainfo_by_user(self.user)
        self.assertEqual(result.id, self.extra.id)

    def test_get_complaints_by_complainer(self):
        qs = selectors.get_complaints_by_complainer(self.extra)
        self.assertEqual(qs.count(), 1)
        self.assertEqual(qs.first().id, self.complaint.id)

    def test_is_caretaker_false(self):
        self.assertFalse(selectors.is_caretaker(self.extra.id))

    def test_is_caretaker_true(self):
        Caretaker.objects.create(staff_id=self.extra, area='hall-1')
        self.assertTrue(selectors.is_caretaker(self.extra.id))

    def test_get_complaint_by_id(self):
        result = selectors.get_complaint_by_id(self.complaint.id)
        self.assertEqual(result.details, 'Selector test')

    def test_get_complaint_by_id_not_found(self):
        with self.assertRaises(StudentComplain.DoesNotExist):
            selectors.get_complaint_by_id(99999)

    def test_get_complaints_by_location(self):
        qs = selectors.get_complaints_by_location('hall-1')
        self.assertEqual(qs.count(), 1)

    def test_get_pending_complaints_by_location(self):
        qs = selectors.get_pending_complaints_by_location('hall-1')
        self.assertEqual(qs.count(), 1)

    def test_get_all_complaints(self):
        qs = selectors.get_all_complaints()
        self.assertTrue(qs.exists())


# ===================================================================
#  SERIALIZER VALIDATION TESTS  (V-21, V-23, V-24, V-25)
# ===================================================================

class SerializerValidationTest(TestCase):
    """Test serializer input validation."""

    def setUp(self):
        self.user = User.objects.create_user(username='ser_test', password='test')
        self.extra = ExtraInfo.objects.create(
            user=self.user, id='SV001', user_type='student'
        )

    def test_student_complain_invalid_complaint_type(self):
        from applications.complaint_system.api.serializers import StudentComplainSerializer
        data = {
            'complainer': self.extra.id,
            'complaint_type': 'INVALID_TYPE',
            'location': 'hall-1',
            'details': 'Test',
        }
        serializer = StudentComplainSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('complaint_type', serializer.errors)

    def test_student_complain_valid_data(self):
        from applications.complaint_system.api.serializers import StudentComplainSerializer
        data = {
            'complainer': self.extra.id,
            'complaint_type': 'internet',
            'location': 'hall-1',
            'details': 'Test complaint',
        }
        serializer = StudentComplainSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_feedback_serializer_rating_range(self):
        from applications.complaint_system.api.serializers import FeedbackSerializer
        invalid_data = {'feedback': 'test', 'rating': 10}
        serializer = FeedbackSerializer(data=invalid_data)
        self.assertFalse(serializer.is_valid())

    def test_feedback_serializer_valid(self):
        from applications.complaint_system.api.serializers import FeedbackSerializer
        valid_data = {'feedback': 'Great!', 'rating': 4}
        serializer = FeedbackSerializer(data=valid_data)
        self.assertTrue(serializer.is_valid())

    def test_resolve_pending_invalid_choice(self):
        from applications.complaint_system.api.serializers import ResolvePendingSerializer
        data = {'yesorno': 'Maybe'}
        serializer = ResolvePendingSerializer(data=data)
        self.assertFalse(serializer.is_valid())

    def test_resolve_pending_valid(self):
        from applications.complaint_system.api.serializers import ResolvePendingSerializer
        data = {'yesorno': 'Yes', 'comment': 'Done'}
        serializer = ResolvePendingSerializer(data=data)
        self.assertTrue(serializer.is_valid())


# ===================================================================
#  API INTEGRATION TESTS
# ===================================================================

class CheckUserAPITest(APITestCase):
    """Test the CheckUser endpoint."""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='apitest', password='test')
        self.extra = ExtraInfo.objects.create(
            user=self.user, id='AP001', user_type='student'
        )
        self.client.force_authenticate(user=self.user)

    def test_check_user_student(self):
        response = self.client.get('/complaint/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['user_type'], 'student')
        self.assertEqual(response.data['next_url'], '/complaint/user/')

    def test_check_user_unauthenticated(self):
        self.client.logout()
        response = self.client.get('/complaint/')
        self.assertIn(response.status_code, [401, 403])


class UserComplaintAPITest(APITestCase):
    """Test user complaint list endpoint."""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='uctest', password='test')
        self.extra = ExtraInfo.objects.create(
            user=self.user, id='UC001', user_type='student'
        )
        self.client.force_authenticate(user=self.user)
        StudentComplain.objects.create(
            complainer=self.extra, complaint_type='internet',
            location='hall-1', details='Integration test', status=0,
        )

    def test_get_complaints(self):
        response = self.client.get('/complaint/user/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['details'], 'Integration test')


class ComplaintDetailAPITest(APITestCase):
    """Test complaint detail endpoint."""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='cdtest', password='test')
        self.extra = ExtraInfo.objects.create(
            user=self.user, id='CD002', user_type='student'
        )
        self.client.force_authenticate(user=self.user)
        self.complaint = StudentComplain.objects.create(
            complainer=self.extra, complaint_type='internet',
            location='hall-1', details='Detail test', status=0,
        )

    def test_get_detail(self):
        url = f'/complaint/user/detail/{self.complaint.id}/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['details'], 'Detail test')

    def test_get_detail_not_found(self):
        response = self.client.get('/complaint/user/detail/99999/')
        self.assertEqual(response.status_code, 404)


class FeedbackAPITest(APITestCase):
    """Test feedback submission endpoints (V-24, V-25)."""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='fbapi', password='test')
        self.extra = ExtraInfo.objects.create(
            user=self.user, id='FA001', user_type='student'
        )
        self.client.force_authenticate(user=self.user)
        self.complaint = StudentComplain.objects.create(
            complainer=self.extra, complaint_type='internet',
            location='hall-1', details='Feedback API test', status=2,
        )
        care_user = User.objects.create_user(username='fb_api_care', password='test')
        care_extra = ExtraInfo.objects.create(
            user=care_user, id='FA002', user_type='staff'
        )
        Caretaker.objects.create(staff_id=care_extra, area='hall-1', rating=0)

    def test_submit_feedback_valid(self):
        url = f'/complaint/user/{self.complaint.id}/'
        response = self.client.post(url, {'feedback': 'Nice', 'rating': 4})
        self.assertEqual(response.status_code, 200)

    def test_submit_feedback_invalid_rating(self):
        url = f'/complaint/user/{self.complaint.id}/'
        response = self.client.post(url, {'feedback': 'Nice', 'rating': 10})
        self.assertEqual(response.status_code, 400)


class DeleteComplaintAPITest(APITestCase):
    """Test complaint deletion with ownership (V-26)."""

    def setUp(self):
        self.client = APIClient()
        self.owner = User.objects.create_user(username='del_owner', password='test')
        self.other = User.objects.create_user(username='del_other', password='test')
        self.owner_extra = ExtraInfo.objects.create(
            user=self.owner, id='DO001', user_type='student'
        )
        self.other_extra = ExtraInfo.objects.create(
            user=self.other, id='DO002', user_type='student'
        )
        self.complaint = StudentComplain.objects.create(
            complainer=self.owner_extra, complaint_type='internet',
            location='hall-1', details='Delete test', status=0,
        )

    def test_owner_delete(self):
        self.client.force_authenticate(user=self.owner)
        url = f'/complaint/caretaker/deletecomplaint/{self.complaint.id}/'
        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)

    def test_non_owner_delete_forbidden(self):
        self.client.force_authenticate(user=self.other)
        url = f'/complaint/caretaker/deletecomplaint/{self.complaint.id}/'
        response = self.client.post(url)
        self.assertEqual(response.status_code, 403)


class GenerateReportAPITest(APITestCase):
    """Test report generation endpoint (V-17)."""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='report_test', password='test')
        self.extra = ExtraInfo.objects.create(
            user=self.user, id='RP001', user_type='student'
        )

    def test_unauthorized_user_gets_403(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/complaint/generate-report/')
        self.assertEqual(response.status_code, 403)

    def test_caretaker_gets_report(self):
        care_user = User.objects.create_user(username='report_care', password='test')
        care_extra = ExtraInfo.objects.create(
            user=care_user, id='RC001', user_type='staff'
        )
        Caretaker.objects.create(staff_id=care_extra, area='hall-1')
        StudentComplain.objects.create(
            complainer=self.extra, complaint_type='internet',
            location='hall-1', details='Report test', status=0,
        )
        self.client.force_authenticate(user=care_user)
        response = self.client.get('/complaint/generate-report/')
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(len(response.data), 1)
