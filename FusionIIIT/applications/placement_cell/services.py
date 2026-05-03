"""
services.py — placement_cell
Business-logic layer.  All write operations and orchestration logic are here.

Tasks addressed:
    T06 / S13, S14, S19, S20 — extract schedule/invite/delete/save services
    T10 / S32, S12            — fix check_invitation_date logging
    T09 / S29, S30, S31, S33  — bare except → logger.exception
"""
import logging

from django.db.models import Q
from django.utils import timezone

from applications.academic_information.models import Student
from applications.globals.models import ExtraInfo
from notification.views import placement_cell_notif

from .models import (
    Achievement, ChairmanVisit, CompanyDetails, Course, Education, Experience,
    Has, NotifyStudent, Patent, PlacementRecord, PlacementSchedule,
    PlacementStatus, PlacementType, Project, Publication, Role,
    Skill, StudentPlacement, StudentRecord,
)

import datetime

logger = logging.getLogger('django.server')


# ---------------------------------------------------------------------------
# Schedule management  (S13, S20, T06)
# ---------------------------------------------------------------------------

def create_placement_schedule(company_name, placement_type, ctc, description,
                               placement_date, location, time, attached_file,
                               role_offered):
    """
    S13 / T06: Move schedule-creation logic out of the placement view.
    Performs get-or-create for CompanyDetails and Role, then creates
    NotifyStudent + PlacementSchedule.

    Returns (notify, schedule) tuple.
    """
    # Ensure company exists in lookup table
    CompanyDetails.objects.get_or_create(company_name=company_name)

    # Ensure role exists
    role_qs = Role.objects.filter(role=role_offered)
    if role_qs.exists():
        role = role_qs[0]
    else:
        role = Role.objects.create(role=role_offered)

    notify = NotifyStudent.objects.create(
        placement_type=placement_type,
        company_name=company_name,
        description=description,
        ctc=ctc,
        timestamp=timezone.now(),
    )

    schedule = PlacementSchedule.objects.create(
        notify_id=notify,
        title=company_name,
        description=description,
        placement_date=placement_date,
        attached_file=attached_file,
        role=role,
        location=location,
        time=time,
    )

    return notify, schedule


def save_schedule(placement_type, company_name, ctc, description, timestamp,
                  title, location, role, resume, schedule_at, date):
    """
    S20 / T06: Service used by placement_schedule_save view.
    Replaces bare except: with logger.exception.
    """
    role_obj = Role.objects.create(role=role)
    notify = NotifyStudent.objects.create(
        placement_type=placement_type,
        company_name=company_name,
        description=description,
        ctc=ctc,
        timestamp=timestamp,
    )
    schedule = PlacementSchedule.objects.create(
        notify_id=notify,
        title=company_name,
        description=description,
        placement_date=date,
        attached_file=resume,
        role=role_obj,
        location=location,
        time=schedule_at,
    )
    return notify, schedule


def delete_schedule(delete_sch_key):
    """
    S33 / T06: Delete a PlacementSchedule and its parent NotifyStudent.
    Raises Exception on failure so view can log/message appropriately.
    """
    placement_schedule = PlacementSchedule.objects.select_related('notify_id').get(
        pk=delete_sch_key
    )
    NotifyStudent.objects.get(pk=placement_schedule.notify_id.id).delete()
    placement_schedule.delete()


# ---------------------------------------------------------------------------
# Invite / debar  (S14, T06)
# ---------------------------------------------------------------------------

def send_invitations(company, rollno, programme, department, cpi, no_of_days, request_user):
    """
    S14 / T06: Bulk-create PlacementStatus rows for eligible students and
    send placement_cell_notif to each.
    """
    from applications.globals.models import DepartmentInfo

    notify = NotifyStudent.objects.get(
        company_name=company.company_name,
        placement_type=company.placement_type,
    )

    students = Student.objects.filter(
        Q(
            id__in=ExtraInfo.objects.filter(
                Q(
                    department__in=DepartmentInfo.objects.filter(Q(name__in=department)),
                    id__icontains=rollno,
                )
            ),
            programme=programme,
            cpi__gte=cpi,
        )
    ).exclude(
        id__in=PlacementStatus.objects.select_related('unique_id', 'notify_id').filter(
            notify_id=notify
        ).values_list('unique_id', flat=True)
    )

    PlacementStatus.objects.bulk_create([
        PlacementStatus(notify_id=notify, unique_id=student, no_of_days=no_of_days)
        for student in students
    ])

    for student in students:
        placement_cell_notif(request_user, student.id.user, "")


def set_debar_status(student_pk, debar_value):
    """
    S05 / T06: Set debar field on StudentPlacement.
    debar_value should be 'DEBAR' or 'NOT DEBAR'.
    """
    sr = StudentPlacement.objects.get(Q(pk=student_pk))
    sr.debar = debar_value
    sr.save()


