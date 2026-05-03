"""
selectors.py — placement_cell
Read-only data-access layer.  All ORM queries are centralised here.

Tasks addressed:
    T03 / S15, S16, R07  — move ORM out of views
    T04 / S21, S22       — replace O(N×M) triple-nested loop with DB aggregation
    T05 / S23, S24, S25  — add select_related / prefetch_related to export/CV paths
"""
import decimal
import logging

from datetime import date as date_cls

from django.db.models import Count, Q

from applications.academic_information.models import Student
from applications.globals.models import DepartmentInfo, ExtraInfo
from django.contrib.auth.models import User

from .models import (
    Achievement, Conference, Course, Education, Experience, Extracurricular,
    Has, NotifyStudent, Patent, PlacementRecord, PlacementSchedule,
    PlacementStatus, Project, Publication, Reference, StudentPlacement,
    StudentRecord, PlacementType,
)

logger = logging.getLogger('django.server')


# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------

def get_all_student_records():
    """S15, S16, R07: Base StudentRecord queryset used in statistics views."""
    return StudentRecord.objects.select_related(
        'unique_id', 'unique_id__id', 'unique_id__id__department',
        'record_id',
    ).all()


def get_placement_years_and_records():
    """S15, S16, R07: Return (years, records) used by statistics aggregation."""
    years = (
        PlacementRecord.objects
        .filter(~Q(placement_type=PlacementType.HIGHER_STUDIES))
        .values('year')
        .annotate(Count('year'))
    )
    records = (
        PlacementRecord.objects
        .values('name', 'year', 'ctc', 'placement_type')
        .annotate(
            Count('name'), Count('year'),
            Count('placement_type'), Count('ctc'),
        )
    )
    return years, records


def get_dept_stats_by_year():
    """
    T04 / S21, S22: Replace the O(N×M) triple-nested Python loop with a single
    DB-level GROUP BY aggregation.

    Returns a dict: { year: {'total': n, 'CSE': n, 'ECE': n, 'ME': n} }
    """
    qs = (
        StudentRecord.objects
        .filter(~Q(record_id__placement_type=PlacementType.HIGHER_STUDIES))
        .select_related(
            'record_id', 'unique_id', 'unique_id__id', 'unique_id__id__department'
        )
        .values('record_id__year', 'unique_id__id__department__name')
        .annotate(cnt=Count('id'))
    )

    stats = {}
    for row in qs:
        year = row['record_id__year']
        dept = row['unique_id__id__department__name']
        count = row['cnt']
        if year not in stats:
            stats[year] = {'total': 0, 'CSE': 0, 'ECE': 0, 'ME': 0}
        stats[year]['total'] += count
        if dept in ('CSE', 'ECE', 'ME'):
            stats[year][dept] += count

    return stats


# ---------------------------------------------------------------------------
# Student search  (S18, S23, T03)
# ---------------------------------------------------------------------------

def search_students(name='', rollno='', programme='', department=None,
                    cpi=0, debar='NOT DEBAR', placed_type='NOT PLACED'):
    """
    S18 / T03: Centralised student filter used by student_records view and
    export helpers.  select_related added for S23 (N+1 on XLS export).
    """
    department = department or []
    try:
        cpi = decimal.Decimal(str(cpi))
    except Exception:
        cpi = decimal.Decimal('0')

    qs = Student.objects.filter(
        Q(
            id__in=ExtraInfo.objects.filter(
                Q(
                    user__in=User.objects.filter(
                        Q(first_name__icontains=name)
                    ),
                    department__in=DepartmentInfo.objects.filter(
                        Q(name__in=department)
                    ),
                    id__icontains=rollno,
                )
            ),
            programme=programme,
            cpi__gte=cpi,
        )
    ).filter(
        Q(
            pk__in=StudentPlacement.objects.filter(
                Q(debar=debar, placed_type=placed_type)
            ).values('unique_id_id')
        )
    ).order_by('id').select_related(
        # S23: eager-load traversal paths used in XLS/PDF export
        'id__user', 'id__department', 'studentplacement',
    )
    return qs


# ---------------------------------------------------------------------------
# Placement record search  (S15, S16, T03)
# ---------------------------------------------------------------------------

def search_placement_records(placement_type, stuname='', rollno='',
                              cname='', ctc=0, year=None):
    """
    T03 / S15 / S16: Selector for placement / PBI student records search.
    Returns a StudentRecord queryset.
    """
    first_name, last_name = _split_name(stuname)
    filters = {
        'record_id__placement_type': placement_type,
        'record_id__name__icontains': cname,
        'record_id__ctc__gte': ctc,
    }
    if year:
        filters['record_id__year'] = year

    qs = StudentRecord.objects.select_related(
        'unique_id', 'record_id',
    ).filter(
        Q(
            **filters,
            unique_id__in=Student.objects.filter(
                Q(
                    id__in=ExtraInfo.objects.filter(
                        Q(
                            user__in=User.objects.filter(
                                first_name__icontains=first_name,
                                last_name__icontains=last_name,
                            ),
                            id__icontains=rollno,
                        )
                    )
                )
            ),
        )
    )
    return qs


