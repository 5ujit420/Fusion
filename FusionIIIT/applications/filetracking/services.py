# services.py
# All business logic for the filetracking module.
# Fixes: V-03, V-04, V-08, V-09, V-10, V-11, V-12, V-13, V-14, V-15, V-16,
#        V-18, V-19, V-23, V-24, V-30, V-32, V-34, V-35, V-37, V-38,
#        R-01, R-04, R-07, R-08, R-09

import io
import os
import logging
import zipfile

from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404          # V-32: top-level import
from django.utils.dateparse import parse_datetime
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

from applications.globals.models import Designation, HoldsDesignation, ExtraInfo
from notification.views import file_tracking_notif       # V-16: wrapped below

from .models import File, Tracking, MAX_FILE_SIZE_BYTES, DEFAULT_SRC_MODULE
from . import selectors

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Notification wrapper  (V-16)
# ---------------------------------------------------------------------------

def _send_notification(sender_user, receiver_user, title):
    """Thin wrapper for notification coupling. (V-16)"""
    file_tracking_notif(sender_user, receiver_user, title)


# ---------------------------------------------------------------------------
# Utilities  (R-03, R-07)
# ---------------------------------------------------------------------------

def get_designation_display_name(holds_designation_obj):
    """Extract the display name from a HoldsDesignation object."""
    return str(holds_designation_obj).split(" - ")[1]


def unique_list(items):
    """Return a list with unique elements preserving order. O(n)."""
    seen = set()
    result = []
    for item in items:
        if item not in seen:
            result.append(item)
            seen.add(item)
    return result


def add_uploader_department_to_files_list(files):
    """Add the department string to each file dict in-place."""
    for f in files:
        uploader_extrainfo = f['uploader']
        if uploader_extrainfo.department is None:
            f['uploader_department'] = 'FTS'
        else:
            f['uploader_department'] = str(uploader_extrainfo.department).split(': ')[1]
    return files


def validate_file_size(upload_file):
    """Raise ValidationError if file exceeds MAX_FILE_SIZE_BYTES."""
    if upload_file and upload_file.size > MAX_FILE_SIZE_BYTES:
        raise ValidationError("File should not be greater than 10MB")


def _resolve_sender_designation(design_id):
    """Resolve (Designation, HoldsDesignation) from a design_id.
    (R-07: unified designation resolution)"""
    hd = selectors.get_holds_designation_by_id(design_id)
    designation = selectors.get_designation_by_name(hd.designation.name)
    return designation, hd


# ---------------------------------------------------------------------------
# Session helpers  (R-04)
# ---------------------------------------------------------------------------

def get_session_designation(request):
    """Read designation from session and return (designation_name, hd_obj).
    (R-04: consolidated session pattern)"""
    from .models import DEFAULT_DESIGNATION
    designation_name = request.session.get('currentDesignationSelected', DEFAULT_DESIGNATION)
    hd_obj = selectors.get_holds_designation_obj(request.user, designation_name)
    return designation_name, hd_obj


def get_designation_redirect_url_from_session(request, path_slug):
    """Build redirect URL from session designation."""
    _, hd_obj = get_session_designation(request)
    return f'/filetracking/{path_slug}/{hd_obj.id}'


# ---------------------------------------------------------------------------
# Read-status helpers  (V-03, V-04, V-08, R-08)
# ---------------------------------------------------------------------------

def _set_file_read_status(file_id, is_read):
    """Set is_read on a file. (R-08: unified archive/unarchive)"""
    selectors.update_file_read_status(file_id, is_read)


def mark_file_as_read(file_id):
    """Mark file is_read=True. (V-03)"""
    _set_file_read_status(file_id, True)


def mark_tracking_as_read(file_or_id):
    """Mark all tracking entries for a file as read. (V-04)"""
    selectors.update_tracking_read_status(file_or_id, is_read=True)


def archive_file_and_tracking(file_id):
    """Archive a file and its tracking entries. (V-08)"""
    _set_file_read_status(file_id, True)
    selectors.update_tracking_read_status(file_id, is_read=True)


