"""
Services module for examination app.
Contains all business logic following the service layer pattern.
Layer: View → Service → Selector → ORM
"""
from decimal import Decimal, ROUND_HALF_UP
from collections import defaultdict
from django.db.models import Q
from applications.academic_procedures.models import course_registration, course_replacement
from applications.online_cms.models import Student_grades
from applications.examination.selectors import (
    get_student_by_id,
    get_student_grades_with_annotations,
    get_cumulative_grades_for_student,
    get_course_registrations_for_student,
    get_course_replacements_for_student,
    get_user_by_username,
)


# Grade conversion constants
GRADE_CONVERSION = {
    "O": 1.0, "A+": 1.0, "A": 0.9, "B+": 0.8, "B": 0.7,
    "C+": 0.6, "C": 0.5, "D+": 0.4, "D": 0.3, "F": 0.2, "S": 0.0,
    **{f"A{i}": Decimal(str(0.9 + i * 0.01)) for i in range(1, 11)},
    **{f"B{i}": Decimal(str(0.8 + i * 0.01)) for i in range(1, 11)},
    **{
        f"{x/10:.1f}": Decimal(f"{x/100:.2f}")
        for x in range(20, 101)
    }
}

ALLOWED_GRADES = {
    "O", "A+", "A",
    "B+", "B",
    "C+", "C",
    "D+", "D", "F",
    "CD", "S", "X"
}

PBI_AND_BTP_ALLOWED_GRADES = {
    f"{x:.1f}" for x in [i / 10 for i in range(20, 101)]
}


def round_from_last_decimal(number, decimal_places=1):
    """
    Round a number to specified decimal places using ROUND_HALF_UP.
    
    Args:
        number: Number to round
        decimal_places: Number of decimal places (default: 1)
        
    Returns:
        Rounded Decimal value
    """
    d = Decimal(str(number))
    return Decimal(d).quantize(Decimal('0.1'), rounding=ROUND_HALF_UP)


def trace_registration(reg_id, mapping):
    """
    Trace a registration ID through a replacement mapping.
    
    Args:
        reg_id: Registration ID to trace
        mapping: Dictionary mapping registration IDs
        
    Returns:
        Original registration ID
    """
    seen = set()
    while reg_id in mapping and reg_id not in seen:
        seen.add(reg_id)
        reg_id = mapping[reg_id]
    return reg_id


def calculate_spi_for_student(student, selected_semester, semester_type):
    """
    Calculate SPI (Semester Performance Index) for a student.
    
    Business Logic:
    - Fetches all grades for the student in the specified semester
    - Applies grade conversion factors
    - Calculates weighted average based on credits
    - Returns SPI, semester units, and total points
    
    Args:
        student: Student object
        selected_semester: Semester number
        semester_type: Type of semester (Odd/Even/Summer)
        
    Returns:
        Tuple of (spi, semester_unit, total_points*10)
        spi: Semester Performance Index rounded to 1 decimal
        semester_unit: Total credits for the semester
        total_points*10: Total grade points multiplied by 10
    """
    grades = get_student_grades_with_annotations(
        roll_no=student.id_id,
        semester=selected_semester,
        semester_type=semester_type
    )
    
    semester_unit = Decimal('0')
    total_points = Decimal('0')
    total_credits = Decimal('0')
    
    for g in grades:
        credit = Decimal(str(g.course_id.credit))
        factor = GRADE_CONVERSION.get(g.grade.strip(), -1)
        if factor >= 0:
            if factor != 0:
                factor = Decimal(str(factor))
                total_points += factor * credit
                total_credits += credit
            semester_unit += credit
    
    if total_credits:
        spi = round_from_last_decimal(Decimal('10') * (total_points / total_credits))
    else:
        spi = 0
    
    return spi, semester_unit, (total_points * 10)


