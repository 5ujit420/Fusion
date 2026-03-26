"""
selectors.py — All database queries for the examination module.

Every function returns either a QuerySet, a model instance, or a plain value
derived directly from a query.  No business logic lives here.
"""

from collections import OrderedDict

from django.contrib.auth import get_user_model
from django.db.models import Q, Case, When, IntegerField
from django.db.models.functions import Cast

from applications.academic_information.models import Student
from applications.academic_procedures.models import (
    course_registration,
    course_replacement,
)
from applications.online_cms.models import Student_grades
from applications.programme_curriculum.models import (
    Course as Courses,
    CourseInstructor,
    Batch,
)

from .models import (
    hidden_grades,
    authentication,
    ResultAnnouncement,
    UG_PROGRAMMES,
    PG_PROGRAMMES,
)

User = get_user_model()

# ---------------------------------------------------------------------------
# Programme-type helpers
# ---------------------------------------------------------------------------

def get_programme_list(programme_type):
    """Return the list of programme names for 'UG' or 'PG', or None."""
    if not programme_type:
        return None
    key = programme_type.upper()
    if key == "UG":
        return list(UG_PROGRAMMES)
    if key == "PG":
        return list(PG_PROGRAMMES)
    return None


def get_student_ids_for_programme(programme_type):
    """Return a flat ValuesQuerySet of student PKs matching the programme type."""
    programme_list = get_programme_list(programme_type)
    if not programme_list:
        return Student.objects.none().values_list("id", flat=True)
    return Student.objects.filter(programme__in=programme_list).values_list(
        "id", flat=True
    )


# ---------------------------------------------------------------------------
# Student lookups
# ---------------------------------------------------------------------------

def get_student_by_roll(roll_no):
    """Return a Student instance or raise Student.DoesNotExist."""
    return Student.objects.get(id_id=roll_no)


def get_user_by_username(username):
    """Return a User instance or raise User.DoesNotExist."""
    return User.objects.get(username=username)


def get_students_by_batch(batch_id, specialization=None):
    qs = Student.objects.filter(batch_id=batch_id)
    if specialization:
        qs = qs.filter(specialization=specialization)
    return qs.order_by("id")


def get_student_programmes():
    return Student.objects.values_list("programme", flat=True).distinct()


def get_student_specializations():
    return (
        Student.objects.exclude(specialization__isnull=True)
        .exclude(specialization__exact="")
        .values_list("specialization", flat=True)
        .distinct()
    )


# ---------------------------------------------------------------------------
# Course / Registration lookups
# ---------------------------------------------------------------------------

def get_course_by_id(course_id):
    """Return a Courses instance or raise Courses.DoesNotExist."""
    return Courses.objects.get(id=course_id)


def get_courses_by_ids(course_ids):
    return Courses.objects.filter(id__in=course_ids)


def get_course_registrations(course_id, session, semester_type, programme_type=None):
    """Return course_registration QS filtered by course/session/semester_type."""
    qs = course_registration.objects.filter(
        course_id_id=course_id,
        session=session,
        semester_type=semester_type,
    )
    if programme_type:
        student_ids = get_student_ids_for_programme(programme_type)
        qs = qs.filter(student_id__in=student_ids)
    return qs


def get_course_registrations_by_working_year(course, working_year, semester_type):
    return course_registration.objects.filter(
        course_id=course,
        working_year=working_year,
        semester_type=semester_type,
    )


def get_courses_for_session(session, semester_type):
    """Return distinct course IDs registered for a given session/semester_type."""
    unique_ids = (
        course_registration.objects.filter(session=session, semester_type=semester_type)
        .values("course_id")
        .distinct()
    )
    return Courses.objects.filter(
        id__in=unique_ids.values_list("course_id", flat=True)
    ).order_by("code")


def get_available_sessions():
    return course_registration.objects.values("session").distinct()


def get_unique_courses_from_registrations():
    unique_ids = (
        course_registration.objects.values("course_id")
        .distinct()
        .annotate(course_id_int=Cast("course_id", IntegerField()))
    )
    from applications.academic_information.models import Course

    return Course.objects.filter(
        id__in=unique_ids.values_list("course_id_int", flat=True)
    )


