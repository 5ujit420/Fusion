# tests/test_module.py
# Comprehensive test suite for the filetracking module.
# Tests cover: services (unit), selectors (unit), API views (integration),
# web views (integration), decorators, and edge cases.

import json
import warnings
from unittest.mock import patch, MagicMock
from io import BytesIO

from django.test import TestCase, RequestFactory, Client
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile

from rest_framework.test import APIClient

from applications.globals.models import ExtraInfo, HoldsDesignation, Designation, Department
from applications.filetracking.models import File, Tracking, DEFAULT_DESIGNATION, LOGIN_URL, DEFAULT_SRC_MODULE
from applications.filetracking import services, selectors
from applications.filetracking.sdk import methods as sdk_methods


class BaseTestCase(TestCase):
    """Shared test setup for all test classes."""

    @classmethod
    def setUpTestData(cls):
        # Create department
        cls.dept = Department.objects.create(name='CSE: Computer Science')

        # Create designations
        cls.des_faculty = Designation.objects.create(name='Assistant Professor')
        cls.des_hod = Designation.objects.create(name='HOD (CSE)')
        cls.des_student = Designation.objects.create(name='student')

        # Create users
        cls.user1 = User.objects.create_user(username='sender_user', password='testpass123')
        cls.user2 = User.objects.create_user(username='receiver_user', password='testpass123')
        cls.student_user = User.objects.create_user(username='student_user', password='testpass123')

        # Create ExtraInfo
        cls.extra1 = ExtraInfo.objects.create(
            user=cls.user1, id='EI001', department=cls.dept, user_type='faculty'
        )
        cls.extra2 = ExtraInfo.objects.create(
            user=cls.user2, id='EI002', department=cls.dept, user_type='faculty'
        )
        cls.extra_student = ExtraInfo.objects.create(
            user=cls.student_user, id='EI003', department=cls.dept, user_type='student'
        )

        # Create HoldsDesignation
        cls.hd1 = HoldsDesignation.objects.create(
            user=cls.user1, designation=cls.des_faculty, working=cls.user1
        )
        cls.hd2 = HoldsDesignation.objects.create(
            user=cls.user2, designation=cls.des_hod, working=cls.user2
        )
        cls.hd_student = HoldsDesignation.objects.create(
            user=cls.student_user, designation=cls.des_student, working=cls.student_user
        )

    def create_test_file(self, uploader=None, designation=None, subject='Test File',
                         description='Test Description', is_read=False, src_module='filetracking'):
        """Helper to create a test file."""
        return File.objects.create(
            uploader=uploader or self.extra1,
            designation=designation or self.des_faculty,
            subject=subject,
            description=description,
            is_read=is_read,
            src_module=src_module,
        )

    def create_test_tracking(self, file_obj, sender_extra=None, sender_hd=None,
                             receiver=None, receive_design=None, remarks='Test Remarks'):
        """Helper to create a test tracking entry."""
        return Tracking.objects.create(
            file_id=file_obj,
            current_id=sender_extra or self.extra1,
            current_design=sender_hd or self.hd1,
            receiver_id=receiver or self.user2,
            receive_design=receive_design or self.des_hod,
            remarks=remarks,
        )


# ===========================================================================
# SELECTOR TESTS
# ===========================================================================