# ---------------------------------------------------------------------------
# Input validation  (V-23, V-24)
# ---------------------------------------------------------------------------

def _validate_compose_fields(title, description, design_id):
    """Validate compose form fields. (V-23)"""
    if not title or not title.strip():
        raise ValidationError("Title is required")
    if not design_id:
        raise ValidationError("Designation is required")


def _validate_send_fields(title, description, design_id, receiver, receive):
    """Validate send form fields. (V-24)"""
    _validate_compose_fields(title, description, design_id)
    if not receiver or not receiver.strip():
        raise ValidationError("Receiver username is required")
    if not receive or not receive.strip():
        raise ValidationError("Receiver designation is required")


# ---------------------------------------------------------------------------
# File creation  (V-19, R-07 — consolidated save/send)
# ---------------------------------------------------------------------------

def save_draft_file(uploader_user, title, description, design_id, upload_file, remarks=None):
    """
    Save a file as draft (no Tracking created, no notification sent).
    """
    _validate_compose_fields(title, description, design_id)     # V-23
    validate_file_size(upload_file)

    uploader = uploader_user.extrainfo
    designation, _ = _resolve_sender_designation(design_id)      # R-07

    extra_json = {
        'remarks': remarks if remarks is not None else '',
    }

    file_obj = selectors.create_file(                            # V-19
        uploader=uploader,
        description=description,
        subject=title,
        designation=designation,
        upload_file=upload_file,
        file_extra_JSON=extra_json,
    )
    return file_obj


def send_file(uploader_user, title, description, design_id, receiver_username,
              receiver_designation_name, upload_file, remarks=None):
    """
    Create a file and send it (create Tracking + notification).
    """
    _validate_send_fields(title, description, design_id, receiver_username, receiver_designation_name)  # V-24
    validate_file_size(upload_file)

    uploader = uploader_user.extrainfo
    designation, current_design = _resolve_sender_designation(design_id)  # R-07

    file_obj = selectors.create_file(                            # V-19
        uploader=uploader,
        description=description,
        subject=title,
        designation=designation,
        upload_file=upload_file,
    )

    current_id = uploader_user.extrainfo
    receiver_id = selectors.get_user_by_username(receiver_username)      # V-18
    receive_design = selectors.get_designation_by_name(receiver_designation_name)  # V-18

    selectors.create_tracking(                                   # V-19
        file_id=file_obj,
        current_id=current_id,
        current_design=current_design,
        receive_design=receive_design,
        receiver_id=receiver_id,
        remarks=remarks,
        upload_file=upload_file,
    )

    _send_notification(uploader_user, receiver_id, title)        # V-16
    return file_obj


# ---------------------------------------------------------------------------
# SDK-compatible file creation  (V-18, V-19)
# ---------------------------------------------------------------------------

def create_file_via_sdk(uploader, uploader_designation, receiver, receiver_designation,
                        subject="", description="", src_module=DEFAULT_SRC_MODULE,
                        src_object_id="", file_extra_JSON=None, attached_file=None):
    """Create a file + tracking entry (SDK create_file equivalent)."""
    if file_extra_JSON is None:
        file_extra_JSON = {}

    uploader_user_obj = selectors.get_user_by_username(uploader)         # V-18
    uploader_extrainfo_obj = selectors.get_extrainfo_by_username(uploader)
    uploader_designation_obj = selectors.get_designation_by_name(uploader_designation)
    receiver_obj = selectors.get_user_by_username(receiver)
    receiver_designation_obj = selectors.get_designation_by_name(receiver_designation)

    new_file = selectors.create_file(                                    # V-19
        uploader=uploader_extrainfo_obj,
        subject=subject,
        description=description,
        designation=uploader_designation_obj,
        src_module=src_module,
        src_object_id=src_object_id,
        file_extra_JSON=file_extra_JSON,
    )

    if attached_file is not None:
        new_file.upload_file.save(attached_file.name, attached_file, save=True)

    uploader_holdsdesignation_obj = selectors.get_holds_designation(
        uploader_user_obj, uploader_designation_obj
    )

    new_tracking = selectors.create_tracking(                            # V-19
        file_id=new_file,
        current_id=uploader_extrainfo_obj,
        current_design=uploader_holdsdesignation_obj,
        receiver_id=receiver_obj,
        receive_design=receiver_designation_obj,
        tracking_extra_JSON=file_extra_JSON,
        remarks=f"File with id:{str(new_file.id)} created by {uploader} and sent to {receiver}",
    )
    if new_tracking is None:
        new_file.delete()
        raise ValidationError('Tracking model data is incorrect')

    return new_file.id


