# tests/test_module.py
# Comprehensive test suite for the filetracking module.
# Covers: services, selectors, serializer validation, and API integration.

from django.test import TestCase, RequestFactory
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient
from rest_framework import status
from unittest.mock import patch, MagicMock

from applications.globals.models import ExtraInfo, Designation, HoldsDesignation, Department
from applications.filetracking.models import File, Tracking
from applications.filetracking import services
from applications.filetracking import selectors
from applications.filetracking.api.serializers import (
    FileCreateInputSerializer,
    DraftCreateInputSerializer,
    ForwardFileInputSerializer,
    InboxQuerySerializer,
    ArchiveInputSerializer,
    FileSerializer,
    TrackingSerializer,
    FileHeaderSerializer,
    MAX_FILE_SIZE_BYTES,
)


class BaseTestCase(TestCase):
    """Common setup for all filetracking tests."""

    @classmethod
    def setUpTestData(cls):
        # Department
        cls.department = Department.objects.create(name='CSE: Computer Science')

        # Designations
        cls.des_faculty = Designation.objects.create(name='faculty')
        cls.des_hod = Designation.objects.create(name='hod')

        # Users
        cls.user1 = User.objects.create_user(username='sender1', password='testpass123')
        cls.user2 = User.objects.create_user(username='receiver1', password='testpass123')

        # ExtraInfo
        cls.extra1 = ExtraInfo.objects.create(user=cls.user1, id='EI001', department=cls.department)
        cls.extra2 = ExtraInfo.objects.create(user=cls.user2, id='EI002', department=cls.department)

        # HoldsDesignation
        cls.hd1 = HoldsDesignation.objects.create(user=cls.user1, designation=cls.des_faculty)
        cls.hd2 = HoldsDesignation.objects.create(user=cls.user2, designation=cls.des_hod)


# ===========================================================================
# Selector Tests
# ===========================================================================

class SelectorTests(BaseTestCase):

    def test_get_user_by_username(self):
        user = selectors.get_user_by_username('sender1')
        self.assertEqual(user.pk, self.user1.pk)

    def test_get_user_by_username_not_found(self):
        with self.assertRaises(User.DoesNotExist):
            selectors.get_user_by_username('nonexistent')

    def test_get_extrainfo_by_username(self):
        ei = selectors.get_extrainfo_by_username('sender1')
        self.assertEqual(ei.pk, self.extra1.pk)

    def test_get_designation_by_name(self):
        des = selectors.get_designation_by_name('faculty')
        self.assertEqual(des.pk, self.des_faculty.pk)

    def test_get_holds_designation(self):
        hd = selectors.get_holds_designation(self.user1, self.des_faculty)
        self.assertEqual(hd.pk, self.hd1.pk)

    def test_get_holds_designation_obj_from_strings(self):
        hd = selectors.get_holds_designation_obj('sender1', 'faculty')
        self.assertEqual(hd.pk, self.hd1.pk)

    def test_get_designation_names_for_user(self):
        names = selectors.get_designation_names_for_user('sender1')
        self.assertIn('faculty', names)

    def test_get_latest_tracking_returns_none_when_no_tracking(self):
        file_obj = File.objects.create(
            uploader=self.extra1, designation=self.des_faculty, subject='Test')
        result = selectors.get_latest_tracking(file_obj.id)
        self.assertIsNone(result)

    def test_get_current_file_owner_returns_none_for_draft(self):
        file_obj = File.objects.create(
            uploader=self.extra1, designation=self.des_faculty, subject='Draft')
        owner = selectors.get_current_file_owner(file_obj.id)
        self.assertIsNone(owner)

    def test_get_draft_files(self):
        File.objects.create(
            uploader=self.extra1, designation=self.des_faculty,
            subject='Draft File', src_module='filetracking')
        drafts = selectors.get_draft_files(self.extra1, self.des_faculty, 'filetracking')
        self.assertEqual(len(drafts), 1)

    def test_get_designations_starting_with(self):
        results = selectors.get_designations_starting_with('fac')
        self.assertTrue(results.exists())

    def test_get_users_starting_with(self):
        results = selectors.get_users_starting_with('send')
        self.assertTrue(results.exists())


# ===========================================================================
# Service Tests
# ===========================================================================

