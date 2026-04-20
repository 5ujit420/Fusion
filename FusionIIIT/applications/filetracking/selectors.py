from dataclasses import dataclass
from typing import Iterable, Optional

from django.contrib.auth.models import User

from applications.globals.models import DepartmentInfo, Designation, ExtraInfo, HoldsDesignation

from .models import File, Tracking


def normalize_username(username) -> str:
    if hasattr(username, "username"):
        return username.username
    return str(username)


def normalize_designation_name(designation) -> str:
    if hasattr(designation, "name"):
        return designation.name
    return str(designation)


def get_file_queryset():
    return File.objects.select_related("uploader__user", "uploader__department", "designation")


def get_tracking_queryset():
    return Tracking.objects.select_related(
        "file_id__uploader__user",
        "file_id__uploader__department",
        "file_id__designation",
        "current_id__user",
        "current_id__department",
        "current_design__user",
        "current_design__working",
        "current_design__designation",
        "receiver_id",
        "receive_design",
    )


def get_user_object_from_username(username) -> User:
    return User.objects.get(username=normalize_username(username))


def get_extra_info_object_from_username(username) -> ExtraInfo:
    return ExtraInfo.objects.select_related("user", "department").get(
        user=get_user_object_from_username(username)
    )


def get_extra_info_object_from_id(extra_info_id):
    return ExtraInfo.objects.select_related("user", "department").get(id=extra_info_id)


def get_designation_obj_from_name(designation) -> Designation:
    return Designation.objects.get(name=normalize_designation_name(designation))


def get_holds_designation_obj(username, designation) -> HoldsDesignation:
    user_object = get_user_object_from_username(username)
    designation_object = get_designation_obj_from_name(designation)
    return HoldsDesignation.objects.select_related("user", "working", "designation").get(
        user=user_object,
        designation=designation_object,
    )


def get_designations_for_user(username):
    user_object = get_user_object_from_username(username)
    return HoldsDesignation.objects.select_related("user", "working", "designation").filter(
        user=user_object
    )


def get_file_by_id(file_id: int) -> File:
    return get_file_queryset().get(id=file_id)


def get_tracking_for_file(file_obj: File):
    return get_tracking_queryset().filter(file_id=file_obj).order_by("receive_date")


def get_tracking_for_file_id(file_id: int):
    return get_tracking_queryset().filter(file_id=file_id).order_by("receive_date")


def get_current_tracking(file_id: int) -> Optional[Tracking]:
    return get_tracking_queryset().filter(file_id=file_id).order_by("-receive_date").first()


def get_last_recv_tracking_for_user(file_id: int, username, designation) -> Optional[Tracking]:
    return get_tracking_queryset().filter(
        file_id=file_id,
        receiver_id=get_user_object_from_username(username),
        receive_design=get_designation_obj_from_name(designation),
    ).order_by("-receive_date").first()


def get_last_forw_tracking_for_user(file_id: int, username, designation) -> Optional[Tracking]:
    return get_tracking_queryset().filter(
        file_id=file_id,
        current_id=get_extra_info_object_from_username(username),
        current_design=get_holds_designation_obj(username, designation),
    ).order_by("-forward_date").first()


def get_designation_suggestions(value: str):
    return Designation.objects.filter(name__startswith=value)


def get_user_suggestions(value: str):
    return User.objects.filter(username__startswith=value)


def get_inbox_tracking(username, designation, src_module: str):
    return get_tracking_queryset().filter(
        receiver_id=get_user_object_from_username(username),
        receive_design=get_designation_obj_from_name(designation),
        file_id__src_module=src_module,
        file_id__is_read=False,
    ).order_by("-receive_date")


def get_outbox_tracking(username, designation, src_module: str):
    return get_tracking_queryset().filter(
        current_id=get_extra_info_object_from_username(username),
        current_design=get_holds_designation_obj(username, designation),
        file_id__src_module=src_module,
        file_id__is_read=False,
    ).order_by("-receive_date")


def get_archived_tracking(username, designation, src_module: str):
    user_object = get_user_object_from_username(username)
    designation_object = get_designation_obj_from_name(designation)
    received_archived_tracking = get_tracking_queryset().filter(
        receiver_id=user_object,
        receive_design=designation_object,
        file_id__src_module=src_module,
        file_id__is_read=True,
    )
    sent_archived_tracking = get_tracking_queryset().filter(
        current_id=get_extra_info_object_from_username(username),
        current_design=get_holds_designation_obj(username, designation),
        file_id__src_module=src_module,
        file_id__is_read=True,
    ).order_by("-receive_date")
    return received_archived_tracking | sent_archived_tracking


def get_draft_files(username, designation, src_module: str):
    return get_file_queryset().filter(
        tracking__isnull=True,
        uploader=get_extra_info_object_from_username(username),
        designation=get_designation_obj_from_name(designation),
        src_module=src_module,
    ).order_by("-upload_date")


def get_user_designation_names(username) -> list:
    return [item.designation.name for item in get_designations_for_user(username)]


@dataclass
class FileEnrichmentMaps:
    latest_tracking_by_file_id: dict
    designations_by_id: dict
    extra_infos_by_id: dict
    departments_by_id: dict


def build_file_enrichment_maps(files: Iterable[File], latest_tracking_by_file_id=None) -> FileEnrichmentMaps:
    file_list = list(files)
    file_ids = [file_obj.id for file_obj in file_list]

    if latest_tracking_by_file_id is None:
        latest_tracking_by_file_id = {}
        for tracking in get_tracking_queryset().filter(file_id__in=file_ids).order_by("-receive_date"):
            latest_tracking_by_file_id.setdefault(tracking.file_id_id, tracking)

    designation_ids = {file_obj.designation_id for file_obj in file_list if file_obj.designation_id}
    uploader_ids = {file_obj.uploader_id for file_obj in file_list if file_obj.uploader_id}

    designations_by_id = Designation.objects.in_bulk(designation_ids)
    extra_infos_by_id = ExtraInfo.objects.select_related("user", "department").in_bulk(uploader_ids)

    department_ids = {
        getattr(designation_obj, "dept_if_not_basic_id", None)
        for designation_obj in designations_by_id.values()
        if getattr(designation_obj, "dept_if_not_basic_id", None) is not None
    }
    departments_by_id = DepartmentInfo.objects.in_bulk(department_ids)

    return FileEnrichmentMaps(
        latest_tracking_by_file_id=latest_tracking_by_file_id,
        designations_by_id=designations_by_id,
        extra_infos_by_id=extra_infos_by_id,
        departments_by_id=departments_by_id,
    )


def resolve_branch_name(file_obj: File, enrichment_maps: FileEnrichmentMaps) -> str:
    designation_obj = enrichment_maps.designations_by_id.get(file_obj.designation_id)
    department_id = getattr(designation_obj, "dept_if_not_basic_id", None) if designation_obj else None
    if department_id is not None:
        department_obj = enrichment_maps.departments_by_id.get(department_id)
        if department_obj is not None:
            return department_obj.name

    extra_info = enrichment_maps.extra_infos_by_id.get(file_obj.uploader_id)
    if extra_info is not None and extra_info.department is not None:
        return extra_info.department.name
    return "FTS"
