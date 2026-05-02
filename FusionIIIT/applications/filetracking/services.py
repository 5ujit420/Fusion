# services.py — filetracking business logic
import io, os, logging, zipfile
from datetime import datetime
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from django.utils.dateparse import parse_datetime
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from applications.globals.models import Designation, HoldsDesignation, ExtraInfo
from notification.views import file_tracking_notif
from .models import File, Tracking, MAX_FILE_SIZE_BYTES, FALLBACK_DEPARTMENT_CODE
from .api.serializers import FileSerializer, FileHeaderSerializer, TrackingSerializer
from . import selectors
from .utils import DESIGNATION_SESSION_KEY, DEFAULT_DESIGNATION_SESSION_VALUE

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def get_designation_display_name(holds_designation_obj):
    return str(holds_designation_obj).split(" - ")[1]


def unique_list(items):
    seen, result = set(), []
    for item in items:
        if item not in seen:
            result.append(item)
            seen.add(item)
    return result


def add_uploader_department_to_files_list(files):
    """T-15/S-37: uses FALLBACK_DEPARTMENT_CODE constant."""
    for f in files:
        ei = f['uploader']
        if ei.department is None:
            f['uploader_department'] = FALLBACK_DEPARTMENT_CODE
        else:
            f['uploader_department'] = str(ei.department).split(': ')[1]
    return files


def validate_file_size(upload_file):
    if upload_file and upload_file.size > MAX_FILE_SIZE_BYTES:
        raise ValidationError("File should not be greater than 10MB")


def filter_files_by_search_params(files, subject_q='', sent_to_q='', date_q='', date_field='last_sent_date'):
    """T-01/S-08,S-17: single implementation of search-filter logic used by outbox and inbox."""
    if subject_q:
        files = [f for f in files if subject_q.lower() in (f.get('subject') or '').lower()]
    if sent_to_q:
        files = [f for f in files if f.get('sent_to_user') and sent_to_q.lower() in f['sent_to_user'].username.lower()]
    if date_q:
        try:
            search_date = datetime.strptime(date_q, '%Y-%m-%d')
            files = [f for f in files if f.get(date_field) and f[date_field].date() == search_date.date()]
        except ValueError:
            files = []
    return files


# ---------------------------------------------------------------------------
# Enrichment helpers  (T-02,T-10/S-01,S-02,S-26,S-27,S-28,S-29,R-09)
# ---------------------------------------------------------------------------

def enrich_outbox_files(files, sender_extrainfo, user_hd):
    """Bulk-enrich outbox file dicts: sent_to_user, sent_to_design, last_sent_date, upload_date, uploader."""
    file_ids = [f['id'] for f in files]
    uploader_ids = [f['uploader'] for f in files]
    forw_map = selectors.get_last_forw_tracking_bulk(file_ids, sender_extrainfo, user_hd)
    ei_map = selectors.get_extrainfo_by_ids(uploader_ids)
    for f in files:
        last_forw = forw_map.get(f['id'])
        f['sent_to_user'] = last_forw.receiver_id if last_forw else None
        f['sent_to_design'] = last_forw.receive_design if last_forw else None
        f['last_sent_date'] = last_forw.forward_date if last_forw else None
        f['upload_date'] = parse_datetime(f['upload_date']) if isinstance(f['upload_date'], str) else f['upload_date']
        f['uploader'] = ei_map.get(f['uploader'], f['uploader'])
    return files


def enrich_inbox_files(files, receiver_user, user_hd):
    """Bulk-enrich inbox file dicts: receive_date, uploader, is_forwarded."""
    file_ids = [f['id'] for f in files]
    uploader_ids = [f['uploader'] for f in files]
    recv_map = selectors.get_last_recv_tracking_bulk(file_ids, receiver_user, user_hd.designation)
    owner_map = selectors.get_current_file_owners_bulk(file_ids)
    ei_map = selectors.get_extrainfo_by_ids(uploader_ids)
    for f in files:
        f['upload_date'] = parse_datetime(f['upload_date']) if isinstance(f['upload_date'], str) else f['upload_date']
        last_recv = recv_map.get(f['id'])
        f['receive_date'] = last_recv.receive_date if last_recv else None
        f['uploader'] = ei_map.get(f['uploader'], f['uploader'])
        current_owner = owner_map.get(f['id'])
        f['is_forwarded'] = (str(current_owner.username) != str(user_hd.user)) if current_owner else True
    return files


