import datetime

from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone

from applications.academic_information.models import Student
from applications.globals.models import ExtraInfo

from .models import (
    Achievement,
    ChairmanVisit,
    CompanyDetails,
    Course,
    Education,
    Experience,
    Has,
    NotifyStudent,
    Patent,
    PlacementRecord,
    PlacementSchedule,
    PlacementStatus,
    Project,
    Publication,
    Role,
    Skill,
    StudentRecord,
)
from . import selectors


def update_invitation_response(status_id, invitation):
    return PlacementStatus.objects.select_related("unique_id", "notify_id").filter(
        pk=status_id
    ).update(invitation=invitation, timestamp=timezone.now())


def create_education(student, cleaned_data):
    return Education.objects.create(unique_id=student, **cleaned_data)


def update_profile(user, payload):
    extrainfo_obj = ExtraInfo.objects.get(user=user)
    extrainfo_obj.about_me = payload["about_me"]
    extrainfo_obj.age = payload["age"]
    extrainfo_obj.address = payload["address"]
    extrainfo_obj.phone_no = payload["contact"]
    extrainfo_obj.profile_picture = payload["profile_picture"]
    extrainfo_obj.save()
    return extrainfo_obj


def create_skill_assignment(student, skill_name, skill_rating):
    skill = Skill.objects.get(skill=skill_name)
    return Has.objects.create(unique_id=student, skill_id=skill, skill_rating=skill_rating)


def create_skill_assignment_from_validated_data(validated_data):
    skill_payload = validated_data.pop("skill_id")
    skill, _ = Skill.objects.get_or_create(**skill_payload)
    if Has.objects.filter(skill_id=skill, unique_id=validated_data["unique_id"]).exists():
        raise ValueError("This skill is already present")
    return Has.objects.create(skill_id=skill, **validated_data)


def create_achievement(student, cleaned_data):
    return Achievement.objects.create(unique_id=student, **cleaned_data)


def create_publication(student, cleaned_data):
    return Publication.objects.create(unique_id=student, **cleaned_data)


def create_patent(student, cleaned_data):
    return Patent.objects.create(unique_id=student, **cleaned_data)


def create_course(student, cleaned_data):
    return Course.objects.create(unique_id=student, **cleaned_data)


def create_project(student, cleaned_data):
    return Project.objects.create(unique_id=student, **cleaned_data)


def create_experience(student, cleaned_data):
    return Experience.objects.create(unique_id=student, **cleaned_data)


def delete_student_related_record(model_class, record_id):
    record = model_class.objects.get(pk=record_id)
    record.delete()
    return record


@transaction.atomic
def delete_schedule(schedule_id):
    placement_schedule = PlacementSchedule.objects.select_related("notify_id").get(pk=schedule_id)
    placement_schedule.notify_id.delete()
    return placement_schedule


@transaction.atomic
def create_schedule(cleaned_data, role_name):
    company_name = cleaned_data["company_name"]
    CompanyDetails.objects.get_or_create(company_name=company_name)
    role, _ = Role.objects.get_or_create(role=role_name)
    notify = NotifyStudent.objects.create(
        placement_type=cleaned_data["placement_type"],
        company_name=company_name,
        description=cleaned_data["description"],
        ctc=cleaned_data["ctc"],
    )
    schedule = PlacementSchedule.objects.create(
        notify_id=notify,
        title=company_name,
        description=cleaned_data["description"],
        placement_date=cleaned_data["placement_date"],
        attached_file=cleaned_data["attached_file"],
        role=role,
        location=cleaned_data["location"],
        time=cleaned_data["time"],
    )
    return schedule


@transaction.atomic
def create_schedule_from_payload(cleaned_data, role_name):
    role = Role.objects.create(role=role_name)
    notify = NotifyStudent.objects.create(
        placement_type=cleaned_data["placement_type"],
        company_name=cleaned_data["company_name"],
        description=cleaned_data.get("description", ""),
        ctc=cleaned_data["ctc"],
    )
    schedule = PlacementSchedule.objects.create(
        notify_id=notify,
        title=cleaned_data.get("title") or cleaned_data["company_name"],
        description=cleaned_data.get("description", ""),
        placement_date=cleaned_data["placement_date"],
        attached_file=cleaned_data.get("attached_file"),
        role=role,
        location=cleaned_data["location"],
        time=cleaned_data["time"],
        schedule_at=cleaned_data.get("schedule_at"),
    )
    return schedule


def create_placement_record(cleaned_data):
    return PlacementRecord.objects.create(**cleaned_data)


def create_chairman_visit(cleaned_data):
    return ChairmanVisit.objects.create(
        company_name=cleaned_data["company_name"],
        location=cleaned_data["location"],
        visiting_date=cleaned_data["visiting_date"],
        description=cleaned_data["description"],
    )


@transaction.atomic
def delete_placement_statistics_record(record_id):
    student_record = StudentRecord.objects.get(pk=record_id)
    student_record.record_id.delete()
    return student_record


def build_cv_render_context(request_user, username, checks, roll_strategy):
    user = get_object_or_404(User, username=username)
    profile = get_object_or_404(ExtraInfo, user=user)
    student = get_object_or_404(Student, id=profile.id)
    resume_data = selectors.get_student_resume_data(student, checks["reference_list"])
    referencecheck = "1" if resume_data["reference"].exists() else "0"

    if roll_strategy == "batch":
        student_info = get_object_or_404(Student, Q(id=user.username))
        batch = student_info.batch
        now = datetime.datetime.now()
        if now.year - batch <= 4:
            roll = now.year - batch
        else:
            roll = 4
    else:
        now = datetime.datetime.now()
        if int(str(profile.id)[:2]) == 20:
            if now.month > 4:
                roll = 1 + now.year - int(str(profile.id)[:4])
            else:
                roll = now.year - int(str(profile.id)[:4])
        else:
            if now.month > 4:
                roll = 1 + now.year - int("20" + str(profile.id)[0:2])
            else:
                roll = now.year - int("20" + str(profile.id)[0:2])

    context = {
        "pagesize": "A4",
        "user": user,
        "references": resume_data["reference"],
        "profile": profile,
        "projects": resume_data["project"],
        "skills": resume_data["skills"],
        "educations": resume_data["education"],
        "courses": resume_data["course"],
        "experiences": resume_data["experience"],
        "referencecheck": referencecheck,
        "achievements": resume_data["achievement"],
        "extracurriculars": resume_data["extracurricular"],
        "publications": resume_data["publication"],
        "patents": resume_data["patent"],
        "roll": roll,
        "achievementcheck": checks["achievementcheck"],
        "extracurricularcheck": checks["extracurricularcheck"],
        "educationcheck": checks["educationcheck"],
        "publicationcheck": checks["publicationcheck"],
        "patentcheck": checks["patentcheck"],
        "conferencecheck": checks["conferencecheck"],
        "conferences": resume_data["conference"],
        "internshipcheck": checks["internshipcheck"],
        "projectcheck": checks["projectcheck"],
        "coursecheck": checks["coursecheck"],
        "skillcheck": checks["skillcheck"],
        "today": datetime.date.today(),
    }
    return context
