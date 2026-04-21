from unittest.mock import MagicMock, patch

from django.test import RequestFactory, SimpleTestCase

from applications.placement_cell.api.serializers import HasSerializer
from applications.placement_cell.forms import AddPlacementSchedule, AddSchedule, SendInvitation, SendInvite
from applications.placement_cell.models import PlacementSchedule
from applications.placement_cell import views


class PlacementCellRefactorTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_add_placement_schedule_aliases_add_schedule(self):
        self.assertIs(AddPlacementSchedule, AddSchedule)

    def test_send_invitation_aliases_send_invite(self):
        self.assertIs(SendInvitation, SendInvite)

    def test_schedule_get_role_returns_empty_string_without_role(self):
        schedule = PlacementSchedule(role=None)
        self.assertEqual(schedule.get_role, "")

    @patch("applications.placement_cell.api.serializers.services.create_skill_assignment_from_validated_data")
    def test_has_serializer_surfaces_duplicate_skill_validation(self, mock_create):
        from rest_framework import serializers

        mock_create.side_effect = ValueError("This skill is already present")
        serializer = HasSerializer()

        with self.assertRaises(serializers.ValidationError):
            serializer.create({"skill_id": {"skill": "Python"}, "unique_id": MagicMock(), "skill_rating": 90})

    @patch("applications.placement_cell.views.redirect")
    @patch("applications.placement_cell.views.messages")
    @patch("applications.placement_cell.views.services.create_placement_record")
    @patch("applications.placement_cell.views.PlacementRecordSaveForm")
    def test_placement_record_save_delegates_to_service(
        self,
        mock_form_cls,
        mock_create_record,
        mock_messages,
        mock_redirect,
    ):
        request = self.factory.post("/placement/placement_record_save/", data={})
        mock_form = MagicMock()
        mock_form.is_valid.return_value = True
        mock_form.cleaned_data = {
            "placement_type": "PLACEMENT",
            "student_name": "Alice",
            "ctc": 10,
            "year": 2026,
            "test_type": "",
            "test_score": None,
        }
        mock_form_cls.return_value = mock_form

        views.placement_record_save(request)

        mock_create_record.assert_called_once_with(mock_form.cleaned_data)
        mock_messages.success.assert_called_once()
        mock_redirect.assert_called_once()

    @patch("applications.placement_cell.views.redirect")
    @patch("applications.placement_cell.views.messages")
    @patch("applications.placement_cell.views.services.delete_placement_statistics_record")
    def test_delete_placement_statistics_uses_service(self, mock_delete, mock_messages, mock_redirect):
        request = self.factory.post("/placement/delete_placement_statistics/", data={"deleterecord": "7"})

        views.delete_placement_statistics(request)

        mock_delete.assert_called_once_with(7)
        mock_messages.success.assert_called_once()
        mock_redirect.assert_called_once()

    @patch("applications.placement_cell.views.redirect")
    @patch("applications.placement_cell.views.messages")
    @patch("applications.placement_cell.views.services.create_schedule_from_payload")
    @patch("applications.placement_cell.views.AddSchedule")
    def test_placement_schedule_save_uses_form_and_service(
        self,
        mock_form_cls,
        mock_create_schedule,
        mock_messages,
        mock_redirect,
    ):
        request = self.factory.post("/placement/placement_schedule_save/", data={"role": "SWE"})
        mock_form = MagicMock()
        mock_form.is_valid.return_value = True
        mock_form.cleaned_data = {
            "placement_type": "PLACEMENT",
            "company_name": "OpenAI",
            "ctc": 42,
            "description": "desc",
            "location": "Remote",
            "attached_file": None,
            "placement_date": "2026-04-22",
            "time": "10:00",
        }
        mock_form_cls.return_value = mock_form

        views.placement_schedule_save(request)

        mock_create_schedule.assert_called_once()
        mock_messages.success.assert_called_once()
        mock_redirect.assert_called_once()