def enrich_draft_files(files):
    """Bulk-enrich draft file dicts: upload_date, uploader. (T-10/S-28)"""
    uploader_ids = [f['uploader'] for f in files]
    ei_map = selectors.get_extrainfo_by_ids(uploader_ids)
    for f in files:
        f['upload_date'] = parse_datetime(f['upload_date']) if isinstance(f['upload_date'], str) else f['upload_date']
        f['uploader'] = ei_map.get(f['uploader'], f['uploader'])
    return files


def enrich_archive_files(files):
    """Bulk-enrich archive file dicts: upload_date, designation obj, uploader obj. (T-10/S-29)"""
    uploader_ids = [f['uploader'] for f in files]
    designation_ids = [f['designation'] for f in files]
    ei_map = selectors.get_extrainfo_by_ids(uploader_ids)
    des_map = selectors.get_designations_by_ids(designation_ids)
    for f in files:
        f['upload_date'] = parse_datetime(f['upload_date']) if isinstance(f['upload_date'], str) else f['upload_date']
        f['designation'] = des_map.get(f['designation'])
        f['uploader'] = ei_map.get(f['uploader'], f['uploader'])
    return files


# ---------------------------------------------------------------------------
# State-mutation helpers  (T-06/S-23,S-24 ; T-07/S-25)
# ---------------------------------------------------------------------------

def mark_file_read(file_id):
    """T-06/S-23: business logic extracted from forward view."""
    File.objects.filter(pk=file_id).update(is_read=True)


def mark_tracking_read(track_qs):
    """T-06/S-24: business logic extracted from forward view."""
    track_qs.update(is_read=True)


def finish_file(file_id, track_qs):
    """T-05/S-21: archive a file + its tracking from finish view."""
    File.objects.filter(pk=file_id).update(is_read=True)
    track_qs.update(is_read=True)


def get_draft_remarks(file_obj):
    """T-07/S-25: extract remarks from file JSON field (moved out of view)."""
    if file_obj.file_extra_JSON and file_obj.file_extra_JSON.get('remarks'):
        return file_obj.file_extra_JSON['remarks']
    return None


# ---------------------------------------------------------------------------
# File creation
# ---------------------------------------------------------------------------

def save_draft_file(uploader_user, title, description, design_id, upload_file, remarks=None):
    """T-08/S-13: routes HoldsDesignation lookup through selector (single call, reused)."""
    validate_file_size(upload_file)
    uploader = uploader_user.extrainfo
    holds_des = selectors.get_holds_designation_by_id(design_id)   # S-13: one selector call
    designation = holds_des.designation                              # reuse object, no second ORM hit
    extra_json = {'remarks': remarks if remarks is not None else ''}
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
    """T-08/S-14: HoldsDesignation fetched once via selector, reused for both designation and current_design."""
    validate_file_size(upload_file)
    uploader = uploader_user.extrainfo
    hd = selectors.get_holds_designation_by_id(design_id)   # S-14: single call, result reused
    designation = hd.designation
    current_design = hd
    receiver_id = selectors.get_user_by_username(receiver_username)
    receive_design = selectors.get_designation_by_name(receiver_designation_name)
    file_obj = File.objects.create(
        uploader=uploader,
        description=description,
        subject=title,
        designation=designation,
        upload_file=upload_file,
    )
    Tracking.objects.create(
        file_id=file_obj,
        current_id=uploader,
        current_design=current_design,
        receive_design=receive_design,
        receiver_id=receiver_id,
        remarks=remarks,
        upload_file=upload_file,
    )
    file_tracking_notif(uploader_user, receiver_id, title)
    return file_obj


# ---------------------------------------------------------------------------
# SDK-compatible file creation
# ---------------------------------------------------------------------------

def create_file_via_sdk(uploader, uploader_designation, receiver, receiver_designation,
                        subject="", description="", src_module="filetracking",
                        src_object_id="", file_extra_JSON=None, attached_file=None):
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
    uploader_holdsdesignation_obj = selectors.get_holds_designation(uploader_user_obj, uploader_designation_obj)
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
# View file
# ---------------------------------------------------------------------------

