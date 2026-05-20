"""
Placement Cell Selectors Layer

This module contains all read-side database queries for the placement cell app.
Selectors are responsible for:
- Fetching data from the database
- Optimizing queries with select_related/prefetch_related
- Providing reusable query building blocks

Layer contract: Views → Services → Selectors → ORM
"""
import datetime
from django.db.models import Count, Q, F, Case, When, Value, IntegerField, CharField
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404

from applications.academic_information.models import Student
from applications.globals.models import ExtraInfo, HoldsDesignation

from .models import (
    Achievement, ChairmanVisit, Conference, Course, Education, Experience,
    Extracurricular, Has, NotifyStudent, Patent, PlacementRecord, Project,
    Publication, Reference, Role, Skill, StudentPlacement, StudentRecord,
    PlacementSchedule, PlacementStatus, CompanyDetails
)


def get_placement_statistics_data():
    """
    Get base data for placement statistics calculation.
    
    Returns:
        tuple: (years queryset, records queryset, all_records queryset)
    """
    years = PlacementRecord.objects.filter(
        ~Q(placement_type="HIGHER STUDIES")
    ).values('year').annotate(Count('year'))
    
    records = PlacementRecord.objects.values(
        'name', 'year', 'ctc', 'placement_type'
    ).annotate(
        Count('name'), 
        Count('year'), 
        Count('placement_type'), 
        Count('ctc')
    )
    
    all_records = PlacementRecord.objects.all()
    
    return years, records, all_records


def get_yearly_placement_stats():
    """
    Get year-wise placement statistics.
    
    Returns:
        QuerySet: Years with counts
    """
    return PlacementRecord.objects.filter(
        ~Q(placement_type="HIGHER STUDIES")
    ).values('year').annotate(Count('year'))


def get_student_record_list(filters=None):
    """
    Get filtered student records with optimized joins.
    
    Args:
        filters (dict, optional): Filter parameters
        
    Returns:
        QuerySet: StudentRecord objects with related data
    """
    queryset = StudentRecord.objects.select_related(
        'unique_id', 'record_id'
    ).all()
    
    if filters:
        if filters.get('name'):
            queryset = queryset.filter(
                Q(record_id__name__icontains=filters['name'])
            )
        if filters.get('year'):
            queryset = queryset.filter(
                Q(record_id__year=filters['year'])
            )
        if filters.get('placement_type'):
            queryset = queryset.filter(
                Q(record_id__placement_type=filters['placement_type'])
            )
    
    return queryset


def get_filtered_placement_records(filters_dict):
    """
    Centralized filter chains for placement records.
    
    Args:
        filters_dict (dict): Filter criteria
        
    Returns:
        QuerySet: Filtered PlacementRecord objects
    """
    queryset = PlacementRecord.objects.all()
    
    if filters_dict.get('placement_type'):
        queryset = queryset.filter(
            Q(placement_type=filters_dict['placement_type'])
        )
    
    if filters_dict.get('name'):
        queryset = queryset.filter(
            Q(name__icontains=filters_dict['name'])
        )
    
    if filters_dict.get('min_ctc'):
        queryset = queryset.filter(
            Q(ctc__gte=filters_dict['min_ctc'])
        )
    
    if filters_dict.get('year'):
        queryset = queryset.filter(
            Q(year=filters_dict['year'])
        )
    
    return queryset


def get_department_counts_for_year(year, studentrecord):
    """
    Calculate department-wise placement counts for a given year.
    
    Args:
        year (int): Year to calculate for
        studentrecord (QuerySet): StudentRecord queryset
        
    Returns:
        dict: Department counts {year: {dept: count}}
    """
    tcse = 0
    tece = 0
    tme = 0
    tadd = 0
    
    for z in studentrecord:
        if z.record_id.year == year:
            dept_name = z.unique_id.id.department.name
            if dept_name == "CSE":
                tcse += 1
            elif dept_name == "ECE":
                tece += 1
            elif dept_name == "ME":
                tme += 1
            tadd += 1
    
    return {
        'year': year,
        'cse': tcse,
        'ece': tece,
        'me': tme,
        'total': tadd
    }


def get_student_cv_data(student_id):
    """
    Get all CV-related data for a student with optimized queries.
    
    Args:
        student_id (str): Student ID
        
    Returns:
        dict: All CV data with optimized fetches
    """
    student = get_object_or_404(Student, Q(id=student_id))
    
    # Use select_related and prefetch_related to avoid N+1
    skills = Has.objects.select_related(
        'skill_id', 'unique_id'
    ).filter(Q(unique_id=student))
    
    education = Education.objects.select_related(
        'unique_id'
    ).filter(Q(unique_id=student))
    
    course = Course.objects.select_related(
        'unique_id'
    ).filter(Q(unique_id=student))
    
    experience = Experience.objects.select_related(
        'unique_id'
    ).filter(Q(unique_id=student))
    
    project = Project.objects.select_related(
        'unique_id'
    ).filter(Q(unique_id=student))
    
    achievement = Achievement.objects.select_related(
        'unique_id'
    ).filter(Q(unique_id=student))
    
    extracurricular = Extracurricular.objects.select_related(
        'unique_id'
    ).filter(Q(unique_id=student))
    
    conference = Conference.objects.select_related(
        'unique_id'
    ).filter(Q(unique_id=student))
    
    publication = Publication.objects.select_related(
        'unique_id'
    ).filter(Q(unique_id=student))
    
    patent = Patent.objects.select_related(
        'unique_id'
    ).filter(Q(unique_id=student))
    
    return {
        'student': student,
        'skills': skills,
        'education': education,
        'course': course,
        'experience': experience,
        'project': project,
        'achievement': achievement,
        'extracurricular': extracurricular,
        'conference': conference,
        'publication': publication,
        'patent': patent,
    }


