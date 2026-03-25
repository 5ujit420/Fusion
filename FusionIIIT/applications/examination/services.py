"""
Examination module services — all business logic.

Every function here was previously embedded in a view class.
Fixes audit violations: V01, V04–V08, V12, V32–V34, V39, R06, R08.
"""

import csv
import logging
from collections import defaultdict, OrderedDict
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from io import BytesIO, StringIO

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Case, When, IntegerField, Q, Count
from django.http import HttpResponse

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill, Border, Side
from openpyxl.utils import get_column_letter

from reportlab.lib import colors
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer, Image,
)

from applications.online_cms.models import Student_grades
from applications.academic_procedures.models import (
    course_registration, course_replacement,
)
from applications.programme_curriculum.models import (
    Course as Courses,
    CourseInstructor,
    CourseSlot,
    Discipline,
    Batch,
)
from applications.academic_information.models import Student
from applications.examination.models import authentication, ResultAnnouncement

from .constants import (
    grade_conversion,
    ALLOWED_GRADES,
    PBI_AND_BTP_ALLOWED_GRADES,
    PBI_BTP_COURSE_CODES,
    ALL_GRADE_LETTERS,
    UG_PROGRAMMES,
    PG_PROGRAMMES,
    MAX_CSV_FILE_SIZE,
    SEMESTER_TYPE_ODD,
    SEMESTER_TYPE_EVEN,
    SEMESTER_TYPE_SUMMER,
)
from . import selectors

logger = logging.getLogger(__name__)
User = get_user_model()


# ===========================================================================
# Pure helper functions (V12)
# ===========================================================================

def round_from_last_decimal(number, decimal_places=1):
    """Round a number using ROUND_HALF_UP to *decimal_places*."""
    d = Decimal(str(number))
    return Decimal(d).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)


def parse_academic_year(academic_year, semester_type):
    """
    Parse an academic year string like ``"2024-25"`` and return
    ``(working_year: int, session: str)``.
    """
    parts = academic_year.split("-")
    if len(parts) != 2:
        raise ValueError(
            "Invalid academic year format. Expected format like '2024-25'."
        )
    first_year = parts[0].strip()
    second_year = parts[1].strip()

    if semester_type == SEMESTER_TYPE_ODD:
        working_year = int(first_year)
    elif semester_type == SEMESTER_TYPE_EVEN:
        working_year = int("20" + second_year)
    else:
        working_year = int("20" + second_year)

    return working_year, academic_year


def is_valid_grade(grade_str: str, course_code: str) -> bool:
    """Return True if *grade_str* is valid for the given *course_code*."""
    if not grade_str or not course_code:
        return False
    code = course_code.strip().upper()
    grade_str = grade_str.strip().upper()

    if code in PBI_BTP_COURSE_CODES:
        return grade_str in PBI_AND_BTP_ALLOWED_GRADES
    return grade_str in ALLOWED_GRADES


def format_semester_display(semester_no, semester_type=None, semester_label=None):
    """Return a human-readable semester string for PDFs."""
    if semester_label and "summer" in semester_label.lower():
        return semester_label
    if semester_type and "summer" in semester_type.lower():
        if semester_no == 2:
            return "Summer 1"
        elif semester_no == 4:
            return "Summer 2"
        elif semester_no == 6:
            return "Summer 3"
        elif semester_no == 8:
            return "Summer 4"
        else:
            return f"Summer {semester_no // 2}"
    return str(semester_no)


def make_label(no: int, sem_type: str) -> str:
    """
    Build a semester label for the student semester list:
    - odd  → "Semester <no>"
    - even & Even Semester → "Semester <no>"
    - even & Summer Semester → "Summer <no//2>"
    """
    if no % 2 == 1:
        return f"Semester {no}"
    if sem_type == SEMESTER_TYPE_SUMMER:
        return f"Summer {no // 2}"
    return f"Semester {no}"


def compute_grade_points(grade_str):
    """
    Convert a letter grade to its numeric factor using ``grade_conversion``.
    Consolidates the large if/elif chains (R08).
    """
    return grade_conversion.get(grade_str.strip(), -1)


# ===========================================================================
# SPI / CPI calculation (V12)
# ===========================================================================

def trace_registration(reg_id, mapping):
    """Follow replacement chain to find the original registration."""
    seen = set()
    while reg_id in mapping and reg_id not in seen:
        seen.add(reg_id)
        reg_id = mapping[reg_id]
    return reg_id


def calculate_spi_for_student(student, selected_semester, semester_type):
    """
    Calculate SPI (Semester Performance Index) for a student.
    Returns ``(spi, semester_unit, total_points_x10)``.
    """
    semester_unit = Decimal("0")
    grades = (
        Student_grades.objects.filter(
            roll_no=student.id_id,
            semester=selected_semester,
            semester_type=semester_type,
        )
        .annotate(
            semester_type_order=Case(
                When(semester_type="Odd Semester", then=0),
                When(semester_type="Even Semester", then=1),
                When(semester_type="Summer Semester", then=2),
                default=3,
                output_field=IntegerField(),
            )
        )
        .order_by("semester", "semester_type_order")
    )

    total_points = Decimal("0")
    total_credits = Decimal("0")

    for g in grades:
        credit = Decimal(str(g.course_id.credit))
        factor = grade_conversion.get(g.grade.strip(), -1)
        if factor >= 0:
            if factor != 0:
                factor = Decimal(str(factor))
                total_points += factor * credit
                total_credits += credit
            semester_unit += credit

    spi = (
        round_from_last_decimal(Decimal("10") * (total_points / total_credits))
        if total_credits
        else 0
    )
    return spi, semester_unit, (total_points * 10)


