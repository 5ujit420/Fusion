"""
Selectors for placement_cell module.

All database queries are centralized here. Views and services call selectors
instead of issuing raw ORM queries.

Audit refs: S01, S02, S14, S23, R06, R12, R13, R14
"""
import logging
from datetime import date

from django.contrib.auth.models import User
from django.db.models import Count, Q

from applications.academic_information.models import Student
from applications.globals.models import DepartmentInfo, ExtraInfo, HoldsDesignation

from .models import (
    Achievement, ChairmanVisit, CompanyDetails, Conference, Course,
    Education, Experience, Extracurricular, Has, NotifyStudent, Patent,
    PlacementRecord, PlacementSchedule, PlacementStatus, Project,
    Publication, Reference, Role, Skill, StudentPlacement, StudentRecord,
    ROLE_PLACEMENT_CHAIRMAN, ROLE_PLACEMENT_OFFICER, ROLE_STUDENT,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Role / User helpers  (R06 — replaces 7+ repeated HoldsDesignation lookups)
# ---------------------------------------------------------------------------

def get_user_placement_roles(user):
    """Return dict with boolean flags for the user's placement roles."""
    is_chairman = HoldsDesignation.objects.filter(
        Q(working=user, designation__name=ROLE_PLACEMENT_CHAIRMAN)
    ).exists()
    is_officer = HoldsDesignation.objects.filter(
        Q(working=user, designation__name=ROLE_PLACEMENT_OFFICER)
    ).exists()
    is_student = HoldsDesignation.objects.filter(
        Q(working=user, designation__name=ROLE_STUDENT)
    ).exists()
    return {
        'is_chairman': is_chairman,
        'is_officer': is_officer,
        'is_student': is_student,
    }


def get_user_designation_qs(user):
    """Return the raw querysets for template context (current, current1, current2).
    Preserves the original template variable contract."""
    current1 = HoldsDesignation.objects.filter(
        Q(working=user, designation__name=ROLE_PLACEMENT_CHAIRMAN))
    current2 = HoldsDesignation.objects.filter(
        Q(working=user, designation__name=ROLE_PLACEMENT_OFFICER))
    current = HoldsDesignation.objects.filter(
        Q(working=user, designation__name=ROLE_STUDENT))
    return current, current1, current2


def get_student_by_user(user):
    """Get the Student object via ExtraInfo for a given user."""
    from django.shortcuts import get_object_or_404
    profile = get_object_or_404(ExtraInfo, Q(user=user))
    student = get_object_or_404(Student, Q(id=profile.id))
    return student


def get_extra_info(user):
    """Get ExtraInfo for a given user."""
    from django.shortcuts import get_object_or_404
    return get_object_or_404(ExtraInfo, Q(user=user))


# ---------------------------------------------------------------------------
# Student search  (R12 — replaces 20+ repeated nested Student queries)
# ---------------------------------------------------------------------------

def search_students_by_name_roll(name='', rollno=''):
    """Filter students by first_name and rollno via ExtraInfo → User.
    This is the common pattern repeated 20+ times in views."""
    return Student.objects.filter(
        Q(id__in=ExtraInfo.objects.filter(
            Q(user__in=User.objects.filter(
                Q(first_name__icontains=name)),
              id__icontains=rollno)))
    )


def search_students_by_name_roll_fullname(first_name='', last_name='', rollno=''):
    """Filter students by first_name, last_name, and rollno."""
    return Student.objects.filter(
        Q(id__in=ExtraInfo.objects.filter(
            Q(user__in=User.objects.filter(
                first_name__icontains=first_name,
                last_name__icontains=last_name),
              id__icontains=rollno)))
    )


def search_students_by_filters(name='', rollno='', programme=None,
                                department=None, cpi=0, debar='NOT DEBAR',
                                placed_type='NOT PLACED'):
    """Full student search with programme, department, CPI, debar filters."""
    qs = Student.objects.filter(
        Q(id__in=ExtraInfo.objects.filter(
            Q(user__in=User.objects.filter(Q(first_name__icontains=name)),
              department__in=DepartmentInfo.objects.filter(Q(name__in=department or [])),
              id__icontains=rollno)),
          programme=programme,
          cpi__gte=cpi)
    ).filter(
        Q(pk__in=StudentPlacement.objects.filter(
            Q(debar=debar, placed_type=placed_type)).values('unique_id_id'))
    ).order_by('id')
    return qs


def search_students_for_invite(rollno='', programme=None, department=None,
                                cpi=0, notify=None):
    """Search students for sending invitations, excluding already-invited."""
    qs = Student.objects.filter(
        Q(id__in=ExtraInfo.objects.filter(
            Q(department__in=DepartmentInfo.objects.filter(Q(name__in=department or [])),
              id__icontains=rollno)),
          programme=programme,
          cpi__gte=cpi)
    )
    if notify:
        qs = qs.exclude(
            id__in=PlacementStatus.objects.select_related('unique_id', 'notify_id').filter(
                notify_id=notify).values_list('unique_id', flat=True))
    return qs


# ---------------------------------------------------------------------------
# Placement Record search  (R13 — replaces 10+ repeated PlacementRecord queries)
# ---------------------------------------------------------------------------

def search_placement_records(placement_type, name='', ctc=0, year=None):
    """Search PlacementRecord by type, name, ctc, optionally year."""
    filters = Q(placement_type=placement_type, name__icontains=name, ctc__gte=ctc)
    if year:
        filters &= Q(year=year)
    return PlacementRecord.objects.filter(filters)


def search_placement_records_stats(placement_type, name='', ctc=0, year=None):
    """Search for statistics view — uses icontains on ctc and year."""
    filters = Q(placement_type=placement_type, name__icontains=name, ctc__icontains=ctc)
    if year:
        filters &= Q(year__icontains=year)
    return PlacementRecord.objects.filter(filters)


# ---------------------------------------------------------------------------
# Student Record search (combined student + record)
# ---------------------------------------------------------------------------

def search_student_records(placement_type, stuname='', rollno='',
                            cname='', ctc=0, year=None,
                            test_type='', test_score=0, uname=''):
    """Search StudentRecord by record type and student filters."""
    record_filters = Q(placement_type=placement_type)

    if placement_type == "HIGHER STUDIES":
        record_filters &= Q(name__icontains=uname)
        if test_type:
            record_filters &= Q(test_type__icontains=test_type)
        if test_score:
            record_filters &= Q(test_score__gte=test_score)
    else:
        record_filters &= Q(name__icontains=cname)
        if ctc:
            record_filters &= Q(ctc__gte=ctc)

    if year:
        record_filters &= Q(year=year)

    # Parse name for first/last
    first_name, last_name = _parse_name(stuname)

    student_qs = search_students_by_name_roll_fullname(first_name, last_name, rollno)

    return StudentRecord.objects.select_related('unique_id', 'record_id').filter(
        Q(record_id__in=PlacementRecord.objects.filter(record_filters),
          unique_id__in=student_qs)
    )


def _parse_name(fullname):
    """Split a full name into first and last name."""
    if not fullname:
        return '', ''
    parts = fullname.split(' ', 1)
    first_name = parts[0]
    last_name = parts[1] if len(parts) > 1 else ''
    return first_name, last_name


# ---------------------------------------------------------------------------
# Placement Status search  (R14 — replaces 8+ repeated PlacementStatus queries)
# ---------------------------------------------------------------------------

def get_placement_status_filtered(placement_type, stuname='', rollno='',
                                   cname='', ctc=0):
    """Filter PlacementStatus by type, student name, roll, company, ctc."""
    student_qs = search_students_by_name_roll(stuname, rollno)
    return PlacementStatus.objects.select_related('unique_id', 'notify_id').filter(
        Q(notify_id__in=NotifyStudent.objects.filter(
            Q(placement_type=placement_type,
              company_name__icontains=cname,
              ctc__gte=ctc)),
          unique_id__in=student_qs)
    )


def get_placement_status_filtered_ordered(placement_type, stuname='', rollno='',
                                           cname='', ctc=0):
    """Same as above but with ordering by id (for PBI tab)."""
    return get_placement_status_filtered(
        placement_type, stuname, rollno, cname, ctc
    ).order_by('id')


# ---------------------------------------------------------------------------
# Active placement statuses for a student
# ---------------------------------------------------------------------------

def get_active_placement_statuses(student):
    """Get active placement statuses for a student (schedules not yet passed)."""
    active_schedule_ids = PlacementSchedule.objects.select_related('notify_id').filter(
        Q(placement_date__gte=date.today())
    ).values_list('notify_id', flat=True)

    return PlacementStatus.objects.select_related('unique_id', 'notify_id').filter(
        Q(unique_id=student, notify_id__in=active_schedule_ids)
    ).order_by('-timestamp')


# ---------------------------------------------------------------------------
# Statistics data  (S46 — supports aggregation)
# ---------------------------------------------------------------------------

def get_placement_years():
    """Get distinct years with counts, excluding HIGHER STUDIES."""
    return PlacementRecord.objects.filter(
        ~Q(placement_type="HIGHER STUDIES")
    ).values('year').annotate(Count('year'))


def get_placement_records_annotated():
    """Get records with annotation counts."""
    return PlacementRecord.objects.values(
        'name', 'year', 'ctc', 'placement_type'
    ).annotate(
        Count('name'), Count('year'), Count('placement_type'), Count('ctc')
    )


def get_all_student_records():
    """Get all student records with related data."""
    return StudentRecord.objects.select_related('unique_id', 'record_id').all()


def get_all_placement_records():
    """Get all placement records."""
    return PlacementRecord.objects.all()


# ---------------------------------------------------------------------------
# CV data  (S14 — replaces 12 separate queries in cv view)
# ---------------------------------------------------------------------------

def get_student_cv_data(student):
    """Get all data needed for a student's CV."""
    return {
        'skills': Has.objects.select_related('skill_id', 'unique_id').filter(Q(unique_id=student)),
        'education': Education.objects.select_related('unique_id').filter(Q(unique_id=student)),
        'course': Course.objects.select_related('unique_id').filter(Q(unique_id=student)),
        'experience': Experience.objects.select_related('unique_id').filter(Q(unique_id=student)),
        'project': Project.objects.select_related('unique_id').filter(Q(unique_id=student)),
        'achievement': Achievement.objects.select_related('unique_id').filter(Q(unique_id=student)),
        'extracurricular': Extracurricular.objects.select_related('unique_id').filter(Q(unique_id=student)),
        'conference': Conference.objects.select_related('unique_id').filter(Q(unique_id=student)),
        'publication': Publication.objects.select_related('unique_id').filter(Q(unique_id=student)),
        'patent': Patent.objects.select_related('unique_id').filter(Q(unique_id=student)),
    }


def get_references_by_ids(reference_ids):
    """Get references by a list of IDs."""
    return Reference.objects.filter(id__in=reference_ids)


# ---------------------------------------------------------------------------
# Schedule, Dropdown, and misc queries
# ---------------------------------------------------------------------------

def get_all_schedules():
    """Get all placement schedules."""
    return PlacementSchedule.objects.select_related('notify_id').all()


def get_company_names_starting_with(prefix):
    """Get company names starting with a prefix for autocomplete."""
    companies = CompanyDetails.objects.filter(Q(company_name__startswith=prefix))
    return [c.company_name for c in companies]


def get_roles_starting_with(prefix):
    """Get role names starting with a prefix for autocomplete."""
    roles = Role.objects.filter(Q(role__startswith=prefix))
    return [r.role for r in roles]


def get_reference_list_for_student(student):
    """Get references for a student."""
    return Reference.objects.filter(unique_id=student)


def get_all_notify_students():
    """Get all NotifyStudent objects."""
    return NotifyStudent.objects.all()


def get_all_roles():
    """Get all Role objects."""
    return Role.objects.all()


def get_all_chairman_visits():
    """Get all ChairmanVisit objects."""
    return ChairmanVisit.objects.all()


def get_student_record_by_pk(pk):
    """Get a StudentRecord by primary key."""
    return StudentRecord.objects.get(pk=pk)


def get_placement_record_by_id(record_id):
    """Get a PlacementRecord by id."""
    return PlacementRecord.objects.get(id=record_id)


def get_student_by_rollno(rollno):
    """Get a Student by roll number (via ExtraInfo id)."""
    return Student.objects.get(
        Q(id=ExtraInfo.objects.get(Q(id=rollno)))
    )
