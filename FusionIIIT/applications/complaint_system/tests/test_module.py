from datetime import date, timedelta
from unittest.mock import patch, MagicMock

from django.test import TestCase, RequestFactory
from django.contrib.auth.models import User

from applications.globals.models import ExtraInfo
from applications.complaint_system.models import (
    Constants, Caretaker, Warden, StudentComplain,
    ServiceProvider, Complaint_Admin, Workers, SectionIncharge,
    AreaChoices, ComplaintTypeChoices, ComplaintStatus,
)
from applications.complaint_system import services, selectors
from applications.complaint_system.api.serializers import (
    FeedbackSerializer, StudentComplainSerializer,
    ResolvePendingSerializer, CaretakerSerializer,
    WorkersSerializer, ServiceProviderSerializer,
    ComplaintAdminSerializer,
)
from applications.complaint_system.permissions import (
    IsCaretaker, IsServiceProvider, IsCaretakerOrServiceProvider,
    IsComplaintOwnerOrStaff, IsReportAuthorized, IsSuperUser,
)


# ============================================================
#  Unit Tests: services.py helper functions
# ============================================================

class CalculateComplaintFinishDateTest(TestCase):

    def test_electricity_gets_2_days(self):
        result = services.calculate_complaint_finish_date('Electricity')
        expected = date.today() + timedelta(days=2)
        self.assertEqual(result, expected)

    def test_garbage_gets_1_day(self):
        result = services.calculate_complaint_finish_date('garbage')
        expected = date.today() + timedelta(days=1)
        self.assertEqual(result, expected)

    def test_internet_gets_4_days(self):
        result = services.calculate_complaint_finish_date('internet')
        expected = date.today() + timedelta(days=4)
        self.assertEqual(result, expected)

    def test_other_gets_3_days(self):
        result = services.calculate_complaint_finish_date('other')
        expected = date.today() + timedelta(days=3)
        self.assertEqual(result, expected)

    def test_unknown_type_gets_default_2_days(self):
        result = services.calculate_complaint_finish_date('unknown_type')
        expected = date.today() + timedelta(days=services.DEFAULT_FINISH_DAYS)
        self.assertEqual(result, expected)

    def test_carpenter_case_insensitive(self):
        result_lower = services.calculate_complaint_finish_date('carpenter')
        result_title = services.calculate_complaint_finish_date('Carpenter')
        self.assertEqual(result_lower, result_title)

    def test_dustbin_gets_1_day(self):
        result = services.calculate_complaint_finish_date('dustbin')
        expected = date.today() + timedelta(days=1)
        self.assertEqual(result, expected)


class ResolveLocationToDesignationTest(TestCase):

    def test_hall1_maps_correctly(self):
        self.assertEqual(services.resolve_location_to_designation('hall-1'), 'hall1caretaker')

    def test_hall3_maps_correctly(self):
        self.assertEqual(services.resolve_location_to_designation('hall-3'), 'hall3caretaker')

    def test_hall4_maps_correctly(self):
        self.assertEqual(services.resolve_location_to_designation('hall-4'), 'hall4caretaker')

    def test_cc1_maps_correctly(self):
        self.assertEqual(services.resolve_location_to_designation('CC1'), 'cc1convener')

    def test_cc2_maps_correctly(self):
        self.assertEqual(services.resolve_location_to_designation('CC2'), 'CC2 convener')

    def test_msh_maps_correctly(self):
        self.assertEqual(
            services.resolve_location_to_designation('Maa Saraswati Hostel'),
            'mshcaretaker',
        )

    def test_unknown_location_gets_default(self):
        self.assertEqual(
            services.resolve_location_to_designation('nonexistent'),
            services.DEFAULT_DESIGNATION,
        )


class UpdateCaretakerRatingTest(TestCase):

    def test_first_rating_sets_directly(self):
        caretaker = MagicMock()
        caretaker.rating = 0
        services._update_caretaker_rating(caretaker, 4)
        self.assertEqual(caretaker.rating, 4)
        caretaker.save.assert_called_once()

    def test_subsequent_rating_averages(self):
        caretaker = MagicMock()
        caretaker.rating = 4
        services._update_caretaker_rating(caretaker, 2)
        self.assertEqual(caretaker.rating, 3)  # int((2+4)/2)
        caretaker.save.assert_called_once()

    def test_rating_rounds_down(self):
        caretaker = MagicMock()
        caretaker.rating = 3
        services._update_caretaker_rating(caretaker, 2)
        self.assertEqual(caretaker.rating, 2)  # int((2+3)/2) = int(2.5) = 2
        caretaker.save.assert_called_once()


