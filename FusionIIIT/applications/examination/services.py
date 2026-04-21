import csv
from collections import OrderedDict
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from io import BytesIO

from django.core.exceptions import ValidationError
from django.db.models import Case, IntegerField, When
from django.http import HttpResponse

from applications.academic_information.models import Student
from applications.academic_procedures.models import course_registration
from applications.online_cms.models import Student_grades
from applications.programme_curriculum.models import Course as Courses

from .models import hidden_grades


FACULTY_ROLES = ("Associate Professor", "Professor", "Assistant Professor")
ACADEMIC_ADMIN_ROLES = ("acadadmin", "Dean Academic")
UG_PROGRAMMES = ("B.Tech", "B.Des")
PG_PROGRAMMES = ("M.Tech", "M.Des", "PhD")
ROLE_REDIRECTS = {
    "Associate Professor": "/examination/submitGradesProf/",
    "Professor": "/examination/submitGradesProf/",
    "Assistant Professor": "/examination/submitGradesProf/",
    "acadadmin": "/examination/updateGrades/",
    "Dean Academic": "/examination/verifyGradesDean/",
}

GRADE_CONVERSION = {
    "O": Decimal("1.0"),
    "A+": Decimal("1.0"),
    "A": Decimal("0.9"),
    "B+": Decimal("0.8"),
    "B": Decimal("0.7"),
    "C+": Decimal("0.6"),
    "C": Decimal("0.5"),
    "D+": Decimal("0.4"),
    "D": Decimal("0.3"),
    "F": Decimal("0.2"),
    "S": Decimal("0.0"),
    **{f"A{i}": Decimal(str(0.9 + i * 0.01)) for i in range(1, 11)},
    **{f"B{i}": Decimal(str(0.8 + i * 0.01)) for i in range(1, 11)},
    **{f"{x/10:.1f}": Decimal(f"{x/100:.2f}") for x in range(20, 101)},
}
ALLOWED_GRADES = {"O", "A+", "A", "B+", "B", "C+", "C", "D+", "D", "F", "CD", "S", "X"}
PBI_AND_BTP_ALLOWED_GRADES = {f"{x:.1f}" for x in [i / 10 for i in range(20, 101)]}
GRADE_CREDIT_WEIGHTS = {
    "O": Decimal("1.0"),
    "A+": Decimal("1.0"),
    "A": Decimal("0.9"),
    "B+": Decimal("0.8"),
    "B": Decimal("0.7"),
    "C+": Decimal("0.6"),
    "C": Decimal("0.5"),
    "D+": Decimal("0.4"),
    "D": Decimal("0.3"),
    "F": Decimal("0.2"),
}


@dataclass(frozen=True)
class BatchGradeRow:
    student_id: str
    semester_id: str
    course_id: str
    grade: str


@dataclass(frozen=True)
class ModeratedGradeRow:
    student_id: str
    semester_id: str
    course_id: str
    grade: str
    remark: str = ""


def get_role_redirect(role):
    return ROLE_REDIRECTS.get(str(role), "/dashboard/")


def build_parallel_rows(student_ids, semester_ids, course_ids, grades):
    return [
        BatchGradeRow(student_id, semester_id, course_id, grade)
        for student_id, semester_id, course_id, grade in zip(
            student_ids,
            semester_ids,
            course_ids,
            grades,
        )
    ]


def build_moderated_rows(student_ids, semester_ids, course_ids, grades, remarks=None):
    remarks = remarks or []
    return [
        ModeratedGradeRow(student_id, semester_id, course_id, grade, remark)
        for student_id, semester_id, course_id, grade, remark in zip(
            student_ids,
            semester_ids,
            course_ids,
            grades,
            remarks,
        )
    ]


def upsert_hidden_grade_rows(rows):
    for row in rows:
        hidden_grade, _ = hidden_grades.objects.get_or_create(
            course_id=row.course_id,
            student_id=row.student_id,
            semester_id=row.semester_id,
            defaults={"grade": row.grade},
        )
        if hidden_grade.grade != row.grade:
            hidden_grade.grade = row.grade
            hidden_grade.save()
    return rows


def moderate_student_grade_rows(rows, allow_resubmission="NO"):
    for row in rows:
        try:
            grade_of_student = Student_grades.objects.get(
                course_id=row.course_id,
                roll_no=row.student_id,
                semester=row.semester_id,
            )
            grade_of_student.grade = row.grade
            grade_of_student.remarks = row.remark
            grade_of_student.verified = True
            if str(allow_resubmission).upper() == "YES":
                grade_of_student.reSubmit = True
            grade_of_student.save()
        except Student_grades.DoesNotExist:
            hidden_grades.objects.create(
                course_id=row.course_id,
                student_id=row.student_id,
                semester_id=row.semester_id,
                grade=row.grade,
            )
    return rows


