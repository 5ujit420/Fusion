# tests/test_module.py
from django.test import TestCase, RequestFactory
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient
from rest_framework import status
from unittest.mock import MagicMock

from applications.globals.models import ExtraInfo, Designation, HoldsDesignation, Department
from applications.filetracking.models import File, Tracking, MAX_FILE_SIZE_BYTES, FALLBACK_DEPARTMENT_CODE
from applications.filetracking import services, selectors
from applications.filetracking.utils import DEFAULT_DESIGNATION_SESSION_VALUE, DESIGNATION_SESSION_KEY
from applications.filetracking.api.serializers import (
    FileCreateInputSerializer, DraftCreateInputSerializer, ForwardFileInputSerializer,
    InboxQuerySerializer, ArchiveInputSerializer, FileSerializer, TrackingSerializer,
    FileHeaderSerializer, DraftQuerySerializer, ArchiveQuerySerializer,
)


class BaseTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.department = Department.objects.create(name='CSE: Computer Science')
        cls.des_faculty = Designation.objects.create(name='faculty')
        cls.des_hod = Designation.objects.create(name='hod')
        cls.user1 = User.objects.create_user(username='sender1', password='testpass123')
        cls.user2 = User.objects.create_user(username='receiver1', password='testpass123')
        cls.extra1 = ExtraInfo.objects.create(user=cls.user1, id='EI001', department=cls.department)
        cls.extra2 = ExtraInfo.objects.create(user=cls.user2, id='EI002', department=cls.department)
        cls.hd1 = HoldsDesignation.objects.create(user=cls.user1, designation=cls.des_faculty)
        cls.hd2 = HoldsDesignation.objects.create(user=cls.user2, designation=cls.des_hod)


# ===========================================================================
# Selector Tests
# ===========================================================================

class SelectorTests(BaseTestCase):

    def test_get_user_by_username(self):
        self.assertEqual(selectors.get_user_by_username('sender1').pk, self.user1.pk)

    def test_get_user_by_username_not_found(self):
        with self.assertRaises(User.DoesNotExist):
            selectors.get_user_by_username('nonexistent')

    def test_get_extrainfo_by_username(self):
        ei = selectors.get_extrainfo_by_username('sender1')
        self.assertEqual(ei.pk, self.extra1.pk)

    def test_get_designation_by_name(self):
        self.assertEqual(selectors.get_designation_by_name('faculty').pk, self.des_faculty.pk)

    def test_get_designation_by_id(self):
        # T-05/S-22
        self.assertEqual(selectors.get_designation_by_id(self.des_faculty.pk).pk, self.des_faculty.pk)

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
        f = File.objects.create(uploader=self.extra1, designation=self.des_faculty, subject='T')
        self.assertIsNone(selectors.get_latest_tracking(f.id))

    def test_get_current_file_owner_returns_none_for_draft(self):
        f = File.objects.create(uploader=self.extra1, designation=self.des_faculty, subject='D')
        self.assertIsNone(selectors.get_current_file_owner(f.id))

    def test_get_draft_files(self):
        File.objects.create(uploader=self.extra1, designation=self.des_faculty,
                            subject='Draft', src_module='filetracking')
        drafts = selectors.get_draft_files(self.extra1, self.des_faculty, 'filetracking')
        self.assertEqual(len(drafts), 1)

    def test_get_designations_starting_with(self):
        self.assertTrue(selectors.get_designations_starting_with('fac').exists())

    def test_get_users_starting_with(self):
        self.assertTrue(selectors.get_users_starting_with('send').exists())

    def test_get_all_files_with_related(self):
        # T-05/S-19 — selector exists and returns queryset
        File.objects.create(uploader=self.extra1, designation=self.des_faculty, subject='All')
        qs = selectors.get_all_files_with_related()
        self.assertTrue(qs.exists())

    def test_get_extrainfo_by_id_has_select_related(self):
        # T-11/S-31 — accessing .department should not hit DB again
        ei = selectors.get_extrainfo_by_id(self.extra1.pk)
        self.assertIsNotNone(ei.department)

    def test_get_extrainfo_by_ids(self):
        # T-10 bulk selector
        ids = [self.extra1.pk, self.extra2.pk]
        mapping = selectors.get_extrainfo_by_ids(ids)
        self.assertIn(self.extra1.pk, mapping)
        self.assertIn(self.extra2.pk, mapping)

    def test_get_designations_by_ids(self):
        # T-10 bulk selector
        ids = [self.des_faculty.pk, self.des_hod.pk]
        mapping = selectors.get_designations_by_ids(ids)
        self.assertIn(self.des_faculty.pk, mapping)

    def test_get_last_forw_tracking_bulk(self):
        # T-10/S-26
        file_id = services.create_file_via_sdk(
            'sender1', 'faculty', 'receiver1', 'hod', subject='Bulk Forw')
        sender_ei = selectors.get_extrainfo_by_username('sender1')
        result = selectors.get_last_forw_tracking_bulk([file_id], sender_ei, self.hd1)
        self.assertIn(file_id, result)

    def test_get_last_recv_tracking_bulk(self):
        # T-10/S-27
        file_id = services.create_file_via_sdk(
            'sender1', 'faculty', 'receiver1', 'hod', subject='Bulk Recv')
        result = selectors.get_last_recv_tracking_bulk([file_id], self.user2, self.des_hod)
        self.assertIn(file_id, result)

    def test_get_current_file_owners_bulk(self):
        # T-10/S-27
        file_id = services.create_file_via_sdk(
            'sender1', 'faculty', 'receiver1', 'hod', subject='Bulk Owner')
        result = selectors.get_current_file_owners_bulk([file_id])
        self.assertIn(file_id, result)
        self.assertEqual(result[file_id], self.user2)