def get_student_profile_data(profile_id):
    """
    Get student profile data for resume/CV generation.
    
    Args:
        profile_id: Profile ID
        
    Returns:
        dict: Profile data
    """
    user = get_object_or_404(User, Q(username=profile_id))
    profile = get_object_or_404(ExtraInfo, Q(user=user))
    student = get_object_or_404(Student, Q(id=profile.id))
    
    cv_data = get_student_cv_data(profile.id)
    cv_data['profile'] = profile
    cv_data['user'] = user
    
    return cv_data


def get_reference_list(student):
    """
    Get reference list for a student.
    
    Args:
        student (Student): Student object
        
    Returns:
        QuerySet: Reference objects
    """
    return Reference.objects.select_related(
        'unique_id'
    ).filter(unique_id=student)


def get_company_names():
    """
    Get list of unique company names.
    
    Returns:
        list: Company names
    """
    return list(NotifyStudent.objects.values_list(
        'company_name', flat=True
    ).distinct())


def get_all_roles():
    """
    Get all available roles.
    
    Returns:
        QuerySet: Role objects
    """
    return Role.objects.all()


def get_placement_status_with_details(notify_id=None, unique_id=None):
    """
    Get placement status with related data optimized.
    
    Args:
        notify_id (int, optional): NotifyStudent ID
        unique_id (str, optional): Student ID
        
    Returns:
        QuerySet: PlacementStatus with select_related
    """
    queryset = PlacementStatus.objects.select_related(
        'unique_id', 'notify_id'
    )
    
    if notify_id:
        queryset = queryset.filter(notify_id=notify_id)
    
    if unique_id:
        queryset = queryset.filter(unique_id__id=unique_id)
    
    return queryset


def check_and_update_invitation_dates(placementstatus_queryset):
    """
    Check invitation dates and update expired ones using bulk operations.
    
    Args:
        placementstatus_queryset (QuerySet): PlacementStatus queryset
        
    Returns:
        int: Number of updated records
    """
    now = datetime.datetime.now()
    updates = []
    
    for ps in placementstatus_queryset:
        if ps.invitation == 'PENDING':
            dt = ps.timestamp + datetime.timedelta(days=ps.no_of_days)
            if dt < now:
                ps.invitation = 'IGNORE'
                updates.append(ps)
    
    if updates:
        PlacementStatus.objects.bulk_update(updates, ['invitation'])
    
    return len(updates)


def get_education_by_student(student):
    """
    Get education records for a student.
    
    Args:
        student (Student): Student object
        
    Returns:
        QuerySet: Education objects
    """
    return Education.objects.select_related(
        'unique_id'
    ).filter(Q(unique_id=student))


def get_has_by_student(student):
    """
    Get skill associations for a student.
    
    Args:
        student (Student): Student object
        
    Returns:
        QuerySet: Has objects with select_related
    """
    return Has.objects.select_related(
        'skill_id', 'unique_id'
    ).filter(Q(unique_id=student))


def get_achievement_by_student(student):
    """
    Get achievements for a student.
    
    Args:
        student (Student): Student object
        
    Returns:
        QuerySet: Achievement objects
    """
    return Achievement.objects.select_related(
        'unique_id'
    ).filter(Q(unique_id=student))


def get_publication_by_student(student):
    """
    Get publications for a student.
    
    Args:
        student (Student): Student object
        
    Returns:
        QuerySet: Publication objects
    """
    return Publication.objects.select_related(
        'unique_id'
    ).filter(Q(unique_id=student))


def get_patent_by_student(student):
    """
    Get patents for a student.
    
    Args:
        student (Student): Student object
        
    Returns:
        QuerySet: Patent objects
    """
    return Patent.objects.select_related(
        'unique_id'
    ).filter(Q(unique_id=student))


def get_course_by_student(student):
    """
    Get courses for a student.
    
    Args:
        student (Student): Student object
        
    Returns:
        QuerySet: Course objects
    """
    return Course.objects.select_related(
        'unique_id'
    ).filter(Q(unique_id=student))


def get_project_by_student(student):
    """
    Get projects for a student.
    
    Args:
        student (Student): Student object
        
    Returns:
        QuerySet: Project objects
    """
    return Project.objects.select_related(
        'unique_id'
    ).filter(Q(unique_id=student))


