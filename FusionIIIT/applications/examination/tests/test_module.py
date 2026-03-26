"""
tests/test_module.py — Unit and integration tests for the examination module.
"""

import csv
import json
from decimal import Decimal
from io import BytesIO, StringIO
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase, RequestFactory
from rest_framework.test import APIClient, APITestCase
from rest_framework import status as http_status

from applications.examination.models import (
    ALLOWED_GRADES,
    GRADE_CONVERSION,
    PBI_AND_BTP_ALLOWED_GRADES,
    PBI_BTP_COURSE_CODES,
    PROFESSOR_ROLES,
    ADMIN_ROLES,
    DEAN_ROLES,
    ADMIN_OR_DEAN_ROLES,
    ALL_STAFF_ROLES,
    UG_PROGRAMMES,
    PG_PROGRAMMES,
    SemesterType,
    hidden_grades,
    authentication,
    grade,
    ResultAnnouncement,
)
from applications.examination import services

User = get_user_model()


# ---------------------------------------------------------------------------
# Unit Tests — Constants & Models
# ---------------------------------------------------------------------------

class TestConstants(TestCase):
    """Verify domain constants are correctly defined."""

    def test_allowed_grades_contains_standard_grades(self):
        expected = {"O", "A+", "A", "B+", "B", "C+", "C", "D+", "D", "F", "CD", "S", "X"}
        self.assertEqual(ALLOWED_GRADES, frozenset(expected))

    def test_pbi_btp_allowed_grades_contains_decimal_grades(self):
        self.assertIn("10.0", PBI_AND_BTP_ALLOWED_GRADES)
        self.assertIn("2.0", PBI_AND_BTP_ALLOWED_GRADES)
        self.assertIn("5.5", PBI_AND_BTP_ALLOWED_GRADES)
        self.assertNotIn("1.9", PBI_AND_BTP_ALLOWED_GRADES)

    def test_pbi_btp_course_codes(self):
        self.assertIn("PR4001", PBI_BTP_COURSE_CODES)
        self.assertIn("PR4002", PBI_BTP_COURSE_CODES)
        self.assertIn("BTP4001", PBI_BTP_COURSE_CODES)

    def test_grade_conversion_standard_grades(self):
        self.assertEqual(GRADE_CONVERSION["O"], 1.0)
        self.assertEqual(GRADE_CONVERSION["A+"], 1.0)
        self.assertEqual(GRADE_CONVERSION["A"], 0.9)
        self.assertEqual(GRADE_CONVERSION["F"], 0.2)
        self.assertEqual(GRADE_CONVERSION["S"], 0.0)

    def test_grade_conversion_extended_grades(self):
        self.assertIn("A1", GRADE_CONVERSION)
        self.assertIn("B5", GRADE_CONVERSION)

    def test_role_constants(self):
        self.assertIn("acadadmin", ADMIN_ROLES)
        self.assertIn("Dean Academic", DEAN_ROLES)
        self.assertTrue(PROFESSOR_ROLES.issubset(ALL_STAFF_ROLES))
        self.assertTrue(ADMIN_OR_DEAN_ROLES.issubset(ALL_STAFF_ROLES))

    def test_programme_constants(self):
        self.assertIn("B.Tech", UG_PROGRAMMES)
        self.assertIn("B.Des", UG_PROGRAMMES)
        self.assertIn("M.Tech", PG_PROGRAMMES)
        self.assertIn("PhD", PG_PROGRAMMES)

    def test_semester_type_choices(self):
        self.assertEqual(SemesterType.ODD, "Odd Semester")
        self.assertEqual(SemesterType.EVEN, "Even Semester")
        self.assertEqual(SemesterType.SUMMER, "Summer Semester")


class TestModelStr(TestCase):
    """Verify model __str__ methods."""

    def test_hidden_grades_str(self):
        obj = hidden_grades(student_id="2021001", course_id="CS101")
        self.assertEqual(str(obj), "2021001, CS101")


# ---------------------------------------------------------------------------
# Unit Tests — Service functions
# ---------------------------------------------------------------------------

class TestParseAcademicYear(TestCase):
    def test_odd_semester(self):
        year, session = services.parse_academic_year("2024-25", "Odd Semester")
        self.assertEqual(year, 2024)
        self.assertEqual(session, "2024-25")

    def test_even_semester(self):
        year, session = services.parse_academic_year("2024-25", "Even Semester")
        self.assertEqual(year, 2025)
        self.assertEqual(session, "2024-25")

    def test_summer_semester(self):
        year, session = services.parse_academic_year("2024-25", "Summer Semester")
        self.assertEqual(year, 2025)
        self.assertEqual(session, "2024-25")

    def test_invalid_format_raises(self):
        with self.assertRaises(ValueError):
            services.parse_academic_year("2024", "Odd Semester")