# ===========================================================================
# Service Utility Tests
# ===========================================================================

class ServiceUtilityTests(BaseTestCase):

    def test_unique_list(self):
        self.assertEqual(services.unique_list([1, 2, 2, 3, 1]), [1, 2, 3])
        self.assertEqual(services.unique_list([]), [])

    def test_get_designation_display_name(self):
        name = services.get_designation_display_name(self.hd1)
        self.assertIsInstance(name, str)
        self.assertTrue(len(name) > 0)

    def test_validate_file_size_ok(self):
        services.validate_file_size(SimpleUploadedFile("small.txt", b"x" * 100))

    def test_validate_file_size_too_large(self):
        big = MagicMock()
        big.size = MAX_FILE_SIZE_BYTES + 1
        with self.assertRaises(ValidationError):
            services.validate_file_size(big)

    def test_validate_file_size_none(self):
        services.validate_file_size(None)

    def test_fallback_department_code_constant(self):
        # T-15/S-37
        self.assertEqual(FALLBACK_DEPARTMENT_CODE, 'FTS')

    def test_default_designation_session_value_constant(self):
        # T-15/S-36
        self.assertEqual(DEFAULT_DESIGNATION_SESSION_VALUE, 'default_value')

    def test_filter_files_by_search_params_subject(self):
        # T-01/S-08
        files = [{'subject': 'Hello World', 'sent_to_user': None, 'last_sent_date': None},
                 {'subject': 'Goodbye', 'sent_to_user': None, 'last_sent_date': None}]
        result = services.filter_files_by_search_params(files, subject_q='hello')
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['subject'], 'Hello World')

    def test_filter_files_by_search_params_bad_date(self):
        # T-01/S-17 — invalid date returns empty list
        files = [{'subject': 'X', 'sent_to_user': None, 'last_sent_date': None}]
        result = services.filter_files_by_search_params(files, date_q='not-a-date')
        self.assertEqual(result, [])

    def test_get_draft_remarks_with_json(self):
        # T-07/S-25
        f = File(file_extra_JSON={'remarks': 'test remark'})
        self.assertEqual(services.get_draft_remarks(f), 'test remark')

    def test_get_draft_remarks_none(self):
        # T-07/S-25
        f = File(file_extra_JSON=None)
        self.assertIsNone(services.get_draft_remarks(f))

    def test_mark_file_read(self):
        # T-06/S-23
        f = File.objects.create(uploader=self.extra1, designation=self.des_faculty,
                                subject='MFR', is_read=False)
        services.mark_file_read(f.id)
        self.assertTrue(File.objects.get(id=f.id).is_read)

    def test_mark_tracking_read(self):
        # T-06/S-24
        file_id = services.create_file_via_sdk(
            'sender1', 'faculty', 'receiver1', 'hod', subject='MTR')
        track_qs = Tracking.objects.filter(file_id=file_id)
        services.mark_tracking_read(track_qs)
        self.assertTrue(all(t.is_read for t in Tracking.objects.filter(file_id=file_id)))

    def test_finish_file(self):
        # T-05/S-21
        file_id = services.create_file_via_sdk(
            'sender1', 'faculty', 'receiver1', 'hod', subject='Finish')
        track_qs = Tracking.objects.filter(file_id=file_id)
        services.finish_file(file_id, track_qs)
        self.assertTrue(File.objects.get(id=file_id).is_read)
        self.assertTrue(all(t.is_read for t in Tracking.objects.filter(file_id=file_id)))