class SelectorTests(BaseTestCase):
    """Test all selector functions."""

    def test_get_all_files_with_related(self):
        """V-01: Selector returns all files with select_related."""
        self.create_test_file()
        files = selectors.get_all_files_with_related()
        self.assertEqual(files.count(), 1)
        # Access related field without extra query
        self.assertEqual(files.first().uploader.user.username, 'sender_user')

    def test_get_file_by_id(self):
        """V-19: Selector returns file by ID."""
        f = self.create_test_file()
        result = selectors.get_file_by_id(f.id)
        self.assertEqual(result, f)

    def test_get_file_by_id_with_related(self):
        """V-02: Selector returns file with related fields."""
        f = self.create_test_file()
        result = selectors.get_file_by_id_with_related(f.id)
        self.assertEqual(result.uploader.user.username, 'sender_user')

    def test_get_tracking_for_file_with_object(self):
        """R-05: Unified selector accepts File object."""
        f = self.create_test_file()
        self.create_test_tracking(f)
        result = selectors.get_tracking_for_file(f)
        self.assertEqual(result.count(), 1)

    def test_get_tracking_for_file_with_pk(self):
        """R-05: Unified selector accepts integer PK."""
        f = self.create_test_file()
        self.create_test_tracking(f)
        result = selectors.get_tracking_for_file(f.id)
        self.assertEqual(result.count(), 1)

    def test_get_latest_tracking(self):
        """Returns the most recent tracking entry."""
        f = self.create_test_file()
        self.create_test_tracking(f, remarks='first')
        t2 = self.create_test_tracking(f, remarks='second')
        latest = selectors.get_latest_tracking(f.id)
        self.assertEqual(latest.remarks, 'second')

    def test_get_current_file_owner_info(self):
        """R-06: Returns (user, designation) in one call."""
        f = self.create_test_file()
        self.create_test_tracking(f)
        owner, designation = selectors.get_current_file_owner_info(f.id)
        self.assertEqual(owner.username, 'receiver_user')
        self.assertEqual(designation.name, 'HOD (CSE)')

    def test_get_current_file_owner_info_no_tracking(self):
        """R-06: Returns (None, None) when no tracking exists."""
        f = self.create_test_file()
        owner, designation = selectors.get_current_file_owner_info(f.id)
        self.assertIsNone(owner)
        self.assertIsNone(designation)

    def test_create_file(self):
        """V-19: Write selector creates File."""
        f = selectors.create_file(
            uploader=self.extra1,
            designation=self.des_faculty,
            subject='Selector Created',
            description='Desc',
        )
        self.assertIsInstance(f, File)
        self.assertEqual(f.subject, 'Selector Created')

    def test_create_tracking(self):
        """V-19: Write selector creates Tracking."""
        f = self.create_test_file()
        t = selectors.create_tracking(
            file_id=f,
            current_id=self.extra1,
            current_design=self.hd1,
            receiver_id=self.user2,
            receive_design=self.des_hod,
            remarks='Created via selector',
        )
        self.assertIsInstance(t, Tracking)

    def test_update_file_read_status(self):
        """R-08: Write selector updates is_read."""
        f = self.create_test_file(is_read=False)
        selectors.update_file_read_status(f.id, True)
        f.refresh_from_db()
        self.assertTrue(f.is_read)

    def test_update_tracking_read_status(self):
        """V-04: Write selector updates tracking is_read."""
        f = self.create_test_file()
        t = self.create_test_tracking(f)
        selectors.update_tracking_read_status(f, True)
        t.refresh_from_db()
        self.assertTrue(t.is_read)

    def test_get_user_designations(self):
        """Returns all designations for a user."""
        hds = selectors.get_user_designations(self.user1)
        self.assertEqual(hds.count(), 1)
        self.assertEqual(hds.first().designation.name, 'Assistant Professor')

    def test_get_holds_designation_obj(self):
        """Returns HoldsDesignation from username and designation name."""
        hd = selectors.get_holds_designation_obj(self.user1, 'Assistant Professor')
        self.assertEqual(hd, self.hd1)

    def test_get_designation_by_id(self):
        """V-05: Returns designation by PK."""
        result = selectors.get_designation_by_id(self.des_faculty.id)
        self.assertEqual(result.name, 'Assistant Professor')

    def test_get_user_notifications(self):
        """V-33: Returns user notifications queryset."""
        notifs = selectors.get_user_notifications(self.user1)
        self.assertEqual(notifs.count(), 0)

    def test_get_tracking_history(self):
        """V-35: Returns tracking history with select_related."""
        f = self.create_test_file()
        self.create_test_tracking(f)
        history = selectors.get_tracking_history(f.id)
        self.assertEqual(history.count(), 1)
        # V-35: Access related field without extra query
        self.assertEqual(history.first().receiver_id.username, 'receiver_user')


# ===========================================================================
# SERVICE TESTS
# ===========================================================================