# ============================================================
#  Unit Tests: serializer validation
# ============================================================

class FeedbackSerializerTest(TestCase):

    def test_valid_feedback(self):
        data = {'feedback': 'Good job', 'rating': 3}
        s = FeedbackSerializer(data=data)
        self.assertTrue(s.is_valid())

    def test_rating_too_high(self):
        data = {'feedback': 'Good job', 'rating': 6}
        s = FeedbackSerializer(data=data)
        self.assertFalse(s.is_valid())
        self.assertIn('rating', s.errors)

    def test_rating_too_low(self):
        data = {'feedback': 'Good job', 'rating': -1}
        s = FeedbackSerializer(data=data)
        self.assertFalse(s.is_valid())
        self.assertIn('rating', s.errors)

    def test_rating_boundary_zero(self):
        data = {'feedback': 'OK', 'rating': 0}
        s = FeedbackSerializer(data=data)
        self.assertTrue(s.is_valid())

    def test_rating_boundary_five(self):
        data = {'feedback': 'Excellent', 'rating': 5}
        s = FeedbackSerializer(data=data)
        self.assertTrue(s.is_valid())

    def test_missing_feedback(self):
        data = {'rating': 3}
        s = FeedbackSerializer(data=data)
        self.assertFalse(s.is_valid())
        self.assertIn('feedback', s.errors)

    def test_missing_rating(self):
        data = {'feedback': 'Good'}
        s = FeedbackSerializer(data=data)
        self.assertFalse(s.is_valid())
        self.assertIn('rating', s.errors)

    def test_empty_feedback_rejected(self):
        data = {'feedback': '', 'rating': 3}
        s = FeedbackSerializer(data=data)
        self.assertFalse(s.is_valid())


class ResolvePendingSerializerTest(TestCase):

    def test_valid_yes(self):
        data = {'yesorno': 'Yes', 'comment': 'Done'}
        s = ResolvePendingSerializer(data=data)
        self.assertTrue(s.is_valid())

    def test_valid_no(self):
        data = {'yesorno': 'No', 'comment': 'Cannot fix'}
        s = ResolvePendingSerializer(data=data)
        self.assertTrue(s.is_valid())

    def test_invalid_choice(self):
        data = {'yesorno': 'Maybe'}
        s = ResolvePendingSerializer(data=data)
        self.assertFalse(s.is_valid())
        self.assertIn('yesorno', s.errors)

    def test_comment_optional(self):
        data = {'yesorno': 'Yes'}
        s = ResolvePendingSerializer(data=data)
        self.assertTrue(s.is_valid())

    def test_blank_comment_allowed(self):
        data = {'yesorno': 'No', 'comment': ''}
        s = ResolvePendingSerializer(data=data)
        self.assertTrue(s.is_valid())


# ============================================================
#  Unit Tests: services.py business logic (with mocked selectors)
# ============================================================

