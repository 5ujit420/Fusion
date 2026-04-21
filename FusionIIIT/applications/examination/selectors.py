from collections import defaultdict

from django.db import connection
from django.db.models import IntegerField
from django.db.models.functions import Cast

from applications.academic_information.models import Course, Student
from applications.academic_procedures.models import course_registration
from applications.department.models import Announcements, SpecialRequest
from applications.online_cms.models import Student_grades
from applications.programme_curriculum.models import Batch, Course as ProgrammeCourse

from .models import ResultAnnouncement, authentication, hidden_grades


def get_course_registration_courses():
    unique_course_ids = (
        course_registration.objects.values("course_id")
        .distinct()
        .annotate(course_id_int=Cast("course_id", IntegerField()))
    )
    return Course.objects.filter(
        id__in=unique_course_ids.values_list("course_id_int", flat=True)
    )


def get_hidden_grade_courses():
    unique_course_ids = (
        hidden_grades.objects.values("course_id")
        .distinct()
        .annotate(course_id_int=Cast("course_id", IntegerField()))
    )
    return Course.objects.filter(
        id__in=unique_course_ids.values_list("course_id_int", flat=True)
    )


def get_student_grade_courses(course_filter=None):
    grade_queryset = Student_grades.objects.all()
    if course_filter is not None:
        grade_queryset = grade_queryset.filter(**course_filter)
    unique_course_ids = (
        grade_queryset.values("course_id")
        .distinct()
        .annotate(course_id_int=Cast("course_id", IntegerField()))
    )
    return ProgrammeCourse.objects.filter(
        id__in=unique_course_ids.values_list("course_id_int", flat=True)
    )


def get_distinct_student_grade_years():
    return Student_grades.objects.values("year").distinct()


def get_distinct_registration_years():
    return course_registration.objects.values("working_year").distinct()


def get_browse_announcements_context():
    return {
        "cse": Announcements.objects.filter(department="CSE"),
        "ece": Announcements.objects.filter(department="ECE"),
        "me": Announcements.objects.filter(department="ME"),
        "sm": Announcements.objects.filter(department="SM"),
        "all": Announcements.objects.filter(department="ALL"),
    }


def get_requests_for_receiver(username):
    return SpecialRequest.objects.filter(request_receiver=username)


def get_hidden_grade_registrations(course_id, semester_id):
    return hidden_grades.objects.filter(course_id=course_id, semester_id=semester_id)


def get_course_registrations(course_id, semester_id):
    return course_registration.objects.filter(
        course_id__id=course_id,
        semester_id=semester_id,
    )


def get_authentication_registrations(course_instance, course_year):
    return authentication.objects.filter(course_id=course_instance, course_year=course_year)


def get_or_create_authentication(course_instance, course_year):
    return authentication.objects.get_or_create(
        course_id=course_instance,
        course_year=course_year,
    )


def get_transcript_grade_data(student_id, semester):
    courses_registered = Student_grades.objects.filter(
        roll_no=student_id,
        semester=semester,
    ).select_related("course_id")
    total_course_registered = Student_grades.objects.filter(
        roll_no=student_id,
        semester__lte=semester,
    ).select_related("course_id")
    all_grades = Student_grades.objects.filter(roll_no=student_id).select_related("course_id")
    return courses_registered, total_course_registered, all_grades


def get_transcript_data(student_id, semester):
    return get_transcript_grade_data(student_id, semester)


def get_students_for_transcript_form(programme=None, batch=None, specialization=None):
    students = Student.objects.all()
    if programme is not None:
        students = students.filter(programme=programme)
    if batch is not None:
        students = students.filter(batch=batch)
    if specialization:
        students = students.filter(specialization=specialization)
    return students


def get_transcript_form_options():
    programmes = Student.objects.values_list("programme", flat=True).distinct()
    specializations = (
        Student.objects.exclude(specialization__isnull=True)
        .values_list("specialization", flat=True)
        .distinct()
    )
    batches = Student.objects.values_list("batch", flat=True).distinct()
    return programmes, batches, specializations


def get_course_students_for_result(batch, branch):
    return Student.objects.filter(batch=batch, specialization=branch).order_by("id")


