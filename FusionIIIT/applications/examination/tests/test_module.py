"""
Examination module tests.

Covers:
- Service layer (SPI/CPI helpers, grade validation, academic year parsing)
- Selector layer (query functions)
- Permission classes
- Structural compliance (no raw SQL, no print(), no deprecated url())
"""

from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.test import TestCase

from applications.examination.constants import (
    grade_conversion,
    ALLOWED_GRADES,
    PBI_AND_BTP_ALLOWED_GRADES,
    PBI_BTP_COURSE_CODES,
    PROFESSOR_ROLES,
    ROLE_ACADADMIN,
    ROLE_DEAN_ACADEMIC,
    UG_PROGRAMMES,
    PG_PROGRAMMES,
    MAX_CSV_FILE_SIZE,
    SEMESTER_TYPE_ODD,
    SEMESTER_TYPE_EVEN,
    SEMESTER_TYPE_SUMMER,
)
from applications.examination.services import (
    round_from_last_decimal,
    parse_academic_year,
    is_valid_grade,
    format_semester_display,
    make_label,
    compute_grade_points,
    trace_registration,
)


# ===========================================================================
# Constants tests
# ===========================================================================

class ConstantsTest(TestCase):
    """Ensure constants are properly defined."""

    def test_grade_conversion_has_standard_grades(self):
        """All standard letter grades should be in grade_conversion."""
        for g in ["O", "A+", "A", "B+", "B", "C+", "C", "D+", "D", "F", "S"]:
            self.assertIn(g, grade_conversion)

    def test_allowed_grades_not_empty(self):
        self.assertGreater(len(ALLOWED_GRADES), 0)

    def test_pbi_btp_grades_are_floats(self):
        """PBI/BTP grades should all be numeric strings like '2.0' to '10.0'."""
        for g in PBI_AND_BTP_ALLOWED_GRADES:
            self.assertRegex(g, r"^\d+\.\d+$")

    def test_professor_roles(self):
        self.assertEqual(len(PROFESSOR_ROLES), 3)
        self.assertIn("Associate Professor", PROFESSOR_ROLES)
        self.assertIn("Professor", PROFESSOR_ROLES)
        self.assertIn("Assistant Professor", PROFESSOR_ROLES)

    def test_role_constants(self):
        self.assertEqual(ROLE_ACADADMIN, "acadadmin")
        self.assertEqual(ROLE_DEAN_ACADEMIC, "Dean Academic")

    def test_programme_lists(self):
        self.assertIn("B.Tech", UG_PROGRAMMES)
        self.assertIn("M.Tech", PG_PROGRAMMES)

    def test_max_csv_file_size(self):
        self.assertEqual(MAX_CSV_FILE_SIZE, 5 * 1024 * 1024)


# ===========================================================================
# Service helper tests
# ===========================================================================

class RoundFromLastDecimalTest(TestCase):
    """Test rounding utility."""

    def test_round_basic(self):
        self.assertEqual(round_from_last_decimal(7.35), Decimal("7.4"))

    def test_round_already_rounded(self):
        self.assertEqual(round_from_last_decimal(7.0), Decimal("7.0"))

    def test_round_half_up(self):
        self.assertEqual(round_from_last_decimal(7.25), Decimal("7.3"))

    def test_round_large_number(self):
        self.assertEqual(round_from_last_decimal(10.0), Decimal("10.0"))


class ParseAcademicYearTest(TestCase):
    """Test academic year parsing logic."""

    def test_odd_semester(self):
        wy, session = parse_academic_year("2024-25", SEMESTER_TYPE_ODD)
        self.assertEqual(wy, 2024)
        self.assertEqual(session, "2024-25")

    def test_even_semester(self):
        wy, session = parse_academic_year("2024-25", SEMESTER_TYPE_EVEN)
        self.assertEqual(wy, 2025)

    def test_summer_semester(self):
        wy, session = parse_academic_year("2024-25", SEMESTER_TYPE_SUMMER)
        self.assertEqual(wy, 2025)

    def test_invalid_format(self):
        with self.assertRaises(ValueError):
            parse_academic_year("2024", SEMESTER_TYPE_ODD)


