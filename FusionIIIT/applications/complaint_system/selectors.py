# selectors.py
# All database queries for the complaint_system module.
# Fixes: V-02, V-38

from django.shortcuts import get_object_or_404

from applications.globals.models import ExtraInfo, HoldsDesignation, User
from .models import (
    Caretaker, Warden, StudentComplain, ServiceProvider,
    Complaint_Admin, ServiceAuthority, Workers, SectionIncharge,
)


# ---------------------------------------------------------------------------
# ExtraInfo selectors
# ---------------------------------------------------------------------------

def get_extrainfo_by_user(user):
    """Return the ExtraInfo instance for the given User."""
    return ExtraInfo.objects.select_related('user', 'department').filter(user=user).first()


# ---------------------------------------------------------------------------
# Role-check selectors  (V-38 – replaces .all() + Python iteration)
# ---------------------------------------------------------------------------

def is_complaint_admin(extrainfo_id):
    return Complaint_Admin.objects.filter(sup_id_id=extrainfo_id).exists()


def is_service_provider(extrainfo_id):
    return ServiceProvider.objects.filter(ser_pro_id_id=extrainfo_id).exists()


def is_caretaker(extrainfo_id):
    return Caretaker.objects.filter(staff_id_id=extrainfo_id).exists()


def is_warden(extrainfo_id):
    return Warden.objects.filter(staff_id_id=extrainfo_id).exists()


# ---------------------------------------------------------------------------
# Complaint selectors
# ---------------------------------------------------------------------------

def get_complaints_by_complainer(extrainfo):
    """Return complaints filed by a specific user, newest first."""
    return StudentComplain.objects.filter(complainer=extrainfo).order_by('-id')


def get_complaints_by_location(location):
    return StudentComplain.objects.filter(location=location).order_by('-id')


def get_complaints_by_type_and_status(complaint_type, status):
    return StudentComplain.objects.filter(complaint_type=complaint_type, status=status).order_by('-id')


def get_complaint_by_id(complaint_id):
    """Return a single complaint or raise DoesNotExist."""
    return StudentComplain.objects.select_related(
        'complainer', 'complainer__user', 'complainer__department'
    ).get(id=complaint_id)


def get_complaint_by_id_basic(complaint_id):
    """Return a complaint without select_related, or raise DoesNotExist."""
    return StudentComplain.objects.get(id=complaint_id)


def get_complaint_detail_for_api(complaint_id):
    """Return a complaint with full select_related for detail views."""
    return StudentComplain.objects.select_related(
        'complainer', 'complainer__user', 'complainer__department'
    ).get(id=complaint_id)


def get_all_complaints():
    return StudentComplain.objects.all()


def get_pending_complaints_by_location(location):
    return StudentComplain.objects.filter(location=location, status=0)


def get_complaints_for_report_service_provider(complaint_type):
    return StudentComplain.objects.filter(complaint_type=complaint_type, status__in=[1, 2, 3])


def get_complaints_for_report_area(area):
    return StudentComplain.objects.filter(location=area)


def get_complaints_assigned_to_worker(worker):
    return StudentComplain.objects.filter(worker_id=worker).count()


# ---------------------------------------------------------------------------
# Caretaker selectors
# ---------------------------------------------------------------------------

def get_caretaker_by_staff_id(extrainfo_id):
    return Caretaker.objects.select_related('staff_id').get(staff_id=extrainfo_id)


def get_caretaker_by_area(area):
    return Caretaker.objects.filter(area=area).first()


def get_caretaker_by_id(caretaker_id):
    return Caretaker.objects.select_related(
        'staff_id', 'staff_id__user', 'staff_id__department'
    ).get(id=caretaker_id)


def get_caretakers_by_area(area):
    return Caretaker.objects.filter(area=area).order_by('-id')


def get_all_caretakers():
    return Caretaker.objects.all()


def get_caretaker_by_pk(pk):
    return Caretaker.objects.get(id=pk)


# ---------------------------------------------------------------------------
# Warden selectors
# ---------------------------------------------------------------------------

def get_warden_by_staff_id(extrainfo):
    return Warden.objects.get(staff_id=extrainfo)


# ---------------------------------------------------------------------------
# ServiceProvider selectors
# ---------------------------------------------------------------------------

def get_service_provider_by_extrainfo(extrainfo):
    return ServiceProvider.objects.select_related('ser_pro_id').get(ser_pro_id=extrainfo)


def get_service_providers_by_type(complaint_type):
    return ServiceProvider.objects.filter(type=complaint_type)


def get_all_service_providers():
    return ServiceProvider.objects.all()


def get_service_provider_by_pk(pk):
    return ServiceProvider.objects.get(id=pk)


# ---------------------------------------------------------------------------
# ServiceAuthority selectors
# ---------------------------------------------------------------------------

def get_service_authority_by_extrainfo(extrainfo):
    return ServiceAuthority.objects.get(ser_pro_id=extrainfo)


# ---------------------------------------------------------------------------
# Complaint_Admin selectors
# ---------------------------------------------------------------------------

def get_complaint_admin_by_extrainfo(extrainfo):
    return Complaint_Admin.objects.get(sup_id=extrainfo)


# ---------------------------------------------------------------------------
# Workers selectors
# ---------------------------------------------------------------------------

def get_worker_by_id(worker_id):
    return Workers.objects.get(id=worker_id)


def get_all_workers():
    return Workers.objects.all()


# ---------------------------------------------------------------------------
# HoldsDesignation selectors
# ---------------------------------------------------------------------------

def get_holds_designation_by_name(designation_name):
    """Return all HoldsDesignation entries for a designation name (distinct users)."""
    return HoldsDesignation.objects.select_related(
        'user', 'working', 'designation'
    ).filter(designation__name=designation_name).distinct('user')


def get_holds_designation_single(designation_name):
    """Return a single HoldsDesignation entry."""
    return HoldsDesignation.objects.select_related(
        'user', 'working', 'designation'
    ).get(designation__name=designation_name)


def get_holds_designations_for_user(user_id):
    return HoldsDesignation.objects.filter(user=user_id).distinct('user_id')


# ---------------------------------------------------------------------------
# User selectors
# ---------------------------------------------------------------------------

def get_user_by_id(user_id):
    return User.objects.get(id=user_id)


def get_user_by_username(username):
    return User.objects.get(username=username)


# ---------------------------------------------------------------------------
# File selectors  (for filetracking integration)
# ---------------------------------------------------------------------------

def get_files_for_complaint(complaint_id):
    """Import here to avoid circular imports with filetracking module."""
    from applications.filetracking.models import File
    return File.objects.filter(src_object_id=complaint_id)
