# selectors.py
# T-03: Centralises all read-side ORM queries (CS-15, CS-22, CS-03, CS-19).
# T-04: is_* helpers replace Python-loop membership tests (CS-28, CS-22).
# T-22: All role checks use .exists() — no full-table Python iteration.
# T-20: get_report_by_role replaces GenerateReportView inline logic (CS-02, CS-10).
# T-17: search_complaints implements stub SearchComplaintView (CS-34).

import logging

from django.db import models as db_models

from applications.globals.models import ExtraInfo

from .models import (
    Caretaker,
    Complaint_Admin,
    ServiceAuthority,
    ServiceProvider,
    StudentComplain,
    Warden,
    Workers,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# ExtraInfo helpers
# ---------------------------------------------------------------------------

def get_extra_info_by_user(user):
    """Return ExtraInfo for the given auth user (with select_related)."""
    return (
        ExtraInfo.objects
        .select_related('user', 'department')
        .filter(user=user)
        .first()
    )


# ---------------------------------------------------------------------------
# Role checks  (T-04, T-22 — replace Python loops with indexed DB lookups)
# ---------------------------------------------------------------------------

def is_complaint_admin(extra_info):
    return Complaint_Admin.objects.filter(sup_id=extra_info).exists()


def is_service_provider(extra_info):
    return ServiceProvider.objects.filter(ser_pro_id=extra_info).exists()


def is_caretaker(extra_info):
    return Caretaker.objects.filter(staff_id=extra_info).exists()


def is_warden(extra_info):
    return Warden.objects.filter(staff_id=extra_info).exists()


# ---------------------------------------------------------------------------
# Complaint queries  (T-03, T-05, T-15)
# ---------------------------------------------------------------------------

def get_complaints_by_complainer(extra_info):
    """Return complaints made by the given ExtraInfo, newest first."""
    return StudentComplain.objects.filter(complainer=extra_info).order_by('-id')


def get_complaints_by_area(area):
    """Return complaints for a location/area, newest first."""
    return StudentComplain.objects.filter(location=area).order_by('-id')


def get_complaints_by_type_and_status(complaint_type, complaint_status=None):
    """Return complaints filtered by type and optionally status."""
    qs = StudentComplain.objects.filter(complaint_type=complaint_type)
    if complaint_status is not None:
        qs = qs.filter(status=complaint_status)
    return qs.order_by('-id')


def get_complaint_by_id(complaint_id):
    """Fetch a single complaint with complainer select_related."""
    return StudentComplain.objects.select_related('complainer').get(id=complaint_id)


def get_complaint_detail_by_id(complaint_id):
    """Fetch complaint with full complainer chain for detail views. (CS-29 fix)"""
    return StudentComplain.objects.select_related(
        'complainer', 'complainer__user', 'complainer__department'
    ).get(id=complaint_id)


def get_all_complaints():
    return StudentComplain.objects.all()


def get_service_provider_by_type(complaint_type):
    """Return first ServiceProvider for a complaint type."""
    return ServiceProvider.objects.filter(type=complaint_type).first()


def get_service_provider_extra_info(service_provider):
    """Return the ExtraInfo linked to a ServiceProvider (CS-21)."""
    return service_provider.ser_pro_id


# ---------------------------------------------------------------------------
# Report query (T-20 — replaces GenerateReportView inline logic)
# ---------------------------------------------------------------------------

def get_report_by_role(user):
    """
    Return a QuerySet of complaints scoped to the user's role,
    or None if the user has no reporting role (caller should return 403).
    """
    extra_info = get_extra_info_by_user(user)

    # Complaint admin sees everything
    try:
        Complaint_Admin.objects.get(sup_id=extra_info)
        return get_all_complaints()
    except Complaint_Admin.DoesNotExist:
        pass

    # Service provider sees their type (assigned / resolved / declined)
    try:
        sp = ServiceProvider.objects.get(ser_pro_id=extra_info)
        return StudentComplain.objects.filter(
            complaint_type=sp.type, status__in=[1, 2, 3]
        )
    except ServiceProvider.DoesNotExist:
        pass

    # Caretaker sees their area
    try:
        caretaker = Caretaker.objects.get(staff_id=extra_info)
        return StudentComplain.objects.filter(location=caretaker.area)
    except Caretaker.DoesNotExist:
        pass

    # Warden sees their area
    try:
        warden = Warden.objects.get(staff_id=extra_info)
        return StudentComplain.objects.filter(location=warden.area)
    except Warden.DoesNotExist:
        pass

    return None  # not authorised


# ---------------------------------------------------------------------------
# Search (T-17 — implements stub SearchComplaintView)
# ---------------------------------------------------------------------------

def search_complaints(query):
    """Full-text search across details, location, and complaint_type."""
    if not query:
        return StudentComplain.objects.none()
    return StudentComplain.objects.filter(
        db_models.Q(details__icontains=query)
        | db_models.Q(location__icontains=query)
        | db_models.Q(complaint_type__icontains=query)
    ).order_by('-id')
