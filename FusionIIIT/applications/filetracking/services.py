import io
import zipfile
from dataclasses import dataclass, field
from typing import Any, Iterable, Optional

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile

from notification.views import file_tracking_notif

from .api.serializers import FileHeaderSerializer, FileSerializer, TrackingSerializer
from .models import File, Tracking
from .selectors import (
    build_file_enrichment_maps,
    get_archived_tracking,
    get_current_tracking,
    get_designation_obj_from_name,
    get_draft_files,
    get_extra_info_object_from_username,
    get_file_by_id,
    get_holds_designation_obj,
    get_inbox_tracking,
    get_outbox_tracking,
    get_tracking_for_file_id,
    get_user_object_from_username,
    get_user_designation_names,
    normalize_designation_name,
    resolve_branch_name,
)

FILETRACKING_MODULE = "filetracking"
MAX_UPLOAD_SIZE_KB = 10240
DEFAULT_PAGE_SIZE = 10
SESSION_CURRENT_DESIGNATION_KEY = "currentDesignationSelected"
SESSION_ALL_DESIGNATIONS_KEY = "allDesignations"


@dataclass
class FileCreateCommand:
    uploader_designation: str
    receiver: str
    receiver_designation: str
    src_module: str = ""
    file_extra_json: dict = field(default_factory=dict)
    uploader: Any = ""
    subject: str = ""
    description: str = ""
    src_object_id: str = ""
    attached_file: Any = None
    remarks: str = ""


@dataclass
class DraftCreateCommand:
    uploader: Any
    uploader_designation: str
    src_module: str = ""
    src_object_id: str = ""
    file_extra_json: dict = field(default_factory=dict)
    attached_file: Any = None


@dataclass
class ForwardFileCommand:
    file_id: int
    receiver: str
    receiver_designation: str
    file_extra_json: dict = field(default_factory=dict)
    remarks: str = ""
    file_attachment: Any = None
    mark_current_tracks_read: bool = False


def zip_attachments(attached_files: Iterable, zip_basename: str) -> Optional[ContentFile]:
    attached_files = list(attached_files or [])
    if not attached_files:
        return None

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_archive:
        for attached_file in attached_files:
            zip_archive.writestr(attached_file.name, attached_file.read())
    zip_buffer.seek(0)
    return ContentFile(zip_buffer.getvalue(), name=zip_basename)


def validate_upload_size(uploaded_file) -> bool:
    return uploaded_file is not None and uploaded_file.size / 1000 > MAX_UPLOAD_SIZE_KB


def create_file_record(command: FileCreateCommand) -> File:
    uploader_user_obj = get_user_object_from_username(command.uploader)
    uploader_extrainfo_obj = get_extra_info_object_from_username(command.uploader)
    uploader_designation_obj = get_designation_obj_from_name(command.uploader_designation)
    receiver_obj = get_user_object_from_username(command.receiver)
    receiver_designation_obj = get_designation_obj_from_name(command.receiver_designation)

    new_file = File.objects.create(
        uploader=uploader_extrainfo_obj,
        subject=command.subject,
        description=command.description,
        designation=uploader_designation_obj,
        src_module=command.src_module,
        src_object_id=command.src_object_id,
        file_extra_JSON=command.file_extra_json,
    )

    if command.attached_file is not None:
        new_file.upload_file.save(command.attached_file.name, command.attached_file, save=True)

    uploader_holdsdesignation_obj = get_holds_designation_obj(
        uploader_user_obj,
        uploader_designation_obj,
    )

    new_tracking = Tracking.objects.create(
        file_id=new_file,
        current_id=uploader_extrainfo_obj,
        current_design=uploader_holdsdesignation_obj,
        receiver_id=receiver_obj,
        receive_design=receiver_designation_obj,
        tracking_extra_JSON=command.file_extra_json,
        remarks=command.remarks,
    )

    if new_tracking is None:
        new_file.delete()
        raise ValidationError("Tracking model data is incorrect")

    return new_file