def get_result_generation_students(batch_id, branch=None):
    students = Student.objects.filter(batch_id=batch_id)
    if branch:
        students = students.filter(specialization=branch)
    return students.order_by("id").select_related("id__user", "id__department", "batch_id__discipline")


def get_result_generation_grades(student_rolls, course_ids, semester, semester_type=None):
    filters = {
        "roll_no__in": student_rolls,
        "course_id_id__in": course_ids,
        "semester": semester,
    }
    if semester_type is not None:
        filters["semester_type"] = semester_type
    return Student_grades.objects.filter(**filters).select_related("course_id")


def get_student_grades_for_course(course_id, academic_year, semester_type):
    return Student_grades.objects.filter(
        course_id=course_id,
        academic_year=academic_year,
        semester_type=semester_type,
    )


def get_student_grade_rows(roll_no, semester, semester_type=None):
    filters = {
        "roll_no": roll_no,
        "semester": semester,
    }
    if semester_type is not None:
        filters["semester_type"] = semester_type
    return Student_grades.objects.filter(**filters).select_related("course_id")


def get_student_grade_map_for_result(student_rolls, course_ids, semester, semester_type=None):
    grade_map = defaultdict(dict)
    for grade in get_result_generation_grades(student_rolls, course_ids, semester, semester_type):
        grade_map[grade.roll_no][grade.course_id_id] = grade
    return grade_map


def get_result_announcement_list():
    return ResultAnnouncement.objects.all().order_by("-created_at").select_related("batch__discipline")


def get_running_batches():
    return Batch.objects.filter(running_batch=True).select_related("discipline")


def get_grade_summary_rows(academic_year, semester_type):
    query = """
        SELECT
            ROW_NUMBER() OVER (ORDER BY pc.code) as sno,
            pc.code as course_code,
            pc.name as course_name,
            STRING_AGG(DISTINCT TRIM(CONCAT(u.first_name, ' ', u.last_name)), ', ') as course_instructor,
            COUNT(CASE WHEN sg.grade = 'O' THEN 1 END) as grade_o,
            COUNT(CASE WHEN sg.grade = 'A+' THEN 1 END) as grade_a_plus,
            COUNT(CASE WHEN sg.grade = 'A' THEN 1 END) as grade_a,
            COUNT(CASE WHEN sg.grade = 'B+' THEN 1 END) as grade_b_plus,
            COUNT(CASE WHEN sg.grade = 'B' THEN 1 END) as grade_b,
            COUNT(CASE WHEN sg.grade = 'C+' THEN 1 END) as grade_c_plus,
            COUNT(CASE WHEN sg.grade = 'C' THEN 1 END) as grade_c,
            COUNT(CASE WHEN sg.grade = 'D+' THEN 1 END) as grade_d_plus,
            COUNT(CASE WHEN sg.grade = 'D' THEN 1 END) as grade_d,
            COUNT(CASE WHEN sg.grade = 'F' THEN 1 END) as grade_f,
            COUNT(CASE WHEN sg.grade = 'CD' THEN 1 END) as grade_cd,
            COUNT(CASE WHEN sg.grade = 'S' THEN 1 END) as grade_s,
            COUNT(CASE WHEN sg.grade = 'X' THEN 1 END) as grade_x,
            COUNT(sg.id) as total_students
        FROM
            online_cms_student_grades sg
            INNER JOIN programme_curriculum_course pc ON sg.course_id_id = pc.id
            LEFT JOIN programme_curriculum_courseinstructor ci ON (
                ci.course_id_id = pc.id
                AND ci.year = sg.year
            )
            LEFT JOIN auth_user u ON ci.instructor_id_id = u.username
        WHERE
            sg.academic_year = %s
            AND sg.semester_type = %s
            AND sg.grade IS NOT NULL
            AND sg.grade <> ''
        GROUP BY
            pc.code, pc.name
        HAVING
            COUNT(sg.id) > 0
        ORDER BY
            pc.code
    """
    with connection.cursor() as cursor:
        cursor.execute(query, [academic_year, semester_type])
        columns = [col[0] for col in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]