class DetermineUserTypeTest(TestCase):

    @patch('applications.complaint_system.services.selectors')
    def test_service_provider_detected(self, mock_selectors):
        user = MagicMock()
        extra = MagicMock()
        extra.id = 1
        extra.user_type = 'faculty'
        mock_selectors.get_extrainfo_by_user.return_value = extra
        mock_selectors.is_service_provider.return_value = True

        user_type, url = services.determine_user_type(user)
        self.assertEqual(user_type, 'service_provider')
        self.assertEqual(url, '/complaint/service_provider/')

    @patch('applications.complaint_system.services.selectors')
    def test_complaint_admin_detected(self, mock_selectors):
        user = MagicMock()
        extra = MagicMock()
        extra.id = 2
        extra.user_type = 'staff'
        mock_selectors.get_extrainfo_by_user.return_value = extra
        mock_selectors.is_service_provider.return_value = False
        mock_selectors.is_complaint_admin.return_value = True

        user_type, url = services.determine_user_type(user)
        self.assertEqual(user_type, 'complaint_admin')
        self.assertEqual(url, '/complaint/complaint_admin/')

    @patch('applications.complaint_system.services.selectors')
    def test_caretaker_detected(self, mock_selectors):
        user = MagicMock()
        extra = MagicMock()
        extra.id = 2
        extra.user_type = 'staff'
        mock_selectors.get_extrainfo_by_user.return_value = extra
        mock_selectors.is_service_provider.return_value = False
        mock_selectors.is_complaint_admin.return_value = False
        mock_selectors.is_caretaker.return_value = True

        user_type, url = services.determine_user_type(user)
        self.assertEqual(user_type, 'caretaker')
        self.assertEqual(url, '/complaint/caretaker/')

    @patch('applications.complaint_system.services.selectors')
    def test_warden_detected(self, mock_selectors):
        user = MagicMock()
        extra = MagicMock()
        extra.id = 4
        extra.user_type = 'faculty'
        mock_selectors.get_extrainfo_by_user.return_value = extra
        mock_selectors.is_service_provider.return_value = False
        mock_selectors.is_complaint_admin.return_value = False
        mock_selectors.is_caretaker.return_value = False
        mock_selectors.is_warden.return_value = True

        user_type, url = services.determine_user_type(user)
        self.assertEqual(user_type, 'warden')
        self.assertEqual(url, '/complaint/warden/')

    @patch('applications.complaint_system.services.selectors')
    def test_student_detected(self, mock_selectors):
        user = MagicMock()
        extra = MagicMock()
        extra.id = 3
        extra.user_type = 'student'
        mock_selectors.get_extrainfo_by_user.return_value = extra
        mock_selectors.is_service_provider.return_value = False
        mock_selectors.is_complaint_admin.return_value = False
        mock_selectors.is_caretaker.return_value = False
        mock_selectors.is_warden.return_value = False

        user_type, url = services.determine_user_type(user)
        self.assertEqual(user_type, 'student')
        self.assertEqual(url, '/complaint/user/')

    @patch('applications.complaint_system.services.selectors')
    def test_faculty_detected(self, mock_selectors):
        user = MagicMock()
        extra = MagicMock()
        extra.id = 5
        extra.user_type = 'faculty'
        mock_selectors.get_extrainfo_by_user.return_value = extra
        mock_selectors.is_service_provider.return_value = False
        mock_selectors.is_complaint_admin.return_value = False
        mock_selectors.is_caretaker.return_value = False
        mock_selectors.is_warden.return_value = False

        user_type, url = services.determine_user_type(user)
        self.assertEqual(user_type, 'faculty')
        self.assertEqual(url, '/complaint/user/')

    @patch('applications.complaint_system.services.selectors')
    def test_no_extrainfo_returns_none(self, mock_selectors):
        user = MagicMock()
        mock_selectors.get_extrainfo_by_user.return_value = None

        user_type, url = services.determine_user_type(user)
        self.assertIsNone(user_type)
        self.assertIsNone(url)

    @patch('applications.complaint_system.services.selectors')
    def test_unknown_user_type_returns_none(self, mock_selectors):
        user = MagicMock()
        extra = MagicMock()
        extra.id = 6
        extra.user_type = 'unknown'
        mock_selectors.get_extrainfo_by_user.return_value = extra
        mock_selectors.is_service_provider.return_value = False
        mock_selectors.is_complaint_admin.return_value = False
        mock_selectors.is_caretaker.return_value = False
        mock_selectors.is_warden.return_value = False

        user_type, url = services.determine_user_type(user)
        self.assertIsNone(user_type)
        self.assertIsNone(url)


class ChangeComplaintStatusTest(TestCase):

    @patch('applications.complaint_system.services.selectors')
    def test_status_resolved_clears_worker(self, mock_selectors):
        complaint = MagicMock()
        mock_selectors.get_complaint_by_id_basic.return_value = complaint

        services.change_complaint_status(1, '2')
        self.assertEqual(complaint.status, '2')
        self.assertIsNone(complaint.worker_id)
        complaint.save.assert_called_once()

    @patch('applications.complaint_system.services.selectors')
    def test_status_declined_clears_worker(self, mock_selectors):
        complaint = MagicMock()
        mock_selectors.get_complaint_by_id_basic.return_value = complaint

        services.change_complaint_status(1, '3')
        self.assertEqual(complaint.status, '3')
        self.assertIsNone(complaint.worker_id)
        complaint.save.assert_called_once()

    @patch('applications.complaint_system.services.selectors')
    def test_status_in_progress_keeps_worker(self, mock_selectors):
        complaint = MagicMock()
        complaint.worker_id = MagicMock()
        mock_selectors.get_complaint_by_id_basic.return_value = complaint

        services.change_complaint_status(1, '1')
        self.assertEqual(complaint.status, '1')
        self.assertIsNotNone(complaint.worker_id)
        complaint.save.assert_called_once()