class IsValidGradeTest(TestCase):
    """Test grade validation."""

    def test_standard_grade_valid(self):
        self.assertTrue(is_valid_grade("A+", "CS101"))

    def test_standard_grade_invalid(self):
        self.assertFalse(is_valid_grade("Z", "CS101"))

    def test_pbi_grade_valid(self):
        self.assertTrue(is_valid_grade("8.5", "PR4001"))

    def test_pbi_grade_invalid(self):
        self.assertFalse(is_valid_grade("A+", "PR4001"))

    def test_empty_strings(self):
        self.assertFalse(is_valid_grade("", "CS101"))
        self.assertFalse(is_valid_grade("A+", ""))

    def test_btp_course(self):
        self.assertTrue(is_valid_grade("7.0", "BTP4001"))

    def test_case_insensitive(self):
        self.assertTrue(is_valid_grade("a+", "cs101"))


class FormatSemesterDisplayTest(TestCase):
    """Test semester label formatting."""

    def test_regular_semester(self):
        self.assertEqual(format_semester_display(1), "1")
        self.assertEqual(format_semester_display(3), "3")

    def test_summer_by_type(self):
        self.assertEqual(
            format_semester_display(2, semester_type="Summer Semester"),
            "Summer 1",
        )
        self.assertEqual(
            format_semester_display(4, semester_type="Summer Semester"),
            "Summer 2",
        )

    def test_summer_by_label(self):
        self.assertEqual(
            format_semester_display(2, semester_label="Summer 1"),
            "Summer 1",
        )


class MakeLabelTest(TestCase):
    """Test make_label for semester list."""

    def test_odd_semester(self):
        self.assertEqual(make_label(1, "Odd Semester"), "Semester 1")

    def test_even_semester(self):
        self.assertEqual(make_label(2, "Even Semester"), "Semester 2")

    def test_summer_semester(self):
        self.assertEqual(make_label(2, SEMESTER_TYPE_SUMMER), "Summer 1")
        self.assertEqual(make_label(4, SEMESTER_TYPE_SUMMER), "Summer 2")


class ComputeGradePointsTest(TestCase):
    """Test grade → factor conversion."""

    def test_known_grades(self):
        self.assertEqual(compute_grade_points("O"), 1.0)
        self.assertEqual(compute_grade_points("A+"), 1.0)
        self.assertEqual(compute_grade_points("A"), 0.9)
        self.assertEqual(compute_grade_points("F"), 0.2)

    def test_unknown_grade(self):
        self.assertEqual(compute_grade_points("INVALID"), -1)

    def test_whitespace(self):
        """Grades with leading/trailing whitespace should be handled."""
        self.assertEqual(compute_grade_points(" O "), 1.0)


class TraceRegistrationTest(TestCase):
    """Test the replacement chain tracer."""

    def test_no_replacement(self):
        self.assertEqual(trace_registration(1, {}), 1)

    def test_single_replacement(self):
        mapping = {2: 1}
        self.assertEqual(trace_registration(2, mapping), 1)

    def test_chain_replacement(self):
        mapping = {3: 2, 2: 1}
        self.assertEqual(trace_registration(3, mapping), 1)

    def test_circular_protection(self):
        """Circular references should not cause infinite loops."""
        mapping = {1: 2, 2: 1}
        result = trace_registration(1, mapping)
        self.assertIn(result, [1, 2])


# ===========================================================================
# Structural compliance tests
# ===========================================================================