def view_file_details(file_id):
    requested_file = selectors.get_file_by_id(file_id)
    serializer = FileSerializer(requested_file)
    return serializer.data


def delete_file(file_id):
    File.objects.filter(id=file_id).delete()
    return True


def delete_file_with_auth(file_id, requesting_user):
    file_obj = selectors.get_file_by_id(file_id)
    if file_obj.uploader.user != requesting_user:
        raise ValidationError("Not authorized to delete this file")
    file_obj.delete()
    return True


# ---------------------------------------------------------------------------
# Inbox / Outbox
# ---------------------------------------------------------------------------

def view_inbox(username, designation, src_module):
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
    return list(sent_files_serialized.data)


# ---------------------------------------------------------------------------
# Archive
# ---------------------------------------------------------------------------

def view_archived(username, designation, src_module):
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
    return list(archived_files_serialized.data)


def archive_file_sdk(file_id):
    File.objects.filter(id=file_id).update(is_read=True)
    return True


def unarchive_file(file_id):
    File.objects.filter(id=file_id).update(is_read=False)
    return True


def archive_file_with_auth(file_id, requesting_user):
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
# Drafts
# ---------------------------------------------------------------------------

def view_drafts(username, designation, src_module):
    user_designation = selectors.get_designation_by_name(designation)
    user_extrainfo = selectors.get_extrainfo_by_username(username)
    draft_files = selectors.get_draft_files(user_extrainfo, user_designation, src_module)
    draft_files_serialized = FileHeaderSerializer(draft_files, many=True)
    return list(draft_files_serialized.data)


# ---------------------------------------------------------------------------
# Forward file  (T-08/S-12,S-15,T-09/S-16)
# ---------------------------------------------------------------------------

def forward_file(file_id, receiver, receiver_designation, file_extra_JSON,
                 remarks="", file_attachment=None):
    """T-09/S-16: validate_file_size enforced here (single point). T-08/S-12: all lookups via selectors."""
    validate_file_size(file_attachment)   # S-16: single enforcement point
    current_owner = selectors.get_current_file_owner(file_id)
    current_owner_designation = selectors.get_current_file_owner_designation(file_id)
    current_owner_extra_info = selectors.get_extrainfo_by_user(current_owner)           # S-12
    current_owner_holds_designation = selectors.get_holds_designation(current_owner, current_owner_designation)  # S-12
    receiver_obj = selectors.get_user_by_username(receiver)                             # S-12
    receiver_designation_obj = selectors.get_designation_by_name(receiver_designation)  # S-12
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
    """T-08/S-15: HoldsDesignation and Designation lookups routed through selectors."""
    current_id = requesting_user.extrainfo
    current_design = selectors.get_holds_designation_by_id(sender_design_id)  # S-15
    receiver_id = selectors.get_user_by_username(receiver_username)            # S-15
    receive_design = selectors.get_designation_by_name(receiver_designation_name)  # S-15
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
# History  (T-11/S-30)
# ---------------------------------------------------------------------------

def view_history(file_id):
    tracking_history = selectors.get_tracking_history(file_id)
    tracking_history_serialized = TrackingSerializer(tracking_history, many=True)
    return list(tracking_history_serialized.data)


def view_history_enriched(file_id):
    """T-11/S-30: bulk-fetch User and Designation — eliminates N+1 per history entry."""
    histories = view_history(file_id)
    receiver_ids = [h['receiver_id'] for h in histories]
    receive_design_ids = [h['receive_design'] for h in histories]
    users = {u.id: u for u in User.objects.filter(id__in=receiver_ids)}
    designations = {d.id: d for d in Designation.objects.filter(id__in=receive_design_ids)}
    tracking_array = []
    for history in histories:
        temp_obj = history.copy()
        temp_obj['receiver_id'] = users[history['receiver_id']].username if history['receiver_id'] in users else ''
        temp_obj['receive_design'] = designations[history['receive_design']].name if history['receive_design'] in designations else ''
        tracking_array.append(temp_obj)
    return tracking_array


# ---------------------------------------------------------------------------
# Designations
# ---------------------------------------------------------------------------

def get_designations(username):
    return selectors.get_designation_names_for_user(username)


# ---------------------------------------------------------------------------
# Edit draft
# ---------------------------------------------------------------------------