class DeleteComplaintTest(TestCase):

    @patch('applications.complaint_system.services.selectors')
    def test_owner_can_delete(self, mock_selectors):
        complaint = MagicMock()
        complaint.complainer_id = 'user123'
        extra = MagicMock()
        extra.id = 'user123'
        mock_selectors.get_complaint_by_id_basic.return_value = complaint
        mock_selectors.get_extrainfo_by_user.return_value = extra
        mock_selectors.is_caretaker.return_value = False
        mock_selectors.is_complaint_admin.return_value = False

        success, msg = services.delete_complaint(1, MagicMock())
        self.assertTrue(success)
        complaint.delete.assert_called_once()

    @patch('applications.complaint_system.services.selectors')
    def test_non_owner_non_staff_cannot_delete(self, mock_selectors):
        complaint = MagicMock()
        complaint.complainer_id = 'owner123'
        extra = MagicMock()
        extra.id = 'other_user'
        mock_selectors.get_complaint_by_id_basic.return_value = complaint
        mock_selectors.get_extrainfo_by_user.return_value = extra
        mock_selectors.is_caretaker.return_value = False
        mock_selectors.is_complaint_admin.return_value = False

        success, msg = services.delete_complaint(1, MagicMock())
        self.assertFalse(success)
        complaint.delete.assert_not_called()

    @patch('applications.complaint_system.services.selectors')
    def test_caretaker_can_delete(self, mock_selectors):
        complaint = MagicMock()
        complaint.complainer_id = 'owner123'
        extra = MagicMock()
        extra.id = 'caretaker_user'
        mock_selectors.get_complaint_by_id_basic.return_value = complaint
        mock_selectors.get_extrainfo_by_user.return_value = extra
        mock_selectors.is_caretaker.return_value = True
        mock_selectors.is_complaint_admin.return_value = False

        success, msg = services.delete_complaint(1, MagicMock())
        self.assertTrue(success)
        complaint.delete.assert_called_once()

    @patch('applications.complaint_system.services.selectors')
    def test_complaint_admin_can_delete(self, mock_selectors):
        complaint = MagicMock()
        complaint.complainer_id = 'owner123'
        extra = MagicMock()
        extra.id = 'admin_user'
        mock_selectors.get_complaint_by_id_basic.return_value = complaint
        mock_selectors.get_extrainfo_by_user.return_value = extra
        mock_selectors.is_caretaker.return_value = False
        mock_selectors.is_complaint_admin.return_value = True

        success, msg = services.delete_complaint(1, MagicMock())
        self.assertTrue(success)
        complaint.delete.assert_called_once()


class RemoveWorkerTest(TestCase):

    @patch('applications.complaint_system.services.selectors')
    def test_unassigned_worker_removed(self, mock_selectors):
        worker = MagicMock()
        mock_selectors.get_worker_by_id.return_value = worker
        mock_selectors.get_complaints_assigned_to_worker.return_value = 0

        success, msg = services.remove_worker(1)
        self.assertTrue(success)
        worker.delete.assert_called_once()

    @patch('applications.complaint_system.services.selectors')
    def test_assigned_worker_not_removed(self, mock_selectors):
        worker = MagicMock()
        mock_selectors.get_worker_by_id.return_value = worker
        mock_selectors.get_complaints_assigned_to_worker.return_value = 3

        success, msg = services.remove_worker(1)
        self.assertFalse(success)
        worker.delete.assert_not_called()