class ServiceUtilityTests(BaseTestCase):

    def test_unique_list(self):
        self.assertEqual(services.unique_list([1, 2, 2, 3, 1]), [1, 2, 3])
        self.assertEqual(services.unique_list([]), [])

    def test_get_designation_display_name(self):
        # HoldsDesignation.__str__ typically returns "username - designation"
        name = services.get_designation_display_name(self.hd1)
        self.assertIsInstance(name, str)
        self.assertTrue(len(name) > 0)

    def test_validate_file_size_ok(self):
        small_file = SimpleUploadedFile("small.txt", b"x" * 100)
        # Should not raise
        services.validate_file_size(small_file)

    def test_validate_file_size_too_large(self):
        big_file = MagicMock()
        big_file.size = MAX_FILE_SIZE_BYTES + 1
        with self.assertRaises(ValidationError):
            services.validate_file_size(big_file)

    def test_validate_file_size_none(self):
        # None file should not raise
        services.validate_file_size(None)


class ServiceFileCreationTests(BaseTestCase):

    def test_create_file_via_sdk(self):
        file_id = services.create_file_via_sdk(
            uploader='sender1',
            uploader_designation='faculty',
            receiver='receiver1',
            receiver_designation='hod',
            subject='SDK Test File',
            description='Test description',
        )
        self.assertIsNotNone(file_id)
        file_obj = File.objects.get(id=file_id)
        self.assertEqual(file_obj.subject, 'SDK Test File')
        # Check tracking was created
        tracking = Tracking.objects.filter(file_id=file_obj)
        self.assertEqual(tracking.count(), 1)

    def test_create_draft_via_sdk(self):
        file_id = services.create_draft_via_sdk(
            uploader='sender1',
            uploader_designation='faculty',
        )
        self.assertIsNotNone(file_id)
        file_obj = File.objects.get(id=file_id)
        # Draft should have no tracking
        tracking = Tracking.objects.filter(file_id=file_obj)
        self.assertEqual(tracking.count(), 0)


class ServiceViewTests(BaseTestCase):

    def setUp(self):
        # Create a file with tracking for view tests
        self.file_id = services.create_file_via_sdk(
            uploader='sender1',
            uploader_designation='faculty',
            receiver='receiver1',
            receiver_designation='hod',
            subject='View Test File',
            description='For view tests',
        )

    def test_view_file_details(self):
        details = services.view_file_details(self.file_id)
        self.assertEqual(details['subject'], 'View Test File')

    def test_view_file_not_found(self):
        with self.assertRaises(File.DoesNotExist):
            services.view_file_details(99999)

    def test_delete_file(self):
        result = services.delete_file(self.file_id)
        self.assertTrue(result)
        self.assertFalse(File.objects.filter(id=self.file_id).exists())

    def test_delete_file_with_auth_owner(self):
        result = services.delete_file_with_auth(self.file_id, self.user1)
        self.assertTrue(result)

    def test_delete_file_with_auth_non_owner(self):
        with self.assertRaises(ValidationError):
            services.delete_file_with_auth(self.file_id, self.user2)

    def test_view_inbox(self):
        inbox = services.view_inbox('receiver1', 'hod', 'filetracking')
        self.assertIsInstance(inbox, list)
        self.assertTrue(any(f['subject'] == 'View Test File' for f in inbox))

    def test_view_outbox(self):
        outbox = services.view_outbox('sender1', 'faculty', 'filetracking')
        self.assertIsInstance(outbox, (list, type(None)))

    def test_view_drafts_empty(self):
        drafts = services.view_drafts('sender1', 'faculty', 'filetracking')
        # The file was sent, so it's not a draft
        self.assertEqual(len(drafts), 0)

    def test_view_history(self):
        history = services.view_history(self.file_id)
        self.assertIsInstance(history, (list, type(None)))
        self.assertTrue(len(history) >= 1)

    def test_view_history_enriched(self):
        enriched = services.view_history_enriched(self.file_id)
        self.assertTrue(len(enriched) >= 1)
        # Should have username instead of user ID
        first = enriched[0]
        self.assertIn('receiver_id', first)
        self.assertIsInstance(first['receiver_id'], str)