def calculate_cpi_for_student(student, selected_semester, semester_type):
    """
    Calculate CPI (Cumulative Performance Index) for a student.
    Returns ``(cpi, total_unit, total_points_x10)``.
    """
    total_unit = Decimal("0")

    if selected_semester % 2 == 0 and semester_type == SEMESTER_TYPE_SUMMER:
        grades = (
            Student_grades.objects.filter(
                roll_no=student.id_id,
                semester__lte=selected_semester,
            )
            .annotate(
                semester_type_order=Case(
                    When(semester_type="Odd Semester", then=0),
                    When(semester_type="Even Semester", then=1),
                    When(semester_type="Summer Semester", then=2),
                    default=3,
                    output_field=IntegerField(),
                )
            )
            .order_by("semester", "semester_type_order")
        )
        registrations = (
            course_registration.objects.select_related("course_id", "semester_id")
            .filter(
                student_id=student,
                semester_id__semester_no__lte=selected_semester,
            )
            .annotate(
                semester_type_order=Case(
                    When(semester_type="Odd Semester", then=0),
                    When(semester_type="Even Semester", then=1),
                    When(semester_type="Summer Semester", then=2),
                    default=3,
                    output_field=IntegerField(),
                )
            )
            .order_by("semester_id__semester_no", "semester_type_order")
        )
    else:
        grades = (
            Student_grades.objects.filter(
                roll_no=student.id_id,
                semester__lte=selected_semester,
            ).exclude(
                semester_type=SEMESTER_TYPE_SUMMER,
                semester=selected_semester,
            )
        )
        registrations = (
            course_registration.objects.select_related("course_id", "semester_id")
            .filter(
                student_id=student,
                semester_id__semester_no__lte=selected_semester,
            )
            .exclude(
                semester_type=SEMESTER_TYPE_SUMMER,
                semester_id__semester_no=selected_semester,
            )
        )

    # Build registration mapping
    reg_mapping = {}
    for reg in registrations:
        key = (reg.course_id.code.strip(), reg.semester_id.semester_no, reg.semester_type)
        reg_mapping[key] = reg.id

    # Build replacement chain
    replacements = course_replacement.objects.filter(
        Q(old_course_registration__student_id=student)
        | Q(new_course_registration__student_id=student)
    ).select_related("old_course_registration", "new_course_registration")

    reg_replacement_map = {}
    for rep in replacements:
        old_reg_id = rep.old_course_registration.id
        new_reg_id = rep.new_course_registration.id
        if new_reg_id != old_reg_id:
            reg_replacement_map[new_reg_id] = old_reg_id

    # Group grades by original registration
    grade_groups = defaultdict(list)
    for g in grades:
        key = (g.course_id.code.strip(), g.semester, g.semester_type)
        reg_id = reg_mapping.get(key)
        if reg_id is None:
            continue
        original_reg_id = trace_registration(reg_id, reg_replacement_map)
        grade_groups[original_reg_id].append(g)

    total_points = Decimal("0")
    total_credits = Decimal("0")
    for _orig_reg, g_list in grade_groups.items():
        best_record = max(
            g_list, key=lambda r: grade_conversion.get(r.grade.strip(), -1)
        )
        grade_factor = grade_conversion.get(best_record.grade.strip(), -1)
        credit = Decimal(str(getattr(best_record.course_id, "credit", 3)))
        if grade_factor >= 0:
            if grade_factor != 0:
                grade_factor = Decimal(str(grade_factor))
                total_points += grade_factor * credit
                total_credits += credit
            total_unit += credit

    cpi = (
        round_from_last_decimal(Decimal("10") * (total_points / total_credits))
        if total_credits
        else 0
    )
    return cpi, total_unit, (total_points * 10)


def gather_related_registrations(initial_reg, max_semester):
    """
    Using BFS, collect all course_registration objects related by
    replacements up to *max_semester*, ignoring semester_type.
    """
    related = set()
    queue = [initial_reg]
    while queue:
        reg = queue.pop(0)
        if reg.id in related:
            continue
        related.add(reg.id)
        olds = course_replacement.objects.filter(old_course_registration=reg)
        news = course_replacement.objects.filter(new_course_registration=reg)
        for rep in list(olds) + list(news):
            for neighbor in (
                rep.old_course_registration,
                rep.new_course_registration,
            ):
                if (
                    neighbor.student_id == initial_reg.student_id
                    and neighbor.semester_id.semester_no <= max_semester
                ):
                    queue.append(neighbor)
    return course_registration.objects.filter(id__in=related).exclude(
        id=initial_reg.id
    )


# ===========================================================================
# CSV upload services (V04, V05)
# ===========================================================================