def edit_and_send_draft(file_obj, track_qs, requesting_user, sender_design_id,
                        receiver_username, receiver_designation_name,
                        upload_file, remarks, subject=None, description=None):
    if subject is not None:
        file_obj.subject = subject
    if description is not None:
        file_obj.description = description
    file_obj.save()
    track_qs.update(is_read=True)
    if upload_file is None and file_obj.upload_file:
        upload_file = file_obj.upload_file
    receiver_id = forward_file_from_view(
        file_obj, requesting_user, sender_design_id,
        receiver_username, receiver_designation_name,
        upload_file, remarks,
    )
    return receiver_id


# ---------------------------------------------------------------------------
# File view permissions
# ---------------------------------------------------------------------------

def get_file_view_permissions(file_id, requesting_user):
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
# Download file  (T-17/S-03)
# ---------------------------------------------------------------------------

def _build_pdf_notesheet(file_obj, track):
    """T-17/S-03: extracted PDF generation helper."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    style_h = styles['Heading1']
    style_p = styles['BodyText']
    elements = [
        Paragraph(f"<center><b>Subject - {file_obj.subject}</b></center>", style_h),
        Spacer(1, 12),
        Paragraph(f"<b>Description:</b> {file_obj.description}", style_p),
        Spacer(1, 12),
    ]
    for t in track:
        sent_by = f"<b>Sent by:</b> {t.current_design} - {t.forward_date.strftime('%B %d, %Y %I:%M %p')}"
        received_by = f"<b>Received by:</b> {t.receiver_id} - {t.receive_design}"
        elements.append(Paragraph(f"{sent_by} &nbsp;&nbsp;&nbsp;&nbsp;&nbsp; {received_by}", style_p))
        elements.append(Spacer(1, 12))
        remarks_text = f"<b>Remarks:</b> {t.remarks}" if t.remarks else "<b>Remarks:</b> No Remarks"
        elements.append(Paragraph(remarks_text, style_p))
        elements.append(Spacer(1, 12))
        attachment = f"<b>Attachment:</b> {os.path.basename(t.upload_file.name)}" if t.upload_file else "<b>Attachment:</b> No attachments"
        elements.append(Paragraph(attachment, style_p))
        elements.append(Paragraph('<hr width="100%" style="border-top: 1px solid #ccc;">', style_p))
        elements.append(Spacer(2, 12))
    doc.build(elements)
    pdf_data = buffer.getvalue()
    buffer.close()
    return pdf_data


def _build_zip_archive(pdf_data, base_filename, track):
    """T-17/S-03: extracted ZIP creation helper."""
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
        zip_file.writestr(base_filename + '.pdf', pdf_data)
        for t in track:
            if t.upload_file:
                zip_file.write(t.upload_file.path, os.path.basename(t.upload_file.name))
    zip_data = zip_buffer.getvalue()
    zip_buffer.close()
    return zip_data


def generate_file_download(file_id):
    """T-17/S-03: orchestrates PDF + ZIP helpers; reduced from 55 to ~10 lines."""
    from django.shortcuts import get_object_or_404
    file_obj = get_object_or_404(File, id=file_id)
    track = selectors.get_tracking_for_file_by_id(file_id)
    formal_filename = (
        f'{file_obj.uploader.department.name}-'
        f'{file_obj.upload_date.year}-{file_obj.upload_date.month}-#{file_obj.id}'
    )
    output_filename = f'iiitdmj-fts-{formal_filename}'
    pdf_data = _build_pdf_notesheet(file_obj, track)
    zip_data = _build_zip_archive(pdf_data, output_filename, track)
    return zip_data, output_filename


# ---------------------------------------------------------------------------
# Redirect helper  (T-15/S-36)
# ---------------------------------------------------------------------------

# T-13/S-34: Dead stub get_designation_redirect_url DELETED.

def get_designation_redirect_url_from_session(request, path_slug):
    """T-15/S-36: uses named constants instead of 'default_value' literal."""
    dropdown_design = request.session.get(DESIGNATION_SESSION_KEY, DEFAULT_DESIGNATION_SESSION_VALUE)
    hd_obj = selectors.get_holds_designation_obj(request.user, dropdown_design)
    return f'/filetracking/{path_slug}/{hd_obj.id}'