# ===========================================================================
# Service File Tests
# ===========================================================================

class ServiceFileCreationTests(BaseTestCase):

    def test_create_file_via_sdk(self):
        file_id = services.create_file_via_sdk(
            'sender1', 'faculty', 'receiver1', 'hod', subject='SDK Test')
        self.assertIsNotNone(file_id)
        self.assertEqual(File.objects.get(id=file_id).subject, 'SDK Test')
        self.assertEqual(Tracking.objects.filter(file_id=file_id).count(), 1)

    def test_create_draft_via_sdk(self):
        file_id = services.create_draft_via_sdk('sender1', 'faculty')
        self.assertIsNotNone(file_id)
        self.assertEqual(Tracking.objects.filter(file_id=file_id).count(), 0)


class ServiceViewTests(BaseTestCase):

    def setUp(self):
        self.file_id = services.create_file_via_sdk(
            'sender1', 'faculty', 'receiver1', 'hod', subject='View Test')

    def test_view_file_details(self):
        self.assertEqual(services.view_file_details(self.file_id)['subject'], 'View Test')

    def test_view_file_not_found(self):
        with self.assertRaises(File.DoesNotExist):
            services.view_file_details(99999)

    def test_delete_file(self):
        self.assertTrue(services.delete_file(self.file_id))
        self.assertFalse(File.objects.filter(id=self.file_id).exists())

    def test_delete_file_with_auth_owner(self):
        self.assertTrue(services.delete_file_with_auth(self.file_id, self.user1))

    def test_delete_file_with_auth_non_owner(self):
        with self.assertRaises(ValidationError):
            services.delete_file_with_auth(self.file_id, self.user2)

    def test_view_inbox(self):
        inbox = services.view_inbox('receiver1', 'hod', 'filetracking')
        self.assertIsInstance(inbox, list)
        self.assertTrue(any(f['subject'] == 'View Test' for f in inbox))

    def test_view_outbox(self):
        outbox = services.view_outbox('sender1', 'faculty', 'filetracking')
        self.assertIsInstance(outbox, list)

    def test_view_drafts_empty(self):
        drafts = services.view_drafts('sender1', 'faculty', 'filetracking')
        self.assertEqual(len(drafts), 0)

    def test_view_history(self):
        history = services.view_history(self.file_id)
        self.assertIsInstance(history, list)
        self.assertGreaterEqual(len(history), 1)

    def test_view_history_enriched(self):
        # T-11/S-30
        enriched = services.view_history_enriched(self.file_id)
        self.assertGreaterEqual(len(enriched), 1)
        self.assertIsInstance(enriched[0]['receiver_id'], str)

    def test_enrich_outbox_files(self):
        # T-10/S-26
        outward = services.view_outbox('sender1', 'faculty', 'filetracking')
        sender_ei = selectors.get_extrainfo_by_username('sender1')
        hd = selectors.get_holds_designation_obj('sender1', 'faculty')
        enriched = services.enrich_outbox_files(list(outward), sender_ei, hd)
        self.assertIsInstance(enriched, list)

    def test_enrich_inbox_files(self):
        # T-10/S-27
        inward = services.view_inbox('receiver1', 'hod', 'filetracking')
        hd = selectors.get_holds_designation_obj('receiver1', 'hod')
        enriched = services.enrich_inbox_files(list(inward), self.user2, hd)
        self.assertIsInstance(enriched, list)