def upload_grades_from_csv(
    *,
    csv_file,
    course_id,
    academic_year,
    semester_type,
    instructor_id=None,
    programme_type=None,
):
    """
    Parse and upsert grades from a CSV file.

    This combines the logic from ``UploadGradesProfAPI`` and the legacy
    ``upload_grades`` / ``upload_grades_prof`` views.

    Returns ``(success_message: str, errors: list[str])``.
    Raises ``ValueError`` for validation failures.
    """
    # File validation
    if not csv_file:
        raise ValueError("No file provided. Please upload a CSV file.")
    if not csv_file.name.lower().endswith(".csv"):
        raise ValueError("Invalid file format. Please upload a CSV file.")
    if csv_file.size > MAX_CSV_FILE_SIZE:
        raise ValueError(
            f"File too large. Maximum size is {MAX_CSV_FILE_SIZE // (1024*1024)} MB."
        )

    # Parse academic year
    working_year, session = parse_academic_year(academic_year, semester_type)

    # Fetch course
    try:
        course = Courses.objects.get(id=course_id)
    except Courses.DoesNotExist:
        raise ValueError("Invalid course ID.")

    # Registration check
    regs = course_registration.objects.filter(
        course_id=course,
        working_year=working_year,
        semester_type=semester_type,
    )
    if not regs.exists():
        raise ValueError(
            "NO STUDENTS REGISTERED IN THIS COURSE FOR THE SELECTED SEMESTER."
        )

    # Programme type filtering
    ug_student_ids = Student.objects.filter(
        programme__in=UG_PROGRAMMES
    ).values_list("id", flat=True)
    pg_student_ids = Student.objects.filter(
        programme__in=PG_PROGRAMMES
    ).values_list("id", flat=True)

    course_has_ug = regs.filter(student_id__in=ug_student_ids).exists()
    course_has_pg = regs.filter(student_id__in=pg_student_ids).exists()

    if programme_type:
        if programme_type.upper() == "UG":
            if not course_has_ug:
                raise ValueError("No UG students registered in this course.")
            regs = regs.filter(student_id__in=ug_student_ids)
        elif programme_type.upper() == "PG":
            if not course_has_pg:
                raise ValueError("No PG students registered in this course.")
            regs = regs.filter(student_id__in=pg_student_ids)
        else:
            raise ValueError("Invalid programme_type. Must be 'UG' or 'PG'.")
    else:
        if course_has_ug and course_has_pg:
            raise ValueError(
                "This course has both UG and PG students. "
                "Please specify programme_type as 'UG' or 'PG'."
            )
        elif course_has_ug:
            programme_type = "UG"
            regs = regs.filter(student_id__in=ug_student_ids)
        elif course_has_pg:
            programme_type = "PG"
            regs = regs.filter(student_id__in=pg_student_ids)

    # Duplicate submission check
    existing_query = Student_grades.objects.filter(
        course_id=course_id,
        academic_year=academic_year,
        semester_type=semester_type,
    )
    if programme_type:
        student_rolls = [reg.student_id_id for reg in regs]
        existing_for_prog = existing_query.filter(roll_no__in=student_rolls)
        if existing_for_prog.exists():
            non_resubmit = existing_for_prog.filter(reSubmit=False)
            if non_resubmit.exists():
                raise ValueError(
                    f"THIS COURSE HAS ALREADY BEEN SUBMITTED FOR "
                    f"{programme_type.upper()} STUDENTS."
                )
    else:
        existing = existing_query.first()
        if existing and not existing.reSubmit:
            raise ValueError("THIS COURSE HAS ALREADY BEEN SUBMITTED.")

    # Instructor ownership check
    if instructor_id:
        if not CourseInstructor.objects.filter(
            course_id_id=course_id,
            instructor_id_id=instructor_id,
            year=working_year,
        ).exists():
            raise PermissionError(
                "Access denied: you are not assigned as instructor for this course."
            )

    # Parse CSV
    decoded = csv_file.read().decode("utf-8").splitlines()
    reader = csv.DictReader(decoded)
    required_cols = {"roll_no", "grade", "remarks"}
    if not required_cols.issubset(reader.fieldnames or []):
        raise ValueError(
            "CSV file must contain columns: roll_no, grade, remarks."
        )

    # Atomic processing
    errors = []
    with transaction.atomic():
        # Reset reSubmit flags
        reset_query = Student_grades.objects.filter(
            course_id_id=course_id,
            academic_year=academic_year,
            semester_type=semester_type,
        )
        if programme_type:
            prog_rolls = [reg.student_id_id for reg in regs]
            reset_query = reset_query.filter(roll_no__in=prog_rolls)
        reset_query.update(reSubmit=False)

        for idx, row in enumerate(reader, start=1):
            roll_no = row.get("roll_no", "").strip()
            grade_val = row.get("grade", "").strip()
            remarks = row.get("remarks", "").strip()
            sem_csv = row.get("semester", "").strip() or None

            # Student exists?
            try:
                stud = Student.objects.get(id_id=roll_no)
            except Student.DoesNotExist:
                errors.append(
                    f"Row {idx}: Student with roll_no {roll_no} does not exist."
                )
                continue

            # Registration check
            student_reg = course_registration.objects.filter(
                student_id=stud,
                course_id=course,
                semester_type=semester_type,
                session=academic_year,
            )
            if not student_reg.exists():
                errors.append(
                    f"Row {idx}: Student {roll_no} not registered for this "
                    f"course/semester."
                )
                continue

            # Programme type check
            if programme_type:
                student_programme = stud.programme
                if programme_type.upper() == "UG" and student_programme not in UG_PROGRAMMES:
                    errors.append(
                        f"Row {idx}: Student {roll_no} is not a UG student "
                        f"(programme: {student_programme})."
                    )
                    continue
                elif programme_type.upper() == "PG" and student_programme not in PG_PROGRAMMES:
                    errors.append(
                        f"Row {idx}: Student {roll_no} is not a PG student "
                        f"(programme: {student_programme})."
                    )
                    continue

            # Valid grade?
            if grade_val not in ALLOWED_GRADES:
                allowed = ", ".join(sorted(ALLOWED_GRADES))
                errors.append(
                    f"Row {idx}: Invalid grade '{grade_val}'. Allowed: {allowed}."
                )
                continue

            # Determine semester & batch
            semester = sem_csv or stud.curr_semester_no
            batch = stud.batch

            # Upsert grade
            try:
                Student_grades.objects.update_or_create(
                    roll_no=roll_no,
                    course_id_id=course_id,
                    year=working_year,
                    batch=batch,
                    academic_year=academic_year,
                    semester_type=semester_type,
                    semester=semester,
                    defaults={
                        "grade": grade_val,
                        "remarks": remarks,
                        "reSubmit": False,
                    },
                )
            except Exception as exc:
                errors.append(
                    f"Row {idx}: Error saving grade for {roll_no}: {str(exc)}"
                )
                continue

        if errors:
            summary = "\n".join(f"- {e}" for e in errors)
            raise Exception(
                f"Upload failed with the following errors:\n{summary}"
            )

    programme_msg = (
        f" for {programme_type.upper()} students" if programme_type else ""
    )
    return f"Grades uploaded successfully{programme_msg}."