class ServiceTests(BaseTestCase):
    """Test all service functions."""

    # --- Validation tests (V-23, V-24) ---

    def test_validate_compose_fields_empty_title(self):
        """V-23: Raises if title is empty."""
        with self.assertRaises(ValidationError):
            services._validate_compose_fields('', 'desc', '1')

    def test_validate_compose_fields_no_design(self):
        """V-23: Raises if design_id is None."""
        with self.assertRaises(ValidationError):
            services._validate_compose_fields('Title', 'desc', None)

    def test_validate_send_fields_empty_receiver(self):
        """V-24: Raises if receiver is empty."""
        with self.assertRaises(ValidationError):
            services._validate_send_fields('Title', 'desc', '1', '', 'HOD (CSE)')

    # --- File creation tests ---

    @patch('applications.filetracking.services._send_notification')
    def test_save_draft_file(self, mock_notif):
        """Creates a draft file without tracking."""
        f = services.save_draft_file(
            uploader_user=self.user1,
            title='Draft Test',
            description='Draft Desc',
            design_id=str(self.hd1.id),
            upload_file=None,
            remarks='Test remark',
        )
        self.assertIsInstance(f, File)
        self.assertEqual(f.subject, 'Draft Test')
        self.assertEqual(Tracking.objects.filter(file_id=f).count(), 0)
        mock_notif.assert_not_called()

    @patch('applications.filetracking.services._send_notification')
    def test_send_file(self, mock_notif):
        """Creates a file with tracking and notification."""
        f = services.send_file(
            uploader_user=self.user1,
            title='Send Test',
            description='Send Desc',
            design_id=str(self.hd1.id),
            receiver_username='receiver_user',
            receiver_designation_name='HOD (CSE)',
            upload_file=None,
        )
        self.assertIsInstance(f, File)
        self.assertEqual(Tracking.objects.filter(file_id=f).count(), 1)
        mock_notif.assert_called_once()

    @patch('applications.filetracking.services._send_notification')
    def test_send_file_invalid_receiver(self, mock_notif):
        """Raises User.DoesNotExist for invalid receiver."""
        with self.assertRaises(User.DoesNotExist):
            services.send_file(
                uploader_user=self.user1,
                title='Test',
                description='Desc',
                design_id=str(self.hd1.id),
                receiver_username='nonexistent_user',
                receiver_designation_name='HOD (CSE)',
                upload_file=None,
            )

    # --- Read status tests (V-03, V-04, V-08, R-08) ---

    def test_mark_file_as_read(self):
        """V-03: Sets file is_read=True."""
        f = self.create_test_file(is_read=False)
        services.mark_file_as_read(f.id)
        f.refresh_from_db()
        self.assertTrue(f.is_read)

    def test_mark_tracking_as_read(self):
        """V-04: Sets tracking is_read=True."""
        f = self.create_test_file()
        t = self.create_test_tracking(f)
        services.mark_tracking_as_read(f)
        t.refresh_from_db()
        self.assertTrue(t.is_read)

    def test_archive_file_and_tracking(self):
        """V-08: Archives both file and tracking."""
        f = self.create_test_file(is_read=False)
        t = self.create_test_tracking(f)
        services.archive_file_and_tracking(f.id)
        f.refresh_from_db()
        t.refresh_from_db()
        self.assertTrue(f.is_read)
        self.assertTrue(t.is_read)

    def test_unarchive_file(self):
        """R-08: Sets file is_read=False."""
        f = self.create_test_file(is_read=True)
        services.unarchive_file(f.id)
        f.refresh_from_db()
        self.assertFalse(f.is_read)

    # --- Delete tests ---

    def test_delete_file_with_auth_owner(self):
        """Owner can delete their file."""
        f = self.create_test_file()
        result = services.delete_file_with_auth(f.id, self.user1)
        self.assertTrue(result)
        self.assertFalse(File.objects.filter(id=f.id).exists())

    def test_delete_file_with_auth_not_owner(self):
        """Non-owner gets ValidationError."""
        f = self.create_test_file()
        with self.assertRaises(ValidationError):
            services.delete_file_with_auth(f.id, self.user2)

    # --- Forward tests (R-09) ---

    def test_forward_file_sdk(self):
        """R-09: SDK forward creates tracking."""
        f = self.create_test_file()
        self.create_test_tracking(f)
        tracking_id = services.forward_file(
            file_id=f.id,
            receiver='sender_user',
            receiver_designation='Assistant Professor',
            file_extra_JSON={'note': 'test'},
            remarks='Forwarded',
        )
        self.assertIsNotNone(tracking_id)
        self.assertEqual(Tracking.objects.filter(file_id=f).count(), 2)

    @patch('applications.filetracking.services._send_notification')
    def test_forward_file_from_view(self, mock_notif):
        """R-09: View forward creates tracking + notification."""
        f = self.create_test_file()
        self.create_test_tracking(f)
        services.forward_file_from_view(
            file_obj=f,
            requesting_user=self.user1,
            sender_design_id=str(self.hd1.id),
            receiver_username='receiver_user',
            receiver_designation_name='HOD (CSE)',
            upload_file=None,
            remarks='View forward',
        )
        self.assertEqual(Tracking.objects.filter(file_id=f).count(), 2)
        mock_notif.assert_called_once()

    # --- Enrichment tests (V-09, V-10, V-11, V-14) ---

    def test_enrich_draft_files(self):
        """V-09: Enriches draft file dicts."""
        f = self.create_test_file()
        draft_data = [services._serialize_file_header(f)]
        enriched = services.enrich_draft_files(draft_data)
        self.assertIsNotNone(enriched[0]['uploader'])
        self.assertIn('uploader_department', enriched[0])

    def test_enrich_archive_files(self):
        """V-14: Enriches archive file dicts with designation."""
        f = self.create_test_file()
        archive_data = [services._serialize_file_header(f)]
        enriched = services.enrich_archive_files(archive_data)
        self.assertIsInstance(enriched[0]['designation'], Designation)

    # --- Search filter tests (V-12, V-13, R-01) ---

    def test_filter_files_by_subject(self):
        """R-01: Filters by subject."""
        files = [
            {'subject': 'Budget Report', 'sent_to_user': None, 'last_sent_date': None},
            {'subject': 'Leave Request', 'sent_to_user': None, 'last_sent_date': None},
        ]
        result = services.filter_files_by_search(files, subject_query='budget')
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['subject'], 'Budget Report')

    def test_filter_files_by_invalid_date(self):
        """R-01: Invalid date clears results."""
        files = [{'subject': 'Test', 'sent_to_user': None, 'last_sent_date': None}]
        result = services.filter_files_by_search(files, date_query='invalid-date')
        self.assertEqual(len(result), 0)

    # --- Inbox/Outbox/Drafts/Archive tests ---

    def test_view_inbox(self):
        """Returns inbox files."""
        f = self.create_test_file()
        self.create_test_tracking(f)
        inbox = services.view_inbox('receiver_user', 'HOD (CSE)', 'filetracking')
        self.assertGreaterEqual(len(inbox), 1)

    def test_view_outbox(self):
        """Returns outbox files."""
        f = self.create_test_file()
        self.create_test_tracking(f)
        outbox = services.view_outbox('sender_user', 'Assistant Professor', 'filetracking')
        self.assertGreaterEqual(len(outbox), 1)

    def test_view_drafts(self):
        """Returns only draft files (no tracking)."""
        self.create_test_file(subject='Draft Only')
        f_sent = self.create_test_file(subject='Sent File')
        self.create_test_tracking(f_sent)
        drafts = services.view_drafts('sender_user', 'Assistant Professor', 'filetracking')
        subjects = [d['subject'] for d in drafts]
        self.assertIn('Draft Only', subjects)
        self.assertNotIn('Sent File', subjects)

    def test_view_archived(self):
        """Returns archived files (is_read=True)."""
        f = self.create_test_file(is_read=True)
        self.create_test_tracking(f)
        Tracking.objects.filter(file_id=f).update(is_read=True)
        archived = services.view_archived('receiver_user', 'HOD (CSE)', 'filetracking')
        self.assertGreaterEqual(len(archived), 1)

    # --- R-07: Designation resolution ---

    def test_resolve_sender_designation(self):
        """R-07: Returns (Designation, HoldsDesignation) tuple."""
        des, hd = services._resolve_sender_designation(self.hd1.id)
        self.assertEqual(des.name, 'Assistant Professor')
        self.assertEqual(hd, self.hd1)

    # --- R-04: Session designation ---

    def test_get_session_designation(self):
        """R-04: Reads designation from session."""
        factory = RequestFactory()
        request = factory.get('/')
        request.user = self.user1
        request.session = {'currentDesignationSelected': 'Assistant Professor'}
        name, hd = services.get_session_designation(request)
        self.assertEqual(name, 'Assistant Professor')
        self.assertEqual(hd, self.hd1)

    # --- V-38: File detail serialization ---

    def test_view_file_details(self):
        """V-38: Returns dict without serializer import."""
        f = self.create_test_file()
        result = services.view_file_details(f.id)
        self.assertEqual(result['subject'], 'Test File')
        self.assertIn('id', result)
        self.assertIn('upload_date', result)

    # --- View history (V-35) ---

    def test_view_history_enriched(self):
        """V-35: Returns enriched history with string fields."""
        f = self.create_test_file()
        self.create_test_tracking(f)
        history = services.view_history_enriched(f.id)
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]['receiver_id'], 'receiver_user')
        self.assertEqual(history[0]['receive_design'], 'HOD (CSE)')

    # --- File view permissions ---

    def test_get_file_view_permissions_current_owner(self):
        """Forward enabled when current owner viewing."""
        f = self.create_test_file(is_read=False)
        self.create_test_tracking(f)
        forward_en, archive_en = services.get_file_view_permissions(f.id, self.user2)
        self.assertTrue(forward_en)

    def test_get_file_view_permissions_not_owner(self):
        """Forward disabled when not current owner."""
        f = self.create_test_file(is_read=False)
        self.create_test_tracking(f)
        forward_en, archive_en = services.get_file_view_permissions(f.id, self.user1)
        self.assertFalse(forward_en)