def create_csv_http_response(filename, headers, rows):
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    writer = csv.writer(response)
    writer.writerow(headers)
    for row in rows:
        writer.writerow(row)
    return response


def rows_to_grade_csv_response(rows, filename="grades.csv"):
    csv_rows = [
        [row.student_id, row.semester_id, row.course_id, row.grade]
        for row in rows
    ]
    return create_csv_http_response(
        filename,
        ["Student ID", "Semester ID", "Course ID", "Grade"],
        csv_rows,
    )


def format_semester_display(semester_no, semester_type=None, semester_label=None):
    if semester_label and "summer" in semester_label.lower():
        return semester_label
    if semester_type and "summer" in semester_type.lower():
        if semester_no == 2:
            return "Summer 1"
        if semester_no == 4:
            return "Summer 2"
        if semester_no == 6:
            return "Summer 3"
        if semester_no == 8:
            return "Summer 4"
        return f"Summer {semester_no // 2}"
    return str(semester_no)


def round_from_last_decimal(number, decimal_places=1):
    quantizer = "0." + ("0" * (decimal_places - 1)) + "1"
    return Decimal(str(number)).quantize(Decimal(quantizer), rounding=ROUND_HALF_UP)


def parse_academic_year(academic_year, semester_type):
    first_year, second_year = academic_year.split("-")
    if semester_type == "Odd Semester":
        working_year = int(first_year)
    else:
        working_year = int("20" + second_year)
    return working_year, academic_year


def is_valid_grade(grade, course_code):
    if not grade:
        return False
    course_code = (course_code or "").upper()
    if "PBI" in course_code or "BTP" in course_code:
        return grade in PBI_AND_BTP_ALLOWED_GRADES
    return grade in ALLOWED_GRADES


def make_label(no, sem_type):
    if no % 2 == 1:
        return f"Semester {no}"
    if sem_type == "Summer Semester":
        return f"Summer {no // 2}"
    return f"Semester {no}"


def gather_related_registrations(initial_reg, max_semester):
    chain = [initial_reg]
    current = initial_reg
    while current.registration_type in ("Backlog", "Improvement", "Replacement"):
        previous = (
            course_registration.objects.filter(
                student_id=current.student_id,
                course_id=current.course_id,
                semester_id__semester_no__lt=current.semester_id.semester_no,
                semester_id__semester_no__lte=max_semester,
            )
            .exclude(pk__in=[reg.pk for reg in chain])
            .order_by("-semester_id__semester_no")
            .first()
        )
        if previous is None:
            break
        chain.append(previous)
        current = previous
    return chain


