"""
Selectors module for examination app.
Contains all database read queries following the selector pattern.
Layer: View → Service → Selector → ORM
"""
from django.db.models import Case, When, IntegerField, Q
from applications.academic_procedures.models import course_registration, course_replacement, Semester
from applications.online_cms.models import Student_grades
from applications.examination.models import hidden_grades, authentication, ResultAnnouncement
from applications.academic_information.models import Student, Spi
from applications.programme_curriculum.models import Course as Courses, CourseInstructor, Batch


def get_student_by_id(student_id):
    """
    Get a student by their ID with related user information.
    
    Args:
        student_id: The student's ID
        
    Returns:
        Student object or None
    """
    try:
        return Student.objects.select_related('id__user', 'batch_id', 'id__department').get(id_id=student_id)
    except Student.DoesNotExist:
        return None


def get_student_grades_for_semester(roll_no, semester, semester_type=None):
    """
    Get all grades for a student in a specific semester.
    Uses select_related to avoid N+1 queries.
    
    Args:
        roll_no: Student roll number
        semester: Semester number
        semester_type: Type of semester (Odd/Even/Summer)
        
    Returns:
        QuerySet of Student_grades with related course and semester
    """
    queryset = Student_grades.objects.select_related('course_id', 'semester_id').filter(
        roll_no=roll_no,
        semester=semester
    )
    if semester_type:
        queryset = queryset.filter(semester_type=semester_type)
    return queryset


def get_student_grades_with_annotations(roll_no, semester=None, semester_type=None):
    """
    Get student grades with semester type ordering annotation.
    
    Args:
        roll_no: Student roll number
        semester: Optional semester filter
        semester_type: Optional semester type filter
        
    Returns:
        QuerySet of Student_grades annotated with semester_type_order
    """
    queryset = Student_grades.objects.select_related('course_id', 'semester_id').annotate(
        semester_type_order=Case(
            When(semester_type="Odd Semester", then=0),
            When(semester_type="Even Semester", then=1),
            When(semester_type="Summer Semester", then=2),
            default=3,
            output_field=IntegerField(),
        )
    ).filter(roll_no=roll_no)
    
    if semester:
        queryset = queryset.filter(semester=semester)
    if semester_type:
        queryset = queryset.filter(semester_type=semester_type)
    
    return queryset.order_by('semester', 'semester_type_order')


def get_cumulative_grades_for_student(roll_no, up_to_semester, semester_type=None):
    """
    Get all grades for CPI calculation up to a given semester.
    
    Args:
        roll_no: Student roll number
        up_to_semester: Maximum semester number to include
        semester_type: Optional semester type filter
        
    Returns:
        QuerySet of Student_grades for CPI calculation
    """
    queryset = Student_grades.objects.select_related('course_id', 'semester_id').annotate(
        semester_type_order=Case(
            When(semester_type="Odd Semester", then=0),
            When(semester_type="Even Semester", then=1),
            When(semester_type="Summer Semester", then=2),
            default=3,
            output_field=IntegerField(),
        )
    ).filter(roll_no=roll_no, semester__lte=up_to_semester)
    
    if semester_type:
        queryset = queryset.exclude(semester_type=semester_type, semester=up_to_semester)
    
    return queryset.order_by('semester', 'semester_type_order')


def get_course_registrations_for_student(student_id, semester_no=None, semester_type=None, session=None):
    """
    Get course registrations for a student with related data.
    
    Args:
        student_id: Student ID
        semester_no: Optional semester number filter
        semester_type: Optional semester type filter
        session: Optional academic session filter
        
    Returns:
        QuerySet of course_registration with select_related
    """
    queryset = course_registration.objects.select_related('course_id', 'semester_id', 'student_id').filter(
        student_id=student_id
    )
    
    if semester_no:
        queryset = queryset.filter(semester_id__semester_no=semester_no)
    if semester_type:
        queryset = queryset.filter(semester_type=semester_type)
    if session:
        queryset = queryset.filter(session=session)
    
    return queryset


