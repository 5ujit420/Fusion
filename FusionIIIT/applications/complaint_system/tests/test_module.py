from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from applications.complaint_system import services


class ComplaintSystemServiceTests(SimpleTestCase):
    def test_get_finish_date_preserves_user_mapping(self):
        self.assertEqual(services.get_finish_date("Internet", "user").day - services.get_finish_date("Electricity", "user").day >= 0, True)

    def test_get_designation_for_location_preserves_existing_mapping(self):
        self.assertEqual(services.get_designation_for_location("hall-3"), "hall3caretaker")
        self.assertEqual(services.get_designation_for_location("unknown"), "rewacaretaker")

    def test_prepare_complaint_payload_sets_defaults(self):
        payload = services.prepare_complaint_payload({"complaint_type": "Electricity"}, 7, "user")
        self.assertEqual(payload["complainer"], 7)
        self.assertEqual(payload["status"], 0)
        self.assertIn("complaint_finish", payload)

    def test_route_user_preserves_role_priority(self):
        extrainfo = SimpleNamespace(user_type="student")
        with patch("applications.complaint_system.services.selectors.get_user_role_flags") as role_flags:
            role_flags.return_value = {
                "is_service_provider": True,
                "is_complaint_admin": True,
                "is_caretaker": True,
                "is_warden": True,
            }
            self.assertEqual(
                services.route_user(extrainfo),
                {"user_type": "service_provider", "next_url": "/complaint/service_provider/"},
            )

    def test_change_complaint_status_clears_worker_for_terminal_states(self):
        complaint = MagicMock()
        complaint.worker_id = object()
        services.change_complaint_status(complaint, "2")
        self.assertEqual(complaint.status, "2")
        self.assertIsNone(complaint.worker_id)
        complaint.save.assert_called_once()
