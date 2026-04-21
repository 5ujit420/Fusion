import datetime

from django.contrib.auth.models import User
from django.db.models import Count, Q

from applications.academic_information.models import Student
from applications.globals.models import ExtraInfo, HoldsDesignation

from .models import (
    Achievement,
    Conference,
    Course,
    Education,
    Experience,
    Extracurricular,
    Has,
    NotifyStudent,
    Patent,
    PlacementRecord,
    PlacementSchedule,
    PlacementStatus,
    Project,
    Publication,
    Reference,
    StudentRecord,
)


ROLE_CHAIRMAN = "placement chairman"
ROLE_OFFICER = "placement officer"
ROLE_STUDENT = "student"

PLACEMENT_TYPE_PLACEMENT = "PLACEMENT"
PLACEMENT_TYPE_PBI = "PBI"
PLACEMENT_TYPE_HIGHER_STUDIES = "HIGHER STUDIES"


def get_role_assignments(user):
    return {
        "current1": HoldsDesignation.objects.filter(
            Q(working=user, designation__name=ROLE_CHAIRMAN)
        ),
        "current2": HoldsDesignation.objects.filter(
            Q(working=user, designation__name=ROLE_OFFICER)
        ),
        "current": HoldsDesignation.objects.filter(
            Q(working=user, designation__name=ROLE_STUDENT)
        ),
    }


def search_invitation_statuses(placement_type, student_name="", ctc=0, company_name="", rollno=""):
    return PlacementStatus.objects.select_related("unique_id", "notify_id").filter(
        Q(
            notify_id__in=NotifyStudent.objects.filter(
                Q(
                    placement_type=placement_type,
                    company_name__icontains=company_name,
                    ctc__gte=ctc,
                )
            ),
            unique_id__in=Student.objects.filter(
                Q(
                    id__in=ExtraInfo.objects.filter(
                        Q(
                            user__in=User.objects.filter(
                                Q(first_name__icontains=student_name)
                            ),
                            id__icontains=rollno,
                        )
                    )
                )
            ),
        )
    )


def search_invitation_statuses_ordered(
    placement_type,
    student_name="",
    ctc=0,
    company_name="",
    rollno="",
):
    return search_invitation_statuses(
        placement_type=placement_type,
        student_name=student_name,
        ctc=ctc,
        company_name=company_name,
        rollno=rollno,
    ).order_by("id")


def list_active_schedule_ids():
    return PlacementSchedule.objects.select_related("notify_id").filter(
        Q(placement_date__gte=datetime.date.today())
    ).values_list("notify_id", flat=True)


def list_student_active_statuses(student):
    active_schedule_ids = list_active_schedule_ids()
    return PlacementStatus.objects.select_related("unique_id", "notify_id").filter(
        Q(unique_id=student, notify_id__in=active_schedule_ids)
    ).order_by("-timestamp")


def get_statistics_base_data():
    student_records = StudentRecord.objects.select_related(
        "unique_id",
        "record_id",
        "unique_id__id__department",
    ).all()
    years = (
        PlacementRecord.objects.filter(~Q(placement_type=PLACEMENT_TYPE_HIGHER_STUDIES))
        .values("year")
        .annotate(Count("year"))
    )
    records = (
        PlacementRecord.objects.values("name", "year", "ctc", "placement_type")
        .annotate(Count("name"), Count("year"), Count("placement_type"), Count("ctc"))
    )
    all_records = PlacementRecord.objects.all()
    return student_records, years, records, all_records


def build_statistics_summary():
    student_records, years, records, all_records = get_statistics_base_data()
    tcse = {}
    tece = {}
    tme = {}
    tadd = {}

    for record in records:
        record["name__count"] = 0
        record["year__count"] = 0
        record["placement_type__count"] = 0

    for year_row in years:
        year = year_row["year"]
        tcse[year] = 0
        tece[year] = 0
        tme[year] = 0

        for record in records:
            if record["year"] != year or record["placement_type"] == PLACEMENT_TYPE_HIGHER_STUDIES:
                continue

            for student_record in student_records:
                if (
                    student_record.record_id.name == record["name"]
                    and student_record.record_id.year == record["year"]
                ):
                    department_name = student_record.unique_id.id.department.name
                    if department_name == "CSE":
                        tcse[year] += 1
                        record["name__count"] += 1
                    if department_name == "ECE":
                        tece[year] += 1
                        record["year__count"] += 1
                    if department_name == "ME":
                        tme[year] += 1
                        record["placement_type__count"] += 1

        tadd[year] = tcse[year] + tece[year] + tme[year]
        year_row["year__count"] = [tadd[year], tcse[year], tece[year], tme[year]]

    return years, records, all_records


def get_student_resume_data(student, reference_list):
    return {
        "skills": Has.objects.select_related("skill_id", "unique_id").filter(Q(unique_id=student)),
        "education": Education.objects.select_related("unique_id").filter(Q(unique_id=student)),
        "reference": Reference.objects.filter(id__in=reference_list),
        "course": Course.objects.select_related("unique_id").filter(Q(unique_id=student)),
        "experience": Experience.objects.select_related("unique_id").filter(Q(unique_id=student)),
        "project": Project.objects.select_related("unique_id").filter(Q(unique_id=student)),
        "achievement": Achievement.objects.select_related("unique_id").filter(Q(unique_id=student)),
        "extracurricular": Extracurricular.objects.select_related("unique_id").filter(Q(unique_id=student)),
        "conference": Conference.objects.select_related("unique_id").filter(Q(unique_id=student)),
        "publication": Publication.objects.select_related("unique_id").filter(Q(unique_id=student)),
        "patent": Patent.objects.select_related("unique_id").filter(Q(unique_id=student)),
    }
