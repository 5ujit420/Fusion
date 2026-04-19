from typing import Iterable, Optional, Sequence

from applications.filetracking.models import File
from applications.globals.models import ExtraInfo, HoldsDesignation, User

from .models import (
    Caretaker,
    Complaint_Admin,
    ServiceAuthority,
    ServiceProvider,
    StudentComplain,
    Warden,
    Workers,
)


COMPLAINT_RELATED_FIELDS = ("complainer", "complainer__user", "complainer__department")
CARETAKER_RELATED_FIELDS = ("staff_id", "staff_id__user", "staff_id__department")


def get_current_extrainfo(user):
    return ExtraInfo.objects.select_related("user", "department").filter(user=user).first()


def get_user_role_flags(extrainfo):
    if extrainfo is None:
        return {
            "is_service_provider": False,
            "is_complaint_admin": False,
            "is_caretaker": False,
            "is_warden": False,
        }

    return {
        "is_service_provider": ServiceProvider.objects.filter(ser_pro_id=extrainfo).exists(),
        "is_complaint_admin": Complaint_Admin.objects.filter(sup_id=extrainfo).exists(),
        "is_caretaker": Caretaker.objects.filter(staff_id=extrainfo).exists(),
        "is_warden": Warden.objects.filter(staff_id=extrainfo).exists(),
    }


def list_user_complaints(extrainfo):
    return StudentComplain.objects.filter(complainer=extrainfo).order_by("-id")


def list_complaints_for_location(location):
    return StudentComplain.objects.filter(location=location).order_by("-id")


def list_complaints_for_type(complaint_type, status_value=None):
    queryset = StudentComplain.objects.filter(complaint_type=complaint_type)
    if status_value is not None:
        queryset = queryset.filter(status=status_value)
    return queryset.order_by("-id")


def list_pending_complaints_by_area(area):
    return StudentComplain.objects.filter(location=area, status=0)


def list_all_complaints():
    return StudentComplain.objects.all()


def get_complaint(complaint_id, related_fields: Sequence[str] = ()):
    queryset = StudentComplain.objects
    if related_fields:
        queryset = queryset.select_related(*related_fields)
    return queryset.get(id=complaint_id)


def get_complaint_or_none(complaint_id, related_fields: Sequence[str] = ()):
    queryset = StudentComplain.objects
    if related_fields:
        queryset = queryset.select_related(*related_fields)
    return queryset.filter(id=complaint_id).first()


def update_complaint(complaint_id, **fields):
    return StudentComplain.objects.filter(id=complaint_id).update(**fields)


def get_caretaker_for_user(extrainfo):
    return Caretaker.objects.select_related("staff_id").get(staff_id=extrainfo)


def get_service_provider_for_user(extrainfo):
    return ServiceProvider.objects.select_related("ser_pro_id").get(ser_pro_id=extrainfo)


def get_warden_for_user(extrainfo):
    return Warden.objects.select_related("staff_id").get(staff_id=extrainfo)


def get_caretaker_by_area(area):
    return Caretaker.objects.filter(area=area).first()


def get_all_caretakers_by_area(area):
    return Caretaker.objects.filter(area=area).order_by("-id")


def get_caretaker_by_id(caretaker_id):
    return Caretaker.objects.select_related(*CARETAKER_RELATED_FIELDS).get(id=caretaker_id)


def get_worker_by_id(work_id):
    return Workers.objects.get(id=work_id)


def count_worker_complaints(worker):
    return StudentComplain.objects.filter(worker_id=worker).count()


def list_holds_designations(designation_name):
    return HoldsDesignation.objects.select_related("user", "working", "designation").filter(
        designation__name=designation_name
    )


def list_distinct_holds_designations(designation_name):
    return list_holds_designations(designation_name).distinct("user")


def get_single_designation_holder(designation_name):
    return list_holds_designations(designation_name).get()


def list_service_providers_by_type(complaint_type):
    return ServiceProvider.objects.select_related("ser_pro_id", "ser_pro_id__user").filter(type=complaint_type)


def list_designation_holders_for_user_id(user_id):
    return HoldsDesignation.objects.select_related("user", "designation").filter(user=user_id).distinct("user_id")


def list_users_by_ids(user_ids: Iterable[int]):
    return User.objects.filter(id__in=list(user_ids))


def list_files_for_complaint(complaint_id):
    return File.objects.filter(src_object_id=complaint_id)


def get_complaint_admin_for_user(extrainfo):
    return Complaint_Admin.objects.get(sup_id=extrainfo)


def get_service_authority_for_user(extrainfo):
    return ServiceAuthority.objects.get(ser_pro_id=extrainfo)