# ===========================================================================
# Grade moderation service
# ===========================================================================

def moderate_student_grades(
    student_ids, semester_ids, course_ids, grades, allow_resubmission=False
):
    """
    Moderate (verify) student grades.
    Extracted from ``ModerateStudentGradesAPI`` and legacy ``moderate_student_grades``.
    """
    from applications.examination.models import hidden_grades as HiddenGrades

    if len(student_ids) != len(semester_ids) or len(student_ids) != len(course_ids) or len(student_ids) != len(grades):
        raise ValueError("Invalid grade data provided")

    for student_id, semester_id, course_id, grade_val in zip(
        student_ids, semester_ids, course_ids, grades
    ):
        try:
            grade_of_student = Student_grades.objects.get(
                course_id=course_id, roll_no=student_id, semester=semester_id
            )
            grade_of_student.grade = grade_val
            grade_of_student.verified = True
            if allow_resubmission:
                grade_of_student.reSubmit = True
            grade_of_student.save()
        except Student_grades.DoesNotExist:
            HiddenGrades.objects.create(
                course_id=course_id,
                student_id=student_id,
                semester_id=semester_id,
                grade=grade_val,
            )


# ===========================================================================
# Dean validation service
# ===========================================================================

def validate_dean_csv(csv_file, course_id, academic_year):
    """
    Validate a CSV file from the dean against stored grades.
    Returns a list of mismatch dicts.
    """
    decoded_file = csv_file.read().decode("utf-8").splitlines()
    reader = csv.DictReader(decoded_file)

    required_columns = ["roll_no", "grade", "remarks"]
    if not all(col in (reader.fieldnames or []) for col in required_columns):
        raise ValueError(
            "CSV file must contain the following columns: roll_no, grade, remarks."
        )

    mismatches = []
    for row in reader:
        roll_no = row["roll_no"]
        grade_val = row["grade"]
        remarks = row["remarks"]

        stud = Student.objects.get(id_id=roll_no)
        semester = stud.curr_semester_no
        batch = stud.batch

        student_grade = Student_grades.objects.get(
            roll_no=roll_no,
            course_id_id=course_id,
            year=academic_year,
            batch=batch,
        )

        if student_grade.grade != grade_val:
            mismatches.append(
                {
                    "roll_no": roll_no,
                    "csv_grade": grade_val,
                    "db_grade": student_grade.grade,
                    "remarks": remarks,
                    "batch": batch,
                    "semester": semester,
                    "course_id": course_id,
                }
            )

    return mismatches


# ===========================================================================
# Excel generation service (V06)
# ===========================================================================