def create_draft_via_sdk(uploader, uploader_designation, src_module=DEFAULT_SRC_MODULE,
                         src_object_id="", file_extra_JSON=None, attached_file=None):
    """Create a draft (no Tracking). SDK create_draft equivalent."""
    if file_extra_JSON is None:
        file_extra_JSON = {}

    uploader_extrainfo_obj = selectors.get_extrainfo_by_username(uploader)
    uploader_designation_obj = selectors.get_designation_by_name(uploader_designation)

    new_file = selectors.create_file(                                    # V-19
        uploader=uploader_extrainfo_obj,
        designation=uploader_designation_obj,
        src_module=src_module,
        src_object_id=src_object_id,
        file_extra_JSON=file_extra_JSON,
        upload_file=attached_file,
    )
    return new_file.id


# ---------------------------------------------------------------------------
# View file  (V-38: decoupled from serializers)
# ---------------------------------------------------------------------------

def view_file_details(file_id):
    """Return file details as a dict. (V-38: no serializer import)"""
    f = selectors.get_file_by_id(file_id)
    return {
        'id': f.id,
        'uploader': f.uploader_id,
        'designation': f.designation_id,
        'subject': f.subject,
        'description': f.description,
        'upload_date': str(f.upload_date) if f.upload_date else None,
        'upload_file': f.upload_file.url if f.upload_file else None,
        'is_read': f.is_read,
        'src_module': f.src_module,
        'src_object_id': f.src_object_id,
        'file_extra_JSON': f.file_extra_JSON,
    }


def delete_file(file_id):
    """Delete a file."""
    selectors.delete_file_by_id(file_id)                                 # V-19
    return True


def delete_file_with_auth(file_id, requesting_user):
    """Delete a file with ownership check."""
    file_obj = selectors.get_file_by_id(file_id)
    if file_obj.uploader.user != requesting_user:
        raise ValidationError("Not authorized to delete this file")
    file_obj.delete()
    return True


# ---------------------------------------------------------------------------
# File header serialization  (V-38: inline without serializer import)
# ---------------------------------------------------------------------------

def _serialize_file_header(file_obj):
    """Serialize a single File to a header dict (excludes upload_file, is_read)."""
    return {
        'id': file_obj.id,
        'uploader': file_obj.uploader_id,
        'designation': file_obj.designation_id,
        'subject': file_obj.subject,
        'description': file_obj.description,
        'upload_date': str(file_obj.upload_date) if file_obj.upload_date else None,
        'src_module': file_obj.src_module,
        'src_object_id': file_obj.src_object_id,
        'file_extra_JSON': file_obj.file_extra_JSON,
    }


def _serialize_file_headers(file_list):
    """Serialize a list of File objects to header dicts."""
    return [_serialize_file_header(f) for f in file_list]


def _serialize_tracking(tracking_obj):
    """Serialize a single Tracking to a dict."""
    return {
        'id': tracking_obj.id,
        'file_id': tracking_obj.file_id_id,
        'current_id': tracking_obj.current_id_id,
        'current_design': tracking_obj.current_design_id,
        'receiver_id': tracking_obj.receiver_id_id,
        'receive_design': tracking_obj.receive_design_id,
        'receive_date': str(tracking_obj.receive_date) if tracking_obj.receive_date else None,
        'forward_date': str(tracking_obj.forward_date) if tracking_obj.forward_date else None,
        'remarks': tracking_obj.remarks,
        'upload_file': tracking_obj.upload_file.url if tracking_obj.upload_file else None,
        'is_read': tracking_obj.is_read,
        'tracking_extra_JSON': tracking_obj.tracking_extra_JSON,
    }