def search_higher_records(stuname='', rollno='', uname='',
                           test_type='', test_score=0, year=None):
    """T03: Selector for HIGHER STUDIES student records search."""
    first_name, last_name = _split_name(stuname)
    filters = {
        'record_id__placement_type': PlacementType.HIGHER_STUDIES,
        'record_id__name__icontains': uname,
        'record_id__test_type__icontains': test_type,
        'record_id__test_score__gte': test_score,
    }
    if year:
        filters['record_id__year'] = year

    qs = StudentRecord.objects.select_related(
        'unique_id', 'record_id',
    ).filter(
        Q(
            **filters,
            unique_id__in=Student.objects.filter(
                Q(
                    id__in=ExtraInfo.objects.filter(
                        Q(
                            user__in=User.objects.filter(
                                first_name__icontains=first_name,
                                last_name__icontains=last_name,
                            ),
                            id__icontains=rollno,
                        )
                    )
                )
            ),
        )
    )
    return qs


# ---------------------------------------------------------------------------
# Invitation status search  (S06, T03)
# ---------------------------------------------------------------------------

def search_placement_status(placement_type, stuname='', rollno='',
                             cname='', ctc=0):
    """T03: Selector for invitation_status view (both PLACEMENT and PBI tabs)."""
    qs = PlacementStatus.objects.select_related(
        'unique_id', 'notify_id',
    ).filter(
        Q(
            notify_id__in=NotifyStudent.objects.filter(
                Q(
                    placement_type=placement_type,
                    company_name__icontains=cname,
                    ctc__gte=ctc,
                )
            ),
            unique_id__in=Student.objects.filter(
                Q(
                    id__in=ExtraInfo.objects.filter(
                        Q(
                            user__in=User.objects.filter(
                                Q(first_name__icontains=stuname)
                            ),
                            id__icontains=rollno,
                        )
                    )
                )
            ),
        )
    )
    return qs


# ---------------------------------------------------------------------------
# CV / resume data  (S25, T05)
# ---------------------------------------------------------------------------

def get_student_cv_data(student):
    """
    S25 / T05: Consolidate the 10 separate ORM calls in the cv view into
    one selector.  Each queryset uses select_related to avoid N+1 on access.
    """
    return {
        'skills': Has.objects.select_related('skill_id', 'unique_id').filter(
            Q(unique_id=student)
        ),
        'education': Education.objects.select_related('unique_id').filter(
            Q(unique_id=student)
        ),
        'course': Course.objects.select_related('unique_id').filter(
            Q(unique_id=student)
        ),
        'experience': Experience.objects.select_related('unique_id').filter(
            Q(unique_id=student)
        ),
        'project': Project.objects.select_related('unique_id').filter(
            Q(unique_id=student)
        ),
        'achievement': Achievement.objects.select_related('unique_id').filter(
            Q(unique_id=student)
        ),
        'extracurricular': Extracurricular.objects.select_related('unique_id').filter(
            Q(unique_id=student)
        ),
        'conference': Conference.objects.select_related('unique_id').filter(
            Q(unique_id=student)
        ),
        'publication': Publication.objects.select_related('unique_id').filter(
            Q(unique_id=student)
        ),
        'patent': Patent.objects.select_related('unique_id').filter(
            Q(unique_id=student)
        ),
    }


# ---------------------------------------------------------------------------
# Schedule
# ---------------------------------------------------------------------------

def get_upcoming_placement_schedules():
    """Return PlacementSchedule objects with placement_date >= today."""
    return PlacementSchedule.objects.select_related('notify_id').filter(
        Q(placement_date__gte=date_cls.today())
    )


def get_all_schedules():
    """Return all PlacementSchedule objects."""
    return PlacementSchedule.objects.select_related('notify_id').all()


def get_student_placement_status(student, schedule_notify_ids):
    """Return the PlacementStatus queryset for a student filtered by schedule."""
    return PlacementStatus.objects.select_related(
        'unique_id', 'notify_id',
    ).filter(
        Q(unique_id=student, notify_id__in=schedule_notify_ids)
    ).order_by('-timestamp')


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _split_name(stuname):
    """Split 'First Last' → ('First', 'Last'); single word → ('word', '')."""
    parts = stuname.split(' ', 1) if stuname else ['', '']
    first = parts[0]
    last = parts[1] if len(parts) > 1 else ''
    return first, last
