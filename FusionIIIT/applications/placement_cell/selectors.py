from django.db.models import Q
from applications.placement_cell.models import (
    PlacementRecord, ChairmanVisit, PlacementSchedule, StudentPlacement,
    PlacementStatus, Skill, Has, Education, Course, Experience, Project,
    Achievement, Publication, Patent, NotifyStudent, Role, CompanyDetails
)
from applications.globals.models import ExtraInfo, HoldsDesignation

def get_placement_records():
    return PlacementRecord.objects.all()

def get_chairman_visits():
    return ChairmanVisit.objects.all()

def get_placement_schedules():
    return PlacementSchedule.objects.all()

def get_student_records(user):
    return ExtraInfo.objects.filter(user=user).first()

def get_user_designations(user):
    return HoldsDesignation.objects.filter(working=user)

def get_placement_status(pk):
    return PlacementStatus.objects.filter(pk=pk).select_related('unique_id', 'notify_id')

def get_company_details(name):
    return CompanyDetails.objects.filter(company_name=name)

def get_role_by_name(role_name):
    return Role.objects.filter(role=role_name).first()

def get_skill_by_name(skill_name):
    return Skill.objects.filter(skill=skill_name).first()