# ---------------------------------------------------------------------------
# Inbox / Outbox  (V-38: decoupled from serializers)
# ---------------------------------------------------------------------------

def view_inbox(username, designation, src_module):
    """Return inbox files for a user+designation."""
    user_designation = selectors.get_designation_by_name(designation)
    recipient_object = selectors.get_user_by_username(username)
    received_files_tracking = selectors.get_tracking_by_receiver(
        recipient_object, user_designation, src_module, is_read=False
    )
    received_files = [tracking.file_id for tracking in received_files_tracking]
    received_files_unique = unique_list(received_files)
    received_files_serialized = _serialize_file_headers(received_files_unique)

    for f in received_files_serialized:
        sender = selectors.get_last_file_sender(f['id'])
        sender_des = selectors.get_last_file_sender_designation(f['id'])
        f['sent_by_user'] = sender.username if sender else ''
        f['sent_by_designation'] = sender_des.name if sender_des else ''

    return received_files_serialized


def view_outbox(username, designation, src_module):
    """Return outbox files for a user+designation."""
    user_designation = selectors.get_designation_by_name(designation)
    user_object = selectors.get_user_by_username(username)
    user_holds_designation = selectors.get_holds_designation(user_object, user_designation)
    sender_extrainfo = selectors.get_extrainfo_by_username(username)
    sent_files_tracking = selectors.get_tracking_by_sender(
        sender_extrainfo, user_holds_designation, src_module, is_read=False
    )
    sent_files = [tracking.file_id for tracking in sent_files_tracking]
    sent_files_unique = unique_list(sent_files)
    return _serialize_file_headers(sent_files_unique)


# ---------------------------------------------------------------------------
# Enrichment functions  (V-09, V-10, V-11, V-14 — moved from views)
# ---------------------------------------------------------------------------

def enrich_draft_files(draft_files):
    """Enrich draft file dicts with parsed dates and uploader info. (V-09)"""
    for f in draft_files:
        f['upload_date'] = parse_datetime(f['upload_date'])
        f['uploader'] = selectors.get_extrainfo_by_id(f['uploader'])
    return add_uploader_department_to_files_list(draft_files)


def enrich_outbox_files(outward_files, user_hd):
    """Enrich outbox file dicts with forwarding info. (V-10)"""
    sender_extrainfo = selectors.get_extrainfo_by_username(user_hd.user)
    for f in outward_files:
        last_forw = selectors.get_last_forw_tracking(
            file_id=f['id'],
            sender_extrainfo=sender_extrainfo,
            sender_holds_designation=user_hd,
        )
        f['sent_to_user'] = last_forw.receiver_id if last_forw else None
        f['sent_to_design'] = last_forw.receive_design if last_forw else None
        f['last_sent_date'] = last_forw.forward_date if last_forw else None
        f['upload_date'] = parse_datetime(f['upload_date'])
        f['uploader'] = selectors.get_extrainfo_by_id(f['uploader'])
    return outward_files


def enrich_inbox_files(inward_files, user_hd):
    """Enrich inbox file dicts with receive info. (V-11)"""
    for f in inward_files:
        f['upload_date'] = parse_datetime(f['upload_date'])
        last_recv = selectors.get_last_recv_tracking(
            file_id=f['id'],
            receiver_user=user_hd.user,
            receive_design=user_hd.designation,
        )
        f['receive_date'] = last_recv.receive_date if last_recv else None
        f['uploader'] = selectors.get_extrainfo_by_id(f['uploader'])
        current_owner = selectors.get_current_file_owner(f['id'])
        f['is_forwarded'] = (str(current_owner.username) != str(user_hd.user)) if current_owner else True
    return add_uploader_department_to_files_list(inward_files)


