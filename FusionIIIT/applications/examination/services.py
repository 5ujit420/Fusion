from decimal import Decimal
from collections import defaultdict
from applications.academic_procedures.models import course_replacement
from applications.examination.selectors import get_student_grades, get_student_registrations
from django.db.models import Q
from decimal import Decimal, ROUND_HALF_UP

grade_conversion = {
    'A+': 10, 'A': 10, 'B+': 9, 'B': 8, 'C+': 7,
    'C': 6, 'D+': 5, 'D': 4, 'F': 0, 'S': 0, 'X': 0, 'E': 0
}

def round_from_last_decimal(value):
    return value.quantize(Decimal('.01'), rounding=ROUND_HALF_UP)

def trace_registration(reg_id, mapping):
    seen = set()
    while reg_id in mapping and reg_id not in seen:
        seen.add(reg_id)
        reg_id = mapping[reg_id]
    return reg_id

def calculate_points(student, selected_semester, semester_type):
    """
    Calculates CPI taking into account grades and registrations.
    """
    grades = get_student_grades(student.id_id, selected_semester, semester_type)
    registrations = get_student_registrations(student, selected_semester, semester_type)
    
    reg_mapping = {}
    for reg in registrations:
        key = (reg.course_id.code.strip(), reg.semester_id.semester_no, reg.semester_type)
        reg_mapping[key] = reg.id

    replacements = course_replacement.objects.filter(
        Q(old_course_registration__student_id=student) |
        Q(new_course_registration__student_id=student)
    ).select_related('old_course_registration', 'new_course_registration')

    reg_replacement_map = {}
    for rep in replacements:
        old_reg_id = rep.old_course_registration.id
        new_reg_id = rep.new_course_registration.id
        if new_reg_id != old_reg_id:
            reg_replacement_map[new_reg_id] = old_reg_id

    grade_groups = defaultdict(list)
    for g in grades:
        key = (g.course_id.code.strip(), g.semester, g.semester_type)
        reg_id = reg_mapping.get(key)
        if reg_id is None:
            continue
        original_reg_id = trace_registration(reg_id, reg_replacement_map)
        grade_groups[original_reg_id].append(g)

    total_points = Decimal('0')
    total_credits = Decimal('0')
    total_unit = Decimal('0')
    
    for orig_reg, g_list in grade_groups.items():
        best_record = max(g_list, key=lambda r: grade_conversion.get(r.grade.strip(), -1))
        grade_factor = grade_conversion.get(best_record.grade.strip(), -1)
        credit = Decimal(str(getattr(best_record.course_id, 'credit', 3)))
        if grade_factor >=  0:
            if grade_factor != 0:
                grade_factor =  Decimal(str(grade_factor))
                total_points += grade_factor * credit
                total_credits += credit
            total_unit += credit
            
    cpi = round_from_last_decimal(Decimal('10') * (total_points / total_credits)) if total_credits else Decimal('0')
    return cpi, total_unit, (total_points * Decimal('10'))

def calculate_cpi_for_student_service(student, selected_semester, semester_type):
    return calculate_points(student, selected_semester, semester_type)

def calculate_spi_for_student_service(student, selected_semester, semester_type):
    from applications.examination.selectors import get_student_grades_for_spi
    grades = get_student_grades_for_spi(student.id_id, selected_semester, semester_type)
    
    total_points = Decimal('0')
    total_credits = Decimal('0')
    semester_unit = Decimal('0')
    
    for g in grades:
        credit = Decimal(str(g.course_id.credit))
        factor = grade_conversion.get(g.grade.strip(), -1)
        if factor >= 0:
            if factor != 0:
                factor = Decimal(str(factor))
                total_points += factor * credit
                total_credits += credit
            semester_unit += credit
            
    spi = round_from_last_decimal(Decimal('10') * (total_points / total_credits)) if total_credits else Decimal('0')
    return spi, semester_unit, (total_points * Decimal('10'))