# ---------------------------------------------------------------------------
# Placement record CRUD  (S10, S19, T06)
# ---------------------------------------------------------------------------

def create_placement_record(placement_type, rollno, ctc, year, name,
                             test_type='', test_score=0):
    """
    S10 / S19 / T06: Centralised PlacementRecord + StudentRecord creation,
    replacing the 3× repeated blocks in manage_records.
    """
    placementr = PlacementRecord.objects.create(
        year=year,
        name=name,
        placement_type=placement_type,
        ctc=ctc if ctc else 0,
        test_type=test_type,
        test_score=test_score,
    )
    studentr = StudentRecord.objects.create(
        record_id=placementr,
        unique_id=Student.objects.get(
            Q(id=ExtraInfo.objects.get(Q(id=rollno)))
        ),
    )
    return placementr, studentr


def delete_placement_record_by_student_record(record_id):
    """
    S19 / T06: Delete StudentRecord + parent PlacementRecord by StudentRecord PK.
    """
    student_record = StudentRecord.objects.get(pk=record_id)
    PlacementRecord.objects.get(id=student_record.record_id.id).delete()
    student_record.delete()


def delete_placement_record_by_placement_id(record_id):
    """Delete a PlacementRecord directly by its PK (used by delete_placement_record view)."""
    PlacementRecord.objects.filter(id=record_id).delete()


def save_placement_record(placement_type, student_name, ctc, year,
                          test_type='', test_score=0):
    """S31 / T06: Create PlacementRecord only (for placement_record_save view)."""
    return PlacementRecord.objects.create(
        placement_type=placement_type,
        name=student_name,
        ctc=ctc,
        year=year,
        test_type=test_type,
        test_score=test_score,
    )


def save_chairman_visit(company_name, location, visiting_date, description, timestamp):
    """S30 / T06: Create ChairmanVisit (for placement_visit_save view)."""
    return ChairmanVisit.objects.create(
        company_name=company_name,
        location=location,
        visiting_date=visiting_date,
        description=description,
        timestamp=timestamp,
    )


# ---------------------------------------------------------------------------
# Resume section services  (S03, S17, T06)
# ---------------------------------------------------------------------------

def add_education(student, institute, degree, grade, stream, sdate, edate):
    return Education.objects.create(
        unique_id=student, degree=degree, grade=grade,
        institute=institute, stream=stream, sdate=sdate, edate=edate,
    )


def add_skill(student, skill_name, skill_rating):
    skill_obj = Skill.objects.get(skill=skill_name)
    return Has.objects.create(
        unique_id=student, skill_id=skill_obj, skill_rating=skill_rating,
    )


def add_achievement(student, achievement, achievement_type, description,
                    issuer, date_earned):
    return Achievement.objects.create(
        unique_id=student, achievement=achievement,
        achievement_type=achievement_type, description=description,
        issuer=issuer, date_earned=date_earned,
    )


def add_publication(student, publication_title, description, publisher, publication_date):
    return Publication.objects.create(
        unique_id=student, publication_title=publication_title,
        publisher=publisher, description=description,
        publication_date=publication_date,
    )


def add_patent(student, patent_name, description, patent_office, patent_date):
    return Patent.objects.create(
        unique_id=student, patent_name=patent_name,
        patent_office=patent_office, description=description,
        patent_date=patent_date,
    )


def add_course(student, course_name, description, license_no, sdate, edate):
    return Course.objects.create(
        unique_id=student, course_name=course_name, license_no=license_no,
        description=description, sdate=sdate, edate=edate,
    )


def add_project(student, project_name, project_status, summary,
                project_link, sdate, edate):
    return Project.objects.create(
        unique_id=student, summary=summary, project_name=project_name,
        project_status=project_status, project_link=project_link,
        sdate=sdate, edate=edate,
    )


def add_experience(student, title, status, company, location,
                   description, sdate, edate):
    return Experience.objects.create(
        unique_id=student, title=title, company=company, location=location,
        status=status, description=description, sdate=sdate, edate=edate,
    )


# ---------------------------------------------------------------------------
# Invitation date check  (S12, S32, T10)
# ---------------------------------------------------------------------------

def check_invitation_date(placementstatus):
    """
    S12 / S32 / T10: Mark PENDING invitations whose response window has
    closed as IGNORE.  Moved from views.py; print() replaced with
    logger.exception so errors surface in the log.
    """
    try:
        for ps in placementstatus:
            if ps.invitation == 'PENDING':
                dt = ps.timestamp + datetime.timedelta(days=ps.no_of_days)
                if dt < datetime.datetime.now(tz=dt.tzinfo):
                    ps.invitation = 'IGNORE'
                    ps.save()
    except Exception:
        logger.exception('check_invitation_date: failed to update PlacementStatus')