def enrich_archive_files(archive_files):
    """Enrich archive file dicts with designation and uploader info. (V-14)"""
    for f in archive_files:
        f['upload_date'] = parse_datetime(f['upload_date'])
        f['designation'] = selectors.get_designation_by_id(f['designation'])   # V-05
        f['uploader'] = selectors.get_extrainfo_by_id(f['uploader'])
    return add_uploader_department_to_files_list(archive_files)


# ---------------------------------------------------------------------------
# Search filtering  (V-12, V-13, R-01)
# ---------------------------------------------------------------------------

def filter_files_by_search(files, subject_query='', sent_to_query='', date_query=''):
    """Filter a file list by subject, sent_to, and date.
    (V-12, V-13, R-01: consolidated from outbox_view/inbox_view)"""
    from datetime import datetime
    if subject_query:
        files = [f for f in files if subject_query.lower() in (f.get('subject') or '').lower()]
    if sent_to_query:
        files = [f for f in files if f.get('sent_to_user') and sent_to_query.lower() in f['sent_to_user'].username.lower()]
    if date_query:
        try:
            search_date = datetime.strptime(date_query, '%Y-%m-%d')
            files = [f for f in files if f.get('last_sent_date') and f['last_sent_date'].date() == search_date.date()]
        except ValueError:
            files = []
    return files


# ---------------------------------------------------------------------------
# Archive  (R-08)
# ---------------------------------------------------------------------------

def view_archived(username, designation, src_module):
    """Return archived files for a user+designation."""
    user_designation = selectors.get_designation_by_name(designation)
    user_object = selectors.get_user_by_username(username)
    received_archived_tracking = selectors.get_tracking_by_receiver(
        user_object, user_designation, src_module, is_read=True
    )

    user_holds_designation = selectors.get_holds_designation(user_object, user_designation)
    sender_extrainfo = selectors.get_extrainfo_by_username(username)
    sent_archived_tracking = selectors.get_tracking_by_sender(
        sender_extrainfo, user_holds_designation, src_module, is_read=True
    )

    archived_tracking = received_archived_tracking | sent_archived_tracking
    archived_files = [tracking.file_id for tracking in archived_tracking]
    archived_files_unique = unique_list(archived_files)
    return _serialize_file_headers(archived_files_unique)


def archive_file_sdk(file_id):
    """Archive a file (set is_read=True). (R-08)"""
    _set_file_read_status(file_id, True)
    return True


def unarchive_file(file_id):
    """Unarchive a file (set is_read=False). (R-08)"""
    _set_file_read_status(file_id, False)
    return True


def archive_file_with_auth(file_id, requesting_user):
    """Archive a file after ownership check."""
    file_obj = get_object_or_404(File, id=file_id)              # V-32: top-level import
    current_owner = selectors.get_current_file_owner(file_id)
    file_uploader_user = file_obj.uploader.user

    if current_owner == requesting_user and file_uploader_user == requesting_user:
        _set_file_read_status(file_id, True)                     # R-08
        return True, 'File Archived'
    return False, 'Unauthorized access'


# ---------------------------------------------------------------------------
# View Drafts
# ---------------------------------------------------------------------------

def view_drafts(username, designation, src_module):
    """Return draft files for a user+designation."""
    user_designation = selectors.get_designation_by_name(designation)
    user_extrainfo = selectors.get_extrainfo_by_username(username)
    draft_files = selectors.get_draft_files(user_extrainfo, user_designation, src_module)
    return _serialize_file_headers(draft_files)


# ---------------------------------------------------------------------------
# Forward file  (R-09: unified core)
# ---------------------------------------------------------------------------