def calculate_cpi_for_student(student, selected_semester, semester_type):
    """
    Calculate CPI (Cumulative Performance Index) for a student.
    
    Business Logic:
    - Fetches all grades up to the specified semester
    - Handles course replacements to get best grades
    - Applies grade conversion factors
    - Calculates cumulative weighted average
    
    Args:
        student: Student object
        selected_semester: Semester number
        semester_type: Type of semester (Odd/Even/Summer)
        
    Returns:
        Tuple of (cpi, total_unit, total_points*10)
        cpi: Cumulative Performance Index rounded to 1 decimal
        total_unit: Total credits accumulated
        total_points*10: Total grade points multiplied by 10
    """
    total_unit = Decimal('0')
    
    # Handle summer semester edge case
    if selected_semester % 2 == 0 and semester_type == 'Summer Semester':
        grades = get_cumulative_grades_for_student(
            roll_no=student.id_id,
            up_to_semester=selected_semester,
            semester_type=semester_type
        )
        
        registrations = get_course_registrations_for_student(
            student_id=student,
            semester_no=selected_semester
        ).exclude(semester_type='Summer Semester', semester_id__semester_no=selected_semester)
    else:
        grades = get_cumulative_grades_for_student(
            roll_no=student.id_id,
            up_to_semester=selected_semester,
            semester_type=None
        )
        
        registrations = get_course_registrations_for_student(
            student_id=student,
            semester_no=None
        ).exclude(semester_type='Summer Semester', semester_id__semester_no=selected_semester)
    
    # Build registration mapping
    reg_mapping = {}
    for reg in registrations:
        key = (reg.course_id.code.strip(), reg.semester_id.semester_no, reg.semester_type)
        reg_mapping[key] = reg.id
    
    # Get course replacements
    replacements = get_course_replacements_for_student(student_id=student)
    
    # Build replacement mapping
    reg_replacement_map = {}
    for rep in replacements:
        old_reg_id = rep.old_course_registration.id
        new_reg_id = rep.new_course_registration.id
        if new_reg_id != old_reg_id:
            reg_replacement_map[new_reg_id] = old_reg_id
    
    # Group grades by original registration ID
    grade_groups = defaultdict(list)
    for g in grades:
        key = (g.course_id.code.strip(), g.semester, g.semester_type)
        reg_id = reg_mapping.get(key)
        if reg_id is None:
            continue
        original_reg_id = trace_registration(reg_id, reg_replacement_map)
        grade_groups[original_reg_id].append(g)
    
    # Calculate CPI using best grade for each course
    total_points = Decimal('0')
    total_credits = Decimal('0')
    
    for orig_reg, g_list in grade_groups.items():
        best_record = max(g_list, key=lambda r: GRADE_CONVERSION.get(r.grade.strip(), -1))
        grade_factor = GRADE_CONVERSION.get(best_record.grade.strip(), -1)
        credit = Decimal(str(getattr(best_record.course_id, 'credit', 3)))
        
        if grade_factor >= 0:
            if grade_factor != 0:
                grade_factor = Decimal(str(grade_factor))
                total_points += grade_factor * credit
                total_credits += credit
            total_unit += credit
    
    if total_credits:
        cpi = round_from_last_decimal(Decimal('10') * (total_points / total_credits))
    else:
        cpi = 0
    
    return cpi, total_unit, (total_points * 10)


def parse_academic_year(academic_year, semester_type):
    """
    Parse academic year string into start and end years.
    
    Args:
        academic_year: Academic year string (e.g., "2023-2024")
        semester_type: Type of semester
        
    Returns:
        Tuple of (start_year, end_year) as integers
    """
    if academic_year and '-' in academic_year:
        try:
            parts = academic_year.split('-')
            start_year = int(parts[0])
            end_year = int(parts[1])
            return start_year, end_year
        except (ValueError, IndexError):
            pass
    
    # Fallback: assume current year
    from datetime import date
    current_year = date.today().year
    return current_year, current_year + 1


def is_valid_grade(grade, course_code):
    """
    Validate if a grade is allowed for a course.
    
    Business Logic:
    - PBI (Project Based Instruction) and BTP (Bachelor Thesis Project) courses
      allow numeric grades (2.0 to 10.0)
    - Other courses use letter grades
    
    Args:
        grade: Grade string to validate
        course_code: Course code to determine validation rules
        
    Returns:
        Boolean indicating if grade is valid
    """
    if not grade:
        return False
    
    grade = str(grade).strip().upper()
    
    # Check if it's a PBI or BTP course
    is_project_course = course_code and ('PBI' in course_code.upper() or 'BTP' in course_code.upper())
    
    if is_project_course:
        # Allow numeric grades from 2.0 to 10.0
        if grade in PBI_AND_BTP_ALLOWED_GRADES:
            return True
        # Also allow standard grades
        return grade in ALLOWED_GRADES
    else:
        return grade in ALLOWED_GRADES