def get_student_registration_for_course(student, course, semester_type, session):
    return course_registration.objects.filter(
        student_id=student,
        course_id=course,
        semester_type=semester_type,
        session=session,
    )


def get_course_registration_ids_for_session(course_id, session, semester_type):
    """Return registration IDs for a given course/session/semester."""
    return course_registration.objects.filter(
        course_id_id=course_id,
        session=session,
        semester_type=semester_type,
    ).values_list("course_id", flat=True).distinct()


# ---------------------------------------------------------------------------
# Unique year selectors
# ---------------------------------------------------------------------------

def get_unique_student_grade_years():
    return (
        Student_grades.objects.values_list("academic_year", flat=True)
        .distinct()
        .order_by("academic_year")
    )


def get_unique_registration_years(programme_type=None):
    qs = course_registration.objects.exclude(session__isnull=True)
    if programme_type:
        student_ids = get_student_ids_for_programme(programme_type)
        if student_ids.exists():
            qs = qs.filter(student_id__in=student_ids)
    return qs.values_list("session", flat=True).distinct().order_by("session")


# ---------------------------------------------------------------------------
# Student grades lookups
# ---------------------------------------------------------------------------

def get_student_grades(course_id, academic_year, semester_type):
    return Student_grades.objects.filter(
        course_id=course_id,
        academic_year=academic_year,
        semester_type=semester_type,
    )


def get_student_grades_for_student(roll_no, semester_no, semester_type):
    return Student_grades.objects.filter(
        roll_no=roll_no,
        semester=semester_no,
        semester_type=semester_type,
    ).select_related("course_id")


def get_unverified_course_ids(academic_year, semester_type):
    unique_ids = (
        Student_grades.objects.filter(
            verified=False,
            academic_year=academic_year,
            semester_type=semester_type,
        )
        .values("course_id")
        .distinct()
        .annotate(course_id_int=Cast("course_id", IntegerField()))
    )
    return Courses.objects.filter(
        id__in=unique_ids.values_list("course_id_int", flat=True)
    )


def get_unique_year_ids_for_grades(academic_year, semester_type):
    return (
        Student_grades.objects.filter(
            academic_year=academic_year,
            semester_type=semester_type,
        )
        .values("year")
        .distinct()
    )


def get_verified_courses_dean(academic_year, semester_type):
    qs = Student_grades.objects.filter(
        academic_year=academic_year,
        semester_type=semester_type,
    )
    course_ids = qs.values_list("course_id_id", flat=True).distinct()
    return Courses.objects.filter(id__in=course_ids).order_by("code")


def get_dean_student_grades(course_id, year, semester_type):
    return Student_grades.objects.filter(
        course_id=course_id,
        academic_year=year,
        semester_type=semester_type,
    )


def get_verified_courses_for_validation():
    unique_ids = (
        Student_grades.objects.filter(verified=True)
        .values("course_id")
        .distinct()
        .annotate(course_id_int=Cast("course_id", IntegerField()))
    )
    return Courses.objects.filter(
        id__in=unique_ids.values_list("course_id_int", flat=True)
    )


def get_working_years():
    return course_registration.objects.values("working_year").distinct()