def _forward_file_core(file_id_or_obj, sender_extrainfo, sender_holds_designation,
                       receiver_user, receiver_designation, remarks="",
                       upload_file=None, extra_json=None, send_notif_user=None):
    """Core forwarding logic shared by SDK and web paths.
    (R-09: unified forward_file + forward_file_from_view)"""
    tracking = selectors.create_tracking(                        # V-19, V-37
        file_id=file_id_or_obj if isinstance(file_id_or_obj, File) else selectors.get_file_by_id(file_id_or_obj),
        current_id=sender_extrainfo,
        current_design=sender_holds_designation,
        receiver_id=receiver_user,
        receive_design=receiver_designation,
        remarks=remarks,
        upload_file=upload_file,
        tracking_extra_JSON=extra_json or {},
    )

    if send_notif_user is not None:
        file_obj = file_id_or_obj if isinstance(file_id_or_obj, File) else selectors.get_file_by_id(file_id_or_obj)
        _send_notification(send_notif_user, receiver_user, file_obj.subject)

    return tracking


def forward_file(file_id, receiver, receiver_designation, file_extra_JSON,
                 remarks="", file_attachment=None):
    """Forward a file to a new recipient (SDK path). (R-09)"""
    current_owner, current_owner_designation = selectors.get_current_file_owner_info(file_id)  # R-06
    current_owner_extra_info = selectors.get_extrainfo_by_user(current_owner)    # V-18
    current_owner_holds_designation = selectors.get_holds_designation(
        current_owner, current_owner_designation
    )                                                                            # V-18
    receiver_obj = selectors.get_user_by_username(receiver)                      # V-18
    receiver_designation_obj = selectors.get_designation_by_name(receiver_designation)  # V-18

    tracking = _forward_file_core(
        file_id_or_obj=file_id,
        sender_extrainfo=current_owner_extra_info,
        sender_holds_designation=current_owner_holds_designation,
        receiver_user=receiver_obj,
        receiver_designation=receiver_designation_obj,
        remarks=remarks,
        upload_file=file_attachment,
        extra_json=file_extra_JSON,
    )
    return tracking.id


def forward_file_from_view(file_obj, requesting_user, sender_design_id,
                           receiver_username, receiver_designation_name,
                           upload_file, remarks):
    """Forward a file from the web view. (R-09)"""
    current_id = requesting_user.extrainfo
    current_design = selectors.get_holds_designation_by_id(sender_design_id)     # V-18
    receiver_id = selectors.get_user_by_username(receiver_username)              # V-18
    receive_design = selectors.get_designation_by_name(receiver_designation_name) # V-18

    _forward_file_core(
        file_id_or_obj=file_obj,
        sender_extrainfo=current_id,
        sender_holds_designation=current_design,
        receiver_user=receiver_id,
        receiver_designation=receive_design,
        remarks=remarks,
        upload_file=upload_file,
        send_notif_user=requesting_user,
    )
    return receiver_id


# ---------------------------------------------------------------------------
# View History  (V-35)
# ---------------------------------------------------------------------------

def view_history(file_id):
    """Return tracking history for a file."""
    tracking_history = selectors.get_tracking_history(file_id)
    return [_serialize_tracking(t) for t in tracking_history]


def view_history_enriched(file_id):
    """Return enriched tracking history with username/designation names (V-35)."""
    tracking_entries = selectors.get_tracking_history(file_id)  # V-35: already select_related
    tracking_array = []
    for t in tracking_entries:
        temp_obj = _serialize_tracking(t)
        temp_obj['receiver_id'] = t.receiver_id.username        # V-35: no extra query
        temp_obj['receive_design'] = t.receive_design.name      # V-35: no extra query
        tracking_array.append(temp_obj)
    return tracking_array


# ---------------------------------------------------------------------------
# Get designations
# ---------------------------------------------------------------------------

def get_designations(username):
    """Return list of designation names for a user."""
    return selectors.get_designation_names_for_user(username)


# ---------------------------------------------------------------------------
# Edit draft  (R-09)
# ---------------------------------------------------------------------------

