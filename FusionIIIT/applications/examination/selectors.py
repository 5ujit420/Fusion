from django.db.models import Case, When, IntegerField, Q
from applications.online_cms.models import Student_grades
from applications.academic_procedures.models import course_registration, course_replacement

def get_student_grades(student_id, selected_semester, semester_type):
    """
    Returns annotated student grades with select_related on course_id.
    """
    if selected_semester % 2 == 0 and semester_type == 'Summer Semester':
        return (
            Student_grades.objects
                .select_related('course_id')
                .filter(roll_no=student_id, semester__lte=selected_semester)
                .annotate(
                    semester_type_order=Case(
                        When(semester_type="Odd Semester",  then=0),
                        When(semester_type="Even Semester", then=1),
                        When(semester_type="Summer Semester", then=2),
                        default=3,
                        output_field=IntegerField(),
                    )
                )
                .order_by('semester', 'semester_type_order')
        )
    else:
        return Student_grades.objects.select_related('course_id').filter(
            roll_no=student_id, semester__lte=selected_semester,
        ).exclude(semester_type='Summer Semester', semester=selected_semester)

def get_student_grades_for_spi(student_id, selected_semester, semester_type):
    return (
        Student_grades.objects
            .select_related('course_id')
            .filter(
                roll_no=student_id,
                semester=selected_semester,
                semester_type=semester_type
            )
            .annotate(
                semester_type_order=Case(
                    When(semester_type="Odd Semester",    then=0),
                    When(semester_type="Even Semester",   then=1),
                    When(semester_type="Summer Semester", then=2),
                    default=3,
                    output_field=IntegerField(),
                )
            )
            .order_by('semester', 'semester_type_order')
    )

def get_student_registrations(student, selected_semester, semester_type):
    """
    Returns annotated course registrations with select_related on course_id, semester_id.
    """
    if selected_semester % 2 == 0 and semester_type == 'Summer Semester':
        return (
            course_registration.objects
                .select_related('course_id', 'semester_id')
                .filter(
                    student_id=student,
                    semester_id__semester_no__lte=selected_semester,
                )
                .annotate(
                    semester_type_order=Case(
                        When(semester_type="Odd Semester",    then=0),
                        When(semester_type="Even Semester",   then=1),
                        When(semester_type="Summer Semester", then=2),
                        default=3,
                        output_field=IntegerField(),
                    )
                )
                .order_by('semester_id__semester_no', 'semester_type_order')
        )
    else:
        return course_registration.objects.select_related('course_id', 'semester_id').filter(
            student_id=student,
            semester_id__semester_no__lte=selected_semester
        ).exclude(semester_type='Summer Semester', semester_id__semester_no=selected_semester)

def check_students_in_course(course_id, session_year, semester_type, programme_list=None):
    """
    Checks if there are students in a given course, filtered optionally by programme_list.
    """
    course_info_query = course_registration.objects.filter(
        course_id_id=course_id,
        session=session_year,
        semester_type=semester_type
    )

    if programme_list is not None:
        from applications.academic_information.models import Student
        student_ids_with_programme = Student.objects.filter(
            programme__in=programme_list
        ).values_list('id', flat=True)
        
        course_info_query = course_info_query.filter(
            student_id__in=student_ids_with_programme
        )
    
    return course_info_query.exists(), course_info_query.count() if course_info_query.exists() else 0