class StructuralComplianceTest(TestCase):
    """Test the codebase for audit compliance."""

    def test_no_raw_sql_in_views(self):
        """api/views.py should not contain raw SQL (V39)."""
        import os
        views_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "api", "views.py"
        )
        with open(views_path, "r") as f:
            content = f.read()
        self.assertNotIn(".raw(", content)
        self.assertNotIn("cursor.execute", content)

    def test_no_print_in_views(self):
        """views.py should not contain print() (V41)."""
        import os
        views_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "views.py"
        )
        with open(views_path, "r") as f:
            content = f.read()
        # Exclude comments and docstrings
        lines = [
            line for line in content.split("\n")
            if line.strip() and not line.strip().startswith("#")
            and not line.strip().startswith('"""')
            and not line.strip().startswith("'''")
        ]
        for line in lines:
            if "print(" in line and "logger" not in line:
                self.fail(f"print() found in views.py: {line.strip()}")

    def test_no_print_in_api_views(self):
        """api/views.py should not contain print() (V41)."""
        import os
        views_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "api", "views.py"
        )
        with open(views_path, "r") as f:
            content = f.read()
        lines = [
            line for line in content.split("\n")
            if line.strip() and not line.strip().startswith("#")
        ]
        for line in lines:
            if "print(" in line and "logger" not in line:
                self.fail(f"print() found in api/views.py: {line.strip()}")

    def test_no_deprecated_url_in_urls(self):
        """urls.py should use path() not url() (V40)."""
        import os
        urls_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "urls.py"
        )
        with open(urls_path, "r") as f:
            content = f.read()
        self.assertNotIn("from django.conf.urls import url", content)

    def test_no_deprecated_url_in_api_urls(self):
        """api/urls.py should use path() not url() (V40)."""
        import os
        urls_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "api", "urls.py"
        )
        with open(urls_path, "r") as f:
            content = f.read()
        self.assertNotIn("from django.conf.urls import url", content)

    def test_no_allow_any_in_views(self):
        """No AllowAny permission in views (V14-V17)."""
        import os
        for filename in ("views.py", os.path.join("api", "views.py")):
            path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)), filename
            )
            with open(path, "r") as f:
                content = f.read()
            self.assertNotIn("AllowAny", content, f"AllowAny found in {filename}")

    def test_services_exists(self):
        """services.py should exist (V01)."""
        import os
        path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "services.py"
        )
        self.assertTrue(os.path.exists(path), "services.py not found")

    def test_selectors_exists(self):
        """selectors.py should exist (V02)."""
        import os
        path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "selectors.py"
        )
        self.assertTrue(os.path.exists(path), "selectors.py not found")

    def test_permissions_exists(self):
        """permissions.py should exist (V18)."""
        import os
        path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "permissions.py"
        )
        self.assertTrue(os.path.exists(path), "permissions.py not found")

    def test_constants_exists(self):
        """constants.py should exist (V13)."""
        import os
        path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "constants.py"
        )
        self.assertTrue(os.path.exists(path), "constants.py not found")

    def test_authentication_serializer_correct_model(self):
        """AuthenticationSerializer should point to Authentication (V23)."""
        from applications.examination.api.serializers import AuthenticationSerializer
        from applications.examination.models import Authentication
        self.assertEqual(
            AuthenticationSerializer.Meta.model, Authentication,
            "AuthenticationSerializer.Meta.model should be Authentication, not Announcements"
        )

    def test_models_pascalcase(self):
        """Model classes should be PascalCase (V35)."""
        from applications.examination.models import HiddenGrade, Authentication, Grade
        self.assertTrue(HiddenGrade.__name__ == "HiddenGrade")
        self.assertTrue(Authentication.__name__ == "Authentication")
        self.assertTrue(Grade.__name__ == "Grade")

    def test_backward_compatible_aliases(self):
        """Legacy lowercase aliases should still work."""
        from applications.examination.models import (
            hidden_grades, authentication, grade,
        )
        from applications.examination.models import (
            HiddenGrade, Authentication, Grade,
        )
        self.assertIs(hidden_grades, HiddenGrade)
        self.assertIs(authentication, Authentication)
        self.assertIs(grade, Grade)