def edit_and_send_draft(file_obj, track_qs, requesting_user, sender_design_id,
                        receiver_username, receiver_designation_name,
                        upload_file, remarks, subject=None, description=None):
    """Edit a draft's metadata and send it."""
    if subject is not None:
        file_obj.subject = subject
    if description is not None:
        file_obj.description = description
    file_obj.save()
    mark_tracking_as_read(file_obj)                              # V-04

    # Reuse forward logic (R-09)
    if upload_file is None and file_obj.upload_file:
        upload_file = file_obj.upload_file

    receiver_id = forward_file_from_view(
        file_obj, requesting_user, sender_design_id,
        receiver_username, receiver_designation_name,
        upload_file, remarks,
    )
    return receiver_id


# ---------------------------------------------------------------------------
# File view context
# ---------------------------------------------------------------------------

def get_file_view_permissions(file_id, requesting_user):
    """Determine forward_enable and archive_enable flags."""
    file_obj = selectors.get_file_by_id(file_id)                # V-19
    current_owner, last_receiver_designation = selectors.get_current_file_owner_info(file_id)  # R-06
    file_uploader = file_obj.uploader.user

    last_receiver_designation_name = last_receiver_designation.name if last_receiver_designation else ''

    forward_enable = False
    archive_enable = False

    if current_owner == requesting_user and file_obj.is_read is False:
        forward_enable = True
    if (current_owner == requesting_user
            and last_receiver_designation_name == file_obj.designation.name
            and file_uploader == requesting_user
            and file_obj.is_read is False):
        archive_enable = True

    return forward_enable, archive_enable


# ---------------------------------------------------------------------------
# Download file
# ---------------------------------------------------------------------------

def generate_file_download(file_id):
    """Generate a ZIP file containing the PDF notesheet and all attachments.
    Returns (zip_data_bytes, output_filename)."""
    file_obj = get_object_or_404(File, id=file_id)              # V-32
    track = selectors.get_tracking_for_file(file_id)             # R-05

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []
    styles = getSampleStyleSheet()
    style_heading = styles['Heading1']
    style_paragraph = styles['BodyText']

    elements.append(
        Paragraph(f"<center><b>Subject - {file_obj.subject}</b></center>", style_heading))
    elements.append(Spacer(1, 12))
    elements.append(
        Paragraph(f"<b>Description:</b> {file_obj.description}", style_paragraph))
    elements.append(Spacer(1, 12))

    for t in track:
        sent_by = f"<b>Sent by:</b> {t.current_design} - {t.forward_date.strftime('%B %d, %Y %I:%M %p')}"
        received_by = f"<b>Received by:</b> {t.receiver_id} - {t.receive_design}"
        combined_info = f"{sent_by} &nbsp;&nbsp;&nbsp;&nbsp;&nbsp; {received_by}"
        elements.append(Paragraph(combined_info, style_paragraph))
        elements.append(Spacer(1, 12))
        remarks_text = f"<b>Remarks:</b> {t.remarks}" if t.remarks else "<b>Remarks:</b> No Remarks"
        elements.append(Paragraph(remarks_text, style_paragraph))
        elements.append(Spacer(1, 12))
        attachment = f"<b>Attachment:</b> {os.path.basename(t.upload_file.name)}" if t.upload_file else "<b>Attachment:</b> No attachments"
        elements.append(Paragraph(attachment, style_paragraph))
        elements.append(Paragraph('<hr width="100%" style="border-top: 1px solid #ccc;">', style_paragraph))
        elements.append(Spacer(2, 12))

    doc.build(elements)
    pdf_data = buffer.getvalue()
    buffer.close()

    formal_filename = f'{file_obj.uploader.department.name}-{file_obj.upload_date.year}-{file_obj.upload_date.month}-#{file_obj.id}'
    output_filename = f'iiitdmj-fts-{formal_filename}'

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
        zip_file.writestr(output_filename + '.pdf', pdf_data)
        for t in track:
            if t.upload_file:
                zip_file.write(t.upload_file.path, os.path.basename(t.upload_file.name))

    zip_data = zip_buffer.getvalue()
    zip_buffer.close()

    return zip_data, output_filename