class ServiceArchiveTests(BaseTestCase):

    def setUp(self):
        self.file_id = services.create_file_via_sdk(
            'sender1', 'faculty', 'receiver1', 'hod', subject='Archive Test')

    def test_archive_file_sdk(self):
        services.archive_file_sdk(self.file_id)
        self.assertTrue(File.objects.get(id=self.file_id).is_read)

    def test_unarchive_file(self):
        services.archive_file_sdk(self.file_id)
        services.unarchive_file(self.file_id)
        self.assertFalse(File.objects.get(id=self.file_id).is_read)

    def test_view_archived(self):
        services.archive_file_sdk(self.file_id)
        archived = services.view_archived('sender1', 'faculty', 'filetracking')
        self.assertIsInstance(archived, list)

    def test_enrich_archive_files(self):
        # T-10/S-29
        services.archive_file_sdk(self.file_id)
        archive = services.view_archived('sender1', 'faculty', 'filetracking')
        enriched = services.enrich_archive_files(list(archive))
        self.assertIsInstance(enriched, list)

    def test_get_file_view_permissions_owner(self):
        forward_en, archive_en = services.get_file_view_permissions(self.file_id, self.user2)
        self.assertTrue(forward_en)


class ServiceDesignationTests(BaseTestCase):

    def test_get_designations(self):
        self.assertIn('faculty', services.get_designations('sender1'))

    def test_get_designation_redirect_url_from_session(self):
        # T-15/S-36 — uses named constants
        factory = RequestFactory()
        request = factory.get('/')
        request.user = self.user1
        request.session = {DESIGNATION_SESSION_KEY: 'faculty'}
        url = services.get_designation_redirect_url_from_session(request, 'drafts')
        self.assertIn('/filetracking/drafts/', url)


# ===========================================================================
# Serializer Validation Tests
# ===========================================================================

