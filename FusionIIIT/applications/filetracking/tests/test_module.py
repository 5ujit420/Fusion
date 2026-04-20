import shutil
import tempfile
from unittest import mock

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework.test import APIRequestFactory, force_authenticate

from applications.filetracking.api.views import CreateDraftFile, CreateFileView, ForwardFileView
from applications.filetracking.models import File, Tracking
from applications.filetracking.sdk.methods import create_file, view_history, view_inbox, view_outbox
from applications.globals.models import DepartmentInfo, Designation, ExtraInfo, HoldsDesignation


@override_settings(MEDIA_ROOT=tempfile.gettempdir())
class FileTrackingRefactorTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.department = DepartmentInfo.objects.create(name="CSE")
        self.sender_designation = Designation.objects.create(name="sender_designation")
        self.receiver_designation = Designation.objects.create(name="receiver_designation")

        self.sender = User.objects.create_user(username="sender", password="pass")
        self.receiver = User.objects.create_user(username="receiver", password="pass")

        self.sender_extrainfo = ExtraInfo.objects.create(
            id="E001",
            user=self.sender,
            user_type="staff",
            department=self.department,
        )
        self.receiver_extrainfo = ExtraInfo.objects.create(
            id="E002",
            user=self.receiver,
            user_type="staff",
            department=self.department,
        )

        HoldsDesignation.objects.create(
            user=self.sender,
            working=self.sender,
            designation=self.sender_designation,
        )
        HoldsDesignation.objects.create(
            user=self.receiver,
            working=self.receiver,
            designation=self.receiver_designation,
        )

    def tearDown(self):
        media_root = tempfile.gettempdir()
        shutil.rmtree(f"{media_root}\\filetracking", ignore_errors=True)

    def test_create_file_service_creates_file_and_initial_tracking(self):
        file_id = create_file(
            uploader=self.sender,
            uploader_designation=self.sender_designation.name,
            receiver=self.receiver.username,
            receiver_designation=self.receiver_designation.name,
            subject="Subject",
            description="Description",
            src_module="filetracking",
            remarks="Initial remarks",
        )

        created_file = File.objects.get(id=file_id)
        self.assertEqual(created_file.subject, "Subject")
        self.assertEqual(created_file.designation, self.sender_designation)
        self.assertEqual(Tracking.objects.filter(file_id=created_file).count(), 1)

    def test_view_inbox_and_outbox_return_enriched_rows(self):
        create_file(
            uploader=self.sender,
            uploader_designation=self.sender_designation.name,
            receiver=self.receiver.username,
            receiver_designation=self.receiver_designation.name,
            subject="Inbox subject",
            description="Inbox description",
            src_module="filetracking",
            remarks="Inbox remarks",
        )

        inbox_rows = view_inbox(self.receiver.username, self.receiver_designation.name, "filetracking")
        outbox_rows = view_outbox(self.sender.username, self.sender_designation.name, "filetracking")

        self.assertEqual(len(inbox_rows), 1)
        self.assertEqual(inbox_rows[0]["sent_by_user"], self.sender.username)
        self.assertEqual(inbox_rows[0]["uploader_designation"], self.sender_designation.name)
        self.assertEqual(len(outbox_rows), 1)
        self.assertEqual(outbox_rows[0]["receiver"], self.receiver.username)

    @mock.patch("applications.filetracking.api.views.file_tracking_notif")
    def test_create_file_api_returns_file_id(self, mock_notify):
        uploaded_file = SimpleUploadedFile("hello.txt", b"hello world")
        request = self.factory.post(
            "/filetracking/api/file/",
            {
                "designation": self.sender_designation.name,
                "receiver_username": self.receiver.username,
                "receiver_designation": self.receiver_designation.name,
                "subject": "API Subject",
                "description": "API Description",
                "src_module": "filetracking",
                "remarks": "API Remarks",
                "files": [uploaded_file],
            },
            format="multipart",
        )
        force_authenticate(request, user=self.sender)
        response = CreateFileView.as_view()(request)

        self.assertEqual(response.status_code, 201)
        self.assertIn("file_id", response.data)
        self.assertTrue(mock_notify.called)

    @mock.patch("applications.filetracking.api.views.file_tracking_notif")
    def test_forward_file_api_returns_tracking_id(self, mock_notify):
        file_id = create_file(
            uploader=self.sender,
            uploader_designation=self.sender_designation.name,
            receiver=self.receiver.username,
            receiver_designation=self.receiver_designation.name,
            subject="Forward Subject",
            description="Forward Description",
            src_module="filetracking",
            remarks="Forward remarks",
        )
        third_user = User.objects.create_user(username="third", password="pass")
        ExtraInfo.objects.create(
            id="E003",
            user=third_user,
            user_type="staff",
            department=self.department,
        )
        third_designation = Designation.objects.create(name="third_designation")
        HoldsDesignation.objects.create(user=third_user, working=third_user, designation=third_designation)

        request = self.factory.post(
            f"/filetracking/api/forwardfile/{file_id}/",
            {
                "receiver": third_user.username,
                "receiver_designation": third_designation.name,
                "remarks": "Forwarded",
            },
            format="multipart",
        )
        force_authenticate(request, user=self.receiver)
        response = ForwardFileView.as_view()(request, file_id=file_id)

        self.assertEqual(response.status_code, 201)
        self.assertIn("tracking_ids", response.data)
        self.assertTrue(mock_notify.called)
        self.assertEqual(view_history(file_id)[0]["receiver_id"], third_user.id)

    def test_create_draft_api_returns_file_ids(self):
        uploaded_file = SimpleUploadedFile("draft.txt", b"draft")
        request = self.factory.post(
            "/filetracking/api/createdraft/",
            {
                "designation": self.sender_designation.name,
                "src_module": "filetracking",
                "subject": "Draft Subject",
                "description": "Draft Description",
                "remarks": "Draft remarks",
                "files": [uploaded_file],
            },
            format="multipart",
        )
        force_authenticate(request, user=self.sender)
        response = CreateDraftFile.as_view()(request)

        self.assertEqual(response.status_code, 201)
        self.assertEqual(len(response.data["file_ids"]), 1)