class ResolveComplaintTest(TestCase):

    @patch('applications.complaint_system.services.complaint_system_notif')
    @patch('applications.complaint_system.services.selectors')
    def test_resolve_yes_sets_status_resolved(self, mock_selectors, mock_notif):
        complaint = MagicMock()
        mock_selectors.get_complaint_by_id_basic.return_value = complaint
        complainer_detail = MagicMock()
        complainer_detail.complainer.user = MagicMock()
        complainer_detail.id = 1
        mock_selectors.get_complaint_by_id.return_value = complainer_detail

        result = services.resolve_complaint(
            cid=1, yesorno='Yes', comment='Fixed',
            upload_file=None, requesting_user=MagicMock()
        )
        self.assertEqual(complaint.status, ComplaintStatus.RESOLVED)
        self.assertEqual(complaint.comment, 'Fixed')
        complaint.save.assert_called_once()
        self.assertEqual(result, {'success': 'Complaint status updated'})

    @patch('applications.complaint_system.services.complaint_system_notif')
    @patch('applications.complaint_system.services.selectors')
    def test_resolve_no_sets_status_declined(self, mock_selectors, mock_notif):
        complaint = MagicMock()
        mock_selectors.get_complaint_by_id_basic.return_value = complaint
        complainer_detail = MagicMock()
        complainer_detail.complainer.user = MagicMock()
        complainer_detail.id = 1
        mock_selectors.get_complaint_by_id.return_value = complainer_detail

        result = services.resolve_complaint(
            cid=1, yesorno='No', comment='Cannot do',
            upload_file=None, requesting_user=MagicMock()
        )
        self.assertEqual(complaint.status, ComplaintStatus.DECLINED)
        complaint.save.assert_called_once()

    @patch('applications.complaint_system.services.complaint_system_notif')
    @patch('applications.complaint_system.services.selectors')
    def test_resolve_with_upload(self, mock_selectors, mock_notif):
        complaint = MagicMock()
        mock_selectors.get_complaint_by_id_basic.return_value = complaint
        complainer_detail = MagicMock()
        complainer_detail.complainer.user = MagicMock()
        complainer_detail.id = 1
        mock_selectors.get_complaint_by_id.return_value = complainer_detail

        fake_file = MagicMock()
        services.resolve_complaint(
            cid=1, yesorno='Yes', comment='Done',
            upload_file=fake_file, requesting_user=MagicMock()
        )
        self.assertEqual(complaint.upload_resolved, fake_file)


class SubmitComplaintFeedbackTest(TestCase):

    @patch('applications.complaint_system.services.selectors')
    def test_feedback_updates_complaint_and_caretaker(self, mock_selectors):
        complaint = MagicMock()
        complaint.location = 'hall-1'
        mock_selectors.get_complaint_by_id.return_value = complaint
        caretaker = MagicMock()
        caretaker.rating = 4
        mock_selectors.get_caretaker_by_area.return_value = caretaker

        services.submit_complaint_feedback(1, 'Good', 3)

        mock_selectors.update_complaint_feedback.assert_called_once_with(1, 'Good', 3)
        self.assertEqual(caretaker.rating, 3)  # int((3+4)/2)

    @patch('applications.complaint_system.services.selectors')
    def test_feedback_no_caretaker_still_updates(self, mock_selectors):
        complaint = MagicMock()
        complaint.location = 'unknown'
        mock_selectors.get_complaint_by_id.return_value = complaint
        mock_selectors.get_caretaker_by_area.return_value = None

        services.submit_complaint_feedback(1, 'OK', 2)
        mock_selectors.update_complaint_feedback.assert_called_once_with(1, 'OK', 2)


# ============================================================
#  Unit Tests: permissions.py
# ============================================================