def create_draft_file_record(command: DraftCreateCommand) -> File:
    file_extra_json = command.file_extra_json or {}
    return File.objects.create(
        uploader=get_extra_info_object_from_username(command.uploader),
        designation=get_designation_obj_from_name(command.uploader_designation),
        src_module=command.src_module,
        src_object_id=command.src_object_id,
        file_extra_JSON=file_extra_json,
        upload_file=command.attached_file,
    )


def forward_file_record(command: ForwardFileCommand) -> Tracking:
    current_tracking = get_current_tracking(command.file_id)
    if current_tracking is None:
        raise ValidationError("forward data is incomplete")

    if command.mark_current_tracks_read:
        get_tracking_for_file_id(command.file_id).update(is_read=True)

    tracking_data = {
        "file_id": command.file_id,
        "current_id": current_tracking.receiver_id.extrainfo.id,
        "current_design": get_holds_designation_obj(
            current_tracking.receiver_id,
            current_tracking.receive_design,
        ).id,
        "receiver_id": get_user_object_from_username(command.receiver).id,
        "receive_design": get_designation_obj_from_name(command.receiver_designation).id,
        "tracking_extra_JSON": command.file_extra_json,
        "remarks": command.remarks,
    }
    if command.file_attachment is not None:
        tracking_data["upload_file"] = command.file_attachment

    tracking_entry = TrackingSerializer(data=tracking_data)
    if tracking_entry.is_valid():
        tracking_entry.save()
        return tracking_entry.instance
    if len(command.remarks) > 1000:
        raise ValidationError("Remarks are too long")
    raise ValidationError("forward data is incomplete")


def archive_file_record(file_id: int) -> bool:
    File.objects.filter(id=file_id).update(is_read=True)
    return True


def unarchive_file_record(file_id: int) -> bool:
    File.objects.filter(id=file_id).update(is_read=False)
    return True


def delete_file_record(file_id: int) -> bool:
    File.objects.filter(id=file_id).delete()
    return True


def notify_file_tracking(sender, recipient, title: str):
    file_tracking_notif(sender, recipient, title)


def serialize_file_detail(file_obj: File) -> dict:
    file_details = FileSerializer(file_obj).data
    enrichment_maps = build_file_enrichment_maps([file_obj])
    designation_obj = enrichment_maps.designations_by_id.get(file_obj.designation_id)
    file_details["branch"] = resolve_branch_name(file_obj, enrichment_maps)
    file_details["uploader_designation"] = designation_obj.name if designation_obj is not None else ""
    return file_details


def _serialize_file_list(file_list, latest_tracking_by_file_id=None):
    serialized = list(FileHeaderSerializer(file_list, many=True).data)
    enrichment_maps = build_file_enrichment_maps(file_list, latest_tracking_by_file_id=latest_tracking_by_file_id)
    return serialized, enrichment_maps


def serialize_inbox(username, designation, src_module: str) -> list:
    tracking_rows = list(get_inbox_tracking(username, designation, src_module))
    latest_tracking_by_file_id = {}
    file_list = []
    for tracking_row in tracking_rows:
        if tracking_row.file_id_id not in latest_tracking_by_file_id:
            latest_tracking_by_file_id[tracking_row.file_id_id] = tracking_row
            file_list.append(tracking_row.file_id)

    serialized, enrichment_maps = _serialize_file_list(file_list, latest_tracking_by_file_id)
    filtered_files = []
    normalized_username = str(username)
    for file_data, file_obj in zip(serialized, file_list):
        latest_tracking = latest_tracking_by_file_id.get(file_obj.id)
        designation_obj = enrichment_maps.designations_by_id.get(file_obj.designation_id)
        file_data["sent_by_user"] = latest_tracking.current_id.user.username if latest_tracking else ""
        file_data["sent_by_designation"] = (
            latest_tracking.current_design.designation.name if latest_tracking else ""
        )
        file_data["branch"] = resolve_branch_name(file_obj, enrichment_maps)
        file_data["uploader_designation"] = designation_obj.name if designation_obj else ""
        if latest_tracking and latest_tracking.receiver_id.username == normalized_username:
            filtered_files.append(file_data)
    return filtered_files