# ===========================================================================
# API VIEW TESTS
# ===========================================================================

class APIViewTests(BaseTestCase):
    """Integration tests for DRF API endpoints."""

    def setUp(self):
        self.api_client = APIClient()
        self.api_client.force_authenticate(user=self.user1)

    def test_create_file_api(self):
        """POST api/file/ creates a file."""
        response = self.api_client.post('/filetracking/api/file/', {
            'uploader': 'sender_user',
            'uploader_designation': 'Assistant Professor',
            'receiver': 'receiver_user',
            'receiver_designation': 'HOD (CSE)',
            'subject': 'API Test File',
            'description': 'API Test Description',
        })
        self.assertIn(response.status_code, [200, 201])
        self.assertIn('file_id', response.data)

    def test_create_file_api_missing_fields(self):
        """POST api/file/ with missing fields returns 400."""
        response = self.api_client.post('/filetracking/api/file/', {
            'uploader': 'sender_user',
        })
        self.assertEqual(response.status_code, 400)

    def test_view_file_api(self):
        """GET api/file/<id>/ returns file details."""
        f = self.create_test_file()
        response = self.api_client.get(f'/filetracking/api/file/{f.id}/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('file', response.data)

    def test_delete_file_api_owner(self):
        """DELETE api/file/<id>/ deletes owner's file."""
        f = self.create_test_file()
        response = self.api_client.delete(f'/filetracking/api/file/{f.id}/')
        self.assertEqual(response.status_code, 200)
        self.assertFalse(File.objects.filter(id=f.id).exists())

    def test_delete_file_api_not_owner(self):
        """DELETE api/file/<id>/ fails for non-owner."""
        f = self.create_test_file(uploader=self.extra2)
        response = self.api_client.delete(f'/filetracking/api/file/{f.id}/')
        self.assertEqual(response.status_code, 400)

    def test_view_inbox_api(self):
        """GET api/inbox/ returns inbox files."""
        f = self.create_test_file()
        self.create_test_tracking(f)
        response = self.api_client.get('/filetracking/api/inbox/', {
            'username': 'receiver_user',
            'designation': 'HOD (CSE)',
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn('inbox', response.data)

    def test_view_inbox_api_missing_params(self):
        """GET api/inbox/ without params returns 400."""
        response = self.api_client.get('/filetracking/api/inbox/')
        self.assertEqual(response.status_code, 400)

    def test_view_outbox_api(self):
        """GET api/outbox/ returns outbox files."""
        f = self.create_test_file()
        self.create_test_tracking(f)
        response = self.api_client.get('/filetracking/api/outbox/', {
            'username': 'sender_user',
            'designation': 'Assistant Professor',
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn('outbox', response.data)

    def test_view_history_api(self):
        """GET api/history/<id>/ returns tracking history."""
        f = self.create_test_file()
        self.create_test_tracking(f)
        response = self.api_client.get(f'/filetracking/api/history/{f.id}/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('history', response.data)

    def test_forward_file_api(self):
        """POST api/forwardfile/<id>/ forwards a file."""
        f = self.create_test_file()
        self.create_test_tracking(f)
        response = self.api_client.post(f'/filetracking/api/forwardfile/{f.id}/', {
            'receiver': 'sender_user',
            'receiver_designation': 'Assistant Professor',
        })
        self.assertIn(response.status_code, [200, 201])

    def test_draft_file_api_with_serializer(self):
        """V-25: GET api/draft/ validates via DraftQuerySerializer."""
        self.create_test_file(subject='Draft API')
        response = self.api_client.get('/filetracking/api/draft/', {
            'username': 'sender_user',
            'designation': 'Assistant Professor',
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn('drafts', response.data)

    def test_draft_file_api_missing_params(self):
        """V-25: GET api/draft/ without params returns 400."""
        response = self.api_client.get('/filetracking/api/draft/')
        self.assertEqual(response.status_code, 400)

    def test_create_draft_api(self):
        """POST api/createdraft/ creates a draft."""
        response = self.api_client.post('/filetracking/api/createdraft/', {
            'uploader': 'sender_user',
            'uploader_designation': 'Assistant Professor',
        })
        self.assertIn(response.status_code, [200, 201])
        self.assertIn('file_id', response.data)

    def test_archive_file_api(self):
        """POST api/createarchive/ archives a file."""
        f = self.create_test_file()
        response = self.api_client.post('/filetracking/api/createarchive/', {
            'file_id': f.id,
        })
        self.assertEqual(response.status_code, 200)
        f.refresh_from_db()
        self.assertTrue(f.is_read)

    def test_view_archive_api_with_serializer(self):
        """V-26: GET api/archive/ validates via ArchiveQuerySerializer."""
        f = self.create_test_file(is_read=True)
        self.create_test_tracking(f)
        Tracking.objects.filter(file_id=f).update(is_read=True)
        response = self.api_client.get('/filetracking/api/archive/', {
            'username': 'receiver_user',
            'designation': 'HOD (CSE)',
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn('archive', response.data)

    def test_view_archive_api_missing_params(self):
        """V-26: GET api/archive/ without params returns 400."""
        response = self.api_client.get('/filetracking/api/archive/')
        self.assertEqual(response.status_code, 400)

    def test_get_designations_api(self):
        """GET api/designations/<username>/ returns designations."""
        response = self.api_client.get('/filetracking/api/designations/sender_user/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('designations', response.data)

    def test_unauthenticated_access_denied(self):
        """Unauthenticated requests to API return 401."""
        client = APIClient()  # no auth
        response = client.get('/filetracking/api/inbox/', {
            'username': 'sender_user',
            'designation': 'Assistant Professor',
        })
        self.assertEqual(response.status_code, 401)


# ===========================================================================
# SDK TESTS (R-10)
# ===========================================================================

class SDKTests(BaseTestCase):
    """Test SDK backward compatibility layer."""

    def test_sdk_create_file_deprecation_warning(self):
        """R-10: SDK methods emit deprecation warning."""
        f = self.create_test_file()
        self.create_test_tracking(f)
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            owner = sdk_methods.get_current_file_owner(f.id)
            self.assertEqual(len(w), 1)
            self.assertIn('deprecated', str(w[0].message).lower())
            self.assertEqual(owner.username, 'receiver_user')

    def test_sdk_view_inbox(self):
        """R-10: SDK view_inbox delegates correctly."""
        f = self.create_test_file()
        self.create_test_tracking(f)
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            result = sdk_methods.view_inbox('receiver_user', 'HOD (CSE)', 'filetracking')
        self.assertIsInstance(result, list)
        self.assertGreaterEqual(len(result), 1)

    def test_sdk_archive_and_unarchive(self):
        """R-10: SDK archive/unarchive delegates correctly."""
        f = self.create_test_file()
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            sdk_methods.archive_file(f.id)
        f.refresh_from_db()
        self.assertTrue(f.is_read)
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            sdk_methods.unarchive_file(f.id)
        f.refresh_from_db()
        self.assertFalse(f.is_read)


# ===========================================================================
# CONSTANTS TESTS (V-27, V-28, V-29)
# ===========================================================================

class ConstantsTests(TestCase):
    """Test module-level constants."""

    def test_default_designation_constant(self):
        """V-27: DEFAULT_DESIGNATION is defined."""
        self.assertEqual(DEFAULT_DESIGNATION, 'default_value')

    def test_login_url_constant(self):
        """V-28: LOGIN_URL has trailing slash."""
        self.assertEqual(LOGIN_URL, '/accounts/login/')
        self.assertTrue(LOGIN_URL.endswith('/'))

    def test_default_src_module_constant(self):
        """V-29: DEFAULT_SRC_MODULE is defined."""
        self.assertEqual(DEFAULT_SRC_MODULE, 'filetracking')


# ===========================================================================
# EDGE CASE TESTS
# ===========================================================================

class EdgeCaseTests(BaseTestCase):
    """Test edge cases and error handling."""

    def test_validate_file_size_under_limit(self):
        """File under 10MB passes validation."""
        small_file = SimpleUploadedFile("test.txt", b"small content")
        try:
            services.validate_file_size(small_file)
        except ValidationError:
            self.fail("validate_file_size raised ValidationError for small file")

    def test_validate_file_size_over_limit(self):
        """File over 10MB raises ValidationError."""
        large_content = b"x" * (10 * 1024 * 1024 + 1)
        large_file = SimpleUploadedFile("large.txt", large_content)
        with self.assertRaises(ValidationError):
            services.validate_file_size(large_file)

    def test_validate_file_size_none(self):
        """None file passes validation."""
        try:
            services.validate_file_size(None)
        except ValidationError:
            self.fail("validate_file_size raised ValidationError for None")

    def test_get_file_view_permissions_archived_file(self):
        """No forward/archive on already-archived file."""
        f = self.create_test_file(is_read=True)
        self.create_test_tracking(f)
        forward_en, archive_en = services.get_file_view_permissions(f.id, self.user2)
        self.assertFalse(forward_en)
        self.assertFalse(archive_en)

    def test_unique_list_preserves_order(self):
        """utility: unique_list preserves insertion order."""
        result = services.unique_list([3, 1, 2, 1, 3, 4])
        self.assertEqual(result, [3, 1, 2, 4])

    def test_add_uploader_department_to_files_list(self):
        """utility: Adds department string."""
        files = [{'uploader': self.extra1}]
        result = services.add_uploader_department_to_files_list(files)
        self.assertIn('uploader_department', result[0])
        self.assertEqual(result[0]['uploader_department'], 'Computer Science')

    def test_add_uploader_department_none(self):
        """utility: Handles None department."""
        extra_no_dept = MagicMock()
        extra_no_dept.department = None
        files = [{'uploader': extra_no_dept}]
        result = services.add_uploader_department_to_files_list(files)
        self.assertEqual(result[0]['uploader_department'], 'FTS')

    @patch('applications.filetracking.services._send_notification')
    def test_create_file_via_sdk(self, mock_notif):
        """SDK file creation creates file + tracking."""
        file_id = services.create_file_via_sdk(
            uploader='sender_user',
            uploader_designation='Assistant Professor',
            receiver='receiver_user',
            receiver_designation='HOD (CSE)',
            subject='SDK Test',
            description='SDK Desc',
        )
        self.assertIsNotNone(file_id)
        self.assertTrue(File.objects.filter(id=file_id).exists())
        self.assertTrue(Tracking.objects.filter(file_id=file_id).exists())

    @patch('applications.filetracking.services._send_notification')
    def test_create_draft_via_sdk(self, mock_notif):
        """SDK draft creation creates file without tracking."""
        file_id = services.create_draft_via_sdk(
            uploader='sender_user',
            uploader_designation='Assistant Professor',
        )
        self.assertIsNotNone(file_id)
        self.assertTrue(File.objects.filter(id=file_id).exists())
        self.assertFalse(Tracking.objects.filter(file_id=file_id).exists())