class SerializerValidationTests(TestCase):

    def test_file_create_input_valid(self):
        s = FileCreateInputSerializer(data={
            'designation': 'faculty', 'receiver_username': 'r1',
            'receiver_designation': 'hod', 'subject': 'Sub',
        })
        self.assertTrue(s.is_valid())

    def test_file_create_input_missing_required(self):
        s = FileCreateInputSerializer(data={'designation': 'faculty'})
        self.assertFalse(s.is_valid())
        self.assertIn('receiver_username', s.errors)

    def test_draft_create_input_valid(self):
        s = DraftCreateInputSerializer(data={'uploader': 's1', 'uploader_designation': 'fac'})
        self.assertTrue(s.is_valid())

    def test_draft_query_serializer_valid(self):
        # 5C new serializer
        s = DraftQuerySerializer(data={'username': 'u1', 'src_module': 'filetracking'})
        self.assertTrue(s.is_valid())

    def test_draft_query_serializer_missing_src_module(self):
        s = DraftQuerySerializer(data={'username': 'u1'})
        self.assertFalse(s.is_valid())

    def test_archive_query_serializer_valid(self):
        # 5C new serializer
        s = ArchiveQuerySerializer(data={'username': 'u1', 'src_module': 'filetracking'})
        self.assertTrue(s.is_valid())

    def test_forward_input_valid(self):
        s = ForwardFileInputSerializer(data={'receiver': 'r1', 'receiver_designation': 'hod'})
        self.assertTrue(s.is_valid())

    def test_inbox_query_valid(self):
        s = InboxQuerySerializer(data={'username': 'u1', 'src_module': 'filetracking'})
        self.assertTrue(s.is_valid())

    def test_archive_input_valid(self):
        s = ArchiveInputSerializer(data={'file_id': 1})
        self.assertTrue(s.is_valid())

    def test_file_header_excludes_upload_file(self):
        self.assertIn('upload_file', FileHeaderSerializer.Meta.exclude)


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
        r = self.client.post('/filetracking/api/file/', {
            'designation': 'faculty', 'receiver_username': 'receiver1',
            'receiver_designation': 'hod', 'subject': 'API File',
        })
        self.assertIn(r.status_code, [status.HTTP_201_CREATED, status.HTTP_400_BAD_REQUEST])

    def test_create_file_api_missing_fields(self):
        r = self.client.post('/filetracking/api/file/', {'designation': 'faculty'})
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_view_file_api(self):
        fid = services.create_file_via_sdk(
            'sender1', 'faculty', 'receiver1', 'hod', subject='API View')
        r = self.client.get(f'/filetracking/api/file/{fid}/')
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data['subject'], 'API View')

    def test_delete_file_api(self):
        fid = services.create_file_via_sdk(
            'sender1', 'faculty', 'receiver1', 'hod', subject='Del Test')
        r = self.client.delete(f'/filetracking/api/file/{fid}/')
        self.assertEqual(r.status_code, status.HTTP_204_NO_CONTENT)

    def test_inbox_api(self):
        services.create_file_via_sdk(
            'sender1', 'faculty', 'receiver1', 'hod', subject='Inbox API')
        r = self.client.get('/filetracking/api/inbox/', {
            'username': 'receiver1', 'designation': 'hod', 'src_module': 'filetracking'})
        self.assertEqual(r.status_code, status.HTTP_200_OK)

    def test_inbox_api_missing_params(self):
        r = self.client.get('/filetracking/api/inbox/', {})
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_outbox_api(self):
        r = self.client.get('/filetracking/api/outbox/', {
            'username': 'sender1', 'designation': 'faculty', 'src_module': 'filetracking'})
        self.assertEqual(r.status_code, status.HTTP_200_OK)

    def test_history_api(self):
        fid = services.create_file_via_sdk(
            'sender1', 'faculty', 'receiver1', 'hod', subject='Hist Test')
        r = self.client.get(f'/filetracking/api/history/{fid}/')
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(r.data), 1)

    def test_create_draft_api(self):
        r = self.client.post('/filetracking/api/createdraft/', {
            'uploader': 'sender1', 'uploader_designation': 'faculty'})
        self.assertIn(r.status_code, [status.HTTP_201_CREATED, status.HTTP_500_INTERNAL_SERVER_ERROR])

    def test_view_drafts_api(self):
        # 5C: now uses DraftQuerySerializer
        r = self.client.get('/filetracking/api/draft/', {
            'username': 'sender1', 'designation': 'faculty', 'src_module': 'filetracking'})
        self.assertEqual(r.status_code, status.HTTP_200_OK)

    def test_view_drafts_api_missing_src_module(self):
        # 5C: serializer enforces required fields
        r = self.client.get('/filetracking/api/draft/', {'username': 'sender1'})
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_archive_api(self):
        fid = services.create_file_via_sdk(
            'sender1', 'faculty', 'receiver1', 'hod', subject='Arch API')
        r = self.client.post('/filetracking/api/createarchive/', {'file_id': fid})
        self.assertEqual(r.status_code, status.HTTP_200_OK)

    def test_view_archived_api(self):
        # 5C: now uses ArchiveQuerySerializer
        r = self.client.get('/filetracking/api/archive/', {
            'username': 'sender1', 'designation': 'faculty', 'src_module': 'filetracking'})
        self.assertEqual(r.status_code, status.HTTP_200_OK)

    def test_view_archived_api_missing_src_module(self):
        r = self.client.get('/filetracking/api/archive/', {'username': 'sender1'})
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_designations_api_requires_auth(self):
        r = APIClient().get('/filetracking/api/designations/sender1/')
        self.assertIn(r.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])

    def test_designations_api_with_auth(self):
        r = self.client.get('/filetracking/api/designations/sender1/')
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertIn('faculty', r.data['designations'])

    def test_forward_file_too_large_rejected_by_service(self):
        # T-09/S-16: size enforcement now in services.forward_file (not view)
        fid = services.create_file_via_sdk(
            'sender1', 'faculty', 'receiver1', 'hod', subject='FwdSzTest')
        big = MagicMock()
        big.size = MAX_FILE_SIZE_BYTES + 1
        with self.assertRaises(ValidationError):
            services.forward_file(fid, 'receiver1', 'hod', {}, 'test', big)


# ===========================================================================
# Constants Tests
# ===========================================================================

class ModelConstantsTests(TestCase):

    def test_max_file_size_bytes(self):
        self.assertEqual(MAX_FILE_SIZE_BYTES, 10 * 1024 * 1024)

    def test_fallback_department_code(self):
        # T-15/S-37
        self.assertEqual(FALLBACK_DEPARTMENT_CODE, 'FTS')