def serialize_outbox(username, designation, src_module: str) -> list:
    tracking_rows = list(get_outbox_tracking(username, designation, src_module))
    file_list = []
    latest_tracking_by_file_id = {}
    file_ids = []
    for tracking_row in tracking_rows:
        if tracking_row.file_id_id not in file_ids:
            file_ids.append(tracking_row.file_id_id)
            file_list.append(tracking_row.file_id)

    if file_ids:
        for latest_tracking in Tracking.objects.select_related(
            "receiver_id",
            "receive_design",
            "current_id__user",
            "current_design__designation",
        ).filter(file_id__in=file_ids).order_by("-receive_date"):
            latest_tracking_by_file_id.setdefault(latest_tracking.file_id_id, latest_tracking)

    serialized, enrichment_maps = _serialize_file_list(file_list, latest_tracking_by_file_id)
    filtered_files = []
    normalized_username = str(username)
    for file_data, file_obj in zip(serialized, file_list):
        latest_tracking = latest_tracking_by_file_id.get(file_obj.id)
        designation_obj = enrichment_maps.designations_by_id.get(file_obj.designation_id)
        file_data["branch"] = resolve_branch_name(file_obj, enrichment_maps)
        file_data["receiver"] = latest_tracking.receiver_id.username if latest_tracking else ""
        file_data["receiver_designation"] = latest_tracking.receive_design.name if latest_tracking else ""
        file_data["uploader_designation"] = designation_obj.name if designation_obj else ""
        if latest_tracking and latest_tracking.receiver_id.username != normalized_username:
            filtered_files.append(file_data)
    return filtered_files


def serialize_archived(username, designation, src_module: str) -> list:
    tracking_rows = list(get_archived_tracking(username, designation, src_module))
    latest_tracking_by_file_id = {}
    file_list = []
    for tracking_row in tracking_rows:
        if tracking_row.file_id_id not in latest_tracking_by_file_id:
            latest_tracking_by_file_id[tracking_row.file_id_id] = tracking_row
            file_list.append(tracking_row.file_id)

    serialized, enrichment_maps = _serialize_file_list(file_list, latest_tracking_by_file_id)
    for file_data, file_obj in zip(serialized, file_list):
        designation_obj = enrichment_maps.designations_by_id.get(file_obj.designation_id)
        file_data["branch"] = resolve_branch_name(file_obj, enrichment_maps)
        file_data["uploader_designation"] = designation_obj.name if designation_obj else ""
    return serialized


def serialize_drafts(username, designation, src_module: str) -> list:
    return FileHeaderSerializer(
        get_draft_files(username, designation, src_module),
        many=True,
    ).data


def serialize_history(file_id: int) -> list:
    return TrackingSerializer(get_tracking_for_file_id(file_id).order_by("-receive_date"), many=True).data


def get_current_file_owner(file_id: int):
    latest_tracking = get_current_tracking(file_id)
    return latest_tracking.receiver_id if latest_tracking is not None else None


def get_current_file_owner_designation(file_id: int):
    latest_tracking = get_current_tracking(file_id)
    return latest_tracking.receive_design if latest_tracking is not None else None


def get_last_file_sender(file_id: int):
    latest_tracking = get_current_tracking(file_id)
    return latest_tracking.current_id.user if latest_tracking is not None else None


def get_last_file_sender_designation(file_id: int):
    first_tracking = get_tracking_for_file_id(file_id).first()
    return first_tracking.current_design.designation if first_tracking is not None else None


def get_designations(username) -> list:
    return get_user_designation_names(username)


def build_create_file_command(
    uploader,
    uploader_designation,
    receiver,
    receiver_designation,
    subject,
    description,
    src_module,
    attached_file=None,
    remarks="",
    src_object_id="",
    file_extra_json=None,
):
    return FileCreateCommand(
        uploader=uploader,
        uploader_designation=normalize_designation_name(uploader_designation),
        receiver=receiver,
        receiver_designation=normalize_designation_name(receiver_designation),
        subject=subject,
        description=description,
        src_module=src_module,
        src_object_id=src_object_id,
        attached_file=attached_file,
        remarks=remarks,
        file_extra_json=file_extra_json or {},
    )