class PermissionTests(TestCase):

    def setUp(self):
        self.factory = RequestFactory()

    @patch('applications.complaint_system.selectors.get_extrainfo_by_user')
    @patch('applications.complaint_system.selectors.is_caretaker')
    def test_is_caretaker_allows_caretaker(self, mock_is_ct, mock_get_extra):
        extra = MagicMock()
        extra.id = 1
        mock_get_extra.return_value = extra
        mock_is_ct.return_value = True

        request = self.factory.get('/')
        request.user = MagicMock()
        perm = IsCaretaker()
        self.assertTrue(perm.has_permission(request, None))

    @patch('applications.complaint_system.selectors.get_extrainfo_by_user')
    @patch('applications.complaint_system.selectors.is_caretaker')
    def test_is_caretaker_denies_non_caretaker(self, mock_is_ct, mock_get_extra):
        extra = MagicMock()
        extra.id = 1
        mock_get_extra.return_value = extra
        mock_is_ct.return_value = False

        request = self.factory.get('/')
        request.user = MagicMock()
        perm = IsCaretaker()
        self.assertFalse(perm.has_permission(request, None))

    @patch('applications.complaint_system.selectors.get_extrainfo_by_user')
    def test_is_caretaker_denies_no_extrainfo(self, mock_get_extra):
        mock_get_extra.return_value = None

        request = self.factory.get('/')
        request.user = MagicMock()
        perm = IsCaretaker()
        self.assertFalse(perm.has_permission(request, None))

    @patch('applications.complaint_system.selectors.get_extrainfo_by_user')
    @patch('applications.complaint_system.selectors.is_service_provider')
    def test_is_service_provider_allows(self, mock_is_sp, mock_get_extra):
        extra = MagicMock()
        extra.id = 1
        mock_get_extra.return_value = extra
        mock_is_sp.return_value = True

        request = self.factory.get('/')
        request.user = MagicMock()
        perm = IsServiceProvider()
        self.assertTrue(perm.has_permission(request, None))

    @patch('applications.complaint_system.selectors.get_extrainfo_by_user')
    @patch('applications.complaint_system.selectors.is_service_provider')
    def test_is_service_provider_denies(self, mock_is_sp, mock_get_extra):
        extra = MagicMock()
        extra.id = 1
        mock_get_extra.return_value = extra
        mock_is_sp.return_value = False

        request = self.factory.get('/')
        request.user = MagicMock()
        perm = IsServiceProvider()
        self.assertFalse(perm.has_permission(request, None))

    def test_is_complaint_owner_or_staff_requires_auth(self):
        request = self.factory.get('/')
        request.user = MagicMock()
        request.user.is_authenticated = True
        perm = IsComplaintOwnerOrStaff()
        self.assertTrue(perm.has_permission(request, None))

    def test_is_complaint_owner_or_staff_denies_anon(self):
        request = self.factory.get('/')
        request.user = MagicMock()
        request.user.is_authenticated = False
        perm = IsComplaintOwnerOrStaff()
        self.assertFalse(perm.has_permission(request, None))

    @patch('applications.complaint_system.selectors.get_extrainfo_by_user')
    @patch('applications.complaint_system.selectors.is_caretaker')
    @patch('applications.complaint_system.selectors.is_service_provider')
    def test_caretaker_or_sp_allows_caretaker(self, mock_is_sp, mock_is_ct, mock_get_extra):
        extra = MagicMock()
        extra.id = 1
        mock_get_extra.return_value = extra
        mock_is_ct.return_value = True
        mock_is_sp.return_value = False

        request = self.factory.get('/')
        request.user = MagicMock()
        perm = IsCaretakerOrServiceProvider()
        self.assertTrue(perm.has_permission(request, None))

    @patch('applications.complaint_system.selectors.get_extrainfo_by_user')
    @patch('applications.complaint_system.selectors.is_caretaker')
    @patch('applications.complaint_system.selectors.is_service_provider')
    def test_caretaker_or_sp_allows_sp(self, mock_is_sp, mock_is_ct, mock_get_extra):
        extra = MagicMock()
        extra.id = 1
        mock_get_extra.return_value = extra
        mock_is_ct.return_value = False
        mock_is_sp.return_value = True

        request = self.factory.get('/')
        request.user = MagicMock()
        perm = IsCaretakerOrServiceProvider()
        self.assertTrue(perm.has_permission(request, None))

    @patch('applications.complaint_system.selectors.get_extrainfo_by_user')
    @patch('applications.complaint_system.selectors.is_caretaker')
    @patch('applications.complaint_system.selectors.is_service_provider')
    def test_caretaker_or_sp_denies_neither(self, mock_is_sp, mock_is_ct, mock_get_extra):
        extra = MagicMock()
        extra.id = 1
        mock_get_extra.return_value = extra
        mock_is_ct.return_value = False
        mock_is_sp.return_value = False

        request = self.factory.get('/')
        request.user = MagicMock()
        perm = IsCaretakerOrServiceProvider()
        self.assertFalse(perm.has_permission(request, None))

    def test_is_superuser_allows(self):
        request = self.factory.get('/')
        request.user = MagicMock()
        request.user.is_superuser = True
        perm = IsSuperUser()
        self.assertTrue(perm.has_permission(request, None))

    def test_is_superuser_denies(self):
        request = self.factory.get('/')
        request.user = MagicMock()
        request.user.is_superuser = False
        perm = IsSuperUser()
        self.assertFalse(perm.has_permission(request, None))

    @patch('applications.complaint_system.selectors.get_extrainfo_by_user')
    @patch('applications.complaint_system.selectors.is_caretaker')
    @patch('applications.complaint_system.selectors.is_service_provider')
    @patch('applications.complaint_system.selectors.is_complaint_admin')
    @patch('applications.complaint_system.selectors.is_warden')
    def test_is_report_authorized_allows_warden(
        self, mock_warden, mock_admin, mock_sp, mock_ct, mock_get_extra
    ):
        extra = MagicMock()
        extra.id = 1
        mock_get_extra.return_value = extra
        mock_ct.return_value = False
        mock_sp.return_value = False
        mock_admin.return_value = False
        mock_warden.return_value = True

        request = self.factory.get('/')
        request.user = MagicMock()
        perm = IsReportAuthorized()
        self.assertTrue(perm.has_permission(request, None))

    @patch('applications.complaint_system.selectors.get_extrainfo_by_user')
    @patch('applications.complaint_system.selectors.is_caretaker')
    @patch('applications.complaint_system.selectors.is_service_provider')
    @patch('applications.complaint_system.selectors.is_complaint_admin')
    @patch('applications.complaint_system.selectors.is_warden')
    def test_is_report_authorized_denies_student(
        self, mock_warden, mock_admin, mock_sp, mock_ct, mock_get_extra
    ):
        extra = MagicMock()
        extra.id = 1
        mock_get_extra.return_value = extra
        mock_ct.return_value = False
        mock_sp.return_value = False
        mock_admin.return_value = False
        mock_warden.return_value = False

        request = self.factory.get('/')
        request.user = MagicMock()
        perm = IsReportAuthorized()
        self.assertFalse(perm.has_permission(request, None))