class TestIsValidGrade(TestCase):
    def test_standard_grade_valid(self):
        self.assertTrue(services.is_valid_grade("A+", "CS101"))
        self.assertTrue(services.is_valid_grade("O", "ME201"))
        self.assertTrue(services.is_valid_grade("F", "EC301"))

    def test_standard_grade_invalid(self):
        self.assertFalse(services.is_valid_grade("Z", "CS101"))
        self.assertFalse(services.is_valid_grade("5.5", "CS101"))

    def test_pbi_btp_grade_valid(self):
        self.assertTrue(services.is_valid_grade("5.5", "PR4001"))
        self.assertTrue(services.is_valid_grade("10.0", "BTP4001"))
        self.assertTrue(services.is_valid_grade("2.0", "PR4002"))

    def test_pbi_btp_standard_grade_invalid(self):
        self.assertFalse(services.is_valid_grade("A+", "PR4001"))

    def test_empty_inputs_return_false(self):
        self.assertFalse(services.is_valid_grade("", "CS101"))
        self.assertFalse(services.is_valid_grade("A", ""))
        self.assertFalse(services.is_valid_grade(None, "CS101"))
        self.assertFalse(services.is_valid_grade("A", None))


class TestRoundFromLastDecimal(TestCase):
    def test_basic_rounding(self):
        result = services.round_from_last_decimal(Decimal("8.45"))
        self.assertEqual(result, Decimal("8.5"))

    def test_round_down(self):
        result = services.round_from_last_decimal(Decimal("8.44"))
        self.assertEqual(result, Decimal("8.4"))

    def test_exact_value(self):
        result = services.round_from_last_decimal(Decimal("8.0"))
        self.assertEqual(result, Decimal("8.0"))

    def test_large_decimal(self):
        result = services.round_from_last_decimal(Decimal("9.999"))
        self.assertEqual(result, Decimal("10.0"))


class TestFormatSemesterDisplay(TestCase):
    def test_regular_semester(self):
        self.assertEqual(services.format_semester_display(3), "3")

    def test_summer_semester_by_type(self):
        self.assertEqual(
            services.format_semester_display(2, semester_type="Summer Semester"),
            "Summer 1",
        )
        self.assertEqual(
            services.format_semester_display(4, semester_type="Summer Semester"),
            "Summer 2",
        )

    def test_summer_semester_by_label(self):
        self.assertEqual(
            services.format_semester_display(2, semester_label="Summer Term"),
            "Summer Term",
        )

    def test_odd_semester_not_summer(self):
        self.assertEqual(
            services.format_semester_display(5, semester_type="Odd Semester"),
            "5",
        )


class TestMakeSemesterLabel(TestCase):
    def test_odd_semester(self):
        self.assertEqual(services.make_semester_label(1, "Odd Semester"), "Semester 1")
        self.assertEqual(services.make_semester_label(3, "Even Semester"), "Semester 3")

    def test_even_regular(self):
        self.assertEqual(services.make_semester_label(4, "Even Semester"), "Semester 4")

    def test_summer(self):
        self.assertEqual(services.make_semester_label(2, "Summer Semester"), "Summer 1")
        self.assertEqual(services.make_semester_label(4, "Summer Semester"), "Summer 2")


class TestTraceRegistration(TestCase):
    def test_no_replacement(self):
        result = services.trace_registration(1, {})
        self.assertEqual(result, 1)

    def test_single_replacement(self):
        result = services.trace_registration(2, {2: 1})
        self.assertEqual(result, 1)

    def test_chain_replacement(self):
        result = services.trace_registration(3, {3: 2, 2: 1})
        self.assertEqual(result, 1)

    def test_circular_replacement_does_not_loop(self):
        result = services.trace_registration(1, {1: 2, 2: 1})
        # Should terminate without infinite loop
        self.assertIn(result, [1, 2])


class TestGetRedirectUrlForRole(TestCase):
    def test_professor_roles(self):
        for role in PROFESSOR_ROLES:
            url = services.get_redirect_url_for_role(role)
            self.assertEqual(url, "/examination/submitGradesProf/")

    def test_acadadmin(self):
        url = services.get_redirect_url_for_role("acadadmin")
        self.assertEqual(url, "/examination/updateGrades/")

    def test_dean(self):
        url = services.get_redirect_url_for_role("Dean Academic")
        self.assertEqual(url, "/examination/verifyGradesDean/")

    def test_unknown_role(self):
        url = services.get_redirect_url_for_role("student")
        self.assertEqual(url, "/dashboard/")


