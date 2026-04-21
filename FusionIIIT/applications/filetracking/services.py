# services.py
# All business logic for the filetracking module.
# Fixes: V-01, V-04–V-11, V-41, R-01, R-02, R-04, R-08

import io
import os
import logging
import zipfile

from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

from applications.globals.models import Designation, HoldsDesignation, ExtraInfo
from notification.views import file_tracking_notif

from .models import File, Tracking, MAX_FILE_SIZE_BYTES
from .api.serializers import FileSerializer, FileHeaderSerializer, TrackingSerializer
from . import selectors

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Utilities  (R-03)
# ---------------------------------------------------------------------------

def get_designation_display_name(holds_designation_obj):
    """Extract the display name from a HoldsDesignation object (R-03)."""
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
    """Raise ValidationError if file exceeds MAX_FILE_SIZE_BYTES (V-39)."""
    if upload_file and upload_file.size > MAX_FILE_SIZE_BYTES:
        raise ValidationError("File should not be greater than 10MB")


# ---------------------------------------------------------------------------
# File creation  (V-04, R-01 — consolidated save/send)
# ---------------------------------------------------------------------------

def save_draft_file(uploader_user, title, description, design_id, upload_file, remarks=None):
    """
    Save a file as draft (no Tracking created, no notification sent).
    Preserves original save-draft logic from views.py L58-87.
    """
    validate_file_size(upload_file)

    uploader = uploader_user.extrainfo
    holds_des = selectors.get_holds_designation_by_id(design_id)
    designation = selectors.get_designation_by_name(
        HoldsDesignation.objects.select_related('designation').get(id=design_id).designation.name
    )

    extra_json = {
        'remarks': remarks if remarks is not None else '',
    }

    file_obj = File.objects.create(
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
    Preserves original send logic from views.py L89-143. (R-01)
    """
    validate_file_size(upload_file)

    uploader = uploader_user.extrainfo
    designation = Designation.objects.get(
        id=HoldsDesignation.objects.select_related(
            'user', 'working', 'designation'
        ).get(id=design_id).designation_id
    )

    file_obj = File.objects.create(
        uploader=uploader,
        description=description,
        subject=title,
        designation=designation,
        upload_file=upload_file,
    )

    current_id = uploader_user.extrainfo
    current_design = HoldsDesignation.objects.select_related(
        'user', 'working', 'designation'
    ).get(id=design_id)

    receiver_id = User.objects.get(username=receiver_username)
    receive_design = Designation.objects.get(name=receiver_designation_name)

    Tracking.objects.create(
        file_id=file_obj,
        current_id=current_id,
        current_design=current_design,
        receive_design=receive_design,
        receiver_id=receiver_id,
        remarks=remarks,
        upload_file=upload_file,
    )

    file_tracking_notif(uploader_user, receiver_id, title)
    return file_obj


# ---------------------------------------------------------------------------
# SDK-compatible file creation  (V-12, V-41)
# ---------------------------------------------------------------------------

def create_file_via_sdk(uploader, uploader_designation, receiver, receiver_designation,
                        subject="", description="", src_module="filetracking",
                        src_object_id="", file_extra_JSON=None, attached_file=None):
    """
    Create a file + tracking entry (SDK create_file equivalent).
    Preserves exact logic from sdk/methods.py L10-73.
    """
    if file_extra_JSON is None:
        file_extra_JSON = {}

    uploader_user_obj = selectors.get_user_by_username(uploader)
    uploader_extrainfo_obj = selectors.get_extrainfo_by_username(uploader)
    uploader_designation_obj = selectors.get_designation_by_name(uploader_designation)
    receiver_obj = selectors.get_user_by_username(receiver)
    receiver_designation_obj = selectors.get_designation_by_name(receiver_designation)

    new_file = File.objects.create(
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

    new_tracking = Tracking.objects.create(
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


def create_draft_via_sdk(uploader, uploader_designation, src_module="filetracking",
                         src_object_id="", file_extra_JSON=None, attached_file=None):
    """
    Create a draft (no Tracking). SDK create_draft equivalent.
    Preserves logic from sdk/methods.py L205-229.
    """
    if file_extra_JSON is None:
        file_extra_JSON = {}

    uploader_extrainfo_obj = selectors.get_extrainfo_by_username(uploader)
    uploader_designation_obj = selectors.get_designation_by_name(uploader_designation)

    new_file = File.objects.create(
        uploader=uploader_extrainfo_obj,
        designation=uploader_designation_obj,
        src_module=src_module,
        src_object_id=src_object_id,
        file_extra_JSON=file_extra_JSON,
        upload_file=attached_file,
    )
    return new_file.id


# ---------------------------------------------------------------------------
# View file  (V-13)
# ---------------------------------------------------------------------------

def view_file_details(file_id):
    """Return serialized file details. Preserves sdk/methods.py L76-86."""
    requested_file = selectors.get_file_by_id(file_id)
    serializer = FileSerializer(requested_file)
    return serializer.data


def delete_file(file_id):
    """Delete a file. Preserves sdk/methods.py L89-97."""
    File.objects.filter(id=file_id).delete()
    return True


def delete_file_with_auth(file_id, requesting_user):
    """Delete a file with ownership check (V-23)."""
    file_obj = selectors.get_file_by_id(file_id)
    if file_obj.uploader.user != requesting_user:
        raise ValidationError("Not authorized to delete this file")
    file_obj.delete()
    return True


# ---------------------------------------------------------------------------
# Inbox / Outbox  (V-05, V-06, V-14, V-15)
# ---------------------------------------------------------------------------

def view_inbox(username, designation, src_module):
    """
    Return inbox files for a user+designation.
    Preserves exact logic from sdk/methods.py L101-123.
    """
    user_designation = selectors.get_designation_by_name(designation)
    recipient_object = selectors.get_user_by_username(username)
    received_files_tracking = selectors.get_tracking_by_receiver(
        recipient_object, user_designation, src_module, is_read=False
    )
    received_files = [tracking.file_id for tracking in received_files_tracking]
    received_files_unique = unique_list(received_files)
    received_files_serialized = list(FileHeaderSerializer(received_files_unique, many=True).data)

    for f in received_files_serialized:
        sender = selectors.get_last_file_sender(f['id'])
        sender_des = selectors.get_last_file_sender_designation(f['id'])
        f['sent_by_user'] = sender.username if sender else ''
        f['sent_by_designation'] = sender_des.name if sender_des else ''

    return received_files_serialized


def view_outbox(username, designation, src_module):
    """
    Return outbox files for a user+designation.
    Preserves exact logic from sdk/methods.py L126-146.
    """
    user_designation = selectors.get_designation_by_name(designation)
    user_object = selectors.get_user_by_username(username)
    user_holds_designation = selectors.get_holds_designation(user_object, user_designation)
    sender_extrainfo = selectors.get_extrainfo_by_username(username)
    sent_files_tracking = selectors.get_tracking_by_sender(
        sender_extrainfo, user_holds_designation, src_module, is_read=False
    )
    sent_files = [tracking.file_id for tracking in sent_files_tracking]
    sent_files_unique = unique_list(sent_files)
    sent_files_serialized = FileHeaderSerializer(sent_files_unique, many=True)
    return sent_files_serialized.data


# ---------------------------------------------------------------------------
# Archive  (V-10, V-20, R-08)
# ---------------------------------------------------------------------------

def view_archived(username, designation, src_module):
    """
    Return archived files for a user+designation.
    Preserves logic from sdk/methods.py L150-179.
    """
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
    archived_files_serialized = FileHeaderSerializer(archived_files_unique, many=True)
    return archived_files_serialized.data


def archive_file_sdk(file_id):
    """Archive a file (set is_read=True). Preserves sdk/methods.py L183-191."""
    File.objects.filter(id=file_id).update(is_read=True)
    return True


def unarchive_file(file_id):
    """Unarchive a file (set is_read=False). Single implementation (R-08)."""
    File.objects.filter(id=file_id).update(is_read=False)
    return True


def archive_file_with_auth(file_id, requesting_user):
    """
    Archive a file after ownership check (V-10).
    Preserves logic from views.py L494-513.
    """
    from django.shortcuts import get_object_or_404
    file_obj = get_object_or_404(File, id=file_id)
    current_owner = selectors.get_current_file_owner(file_id)
    file_uploader_user = file_obj.uploader.user

    if current_owner == requesting_user and file_uploader_user == requesting_user:
        file_obj.is_read = True
        file_obj.save()
        return True, 'File Archived'
    return False, 'Unauthorized access'


# ---------------------------------------------------------------------------
# View Drafts  (V-18, V-19)
# ---------------------------------------------------------------------------

def view_drafts(username, designation, src_module):
    """
    Return draft files for a user+designation.
    Preserves logic from sdk/methods.py L232-241.
    """
    user_designation = selectors.get_designation_by_name(designation)
    user_extrainfo = selectors.get_extrainfo_by_username(username)
    draft_files = selectors.get_draft_files(user_extrainfo, user_designation, src_module)
    draft_files_serialized = FileHeaderSerializer(draft_files, many=True)
    return draft_files_serialized.data


# ---------------------------------------------------------------------------
# Forward file  (V-07, V-17, R-02)
# ---------------------------------------------------------------------------

def forward_file(file_id, receiver, receiver_designation, file_extra_JSON,
                 remarks="", file_attachment=None):
    """
    Forward a file to a new recipient.
    Preserves exact logic from sdk/methods.py L245-284.
    """
    current_owner = selectors.get_current_file_owner(file_id)
    current_owner_designation = selectors.get_current_file_owner_designation(file_id)
    current_owner_extra_info = ExtraInfo.objects.get(user=current_owner)
    current_owner_holds_designation = HoldsDesignation.objects.get(
        user=current_owner, designation=current_owner_designation
    )
    receiver_obj = User.objects.get(username=receiver)
    receiver_designation_obj = Designation.objects.get(name=receiver_designation)

    tracking_data = {
        'file_id': file_id,
        'current_id': current_owner_extra_info.id,
        'current_design': current_owner_holds_designation.id,
        'receiver_id': receiver_obj.id,
        'receive_design': receiver_designation_obj.id,
        'tracking_extra_JSON': file_extra_JSON,
        'remarks': remarks,
    }
    if file_attachment is not None:
        tracking_data['upload_file'] = file_attachment

    tracking_entry = TrackingSerializer(data=tracking_data)
    if tracking_entry.is_valid():
        tracking_entry.save()
        return tracking_entry.instance.id
    else:
        raise ValidationError('forward data is incomplete')


def forward_file_from_view(file_obj, requesting_user, sender_design_id,
                           receiver_username, receiver_designation_name,
                           upload_file, remarks):
    """
    Forward a file from the web view (V-07, R-02).
    Common logic shared by forward() and edit_draft_view().
    """
    current_id = requesting_user.extrainfo
    current_design = HoldsDesignation.objects.select_related(
        'user', 'working', 'designation'
    ).get(id=sender_design_id)

    receiver_id = User.objects.get(username=receiver_username)
    receive_design = Designation.objects.get(name=receiver_designation_name)

    Tracking.objects.create(
        file_id=file_obj,
        current_id=current_id,
        current_design=current_design,
        receive_design=receive_design,
        receiver_id=receiver_id,
        remarks=remarks,
        upload_file=upload_file,
    )

    file_tracking_notif(requesting_user, receiver_id, file_obj.subject)
    return receiver_id


# ---------------------------------------------------------------------------
# View History  (V-16)
# ---------------------------------------------------------------------------

def view_history(file_id):
    """
    Return tracking history for a file.
    Preserves sdk/methods.py L287-295.
    """
    tracking_history = selectors.get_tracking_history(file_id)
    tracking_history_serialized = TrackingSerializer(tracking_history, many=True)
    return tracking_history_serialized.data


def view_history_enriched(file_id):
    """
    Return enriched tracking history with username/designation names (V-16).
    Preserves api/views.py ViewHistoryView L152-161.
    """
    histories = view_history(file_id)
    tracking_array = []
    for history in histories:
        temp_obj = history.copy()
        temp_obj['receiver_id'] = User.objects.get(id=history['receiver_id']).username
        temp_obj['receive_design'] = Designation.objects.get(id=history['receive_design']).name
        tracking_array.append(temp_obj)
    return tracking_array


# ---------------------------------------------------------------------------
# Get designations  (for both web and API views)
# ---------------------------------------------------------------------------

def get_designations(username):
    """Return list of designation names for a user. Preserves sdk/methods.py L341-348."""
    return selectors.get_designation_names_for_user(username)


# ---------------------------------------------------------------------------
# Edit draft  (V-08, R-02)
# ---------------------------------------------------------------------------

def edit_and_send_draft(file_obj, track_qs, requesting_user, sender_design_id,
                        receiver_username, receiver_designation_name,
                        upload_file, remarks, subject=None, description=None):
    """
    Edit a draft's metadata and send it.
    Preserves views.py L911-977.
    """
    if subject is not None:
        file_obj.subject = subject
    if description is not None:
        file_obj.description = description
    file_obj.save()
    track_qs.update(is_read=True)

    # Reuse forward logic (R-02)
    if upload_file is None and file_obj.upload_file:
        upload_file = file_obj.upload_file

    receiver_id = forward_file_from_view(
        file_obj, requesting_user, sender_design_id,
        receiver_username, receiver_designation_name,
        upload_file, remarks,
    )
    return receiver_id


# ---------------------------------------------------------------------------
# File view context  (V-11)
# ---------------------------------------------------------------------------

def get_file_view_permissions(file_id, requesting_user):
    """
    Determine forward_enable and archive_enable flags.
    Preserves views.py L469-480.
    """
    file_obj = File.objects.get(id=file_id)
    current_owner = selectors.get_current_file_owner(file_id)
    file_uploader = file_obj.uploader.user

    last_receiver_designation = selectors.get_current_file_owner_designation(file_id)
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
# Download file  (V-09)
# ---------------------------------------------------------------------------

def generate_file_download(file_id):
    """
    Generate a ZIP file containing the PDF notesheet and all attachments.
    Preserves views.py L1014-1073.
    Returns (zip_data_bytes, output_filename).
    """
    from django.shortcuts import get_object_or_404
    file_obj = get_object_or_404(File, id=file_id)
    track = selectors.get_tracking_for_file_by_id(file_id)

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


# ---------------------------------------------------------------------------
# Redirect helper  (R-04)
# ---------------------------------------------------------------------------

def get_designation_redirect_url(requesting_user, path_slug):
    """
    Build a redirect URL for designation-based pages (R-04).
    Consolidates draft_design, outward, inward, archive_design.
    """
    dropdown_design = None  # Must be passed from session
    raise NotImplementedError("Use get_designation_redirect_url_from_session instead")


def get_designation_redirect_url_from_session(request, path_slug):
    """Build redirect URL from session designation."""
    dropdown_design = request.session.get('currentDesignationSelected', 'default_value')
    hd_obj = selectors.get_holds_designation_obj(request.user, dropdown_design)
    return f'/filetracking/{path_slug}/{hd_obj.id}'