def get_course_replacements_for_student(student_id):
    """
    Get course replacements for a student.
    
    Args:
        student_id: Student ID
        
    Returns:
        QuerySet of course_replacement with select_related
    """
    return course_replacement.objects.filter(
        Q(old_course_registration__student_id=student_id) |
        Q(new_course_registration__student_id=student_id)
    ).select_related('old_course_registration', 'new_course_registration')


def get_hidden_grades(student_id=None, course_id=None, semester_id=None):
    """
    Get hidden grades with optional filters.
    
    Args:
        student_id: Optional student ID filter
        course_id: Optional course ID filter
        semester_id: Optional semester ID filter
        
    Returns:
        QuerySet of hidden_grades
    """
    queryset = hidden_grades.objects.all()
    if student_id:
        queryset = queryset.filter(student_id=student_id)
    if course_id:
        queryset = queryset.filter(course_id=course_id)
    if semester_id:
        queryset = queryset.filter(semester_id=semester_id)
    return queryset


def get_authentication_records(course_id=None, course_year=None):
    """
    Get authentication records with optional filters.
    
    Args:
        course_id: Optional course ID filter
        course_year: Optional course year filter
        
    Returns:
        QuerySet of authentication records
    """
    queryset = authentication.objects.select_related('course_id').all()
    if course_id:
        queryset = queryset.filter(course_id=course_id)
    if course_year:
        queryset = queryset.filter(course_year=course_year)
    return queryset


def get_result_announcements(batch=None, semester=None):
    """
    Get result announcements with optional filters.
    
    Args:
        batch: Optional batch filter
        semester: Optional semester filter
        
    Returns:
        QuerySet of ResultAnnouncement
    """
    queryset = ResultAnnouncement.objects.select_related('batch').all()
    if batch:
        queryset = queryset.filter(batch=batch)
    if semester:
        queryset = queryset.filter(semester=semester)
    return queryset


def get_courses_for_batch_and_semester(batch, semester, semester_type):
    """
    Get courses for a specific batch and semester.
    
    Args:
        batch: Batch object
        semester: Semester number
        semester_type: Type of semester
        
    Returns:
        QuerySet of Courses
    """
    return Courses.objects.filter(
        batch=batch,
        semester=semester,
        semester_type=semester_type
    ).select_related('department')


def get_course_instructors(course_id, session):
    """
    Get instructors for a course in a specific session.
    
    Args:
        course_id: Course ID
        session: Academic session
        
    Returns:
        QuerySet of CourseInstructor
    """
    return CourseInstructor.objects.filter(
        course_id=course_id,
        session=session
    ).select_related('instructor_id__user')


def get_students_for_batch(batch):
    """
    Get all students in a batch.
    
    Args:
        batch: Batch object
        
    Returns:
        QuerySet of Student with select_related
    """
    return Student.objects.filter(batch_id=batch).select_related('id__user', 'id__department')


def get_spi_for_student(student, semester=None):
    """
    Get SPI records for a student.
    
    Args:
        student: Student object
        semester: Optional semester filter
        
    Returns:
        QuerySet of Spi records
    """
    queryset = Spi.objects.filter(student=student)
    if semester:
        queryset = queryset.filter(semester=semester)
    return queryset


def get_user_by_username(username):
    """
    Get a user by username.
    
    Args:
        username: Username
        
    Returns:
        User object or None
    """
    from django.contrib.auth import get_user_model
    User = get_user_model()
    try:
        return User.objects.get(username=username)
    except User.DoesNotExist:
        return None


def get_course_by_code(course_code):
    """
    Get a course by its code.
    
    Args:
        course_code: Course code
        
    Returns:
        Course object or None
    """
    try:
        return Courses.objects.get(code=course_code)
    except Courses.DoesNotExist:
        return None


def get_semester_by_no(semester_no):
    """
    Get a semester by its number.
    
    Args:
        semester_no: Semester number
        
    Returns:
        Semester object or None
    """
    try:
        return Semester.objects.get(semester_no=semester_no)
    except Semester.DoesNotExist:
        return None