def generate_result_excel(semester, branch, batch, semester_type=None, academic_year=None):
    """
    Generate an Excel workbook with student grades for a batch/branch/semester.
    Extracted from ``GenerateResultAPI.post()``.
    Returns an ``openpyxl.Workbook`` instance.
    """
    from applications.academic_procedures.models import Semester as SemesterModel

    branch_info = Discipline.objects.filter(acronym=branch).first()
    if not branch_info:
        raise ValueError("Branch not found")

    batch_obj = Batch.objects.filter(
        year=batch, discipline_id=branch_info.id
    ).first()
    if not batch_obj:
        raise ValueError("Batch not found")

    curriculum_id = batch_obj.curriculum_id
    if not curriculum_id:
        raise ValueError("Curriculum not found")

    semester_info = SemesterModel.objects.filter(
        curriculum_id=curriculum_id, semester_no=semester
    ).first()
    if not semester_info:
        raise ValueError("Semester not found")

    course_slots = CourseSlot.objects.filter(semester_id=semester_info)
    course_ids_from_slots = set(course_slots.values_list("courses", flat=True))

    grade_filter = {"batch": batch, "semester": semester}
    if academic_year:
        grade_filter["academic_year"] = academic_year
    if semester_type:
        grade_filter["semester_type"] = semester_type

    course_ids_from_grades = set(
        Student_grades.objects.filter(**grade_filter).values_list(
            "course_id_id", flat=True
        )
    )
    course_ids = course_ids_from_slots | course_ids_from_grades
    courses = Courses.objects.filter(id__in=course_ids)

    courses_map = {c.id: c.credit for c in courses}
    students = Student.objects.filter(
        batch=batch, specialization=branch
    ).order_by("id")

    wb = Workbook()
    ws = wb.active
    ws.title = "Student Grades"

    ws["A1"] = "S. No"
    ws["B1"] = "Roll No"
    for cell in ("A1", "B1"):
        ws[cell].alignment = Alignment(horizontal="center", vertical="center")
        ws[cell].font = Font(bold=True)

    ws.column_dimensions[get_column_letter(1)].width = 12
    ws.column_dimensions[get_column_letter(2)].width = 18

    col_idx = 3
    for course in courses:
        ws.merge_cells(
            start_row=1, start_column=col_idx, end_row=1, end_column=col_idx + 1
        )
        ws.merge_cells(
            start_row=2, start_column=col_idx, end_row=2, end_column=col_idx + 1
        )
        ws.merge_cells(
            start_row=3, start_column=col_idx, end_row=3, end_column=col_idx + 1
        )

        ws.cell(row=1, column=col_idx).value = course.code
        ws.cell(row=1, column=col_idx).alignment = Alignment(
            horizontal="center", vertical="center"
        )
        ws.cell(row=1, column=col_idx).font = Font(bold=True)
        ws.cell(row=2, column=col_idx).value = course.name
        ws.cell(row=2, column=col_idx).alignment = Alignment(
            horizontal="center", vertical="center"
        )
        ws.cell(row=2, column=col_idx).font = Font(bold=True)
        ws.cell(row=3, column=col_idx).value = course.credit
        ws.cell(row=3, column=col_idx).alignment = Alignment(
            horizontal="center", vertical="center"
        )
        ws.cell(row=3, column=col_idx).font = Font(bold=True)
        ws.cell(row=4, column=col_idx).value = "Grade"
        ws.cell(row=4, column=col_idx + 1).value = "Remarks"
        ws.cell(row=4, column=col_idx).alignment = Alignment(
            horizontal="center", vertical="center"
        )
        ws.cell(row=4, column=col_idx + 1).alignment = Alignment(
            horizontal="center", vertical="center"
        )
        ws.column_dimensions[get_column_letter(col_idx)].width = 25
        ws.column_dimensions[get_column_letter(col_idx + 1)].width = 25
        col_idx += 2

    ws.cell(row=1, column=col_idx).value = "SPI"
    ws.cell(row=1, column=col_idx).alignment = Alignment(
        horizontal="center", vertical="center"
    )
    ws.cell(row=1, column=col_idx).font = Font(bold=True)
    ws.cell(row=1, column=col_idx + 1).value = "CPI"
    ws.cell(row=1, column=col_idx + 1).alignment = Alignment(
        horizontal="center", vertical="center"
    )
    ws.cell(row=1, column=col_idx + 1).font = Font(bold=True)

    row_idx = 5
    for idx, student in enumerate(students, start=1):
        ws.cell(row=row_idx, column=1).value = idx
        ws.cell(row=row_idx, column=2).value = student.id_id
        ws.cell(row=row_idx, column=1).alignment = Alignment(
            horizontal="center", vertical="center"
        )
        ws.cell(row=row_idx, column=2).alignment = Alignment(
            horizontal="center", vertical="center"
        )

        student_grades_qs = Student_grades.objects.filter(
            roll_no=student.id_id,
            course_id_id__in=course_ids,
            semester=semester,
        )

        grades_map = {}
        for g in student_grades_qs:
            grades_map[g.course_id_id] = (
                g.grade,
                g.remarks,
                courses_map.get(g.course_id_id, 0),
            )

        col = 3
        gained_credit = 0
        total_credit = 0
        for course in courses:
            grade_val, remark, credits = grades_map.get(
                course.id, ("N/A", "N/A", 0)
            )
            ws.cell(row=row_idx, column=col).value = grade_val
            ws.cell(row=row_idx, column=col + 1).value = remark
            ws.cell(row=row_idx, column=col).alignment = Alignment(
                horizontal="center", vertical="center"
            )
            ws.cell(row=row_idx, column=col + 1).alignment = Alignment(
                horizontal="center", vertical="center"
            )

            factor = compute_grade_points(grade_val) if grade_val != "N/A" else -1
            if factor > 0:
                gained_credit += factor * credits
                total_credit += credits
            elif factor == 0:
                total_credit += credits

            col += 2

        spi = 10 * (gained_credit / total_credit) if total_credit > 0 else 0
        ws.cell(row=row_idx, column=col).value = spi
        ws.cell(row=row_idx, column=col + 1).value = 0
        ws.cell(row=row_idx, column=col).alignment = Alignment(
            horizontal="center", vertical="center"
        )
        ws.cell(row=row_idx, column=col + 1).alignment = Alignment(
            horizontal="center", vertical="center"
        )
        row_idx += 1

    return wb