class TestComputeGradePoints(TestCase):
    def test_standard_grade(self):
        self.assertEqual(services.compute_grade_points("O"), Decimal("10.0"))
        self.assertEqual(services.compute_grade_points("A"), Decimal("9.0"))

    def test_unknown_grade(self):
        self.assertEqual(services.compute_grade_points("Z"), Decimal("0.0"))


class TestGetProgrammeListOrError(TestCase):
    def test_ug(self):
        result = services.get_programme_list_or_error("UG")
        self.assertEqual(result, list(UG_PROGRAMMES))

    def test_pg(self):
        result = services.get_programme_list_or_error("PG")
        self.assertEqual(result, list(PG_PROGRAMMES))

    def test_none(self):
        result = services.get_programme_list_or_error(None)
        self.assertIsNone(result)

    def test_invalid_raises(self):
        with self.assertRaises(ValueError):
            services.get_programme_list_or_error("INVALID")


# ---------------------------------------------------------------------------
# Unit Tests — Serializer validation
# ---------------------------------------------------------------------------

class TestSerializerValidation(TestCase):
    def test_exam_view_serializer_requires_role(self):
        from applications.examination.api.serializers import ExamViewSerializer

        s = ExamViewSerializer(data={})
        self.assertFalse(s.is_valid())

        s = ExamViewSerializer(data={"Role": "acadadmin"})
        self.assertTrue(s.is_valid())

    def test_submit_grades_serializer_rejects_non_admin(self):
        from applications.examination.api.serializers import SubmitGradesSerializer

        s = SubmitGradesSerializer(data={"Role": "student"})
        self.assertFalse(s.is_valid())

    def test_submit_grades_serializer_accepts_admin(self):
        from applications.examination.api.serializers import SubmitGradesSerializer

        s = SubmitGradesSerializer(data={"Role": "acadadmin"})
        self.assertTrue(s.is_valid())

    def test_moderate_grades_requires_matching_lengths(self):
        from applications.examination.api.serializers import ModerateStudentGradesSerializer

        s = ModerateStudentGradesSerializer(data={
            "Role": "acadadmin",
            "student_ids": ["s1", "s2"],
            "semester_ids": ["1"],
            "course_ids": ["c1", "c2"],
            "grades": ["A", "B"],
        })
        self.assertFalse(s.is_valid())

    def test_moderate_grades_valid(self):
        from applications.examination.api.serializers import ModerateStudentGradesSerializer

        s = ModerateStudentGradesSerializer(data={
            "Role": "acadadmin",
            "student_ids": ["s1", "s2"],
            "semester_ids": ["1", "2"],
            "course_ids": ["c1", "c2"],
            "grades": ["A", "B"],
        })
        self.assertTrue(s.is_valid())

    def test_download_template_requires_fields(self):
        from applications.examination.api.serializers import DownloadTemplateSerializer

        s = DownloadTemplateSerializer(data={"Role": "acadadmin"})
        self.assertFalse(s.is_valid())

    def test_check_result_serializer(self):
        from applications.examination.api.serializers import CheckResultSerializer

        s = CheckResultSerializer(data={})
        self.assertFalse(s.is_valid())

        s = CheckResultSerializer(data={"semester_no": 3, "semester_type": "Odd Semester"})
        self.assertTrue(s.is_valid())

    def test_verify_grades_dean_rejects_non_dean(self):
        from applications.examination.api.serializers import VerifyGradesDeanSerializer

        s = VerifyGradesDeanSerializer(data={
            "Role": "acadadmin",
            "academic_year": "2024-25",
            "semester_type": "Odd Semester",
        })
        self.assertFalse(s.is_valid())

    def test_verify_grades_dean_accepts_dean(self):
        from applications.examination.api.serializers import VerifyGradesDeanSerializer

        s = VerifyGradesDeanSerializer(data={
            "Role": "Dean Academic",
            "academic_year": "2024-25",
            "semester_type": "Odd Semester",
        })
        self.assertTrue(s.is_valid())

    def test_grade_status_requires_year_and_type(self):
        from applications.examination.api.serializers import GradeStatusSerializer

        s = GradeStatusSerializer(data={"Role": "acadadmin"})
        self.assertFalse(s.is_valid())

        s = GradeStatusSerializer(data={
            "Role": "acadadmin",
            "academic_year": "2024-25",
            "semester_type": "Odd Semester",
        })
        self.assertTrue(s.is_valid())

    def test_create_announcement_requires_batch_and_semester(self):
        from applications.examination.api.serializers import CreateAnnouncementSerializer

        s = CreateAnnouncementSerializer(data={"Role": "acadadmin"})
        self.assertFalse(s.is_valid())

        s = CreateAnnouncementSerializer(data={
            "Role": "acadadmin",
            "batch": 1,
            "semester": 3,
        })
        self.assertTrue(s.is_valid())

    def test_upload_grades_prof_accepts_professor(self):
        from applications.examination.api.serializers import UploadGradesProfSerializer

        for role in PROFESSOR_ROLES:
            s = UploadGradesProfSerializer(data={
                "Role": role,
                "course_id": "1",
                "academic_year": "2024-25",
                "semester_type": "Odd Semester",
            })
            self.assertTrue(s.is_valid(), f"Failed for role: {role}")

    def test_download_excel_requires_equal_lengths(self):
        from applications.examination.api.serializers import DownloadExcelSerializer

        s = DownloadExcelSerializer(data={
            "student_ids": ["s1"],
            "semester_ids": ["1", "2"],
            "course_ids": ["c1"],
            "grades": ["A"],
        })
        self.assertFalse(s.is_valid())


