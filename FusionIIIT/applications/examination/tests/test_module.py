from django.test import SimpleTestCase

from applications.examination import services


class ExaminationServiceTests(SimpleTestCase):
    def test_get_role_redirect_uses_canonical_routes(self):
        self.assertEqual(
            services.get_role_redirect("acadadmin"),
            "/examination/updateGrades/",
        )
        self.assertEqual(
            services.get_role_redirect("Professor"),
            "/examination/submitGradesProf/",
        )
        self.assertEqual(
            services.get_role_redirect("unknown"),
            "/dashboard/",
        )

    def test_parse_academic_year_preserves_existing_semantics(self):
        self.assertEqual(
            services.parse_academic_year("2024-25", "Odd Semester"),
            (2024, "2024-25"),
        )
        self.assertEqual(
            services.parse_academic_year("2024-25", "Even Semester"),
            (2025, "2024-25"),
        )
        self.assertEqual(
            services.parse_academic_year("2024-25", "Summer Semester"),
            (2025, "2024-25"),
        )

    def test_is_valid_grade_supports_special_course_rules(self):
        self.assertTrue(services.is_valid_grade("A", "CS101"))
        self.assertFalse(services.is_valid_grade("9.5", "CS101"))
        self.assertTrue(services.is_valid_grade("9.5", "PBI4001"))

    def test_build_parallel_rows_keeps_row_alignment(self):
        rows = services.build_parallel_rows(
            ["S1", "S2"],
            ["1", "2"],
            ["C1", "C2"],
            ["A", "B"],
        )
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0].student_id, "S1")
        self.assertEqual(rows[1].course_id, "C2")

    def test_apply_credit_weight_uses_shared_policy(self):
        gained_credit, total_credit = services.apply_credit_weight(0, 0, "A", 4)
        self.assertEqual(gained_credit, services.Decimal("3.6"))
        self.assertEqual(total_credit, services.Decimal("4"))

    def test_make_label_preserves_semester_labels(self):
        self.assertEqual(services.make_label(1, "Odd Semester"), "Semester 1")
        self.assertEqual(services.make_label(2, "Summer Semester"), "Summer 1")