# ===========================================================================
# PDF generation services (V07, V08, R06)
# ===========================================================================

def generate_course_grade_pdf(
    course_info, grades_qs, instructor_name, academic_year, semester_type=None, programme_type=None
):
    """
    Generate a faculty course grade sheet PDF.
    Extracted from ``GeneratePDFAPI.post()`` faculty branch (V07).
    Returns an ``HttpResponse`` with PDF content.
    """
    if programme_type:
        student_ids = selectors.get_students_by_programme_type(programme_type)
        grades_qs = grades_qs.filter(roll_no__in=student_ids)

    grades_qs = grades_qs.order_by("roll_no")
    grade_counts = {g: grades_qs.filter(grade=g).count() for g in ALL_GRADE_LETTERS}

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = (
        f'attachment; filename="{course_info.code}_grades.pdf"'
    )

    pdf_title = f"Course Grades - {course_info.code} - {course_info.name}"
    doc = SimpleDocTemplate(
        response,
        pagesize=letter,
        leftMargin=inch,
        rightMargin=inch,
        topMargin=2 * inch,
        bottomMargin=inch,
        title=pdf_title,
        author="PDPM IIITDM Jabalpur",
        subject=f"Course Grade Report - {course_info.code}",
        creator="Fusion Academic System",
    )

    elements = []
    styles = getSampleStyleSheet()

    field_label_style = ParagraphStyle(
        "FieldLabelStyle",
        parent=styles["Normal"],
        fontSize=12,
        textColor=colors.black,
        spaceAfter=5,
    )
    header_style = ParagraphStyle(
        "HeaderStyle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=16,
        textColor=HexColor("#333333"),
        spaceAfter=20,
        alignment=1,
    )

    # Main grades table
    data = [["S.No.", "Roll Number", "Grade"]]
    for i, g in enumerate(grades_qs, 1):
        data.append([i, g.roll_no, g.grade])
    tbl = Table(data, colWidths=[80, 300, 100])
    tbl.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), HexColor("#E0E0E0")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 14),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [HexColor("#F9F9F9"), colors.white]),
                ("TEXTCOLOR", (0, 1), (-1, -1), colors.black),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 1), (-1, -1), 12),
                ("ALIGN", (0, 1), (-1, -1), "CENTER"),
            ]
        )
    )
    elements.append(tbl)
    elements.append(Spacer(1, 20))

    # Grade distribution tables
    grade_data1 = [["O", "A+", "A", "B+", "B", "C+", "C", "D+"]]
    grade_data1.append([grade_counts[g] for g in grade_data1[0]])
    grade_table1 = Table(grade_data1, colWidths=[60] * 8)
    grade_table1.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), HexColor("#E0E0E0")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 12),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ]
        )
    )
    elements.append(grade_table1)
    elements.append(Spacer(1, 10))

    grade_data2 = [["D", "F", "S", "X", "CD"]]
    grade_data2.append([grade_counts[g] for g in grade_data2[0]])
    grade_table2 = Table(grade_data2, colWidths=[80] * 5)
    grade_table2.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), HexColor("#E0E0E0")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 12),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ]
        )
    )
    elements.append(grade_table2)
    elements.append(Spacer(1, 40))

    verified_style = ParagraphStyle(
        "VerifiedStyle",
        parent=styles["Normal"],
        fontSize=13,
        textColor=HexColor("#333333"),
        spaceAfter=20,
    )
    elements.append(
        Paragraph(
            "I have carefully checked and verified the submitted grades. "
            "The grade distribution and submitted grades are correct. "
            "[Please mention any exception below.]",
            verified_style,
        )
    )

    course_details = (
        f"L:{course_info.lecture_hours}, T:{course_info.tutorial_hours}, "
        f"P:{course_info.project_hours}, C:{course_info.credit}"
    )

    def draw_page(canvas_obj, doc_obj):
        canvas_obj.setTitle(f"Grade Sheet - {course_info.code}")
        canvas_obj.saveState()
        width, height = letter

        p_title = Paragraph("Grade Sheet", header_style)
        w, h = p_title.wrap(doc_obj.width, doc_obj.topMargin)
        p_title.drawOn(canvas_obj, doc_obj.leftMargin, height - h)

        hdr_texts = [
            f"<b>Session:</b> {academic_year}",
            f"<b>Course Code:</b> {course_info.code}",
            f"<b>Course Name:</b> {course_info.name} ({course_details})",
            f"<b>Instructor:</b> {instructor_name}",
        ]
        y = height - h - header_style.spaceAfter
        for txt in hdr_texts:
            p = Paragraph(txt, field_label_style)
            w2, h2 = p.wrap(doc_obj.width, doc_obj.topMargin)
            p.drawOn(canvas_obj, doc_obj.leftMargin, y - h2)
            y -= h2 + field_label_style.spaceAfter

        canvas_obj.setFont("Helvetica", 9)
        canvas_obj.drawRightString(
            width - inch, 0.3 * inch, f"Page {doc_obj.page}"
        )
        canvas_obj.setFont("Helvetica", 12)
        canvas_obj.drawString(inch, 0.5 * inch, "Date")
        canvas_obj.drawString(
            width - 4 * inch, 0.5 * inch, "Course Instructor's Signature"
        )
        canvas_obj.restoreState()

    doc.build(elements, onFirstPage=draw_page, onLaterPages=draw_page)
    return response