# ---------------------------------------------------------------------------
# Integration Tests — API endpoints
# ---------------------------------------------------------------------------

class TestExamViewAPI(APITestCase):
    """Test the exam_view endpoint."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", password="testpass123"
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_exam_view_requires_role(self):
        response = self.client.post("/examination/api/exam_view/", {})
        self.assertIn(response.status_code, [400, 403])

    def test_exam_view_professor_redirect(self):
        response = self.client.post(
            "/examination/api/exam_view/", {"Role": "Professor"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["redirect_url"], "/examination/submitGradesProf/"
        )

    def test_exam_view_acadadmin_redirect(self):
        response = self.client.post(
            "/examination/api/exam_view/", {"Role": "acadadmin"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["redirect_url"], "/examination/updateGrades/"
        )

    def test_exam_view_dean_redirect(self):
        response = self.client.post(
            "/examination/api/exam_view/", {"Role": "Dean Academic"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["redirect_url"], "/examination/verifyGradesDean/"
        )

    def test_exam_view_unknown_role_redirect(self):
        response = self.client.post(
            "/examination/api/exam_view/", {"Role": "student"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["redirect_url"], "/dashboard/")


class TestUniqueYearsAPI(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", password="testpass123"
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_unique_student_grade_years_unauthenticated(self):
        client = APIClient()
        response = client.get("/examination/api/unique-stu-grades-years/")
        self.assertEqual(response.status_code, 401)

    def test_unique_student_grade_years_authenticated(self):
        response = self.client.get("/examination/api/unique-stu-grades-years/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("academic_years", response.data)

    def test_unique_registration_years_authenticated(self):
        response = self.client.get("/examination/api/unique-course-reg-years/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("academic_years", response.data)


class TestAccessControlAPI(APITestCase):
    """Test that role-based access control works across endpoints."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", password="testpass123"
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_submit_grades_denies_non_admin(self):
        response = self.client.post(
            "/examination/api/submitGrades/",
            {"Role": "student"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_update_grades_denies_non_admin(self):
        response = self.client.post(
            "/examination/api/update_grades/",
            {"Role": "Professor", "academic_year": "2024-25", "semester_type": "Odd Semester"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_verify_grades_dean_denies_non_dean(self):
        response = self.client.post(
            "/examination/api/verify_grades_dean/",
            {"Role": "acadadmin", "academic_year": "2024-25", "semester_type": "Odd Semester"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_validate_dean_denies_non_dean(self):
        response = self.client.post(
            "/examination/api/validate_dean/",
            {"Role": "acadadmin"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_upload_grades_denies_non_admin(self):
        response = self.client.post(
            "/examination/api/upload_grades/",
            {"Role": "Professor", "course_id": "1", "academic_year": "2024-25", "semester_type": "Odd"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_download_template_denies_unauthorized_role(self):
        response = self.client.post(
            "/examination/api/download_template/",
            {"Role": "student", "course": "1", "year": "2024-25", "semester_type": "Odd Semester"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_unauthenticated_requests_denied(self):
        client = APIClient()
        endpoints = [
            ("/examination/api/submitGrades/", "post"),
            ("/examination/api/upload_grades/", "post"),
            ("/examination/api/update_grades/", "post"),
            ("/examination/api/verify_grades_dean/", "post"),
            ("/examination/api/check_result/", "post"),
            ("/examination/api/grade_status/", "post"),
        ]
        for url, method in endpoints:
            response = getattr(client, method)(url, {}, format="json")
            self.assertEqual(
                response.status_code, 401,
                f"Expected 401 for unauthenticated {method.upper()} {url}, got {response.status_code}",
            )


class TestStudentSemesterListAPI(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", password="testpass123"
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_returns_success_with_semesters(self):
        response = self.client.get("/examination/api/student/result_semesters/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertIn("semesters", data)
        self.assertIsInstance(data["semesters"], list)


class TestDownloadExcelAPI(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", password="testpass123"
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_valid_data_returns_csv(self):
        response = self.client.post(
            "/examination/api/download_excel/",
            {
                "student_ids": ["s1", "s2"],
                "semester_ids": ["1", "2"],
                "course_ids": ["c1", "c2"],
                "grades": ["A", "B"],
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv")
        content = response.content.decode("utf-8")
        self.assertIn("Student ID", content)
        self.assertIn("s1", content)

    def test_invalid_data_returns_400(self):
        response = self.client.post(
            "/examination/api/download_excel/",
            {
                "student_ids": ["s1"],
                "semester_ids": ["1", "2"],
                "course_ids": ["c1"],
                "grades": ["A"],
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)


class TestCheckResultAPI(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", password="testpass123"
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_missing_params_returns_400(self):
        response = self.client.post(
            "/examination/api/check_result/", {}, format="json"
        )
        self.assertEqual(response.status_code, 400)

    def test_nonexistent_student_returns_error(self):
        response = self.client.post(
            "/examination/api/check_result/",
            {"semester_no": 3, "semester_type": "Odd Semester"},
            format="json",
        )
        data = response.json()
        self.assertFalse(data.get("success", True))


class TestGradeStatusAPI(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", password="testpass123"
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_missing_params_returns_400(self):
        response = self.client.post(
            "/examination/api/grade_status/",
            {"Role": "acadadmin"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_valid_request_returns_200(self):
        response = self.client.post(
            "/examination/api/grade_status/",
            {
                "Role": "acadadmin",
                "academic_year": "2024-25",
                "semester_type": "Odd Semester",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["success"])
        self.assertIn("grade_status", response.data)


class TestGradeSummaryAPI(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", password="testpass123"
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_missing_params_returns_400(self):
        response = self.client.post(
            "/examination/api/grade_summary/",
            {"Role": "acadadmin"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)


# ---------------------------------------------------------------------------
# Service function tests with mocked selectors
# ---------------------------------------------------------------------------

class TestGenerateDownloadExcelCSV(TestCase):
    def test_generates_valid_csv(self):
        response = services.generate_download_excel_csv(
            ["s1", "s2"], ["1", "2"], ["c1", "c2"], ["A", "B"]
        )
        self.assertEqual(response["Content-Type"], "text/csv")
        content = response.content.decode("utf-8")
        reader = csv.reader(StringIO(content))
        rows = list(reader)
        self.assertEqual(rows[0], ["Student ID", "Semester ID", "Course ID", "Grade"])
        self.assertEqual(len(rows), 3)  # header + 2 data rows
        self.assertEqual(rows[1], ["s1", "1", "c1", "A"])


class TestCheckCourseStudentsService(TestCase):
    @patch("applications.examination.services.selectors.get_course_registrations")
    def test_returns_count(self, mock_regs):
        mock_qs = MagicMock()
        mock_qs.exists.return_value = True
        mock_qs.count.return_value = 5
        mock_regs.return_value = mock_qs

        has_students, count = services.check_course_students("1", "2024-25", "Odd Semester")
        self.assertTrue(has_students)
        self.assertEqual(count, 5)

    @patch("applications.examination.services.selectors.get_course_registrations")
    def test_no_students(self, mock_regs):
        mock_qs = MagicMock()
        mock_qs.exists.return_value = False
        mock_regs.return_value = mock_qs

        has_students, count = services.check_course_students("1", "2024-25", "Odd Semester")
        self.assertFalse(has_students)
        self.assertEqual(count, 0)


class TestGetStudentSemesterList(TestCase):
    @patch("applications.examination.services.selectors.get_student_semester_list")
    def test_builds_semester_list(self, mock_qs):
        mock_qs.return_value = [(1, "Odd Semester"), (2, "Even Semester"), (2, "Summer Semester")]

        result = services.get_student_semester_list("2021001")
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0]["label"], "Semester 1")
        self.assertEqual(result[1]["label"], "Semester 2")
        self.assertEqual(result[2]["label"], "Summer 1")

    @patch("applications.examination.services.selectors.get_student_semester_list")
    def test_empty_list(self, mock_qs):
        mock_qs.return_value = []
        result = services.get_student_semester_list("2021001")
        self.assertEqual(result, [])