def get_grades_for_student_semester(roll_no, semester, semester_type):
    """Return grades for a student's SPI calculation with ordering."""
    return (
        Student_grades.objects.filter(
            roll_no=roll_no,
            semester=semester,
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


def get_grades_up_to_semester(roll_no, semester, semester_type):
    """Return grades up to a given semester for CPI calculation."""
    if semester % 2 == 0 and semester_type == "Summer Semester":
        return (
            Student_grades.objects.filter(roll_no=roll_no, semester__lte=semester)
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
    return (
        Student_grades.objects.filter(roll_no=roll_no, semester__lte=semester)
        .exclude(semester_type="Summer Semester", semester=semester)
    )


def get_registrations_up_to_semester(student, semester, semester_type):
    """Return course_registrations up to a given semester for CPI."""
    if semester % 2 == 0 and semester_type == "Summer Semester":
        return (
            course_registration.objects.select_related("course_id", "semester_id")
            .filter(student_id=student, semester_id__semester_no__lte=semester)
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
    return (
        course_registration.objects.select_related("course_id", "semester_id")
        .filter(student_id=student, semester_id__semester_no__lte=semester)
        .exclude(semester_type="Summer Semester", semester_id__semester_no=semester)
    )


def get_course_replacements_for_student(student):
    return course_replacement.objects.filter(
        Q(old_course_registration__student_id=student)
        | Q(new_course_registration__student_id=student)
    ).select_related("old_course_registration", "new_course_registration")


# ---------------------------------------------------------------------------
# Instructor lookups
# ---------------------------------------------------------------------------

def get_instructor_courses(instructor_id, working_year, semester_type):
    unique_ids = (
        CourseInstructor.objects.filter(
            instructor_id_id=instructor_id,
            year=working_year,
            semester_type=semester_type,
        )
        .values("course_id_id")
        .distinct()
        .annotate(course_id_int=Cast("course_id_id", IntegerField()))
    )
    return Courses.objects.filter(
        id__in=unique_ids.values_list("course_id_int", flat=True)
    )


def get_instructor_course_ids(instructor_id, working_year, semester_type):
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


def check_instructor_ownership(course_id, instructor_id, working_year):
    return CourseInstructor.objects.filter(
        course_id_id=course_id,
        instructor_id_id=instructor_id,
        year=working_year,
    ).exists()


def get_course_instructors_bulk(course_ids, working_year, semester_type):
    return CourseInstructor.objects.filter(
        course_id__in=course_ids,
        year=working_year,
        semester_type=semester_type,
    ).select_related()


def get_users_by_usernames(usernames):
    users = User.objects.filter(username__in=usernames)
    return {
        user.username: f"{user.first_name} {user.last_name}".strip()
        for user in users
    }


# ---------------------------------------------------------------------------
# Result Announcement lookups
# ---------------------------------------------------------------------------

def get_result_announcements():
    return ResultAnnouncement.objects.all().order_by("-created_at")


def get_result_announcement(batch_id, semester):
    return ResultAnnouncement.objects.filter(
        batch=batch_id,
        semester=semester,
    ).first()


def get_running_batches():
    return Batch.objects.filter(running_batch=True)


def get_batch_by_id(batch_id):
    return Batch.objects.filter(id=batch_id).first()


# ---------------------------------------------------------------------------
# Authentication lookups
# ---------------------------------------------------------------------------

def get_authentication_records_bulk(course_ids, working_year):
    return authentication.objects.filter(
        course_id__in=course_ids,
        course_year=working_year,
    )


# ---------------------------------------------------------------------------
# Student semester lookups
# ---------------------------------------------------------------------------

def get_student_semester_list(roll_number):
    return (
        Student_grades.objects.filter(roll_no=roll_number)
        .values_list("semester", "semester_type")
        .distinct()
        .order_by("semester")
    )


# ---------------------------------------------------------------------------
# Grade status / summary lookups
# ---------------------------------------------------------------------------

def get_submitted_course_ids(course_ids, academic_year, semester_type):
    return set(
        Student_grades.objects.filter(
            course_id__in=course_ids,
            academic_year=academic_year,
            semester_type=semester_type,
        )
        .values_list("course_id", flat=True)
        .distinct()
    )


def get_verified_course_ids(course_ids, academic_year, semester_type):
    return set(
        Student_grades.objects.filter(
            course_id__in=course_ids,
            academic_year=academic_year,
            semester_type=semester_type,
            verified=True,
        )
        .values_list("course_id", flat=True)
        .distinct()
    )


def get_course_registrations_for_validation(course_id, working_year):
    return course_registration.objects.filter(
        course_id_id=course_id,
        working_year=working_year,
    )


# ---------------------------------------------------------------------------
# Replacement-chain helpers (pure DB queries)
# ---------------------------------------------------------------------------

def get_related_replacements(reg):
    """Return replacement objects linked to a given registration."""
    from applications.academic_procedures.models import course_replacement

    olds = course_replacement.objects.filter(old_course_registration=reg)
    news = course_replacement.objects.filter(new_course_registration=reg)
    return list(olds) + list(news)


def get_grade_for_registration(roll_no, course_code, semester_no, semester_type, session):
    return Student_grades.objects.filter(
        roll_no=roll_no,
        course_id__code=course_code,
        semester=semester_no,
        semester_type=semester_type,
        academic_year=session,
    ).order_by("-semester").first()
