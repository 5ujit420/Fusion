from typing import Any

from django.core.exceptions import ValidationError

from applications.filetracking.selectors import (
    get_designation_obj_from_name as selector_get_designation_obj_from_name,
    get_extra_info_object_from_id as selector_get_extra_info_object_from_id,
    get_extra_info_object_from_username as selector_get_extra_info_object_from_username,
    get_file_by_id,
    get_holds_designation_obj as selector_get_holds_designation_obj,
    get_last_forw_tracking_for_user as selector_get_last_forw_tracking_for_user,
    get_last_recv_tracking_for_user as selector_get_last_recv_tracking_for_user,
    get_user_object_from_username as selector_get_user_object_from_username,
)
from applications.filetracking.services import (
    DraftCreateCommand,
    FileCreateCommand,
    ForwardFileCommand,
    archive_file_record,
    create_draft_file_record,
    create_file_record,
    delete_file_record,
    forward_file_record,
    get_current_file_owner as service_get_current_file_owner,
    get_current_file_owner_designation as service_get_current_file_owner_designation,
    get_designations as service_get_designations,
    get_last_file_sender as service_get_last_file_sender,
    get_last_file_sender_designation as service_get_last_file_sender_designation,
    serialize_archived,
    serialize_drafts,
    serialize_file_detail,
    serialize_history,
    serialize_inbox,
    serialize_outbox,
    unarchive_file_record,
)


def create_file(
    uploader_designation: str,
    receiver: str,
    receiver_designation: str,
    src_module: str = "",
    file_extra_JSON: dict = None,
    uploader: str = "",
    subject: str = "",
    description: str = "",
    src_object_id: str = "",
    attached_file: Any = None,
    remarks: str = "",
) -> int:
    new_file = create_file_record(
        FileCreateCommand(
            uploader_designation=uploader_designation,
            receiver=receiver,
            receiver_designation=receiver_designation,
            src_module=src_module,
            file_extra_json=file_extra_JSON or {},
            uploader=uploader,
            subject=subject,
            description=description,
            src_object_id=src_object_id,
            attached_file=attached_file,
            remarks=remarks,
        )
    )
    return new_file.id


def view_file(file_id: int) -> dict:
    return serialize_file_detail(get_file_by_id(file_id))


def delete_file(file_id: int) -> bool:
    return delete_file_record(file_id)


def view_inbox(username: str, designation: str, src_module: str) -> list:
    return serialize_inbox(username, designation, src_module)


def view_outbox(username: str, designation: str, src_module: str) -> list:
    return serialize_outbox(username, designation, src_module)


def view_archived(username: str, designation: str, src_module: str) -> dict:
    return serialize_archived(username, designation, src_module)


def archive_file(file_id: int) -> bool:
    return archive_file_record(file_id)


def unarchive_file(file_id: int) -> bool:
    return unarchive_file_record(file_id)


def create_draft(
    uploader: str,
    uploader_designation: str,
    src_module: str = "",
    src_object_id: str = "",
    file_extra_JSON: dict = None,
    attached_file: Any = None,
) -> int:
    return create_draft_file_record(
        DraftCreateCommand(
            uploader=uploader,
            uploader_designation=uploader_designation,
            src_module=src_module,
            src_object_id=src_object_id,
            file_extra_json=file_extra_JSON or {},
            attached_file=attached_file,
        )
    ).id


def view_drafts(username: str, designation: str, src_module: str) -> dict:
    return serialize_drafts(username, designation, src_module)


def forward_file(
    file_id: int,
    receiver: str,
    receiver_designation: str,
    file_extra_JSON: dict = None,
    remarks: str = "",
    file_attachment: Any = None,
) -> int:
    return forward_file_record(
        ForwardFileCommand(
            file_id=file_id,
            receiver=receiver,
            receiver_designation=receiver_designation,
            file_extra_json=file_extra_JSON or {},
            remarks=remarks,
            file_attachment=file_attachment,
        )
    ).id


def view_history(file_id: int) -> dict:
    return serialize_history(file_id)


def get_current_file_owner(file_id: int):
    return service_get_current_file_owner(file_id)


def get_current_file_owner_designation(file_id: int):
    return service_get_current_file_owner_designation(file_id)


def get_last_file_sender(file_id: int):
    return service_get_last_file_sender(file_id)


def get_last_file_sender_designation(file_id: int):
    return service_get_last_file_sender_designation(file_id)


def get_designations(username: str) -> list:
    return service_get_designations(username)


def get_user_object_from_username(username: str):
    return selector_get_user_object_from_username(username)


def get_ExtraInfo_object_from_username(username: str):
    return selector_get_extra_info_object_from_username(username)


def uniqueList(items: list) -> list:
    seen = set()
    unique_list = []
    for item in items:
        item_key = getattr(item, "id", item)
        if item_key not in seen:
            unique_list.append(item)
            seen.add(item_key)
    return unique_list


def add_uploader_department_to_files_list(files: list) -> list:
    for file_data in files:
        uploader_extrainfo = file_data["uploader"]
        if uploader_extrainfo.department is None:
            file_data["uploader_department"] = "FTS"
        else:
            file_data["uploader_department"] = str(uploader_extrainfo.department).split(": ")[1]
    return files


def get_designation_obj_from_name(designation: str):
    return selector_get_designation_obj_from_name(designation)


def get_HoldsDesignation_obj(username: str, designation: str):
    return selector_get_holds_designation_obj(username, designation)


def get_last_recv_tracking_for_user(file_id: int, username: str, designation: str):
    tracking = selector_get_last_recv_tracking_for_user(file_id, username, designation)
    if tracking is None:
        raise ValidationError("Tracking not found")
    return tracking


def get_last_forw_tracking_for_user(file_id: int, username: str, designation: str):
    return selector_get_last_forw_tracking_for_user(file_id, username, designation)


def get_extra_info_object_from_id(id: int):
    return selector_get_extra_info_object_from_id(id)