# ============================================================
#  Constants / Model-level tests
# ============================================================

class ConstantsAndChoicesTest(TestCase):

    def test_area_choices_are_tuples(self):
        for choice in Constants.AREA:
            self.assertEqual(len(choice), 2)

    def test_complaint_type_choices_are_tuples(self):
        for choice in Constants.COMPLAINT_TYPE:
            self.assertEqual(len(choice), 2)

    def test_complaint_type_days_covers_all_types(self):
        for choice_value, _ in Constants.COMPLAINT_TYPE:
            self.assertIn(
                choice_value,
                services.COMPLAINT_TYPE_DAYS,
                f"COMPLAINT_TYPE_DAYS missing entry for '{choice_value}'",
            )

    def test_area_choices_text_choices_match_constants(self):
        self.assertEqual(AreaChoices.choices, Constants.AREA)

    def test_complaint_type_text_choices_match_constants(self):
        self.assertEqual(ComplaintTypeChoices.choices, Constants.COMPLAINT_TYPE)

    def test_complaint_status_values(self):
        self.assertEqual(ComplaintStatus.PENDING, 0)
        self.assertEqual(ComplaintStatus.FORWARDED, 1)
        self.assertEqual(ComplaintStatus.RESOLVED, 2)
        self.assertEqual(ComplaintStatus.DECLINED, 3)


# ============================================================
#  Integration-style tests: services with mocked external deps
# ============================================================

class GetComplaintsForUserTest(TestCase):

    @patch('applications.complaint_system.services.selectors')
    def test_student_gets_own_complaints(self, mock_selectors):
        user = MagicMock()
        extra = MagicMock()
        extra.user_type = 'student'
        mock_selectors.get_extrainfo_by_user.return_value = extra
        mock_selectors.get_complaints_by_complainer.return_value = ['c1', 'c2']

        result = services.get_complaints_for_user(user)
        self.assertEqual(result, ['c1', 'c2'])
        mock_selectors.get_complaints_by_complainer.assert_called_once_with(extra)

    @patch('applications.complaint_system.services.selectors')
    def test_staff_gets_location_complaints(self, mock_selectors):
        user = MagicMock()
        extra = MagicMock()
        extra.user_type = 'staff'
        extra.id = 10
        caretaker = MagicMock()
        caretaker.area = 'hall-1'
        mock_selectors.get_extrainfo_by_user.return_value = extra
        mock_selectors.get_caretaker_by_staff_id.return_value = caretaker
        mock_selectors.get_complaints_by_location.return_value = ['c3']

        result = services.get_complaints_for_user(user)
        self.assertEqual(result, ['c3'])
        mock_selectors.get_complaints_by_location.assert_called_once_with('hall-1')

    @patch('applications.complaint_system.services.selectors')
    def test_unknown_type_gets_empty(self, mock_selectors):
        user = MagicMock()
        extra = MagicMock()
        extra.user_type = 'unknown'
        mock_selectors.get_extrainfo_by_user.return_value = extra
        mock_selectors.get_empty_complaints_queryset.return_value = []

        result = services.get_complaints_for_user(user)
        self.assertEqual(result, [])