def gather_related_registrations(initial_reg, max_semester):
    """
    Gather all related course registrations including replacements.
    
    Business Logic:
    - Traces through course replacement chain
    - Collects all registrations for the same course across semesters
    - Used to determine multiple attempts at a course
    
    Args:
        initial_reg: Initial course registration
        max_semester: Maximum semester number to include
        
    Returns:
        List of related course registrations
    """
    related = [initial_reg]
    visited = {initial_reg.id}
    queue = [initial_reg]
    
    while queue:
        current = queue.pop(0)
        
        # Find replacements where this is the old registration
        forward_replacements = course_replacement.objects.filter(
            old_course_registration=current
        ).select_related('new_course_registration')
        
        for rep in forward_replacements:
            new_reg = rep.new_course_registration
            if new_reg.id not in visited and new_reg.semester_id.semester_no <= max_semester:
                visited.add(new_reg.id)
                related.append(new_reg)
                queue.append(new_reg)
        
        # Find replacements where this is the new registration
        backward_replacements = course_replacement.objects.filter(
            new_course_registration=current
        ).select_related('old_course_registration')
        
        for rep in backward_replacements:
            old_reg = rep.old_course_registration
            if old_reg.id not in visited:
                visited.add(old_reg.id)
                related.append(old_reg)
                queue.append(old_reg)
    
    return related


def format_semester_display(semester_no, semester_type=None, semester_label=None):
    """
    Format semester number and type for display.
    
    Args:
        semester_no: Semester number
        semester_type: Type of semester (Odd/Even/Summer)
        semester_label: Optional custom label
        
    Returns:
        Formatted semester string
    """
    if semester_label and 'summer' in semester_label.lower():
        return semester_label
    
    if semester_type and 'summer' in semester_type.lower():
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
    else:
        return str(semester_no)


def get_student_attempt_info(student_id, course, semester, semester_type, grade_entry):
    """
    Get attempt information for a student's course grade.
    
    Business Logic:
    - Finds all registrations for the course
    - Gathers related registrations through replacements
    - Collects all grade attempts
    - Determines best grade and attempt count
    
    Args:
        student_id: Student ID
        course: Course object
        semester: Semester number
        semester_type: Type of semester
        grade_entry: Student_grades entry
        
    Returns:
        Tuple of (remark, attempts) where:
        - remark: String indicating attempt status (e.g., "1st Attempt", "2nd Attempt (Improved)")
        - attempts: List of (course_code, grade) tuples
    """
    reg = course_registration.objects.filter(
        student_id=student_id,
        course_id=course,
        semester_id__semester_no=semester,
        semester_type=semester_type,
        session=grade_entry.academic_year,
    ).first()
    
    if not reg:
        return '-', []
    
    related_regs = gather_related_registrations(reg, semester)
    attempts = []
    
    for r in related_regs:
        g = Student_grades.objects.filter(
            roll_no=student_id.id_id,
            course_id__code=r.course_id.code,
            semester=r.semester_id.semester_no,
            semester_type=r.semester_type,
            academic_year=r.session
        ).order_by('-semester').first()
        
        if g:
            attempts.append((r.course_id.code, g.grade))
    
    if len(attempts) >= 1:
        scored = sorted(
            attempts,
            key=lambda x: GRADE_CONVERSION.get(x[1], -1),
            reverse=True
        )
        best_grade = scored[0][1]
        attempt_count = len(set([a[0] for a in attempts]))
        
        if attempt_count == 1:
            remark = '1st Attempt'
        else:
            if grade_entry.grade == best_grade:
                remark = f'{attempt_count}nd Attempt (Improved)'
            else:
                remark = f'{attempt_count}nd Attempt'
        return remark, attempts
    
    return '-', []
