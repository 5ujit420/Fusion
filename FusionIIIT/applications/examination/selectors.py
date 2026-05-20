from collections import defaultdict

from django.contrib.auth import get_user_model
from django.db.models import Case, When, IntegerField, Q

from applications.academic_procedures.models import course_registration, course_replacement
from applications.online_cms.models import Student_grades


def get_student_grades_for_spi(student, selected_semester, semester_type):
    return (
        Student_grades.objects
            .filter(
                roll_no=student.id_id,
                semester=selected_semester,
                semester_type=semester_type
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
            .order_by('semester', 'semester_type_order')
    )


def get_grade_and_registration_queries_for_cpi(student, selected_semester, semester_type):
    if selected_semester % 2 == 0 and semester_type == 'Summer Semester':
        grades = (
            Student_grades.objects
                .filter(roll_no=student.id_id, semester__lte=selected_semester)
                .annotate(
                    semester_type_order=Case(
                        When(semester_type="Odd Semester", then=0),
                        When(semester_type="Even Semester", then=1),
                        When(semester_type="Summer Semester", then=2),
                        default=3,
                        output_field=IntegerField(),
                    )
                )
                .order_by('semester', 'semester_type_order')
        )
        registrations = (
            course_registration.objects
                .select_related('course_id', 'semester_id')
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
                .order_by('semester_id__semester_no', 'semester_type_order')
        )
    else:
        grades = Student_grades.objects.filter(
            roll_no=student.id_id, semester__lte=selected_semester,
        ).exclude(semester_type='Summer Semester', semester=selected_semester)

        registrations = course_registration.objects.select_related('course_id', 'semester_id').filter(
            student_id=student,
            semester_id__semester_no__lte=selected_semester
        ).exclude(semester_type='Summer Semester', semester_id__semester_no=selected_semester)

    return grades, registrations


def get_replacement_records_for_student(student):
    return (
        course_replacement.objects
            .filter(
                Q(old_course_registration__student_id=student) |
                Q(new_course_registration__student_id=student)
            )
            .select_related('old_course_registration', 'new_course_registration')
    )


def get_users_by_usernames(usernames):
    User = get_user_model()
    return User.objects.in_bulk(usernames, field_name='username')
