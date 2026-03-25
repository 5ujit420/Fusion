"""
Examination module selectors — all database read queries.

Each function returns a queryset or scalar value.
Fixes audit violations: V02, R09, R10, R11.
"""

from django.db.models import IntegerField, Case, When
from django.db.models.functions import Cast
from django.contrib.auth import get_user_model

from applications.online_cms.models import Student_grades
from applications.academic_procedures.models import course_registration
from applications.programme_curriculum.models import (
    Course as Courses,
    CourseInstructor,
    Batch,
)
from applications.academic_information.models import Student
from applications.examination.models import authentication, ResultAnnouncement

from .constants import UG_PROGRAMMES, PG_PROGRAMMES


User = get_user_model()


# ---------------------------------------------------------------------------
# Student look-ups
# ---------------------------------------------------------------------------

def get_student_by_roll(roll_no):
    """Return a Student instance or raise Student.DoesNotExist."""
    return Student.objects.get(id_id=roll_no)


def get_students_by_programme_type(programme_type):
    """
    Return a queryset of Student IDs filtered by programme type.
    Consolidates the duplicated 'UG' / 'PG' → programme list logic (R09).
    """
    if programme_type.upper() == "UG":
        programme_list = UG_PROGRAMMES
    elif programme_type.upper() == "PG":
        programme_list = PG_PROGRAMMES
    else:
        return Student.objects.none().values_list("id", flat=True)
    return Student.objects.filter(programme__in=programme_list).values_list(
        "id", flat=True
    )


def get_programme_list(programme_type):
    """Return the list of programme strings for a given type."""
    if programme_type.upper() == "UG":
        return UG_PROGRAMMES
    elif programme_type.upper() == "PG":
        return PG_PROGRAMMES
    return []


# ---------------------------------------------------------------------------
# Grade queries
# ---------------------------------------------------------------------------

def get_student_grades_for_semester(roll_no, semester, semester_type):
    """Grades for a single student in a specific semester, with course FK."""
    return (
        Student_grades.objects
        .filter(
            roll_no=roll_no,
            semester=semester,
            semester_type=semester_type,
        )
        .select_related("course_id")
    )


def get_grades_for_course(course_id, academic_year, semester_type):
    """All student grades for a given course/year/semester."""
    return Student_grades.objects.filter(
        course_id_id=course_id,
        academic_year=academic_year,
        semester_type=semester_type,
    )


def get_unverified_courses(academic_year=None, semester_type=None):
    """
    Return Courses queryset whose grades are NOT yet verified.
    If academic_year/semester_type provided, filter on them.
    """
    qs = Student_grades.objects.filter(verified=False)
    if academic_year:
        qs = qs.filter(academic_year=academic_year)
    if semester_type:
        qs = qs.filter(semester_type=semester_type)

    course_ids = (
        qs.values("course_id")
        .distinct()
        .annotate(course_id_int=Cast("course_id", IntegerField()))
        .values_list("course_id_int", flat=True)
    )
    return Courses.objects.filter(id__in=course_ids)


def get_verified_courses():
    """
    Return Courses queryset whose grades have been verified. (R11)
    """
    course_ids = (
        Student_grades.objects.filter(verified=True)
        .values("course_id")
        .distinct()
        .annotate(course_id_int=Cast("course_id", IntegerField()))
        .values_list("course_id_int", flat=True)
    )
    return Courses.objects.filter(id__in=course_ids)


def get_submitted_course_ids(academic_year, semester_type):
    """Course IDs that have at least one submitted grade record."""
    return set(
        Student_grades.objects.filter(
            academic_year=academic_year,
            semester_type=semester_type,
        )
        .values_list("course_id", flat=True)
        .distinct()
    )


def get_verified_course_ids(academic_year, semester_type):
    """Course IDs where all grades are verified."""
    return set(
        Student_grades.objects.filter(
            academic_year=academic_year,
            semester_type=semester_type,
            verified=True,
        )
        .values_list("course_id", flat=True)
        .distinct()
    )


# ---------------------------------------------------------------------------
# Registration queries
# ---------------------------------------------------------------------------

def get_course_registrations(course_id, session=None, semester_type=None,
                             working_year=None):
    """Flexible course registration filter used across endpoints."""
    qs = course_registration.objects.filter(course_id_id=course_id)
    if session:
        qs = qs.filter(session=session)
    if semester_type:
        qs = qs.filter(semester_type=semester_type)
    if working_year:
        qs = qs.filter(working_year=working_year)
    return qs


def get_unique_academic_years():
    """All distinct academic_year values from Student_grades."""
    return (
        Student_grades.objects
        .values_list("academic_year", flat=True)
        .distinct()
        .order_by("academic_year")
    )


def get_unique_registration_years():
    """All distinct working_year values from course_registration."""
    return course_registration.objects.values("working_year").distinct()


# ---------------------------------------------------------------------------
# Instructor queries
# ---------------------------------------------------------------------------

def get_instructor_courses(instructor_id, working_year, semester_type):
    """Course IDs taught by an instructor in a given year & semester."""
    return (
        CourseInstructor.objects.filter(
            instructor_id_id=instructor_id,
            year=working_year,
            semester_type=semester_type,
        )
        .values("course_id_id")
        .distinct()
        .annotate(course_id_int=Cast("course_id_id", IntegerField()))
    )


def get_instructor_map(course_ids, working_year, semester_type):
    """
    Return {course_id: CourseInstructor} for a bulk set of courses.
    Avoids N+1 queries (V32).
    """
    instructors = CourseInstructor.objects.filter(
        course_id__in=course_ids,
        year=working_year,
        semester_type=semester_type,
    ).select_related()
    return {inst.course_id_id: inst for inst in instructors}


def get_user_fullname_map(usernames):
    """Return {username: 'First Last'} mapping for a list of usernames."""
    users = User.objects.filter(username__in=usernames)
    return {
        u.username: f"{u.first_name} {u.last_name}".strip()
        for u in users
    }


# ---------------------------------------------------------------------------
# Authentication queries
# ---------------------------------------------------------------------------

def get_authentication_records(course_ids, working_year):
    """Return {course_id: authentication_obj} for bulk lookup."""
    records = authentication.objects.filter(
        course_id__in=course_ids,
        course_year=working_year,
    )
    return {rec.course_id_id: rec for rec in records}


# ---------------------------------------------------------------------------
# Batch / Announcement queries
# ---------------------------------------------------------------------------

def get_running_batches():
    """Return running Batch objects."""
    return Batch.objects.filter(running_batch=True)


def get_result_announcement(batch_id, semester):
    """Return a single ResultAnnouncement or None."""
    return ResultAnnouncement.objects.filter(
        batch=batch_id,
        semester=semester,
    ).first()


def get_all_announcements():
    """All announcements ordered by most recent first."""
    return ResultAnnouncement.objects.all().order_by("-created_at")