def get_experience_by_student(student):
    """
    Get experiences for a student.
    
    Args:
        student (Student): Student object
        
    Returns:
        QuerySet: Experience objects
    """
    return Experience.objects.select_related(
        'unique_id'
    ).filter(Q(unique_id=student))


def get_extracurricular_by_student(student):
    """
    Get extracurricular activities for a student.
    
    Args:
        student (Student): Student object
        
    Returns:
        QuerySet: Extracurricular objects
    """
    return Extracurricular.objects.select_related(
        'unique_id'
    ).filter(Q(unique_id=student))


def get_conference_by_student(student):
    """
    Get conferences for a student.
    
    Args:
        student (Student): Student object
        
    Returns:
        QuerySet: Conference objects
    """
    return Conference.objects.select_related(
        'unique_id'
    ).filter(Q(unique_id=student))


def get_current_user_designations(user):
    """
    Get current designations held by a user.
    
    Args:
        user (User): Django user
        
    Returns:
        tuple: (chairman_check, officer_check, student_check)
    """
    current1 = HoldsDesignation.objects.filter(
        Q(working=user, designation__name="placement chairman")
    )
    current2 = HoldsDesignation.objects.filter(
        Q(working=user, designation__name="placement officer")
    )
    current = HoldsDesignation.objects.filter(
        Q(working=user, designation__name="student")
    )
    
    return bool(current1), bool(current2), bool(current)


def get_skill_by_name(skill_name):
    """
    Get or create a skill by name.
    
    Args:
        skill_name (str): Skill name
        
    Returns:
        Skill: Skill object
    """
    skill, created = Skill.objects.get_or_create(skill=skill_name)
    return skill


def get_student_by_id(student_id):
    """
    Get student by ID.
    
    Args:
        student_id (str): Student ID
        
    Returns:
        Student: Student object
    """
    return get_object_or_404(Student, Q(id=student_id))


def get_extra_info_by_user(user):
    """
    Get extra info for a user.
    
    Args:
        user (User): Django user
        
    Returns:
        ExtraInfo: ExtraInfo object
    """
    return get_object_or_404(ExtraInfo, Q(user=user))


def get_placement_schedule_by_notify(notify_id):
    """
    Get placement schedule by notify ID.
    
    Args:
        notify_id (int): NotifyStudent ID
        
    Returns:
        PlacementSchedule: Schedule object or None
    """
    return PlacementSchedule.objects.filter(
        notify_id=notify_id
    ).first()


def get_chairman_visits():
    """
    Get all chairman visits.
    
    Returns:
        QuerySet: ChairmanVisit objects
    """
    return ChairmanVisit.objects.all()


def get_message_officer_messages():
    """
    Get all messages from placement officer.
    
    Returns:
        QuerySet: MessageOfficer objects
    """
    from .models import MessageOfficer
    return MessageOfficer.objects.all()


def get_notify_student_by_filters(filters):
    """
    Get NotifyStudent objects by filters.
    
    Args:
        filters (dict): Filter criteria
        
    Returns:
        QuerySet: NotifyStudent objects
    """
    queryset = NotifyStudent.objects.all()
    
    if filters.get('company_name'):
        queryset = queryset.filter(
            company_name__icontains=filters['company_name']
        )
    
    if filters.get('placement_type'):
        queryset = queryset.filter(
            placement_type=filters['placement_type']
        )
    
    return queryset


def get_placement_record_by_filters(filters):
    """
    Get PlacementRecord objects by filters.
    
    Args:
        filters (dict): Filter criteria
        
    Returns:
        QuerySet: PlacementRecord objects
    """
    queryset = PlacementRecord.objects.all()
    
    if filters.get('placement_type'):
        queryset = queryset.filter(
            placement_type=filters['placement_type']
        )
    
    if filters.get('year'):
        queryset = queryset.filter(year=filters['year'])
    
    if filters.get('name'):
        queryset = queryset.filter(
            name__icontains=filters['name']
        )
    
    return queryset


def get_student_placement_by_unique_id(unique_id):
    """
    Get StudentPlacement by unique ID.
    
    Args:
        unique_id (Student): Student object
        
    Returns:
        StudentPlacement: StudentPlacement object or None
    """
    try:
        return StudentPlacement.objects.get(unique_id=unique_id)
    except StudentPlacement.DoesNotExist:
        return None


def get_role_by_id(role_id):
    """
    Get role by ID.
    
    Args:
        role_id (int): Role ID
        
    Returns:
        Role: Role object or None
    """
    try:
        return Role.objects.get(id=role_id)
    except Role.DoesNotExist:
        return None


def get_company_details_by_name(company_name):
    """
    Get or create company details by name.
    
    Args:
        company_name (str): Company name
        
    Returns:
        CompanyDetails: CompanyDetails object
    """
    company, created = CompanyDetails.objects.get_or_create(
        company_name=company_name
    )
    return company