def calculate_spi_for_student(student, selected_semester, semester_type):
    semester_unit = Decimal("0")
    grades = (
        Student_grades.objects.filter(
            roll_no=student.id_id,
            semester=selected_semester,
            semester_type=semester_type,
        )
        .select_related("course_id")
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
    for grade in grades:
        credit = Decimal(str(grade.course_id.credit))
        factor = GRADE_CONVERSION.get((grade.grade or "").strip(), Decimal("-1"))
        if factor >= 0:
            if factor != 0:
                total_points += factor * credit
                total_credits += credit
            semester_unit += credit
    return (
        round_from_last_decimal(Decimal("10") * (total_points / total_credits))
        if total_credits
        else 0,
        semester_unit,
        total_points * 10,
    )


def calculate_cpi_for_student(student, selected_semester, semester_type):
    total_unit = Decimal("0")
    if selected_semester % 2 == 0 and semester_type == "Summer Semester":
        grades = (
            Student_grades.objects.filter(
                roll_no=student.id_id,
                semester__lte=selected_semester,
            )
            .select_related("course_id")
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
    else:
        registrations = (
            course_registration.objects.filter(
                student_id=student,
                semester_id__semester_no__lte=selected_semester,
            )
            .select_related("course_id", "semester_id")
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
        grades = Student_grades.objects.filter(
            roll_no=student.id_id,
        ).select_related("course_id").exclude(
            semester_type="Summer Semester",
            semester=selected_semester,
        )
        registration_map = OrderedDict()
        for registration in registrations.exclude(
            semester_type="Summer Semester",
            semester_id__semester_no=selected_semester,
        ):
            key = (
                registration.course_id.code.strip(),
                registration.semester_id.semester_no,
                registration.semester_type,
            )
            registration_map[key] = registration
        grades = [
            grade
            for grade in grades
            if (
                grade.course_id.code.strip(),
                grade.semester,
                grade.semester_type,
            )
            in registration_map
        ]
    total_points = Decimal("0")
    total_credits = Decimal("0")
    for grade in grades:
        credit = Decimal(str(grade.course_id.credit))
        factor = GRADE_CONVERSION.get((grade.grade or "").strip(), Decimal("-1"))
        if factor >= 0:
            if factor != 0:
                total_points += factor * credit
                total_credits += credit
            total_unit += credit
    return (
        round_from_last_decimal(Decimal("10") * (total_points / total_credits))
        if total_credits
        else 0,
        total_unit,
        total_points * 10,
    )


def apply_credit_weight(gained_credit, total_credit, grade, credits):
    weight = GRADE_CREDIT_WEIGHTS.get(grade)
    if weight is None:
        return gained_credit, total_credit
    return gained_credit + (weight * Decimal(str(credits))), total_credit + Decimal(str(credits))


def build_semester_rows(student_grades):
    return {
        grade.course_id_id: (
            grade.grade,
            grade.remarks,
            getattr(grade.course_id, "credit", 0),
        )
        for grade in student_grades
    }


def workbook_bytes(workbook):
    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def parse_csv_rows(csv_file, required_columns):
    decoded_rows = csv_file.read().decode("utf-8").splitlines()
    reader = csv.DictReader(decoded_rows)
    if not set(required_columns).issubset(reader.fieldnames or []):
        required = ", ".join(required_columns)
        raise ValidationError(
            f"CSV file must contain the following columns: {required}."
        )
    return list(reader)


def handle_legacy_grade_upload(
    csv_file,
    course_id,
    academic_year,
    success_redirect_url,
):
    if not csv_file.name.endswith(".csv"):
        raise ValidationError("Invalid file format. Please upload a CSV file.")
    if academic_year == "None" or not str(academic_year).isdigit():
        raise ValidationError("Academic year must be a valid number.")
    if not course_id or not academic_year:
        raise ValidationError("Course ID and Academic Year are required.")

    course = Courses.objects.get(id=course_id)
    existing_grades = Student_grades.objects.filter(
        course_id=course.id,
        year=academic_year,
    )
    registrations = course_registration.objects.filter(
        course_id_id=course_id,
        working_year=academic_year,
    )

    if not registrations.exists():
        raise ValidationError("NO STUDENTS REGISTERED IN THIS COURSE THIS SEMESTER")
    if existing_grades.exists() and not existing_grades.first().reSubmit:
        raise ValidationError("THIS Course was Already Submitted")

    rows = parse_csv_rows(csv_file, ["roll_no", "grade", "remarks"])
    for row in rows:
        roll_no = row["roll_no"]
        grade = row["grade"]
        remarks = row["remarks"]
        semester = row["semester"] if row.get("semester") else None
        student = Student.objects.get(id_id=roll_no)
        Student_grades.objects.update_or_create(
            roll_no=roll_no,
            course_id_id=course_id,
            year=academic_year,
            semester=semester or student.curr_semester_no,
            batch=student.batch,
            defaults={
                "grade": grade,
                "remarks": remarks,
                "reSubmit": False,
            },
        )
    return {
        "message": "Grades uploaded successfully.",
        "redirect_url": success_redirect_url,
    }


def build_student_result_payload(student, grades_info, semester_no, semester_type):
    academic_year = grades_info.first().academic_year if grades_info.exists() else None
    spi, su, _ = calculate_spi_for_student(student, semester_no, semester_type)
    cpi, tu, _ = calculate_cpi_for_student(student, semester_no, semester_type)
    student_info = {
        "name": f"{student.id.user.first_name} {student.id.user.last_name}".strip(),
        "rollNumber": student.id.user.username,
        "roll_number": student.id.user.username,
        "programme": student.programme,
        "batch": str(student.batch_id) if student.batch_id else str(student.batch),
        "branch": student.id.department.name if student.id.department else "",
        "department": student.id.department.name if student.id.department else "",
        "semester": student.curr_semester_no,
        "academicYear": academic_year or "",
        "academic_year": academic_year or "",
    }
    courses = [
        {
            "coursecode": grade.course_id.code,
            "courseid": grade.course_id.id,
            "coursename": grade.course_id.name,
            "credits": grade.course_id.credit,
            "grade": grade.grade,
            "points": Decimal(str(GRADE_CONVERSION.get(grade.grade, 0) * 10)).quantize(
                Decimal("0.1"),
                rounding=ROUND_HALF_UP,
            ),
        }
        for grade in grades_info
    ]
    return student_info, courses, spi, cpi, su, tu