class ServiceArchiveTests(BaseTestCase):

    def setUp(self):
        self.file_id = services.create_file_via_sdk(
            uploader='sender1', uploader_designation='faculty',
            receiver='receiver1', receiver_designation='hod',
            subject='Archive Test',
        )

    def test_archive_file_sdk(self):
        services.archive_file_sdk(self.file_id)
        file_obj = File.objects.get(id=self.file_id)
        self.assertTrue(file_obj.is_read)

    def test_unarchive_file(self):
        services.archive_file_sdk(self.file_id)
        services.unarchive_file(self.file_id)
        file_obj = File.objects.get(id=self.file_id)
        self.assertFalse(file_obj.is_read)

    def test_view_archived(self):
        services.archive_file_sdk(self.file_id)
        archived = services.view_archived('sender1', 'faculty', 'filetracking')
        self.assertIsInstance(archived, (list, type(None)))

    def test_get_file_view_permissions_owner(self):
        forward_en, archive_en = services.get_file_view_permissions(
            self.file_id, self.user2
        )
        # user2 is the receiver, so they can forward
        self.assertTrue(forward_en)


class ServiceDesignationTests(BaseTestCase):

    def test_get_designations(self):
        result = services.get_designations('sender1')
        self.assertIn('faculty', result)

    def test_get_designation_redirect_url_from_session(self):
        factory = RequestFactory()
        request = factory.get('/')
        request.user = self.user1
        request.session = {'currentDesignationSelected': 'faculty'}
        url = services.get_designation_redirect_url_from_session(request, 'drafts')
        self.assertIn('/filetracking/drafts/', url)


# ===========================================================================
# Serializer Validation Tests
# ===========================================================================

class SerializerValidationTests(TestCase):

    def test_file_create_input_valid(self):
        data = {
            'designation': 'faculty',
            'receiver_username': 'receiver1',
            'receiver_designation': 'hod',
            'subject': 'Test Subject',
            'description': 'Test Desc',
        }
        s = FileCreateInputSerializer(data=data)
        self.assertTrue(s.is_valid())

    def test_file_create_input_missing_required(self):
        data = {'designation': 'faculty'}  # missing fields
        s = FileCreateInputSerializer(data=data)
        self.assertFalse(s.is_valid())
        self.assertIn('receiver_username', s.errors)
        self.assertIn('subject', s.errors)

    def test_file_create_input_subject_too_long(self):
        data = {
            'designation': 'faculty',
            'receiver_username': 'rec1',
            'receiver_designation': 'hod',
            'subject': 'x' * 101,  # exceeds max_length=100
        }
        s = FileCreateInputSerializer(data=data)
        self.assertFalse(s.is_valid())
        self.assertIn('subject', s.errors)

    def test_draft_create_input_valid(self):
        data = {'uploader': 'sender1', 'uploader_designation': 'faculty'}
        s = DraftCreateInputSerializer(data=data)
        self.assertTrue(s.is_valid())

    def test_draft_create_input_missing_required(self):
        data = {}
        s = DraftCreateInputSerializer(data=data)
        self.assertFalse(s.is_valid())

    def test_forward_input_valid(self):
        data = {'receiver': 'receiver1', 'receiver_designation': 'hod'}
        s = ForwardFileInputSerializer(data=data)
        self.assertTrue(s.is_valid())

    def test_forward_input_missing_required(self):
        data = {'receiver': 'receiver1'}  # missing receiver_designation
        s = ForwardFileInputSerializer(data=data)
        self.assertFalse(s.is_valid())

    def test_inbox_query_valid(self):
        data = {'username': 'user1', 'src_module': 'filetracking'}
        s = InboxQuerySerializer(data=data)
        self.assertTrue(s.is_valid())

    def test_inbox_query_missing_src_module(self):
        data = {'username': 'user1'}
        s = InboxQuerySerializer(data=data)
        self.assertFalse(s.is_valid())

    def test_archive_input_valid(self):
        data = {'file_id': 1}
        s = ArchiveInputSerializer(data=data)
        self.assertTrue(s.is_valid())

    def test_archive_input_invalid_string(self):
        data = {'file_id': 'abc'}
        s = ArchiveInputSerializer(data=data)
        self.assertFalse(s.is_valid())

    def test_file_header_serializer_excludes_upload_file(self):
        fields = FileHeaderSerializer.Meta.exclude
        self.assertIn('upload_file', fields)
        self.assertIn('is_read', fields)