def generate_student_result_pdf(
    student_info,
    courses,
    spi,
    cpi,
    su,
    tu,
    semester_no,
    semester_type=None,
    semester_label=None,
    is_transcript=False,
):
    """
    Generate a student result / transcript PDF.
    Consolidates ``GeneratePDFAPI.generate_student_result_pdf()`` and
    ``GenerateStudentResultPDFAPI.post()`` (R06).
    Returns an ``HttpResponse`` with PDF content.
    """
    formatted_semester = format_semester_display(
        semester_no, semester_type, semester_label
    )

    buffer = BytesIO()
    doc_type = "Transcript" if is_transcript else "Student Result"
    pdf_title = (
        f"{doc_type} - "
        f"{student_info.get('name', student_info.get('rollNumber', 'Student'))} "
        f"- {formatted_semester}"
    )

    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.5 * inch,
        leftMargin=0.5 * inch,
        topMargin=0.5 * inch,
        bottomMargin=0.5 * inch,
        title=pdf_title,
        author="PDPM IIITDM Jabalpur",
        subject=f"{doc_type} Report - {formatted_semester}",
        creator="Fusion Academic System",
    )

    story = []
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "Title",
        parent=styles["Heading1"],
        fontSize=14,
        spaceAfter=2,
        leading=18,
        alignment=1,
        fontName="Times-Bold",
    )
    subtitle_style = ParagraphStyle(
        "Subtitle",
        parent=styles["Normal"],
        fontSize=11,
        spaceAfter=6,
        alignment=1,
        fontName="Times-Roman",
    )

    # Header with optional logo
    try:
        from django.conf import settings
        import os

        logo_path = os.path.join(settings.MEDIA_ROOT, "logo2.jpg")
        if os.path.exists(logo_path):
            logo = Image(logo_path, width=0.8 * inch, height=0.8 * inch)
            title_para = Paragraph(
                "PDPM Indian Institute of Information Technology,", title_style
            )
            subtitle1_para = Paragraph(
                "Design &amp; Manufacturing, Jabalpur", title_style
            )
            subtitle2_para = Paragraph(
                "(An Institute of National Importance under MoE, Govt. of India)",
                subtitle_style,
            )
            subtitle3_para = Paragraph(
                "<b><u>Semester Grade Report / Marksheet</u></b>",
                subtitle_style,
            )
            header_table_data = [
                [logo, [title_para, subtitle1_para, subtitle2_para, subtitle3_para]]
            ]
            header_table = Table(header_table_data, colWidths=[1 * inch, 6 * inch])
            header_table.setStyle(
                TableStyle(
                    [
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ("ALIGN", (0, 0), (0, 0), "CENTER"),
                        ("ALIGN", (1, 0), (1, 0), "CENTER"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 5),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                        ("TOPPADDING", (0, 0), (-1, -1), 5),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ]
                )
            )
            story.append(header_table)
        else:
            raise FileNotFoundError
    except Exception:
        story.append(
            Paragraph(
                "PDPM Indian Institute of Information Technology,", title_style
            )
        )
        story.append(
            Paragraph("Design &amp; Manufacturing, Jabalpur", title_style)
        )
        story.append(
            Paragraph(
                "(An Institute of National Importance under MoE, Govt. of India)",
                subtitle_style,
            )
        )
        story.append(
            Paragraph(
                "<b><u>Semester Grade Report / Marksheet</u></b>",
                subtitle_style,
            )
        )

    story.append(Spacer(1, 12))

    # Student information table
    cell_style = ParagraphStyle(
        "CellStyle",
        parent=styles["Normal"],
        fontSize=10,
        fontName="Times-Roman",
        wordWrap="CJK",
    )

    student_data = [
        [
            Paragraph("Name of Student:", cell_style),
            Paragraph(student_info.get("name", "N/A"), cell_style),
            Paragraph("Roll No.:", cell_style),
            Paragraph(
                student_info.get(
                    "rollNumber", student_info.get("roll_number", "N/A")
                ),
                cell_style,
            ),
        ],
        [
            Paragraph("Programme:", cell_style),
            Paragraph(student_info.get("programme", "N/A"), cell_style),
            Paragraph("Branch:", cell_style),
            Paragraph(
                student_info.get(
                    "branch", student_info.get("department", "N/A")
                ),
                cell_style,
            ),
        ],
        [
            Paragraph("Semester:", cell_style),
            Paragraph(formatted_semester, cell_style),
            Paragraph("Academic Year:", cell_style),
            Paragraph(
                student_info.get(
                    "academicYear", student_info.get("academic_year", "N/A")
                ),
                cell_style,
            ),
        ],
    ]

    student_table = Table(
        student_data, colWidths=[1.14 * inch, 3.56 * inch, 1.3 * inch, 1.0 * inch]
    )
    student_table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), "Times-Roman"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("GRID", (0, 0), (-1, -1), 1, colors.black),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(student_table)
    story.append(Spacer(1, 12))

    # Courses table
    headers = [
        "S. No.",
        "Course Code",
        "Course Title",
        "Credits",
        "Grade",
        "Grade Points",
    ]
    course_data = [headers]
    for i, course in enumerate(courses, 1):
        course_data.append(
            [
                str(i),
                course.get("coursecode", ""),
                course.get("coursename", ""),
                str(course.get("credits", "")),
                course.get("grade", ""),
                str(course.get("points", "")),
            ]
        )

    course_table = Table(
        course_data,
        colWidths=[0.5 * inch, 1 * inch, 3.2 * inch, 0.7 * inch, 0.6 * inch, 1 * inch],
    )
    course_table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, 0), "Times-Bold"),
                ("FONTNAME", (0, 1), (-1, -1), "Times-Roman"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("GRID", (0, 0), (-1, -1), 1, colors.black),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("ALIGN", (2, 1), (2, -1), "LEFT"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("LEFTPADDING", (0, 0), (-1, -1), 3),
                ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    story.append(course_table)
    story.append(Spacer(1, 15))

    # Summary table
    summary_data = [
        ["Total Credits Registered:", str(tu), "Semester Credits Earned:", str(su)],
        ["SPI:", f"{spi:.1f}", "CPI:", f"{cpi:.1f}"],
    ]
    summary_table = Table(
        summary_data, colWidths=[2.2 * inch, 0.8 * inch, 2.2 * inch, 0.8 * inch]
    )
    summary_table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), "Times-Roman"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(summary_table)
    story.append(Spacer(1, 25))

    # Footer
    footer_style = ParagraphStyle(
        "Footer",
        parent=styles["Normal"],
        fontSize=8,
        alignment=1,
        fontName="Times-Italic",
    )
    current_date = datetime.now().strftime("%d/%m/%Y")
    story.append(
        Paragraph(
            f"This is a computer-generated document. Generated on {current_date}",
            footer_style,
        )
    )

    doc.build(story)
    pdf_data = buffer.getvalue()
    buffer.close()

    response = HttpResponse(pdf_data, content_type="application/pdf")
    semester_suffix = (
        formatted_semester.replace(" ", "_").replace(":", "").lower()
    )
    prefix = "transcript_" if is_transcript else "result_"
    filename = (
        f"{prefix}"
        f"{student_info.get('rollNumber', student_info.get('roll_number', 'student'))}"
        f"_{semester_suffix}.pdf"
    )
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    response["Content-Length"] = len(pdf_data)
    return response


# ===========================================================================
# Grade summary (V39 — ORM-based replacement for raw SQL)
# ===========================================================================

def get_grade_summary(academic_year, semester_type):
    """
    Return grade distribution per course for the given year/semester.

    This replaces the raw SQL query in ``GradeSummaryAPI`` (V39) with
    Django ORM aggregation.
    """
    from django.db.models import Count, Q as DjangoQ, Value, CharField
    from django.db.models.functions import Concat, Trim

    grades_qs = Student_grades.objects.filter(
        academic_year=academic_year,
        semester_type=semester_type,
    ).exclude(grade__isnull=True).exclude(grade="")

    course_ids = grades_qs.values_list("course_id_id", flat=True).distinct()
    courses = Courses.objects.filter(id__in=course_ids).order_by("code")

    # Bulk-fetch instructor names
    working_year, _ = parse_academic_year(academic_year, semester_type)
    instructor_map = selectors.get_instructor_map(course_ids, working_year, semester_type)
    instructor_ids = [inst.instructor_id_id for inst in instructor_map.values()]
    user_map = selectors.get_user_fullname_map(instructor_ids)

    results = []
    for sno, course in enumerate(courses, 1):
        course_grades = grades_qs.filter(course_id_id=course.id)

        grade_counts = {}
        for g in ALL_GRADE_LETTERS:
            grade_counts[f"grade_{g.lower().replace('+', '_plus')}"] = (
                course_grades.filter(grade=g).count()
            )

        inst = instructor_map.get(course.id)
        instructor_name = (
            user_map.get(inst.instructor_id_id, inst.instructor_id_id)
            if inst
            else "Not Assigned"
        )

        row = {
            "sno": sno,
            "course_code": course.code,
            "course_name": course.name,
            "course_instructor": instructor_name,
            "grade_o": course_grades.filter(grade="O").count(),
            "grade_a_plus": course_grades.filter(grade="A+").count(),
            "grade_a": course_grades.filter(grade="A").count(),
            "grade_b_plus": course_grades.filter(grade="B+").count(),
            "grade_b": course_grades.filter(grade="B").count(),
            "grade_c_plus": course_grades.filter(grade="C+").count(),
            "grade_c": course_grades.filter(grade="C").count(),
            "grade_d_plus": course_grades.filter(grade="D+").count(),
            "grade_d": course_grades.filter(grade="D").count(),
            "grade_f": course_grades.filter(grade="F").count(),
            "grade_cd": course_grades.filter(grade="CD").count(),
            "grade_s": course_grades.filter(grade="S").count(),
            "grade_x": course_grades.filter(grade="X").count(),
            "total_students": course_grades.count(),
        }
        results.append(row)

    return results