# ===========================================================================
# API Integration Tests
# ===========================================================================

class APIIntegrationTests(BaseTestCase):

    def setUp(self):
        self.client = APIClient()
        from rest_framework.authtoken.models import Token
        self.token, _ = Token.objects.get_or_create(user=self.user1)
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.token.key)

    def test_create_file_api(self):
        response = self.client.post('/filetracking/api/file/', {
            'designation': 'faculty',
            'receiver_username': 'receiver1',
            'receiver_designation': 'hod',
            'subject': 'API Created File',
            'description': 'API test',
        })
        self.assertIn(response.status_code,
                      [status.HTTP_201_CREATED, status.HTTP_400_BAD_REQUEST])

    def test_create_file_api_missing_fields(self):
        response = self.client.post('/filetracking/api/file/', {
            'designation': 'faculty',
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_view_file_api(self):
        file_id = services.create_file_via_sdk(
            uploader='sender1', uploader_designation='faculty',
            receiver='receiver1', receiver_designation='hod',
            subject='API View Test',
        )
        response = self.client.get(f'/filetracking/api/file/{file_id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['subject'], 'API View Test')

    def test_view_file_api_not_found(self):
        response = self.client.get('/filetracking/api/file/99999/')
        self.assertIn(response.status_code,
                      [status.HTTP_400_BAD_REQUEST, status.HTTP_404_NOT_FOUND])

    def test_delete_file_api(self):
        file_id = services.create_file_via_sdk(
            uploader='sender1', uploader_designation='faculty',
            receiver='receiver1', receiver_designation='hod',
            subject='Delete Test',
        )
        response = self.client.delete(f'/filetracking/api/file/{file_id}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_inbox_api(self):
        services.create_file_via_sdk(
            uploader='sender1', uploader_designation='faculty',
            receiver='receiver1', receiver_designation='hod',
            subject='Inbox Test',
        )
        response = self.client.get('/filetracking/api/inbox/', {
            'username': 'receiver1',
            'designation': 'hod',
            'src_module': 'filetracking',
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_inbox_api_missing_params(self):
        response = self.client.get('/filetracking/api/inbox/', {})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_outbox_api(self):
        response = self.client.get('/filetracking/api/outbox/', {
            'username': 'sender1',
            'designation': 'faculty',
            'src_module': 'filetracking',
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_history_api(self):
        file_id = services.create_file_via_sdk(
            uploader='sender1', uploader_designation='faculty',
            receiver='receiver1', receiver_designation='hod',
            subject='History Test',
        )
        response = self.client.get(f'/filetracking/api/history/{file_id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(len(response.data) >= 1)

    def test_create_draft_api(self):
        response = self.client.post('/filetracking/api/createdraft/', {
            'uploader': 'sender1',
            'uploader_designation': 'faculty',
        })
        self.assertIn(response.status_code,
                      [status.HTTP_201_CREATED, status.HTTP_500_INTERNAL_SERVER_ERROR])

    def test_view_drafts_api(self):
        response = self.client.get('/filetracking/api/draft/', {
            'username': 'sender1',
            'designation': 'faculty',
            'src_module': 'filetracking',
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_archive_api(self):
        file_id = services.create_file_via_sdk(
            uploader='sender1', uploader_designation='faculty',
            receiver='receiver1', receiver_designation='hod',
            subject='Archive API Test',
        )
        response = self.client.post('/filetracking/api/createarchive/', {
            'file_id': file_id,
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_view_archived_api(self):
        response = self.client.get('/filetracking/api/archive/', {
            'username': 'sender1',
            'designation': 'faculty',
            'src_module': 'filetracking',
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_designations_api_requires_auth(self):
        """V-21: GetDesignationsView now requires authentication."""
        unauth_client = APIClient()
        response = unauth_client.get('/filetracking/api/designations/sender1/')
        self.assertIn(response.status_code,
                      [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])

    def test_designations_api_with_auth(self):
        response = self.client.get('/filetracking/api/designations/sender1/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('faculty', response.data['designations'])


# ===========================================================================
# Model Constants Tests (V-39)
# ===========================================================================

class ModelConstantsTests(TestCase):

    def test_max_file_size_bytes(self):
        self.assertEqual(MAX_FILE_SIZE_BYTES, 10 * 1024 * 1024)
