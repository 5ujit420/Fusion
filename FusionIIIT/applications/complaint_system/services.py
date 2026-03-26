# services.py
# All business logic for the complaint_system module.
# Addresses: RR-01, RR-02, RR-03, RR-05, RR-06, RR-08, RR-11, RR-13, RR-14, RR-15, RR-16, RR-24

import logging
from datetime import datetime, timedelta

from django.shortcuts import get_object_or_404

from applications.globals.models import ExtraInfo
from notification.views import complaint_system_notif
from applications.filetracking.sdk.methods import forward_file

from .models import (
    Caretaker, Warden, StudentComplain, ServiceProvider,
    Complaint_Admin, ServiceAuthority, Workers,
)
from . import selectors

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants: complaint type -> finish days  (RR-01)
# ---------------------------------------------------------------------------

COMPLAINT_TYPE_DAYS = {
    'Electricity': 2,
    'Carpenter': 2,
    'carpenter': 2,
    'Plumber': 2,
    'plumber': 2,
    'Garbage': 1,
    'garbage': 1,
    'Dustbin': 1,
    'dustbin': 1,
    'Internet': 4,
    'internet': 4,
    'Other': 3,
    'other': 3,
}

DEFAULT_FINISH_DAYS = 2

# ---------------------------------------------------------------------------
# Constants: location -> designation  (RR-02)
# ---------------------------------------------------------------------------

LOCATION_DESIGNATION_MAP = {
    'hall-1': 'hall1caretaker',
    'hall-3': 'hall3caretaker',
    'hall-4': 'hall4caretaker',
    'CC1': 'cc1convener',
    'CC2': 'CC2 convener',
    'core_lab': 'corelabcaretaker',
    'LHTC': 'lhtccaretaker',
    'NR2': 'nr2caretaker',
    'Maa Saraswati Hostel': 'mshcaretaker',
    'Nagarjun Hostel': 'nhcaretaker',
    'Panini Hostel': 'phcaretaker',
}

DEFAULT_DESIGNATION = 'rewacaretaker'


# ---------------------------------------------------------------------------
# Helper: calculate complaint finish date  (RR-01)
# ---------------------------------------------------------------------------

def calculate_complaint_finish_date(complaint_type):
    """Return the finish date based on complaint type."""
    days = COMPLAINT_TYPE_DAYS.get(complaint_type, DEFAULT_FINISH_DAYS)
    return (datetime.now() + timedelta(days=days)).date()


# ---------------------------------------------------------------------------
# Helper: resolve location to caretaker designation  (RR-02)
# ---------------------------------------------------------------------------

def resolve_location_to_designation(location):
    """Return the caretaker designation name for a given location."""
    return LOCATION_DESIGNATION_MAP.get(location, DEFAULT_DESIGNATION)


# ---------------------------------------------------------------------------
# Helper: update caretaker rating  (RR-05)
# ---------------------------------------------------------------------------

def _update_caretaker_rating(caretaker, new_rating):
    """Average the new rating with the caretaker's existing rating."""
    rate = caretaker.rating
    if rate == 0:
        caretaker.rating = new_rating
    else:
        caretaker.rating = int((new_rating + rate) / 2)
    caretaker.save()


# ---------------------------------------------------------------------------
# Determine user type  (RR-24)
# ---------------------------------------------------------------------------

def determine_user_type(user):
    """
    Determine the role of a user and return (user_type, next_url).
    Uses .filter().exists() instead of fetching all rows.
    """
    extra = selectors.get_extrainfo_by_user(user)
    if extra is None:
        return None, None

    if selectors.is_service_provider(extra.id):
        return 'service_provider', '/complaint/service_provider/'
    if selectors.is_complaint_admin(extra.id):
        return 'complaint_admin', '/complaint/complaint_admin/'
    if selectors.is_caretaker(extra.id):
        return 'caretaker', '/complaint/caretaker/'
    if selectors.is_warden(extra.id):
        return 'warden', '/complaint/warden/'
    if extra.user_type in ('student', 'staff', 'faculty'):
        return extra.user_type, '/complaint/user/'
    return None, None


# ---------------------------------------------------------------------------
# Lodge complaint  (RR-03)
# ---------------------------------------------------------------------------

def lodge_complaint(user, validated_data, notify_single=False):
    """
    Create a complaint and send notification to the relevant caretaker(s).

    Args:
        user: The requesting User object (for notification sender).
        validated_data: Dict with complaint fields.
        notify_single: If True, use .get() for caretaker lookup.
                       If False, use .filter().distinct() and notify all.

    Returns:
        Tuple of (created StudentComplain instance, serialized data dict).
    """
    extra = selectors.get_extrainfo_by_user(user)
    validated_data['complainer'] = extra.id
    validated_data['status'] = 0

    comp_type = validated_data.get('complaint_type', '')
    validated_data['complaint_finish'] = calculate_complaint_finish_date(comp_type)

    from .serializers import StudentComplainSerializer
    serializer = StudentComplainSerializer(data=validated_data)
    serializer.is_valid(raise_exception=True)
    complaint = serializer.save()

    # Notification
    location = validated_data.get('location', '')
    dsgn = resolve_location_to_designation(location)

    student = 1
    message = "A New Complaint has been lodged"

    if notify_single:
        caretaker_hd = selectors.get_holds_designation_single(dsgn)
        complaint_system_notif(
            user, caretaker_hd.user, 'lodge_comp_alert',
            complaint.id, student, message
        )
    else:
        caretakers = selectors.get_holds_designation_by_name(dsgn)
        for caretaker in caretakers:
            complaint_system_notif(
                user, caretaker.user, 'lodge_comp_alert',
                complaint.id, student, message
            )

    return complaint, serializer.data


# ---------------------------------------------------------------------------
# Submit caretaker area feedback
# ---------------------------------------------------------------------------

def submit_caretaker_area_feedback(caretaker_type, feedback, rating):
    """
    Submit feedback for all caretakers in a given area.
    Preserves original logic: update every caretaker of that area.
    """
    all_caretaker = selectors.get_caretakers_by_area(caretaker_type)
    for caretaker in all_caretaker:
        _update_caretaker_rating(caretaker, rating)
        caretaker.myfeedback = feedback
        caretaker.save()


# ---------------------------------------------------------------------------
# Submit complaint feedback  (RR-05)
# ---------------------------------------------------------------------------

def submit_complaint_feedback(complaint_id, feedback, rating):
    """
    Update complaint feedback/flag and recalculate the caretaker rating.
    Raises StudentComplain.DoesNotExist or Caretaker.DoesNotExist on error.
    """
    selectors.update_complaint_feedback(complaint_id, feedback, rating)
    complaint = selectors.get_complaint_by_id(complaint_id)
    caretaker = selectors.get_caretaker_by_area(complaint.location)
    if caretaker:
        _update_caretaker_rating(caretaker, rating)


# ---------------------------------------------------------------------------
# Resolve complaint  (RR-08)
# ---------------------------------------------------------------------------

def resolve_complaint(cid, yesorno, comment, upload_file, requesting_user):
    """
    Resolve or decline a complaint.

    Args:
        cid: Complaint ID.
        yesorno: 'Yes' to resolve, 'No' to decline.
        comment: Caretaker's comment.
        upload_file: Optional uploaded image or None.
        requesting_user: The User resolving the complaint.

    Returns:
        dict with success message.
    """
    intstatus = 2 if yesorno == 'Yes' else 3

    complaint = selectors.get_complaint_by_id_basic(cid)
    complaint.status = intstatus
    complaint.comment = comment

    if upload_file:
        complaint.upload_resolved = upload_file

    complaint.save()

    # Notification
    complainer_details = selectors.get_complaint_by_id(cid)
    student = 0
    if yesorno == 'Yes':
        message = "Congrats! Your complaint has been resolved"
        notification_type = 'comp_resolved_alert'
    else:
        message = "Your complaint has been declined"
        notification_type = 'comp_declined_alert'

    complaint_system_notif(
        requesting_user,
        complainer_details.complainer.user,
        notification_type,
        complainer_details.id,
        student,
        message,
    )

    return {'success': 'Complaint status updated'}


# ---------------------------------------------------------------------------
# Forward complaint to service provider  (RR-14)
# ---------------------------------------------------------------------------

def forward_complaint_to_service_provider(comp_id, requesting_user):
    """
    Forward a complaint to the relevant service provider.
    Returns a tuple (result_dict, http_status_code).
    """
    complaint = selectors.get_complaint_by_id_basic(comp_id)
    complaint_type = complaint.complaint_type

    service_providers = selectors.get_service_providers_by_type(complaint_type)
    if not service_providers.exists():
        return {'error': 'ServiceProvider does not exist for this complaint type'}, 404

    service_provider = service_providers.first()
    service_provider_details = ExtraInfo.objects.get(id=service_provider.ser_pro_id.id)

    # Update complaint status
    complaint.status = 1
    complaint.save()

    # Notify service providers
    sup_designations = selectors.get_holds_designations_for_user(service_provider_details.user_id)
    for sup in sup_designations:
        complaint_system_notif(
            requesting_user,
            selectors.get_user_by_id(sup.user_id),
            'comp_assigned_alert',
            comp_id,
            0,
            "A new complaint has been assigned to you",
        )

    # Forward file
    files = selectors.get_files_for_complaint(comp_id)
    if not files.exists():
        return {'error': 'No files associated with this complaint'}, 206

    service_provider_username = selectors.get_user_by_id(service_provider_details.user_id).username
    forward_file(
        file_id=files.first().id,
        receiver=service_provider_username,
        receiver_designation=sup_designations.first().designation,
        file_extra_JSON={},
        remarks="",
        file_attachment=None,
    )

    return {'success': 'Complaint assigned to service_provider'}, 200


# ---------------------------------------------------------------------------
# Change complaint status  (RR-06)
# ---------------------------------------------------------------------------

def change_complaint_status(complaint_id, new_status):
    """
    Change the status of a complaint.
    If status is '2' or '3', also clear worker_id.
    """
    complaint = selectors.get_complaint_by_id_basic(complaint_id)
    complaint.status = new_status
    if new_status in ('2', '3'):
        complaint.worker_id = None
    complaint.save()


# ---------------------------------------------------------------------------
# Remove worker
# ---------------------------------------------------------------------------

def remove_worker(work_id):
    """
    Remove a worker if not assigned to any complaints.
    Returns (success_bool, message).
    """
    worker = selectors.get_worker_by_id(work_id)
    assigned = selectors.get_complaints_assigned_to_worker(worker)
    if assigned == 0:
        worker.delete()
        return True, 'Worker removed successfully'
    return False, 'Worker is assigned to some complaints'


# ---------------------------------------------------------------------------
# Delete complaint  (RR-13)
# ---------------------------------------------------------------------------

def delete_complaint(complaint_id, requesting_user):
    """
    Delete a complaint after ownership/role checks.
    Returns (success_bool, message).
    """
    complaint = selectors.get_complaint_by_id_basic(complaint_id)
    extra = selectors.get_extrainfo_by_user(requesting_user)

    is_owner = (complaint.complainer_id == extra.id)
    is_care = selectors.is_caretaker(extra.id)
    is_admin = selectors.is_complaint_admin(extra.id)

    if not (is_owner or is_care or is_admin):
        return False, 'Not authorized to delete this complaint'

    complaint.delete()
    return True, 'Complaint deleted successfully'


# ---------------------------------------------------------------------------
# Generate report  (RR-15)
# ---------------------------------------------------------------------------

def generate_report(user):
    """
    Return the appropriate complaints queryset for report generation
    based on the user's role.  Returns (queryset, error_message).
    """
    extra = selectors.get_extrainfo_by_user(user)

    # Check if complaint admin first
    try:
        selectors.get_complaint_admin_by_extrainfo(extra)
        return selectors.get_all_complaints(), None
    except Complaint_Admin.DoesNotExist:
        pass

    is_care = selectors.is_caretaker(extra.id)
    is_sp = False
    is_warden_flag = False
    is_sa = False

    service_provider = None
    try:
        service_provider = selectors.get_service_provider_by_extrainfo(extra)
        is_sp = True
    except ServiceProvider.DoesNotExist:
        pass

    try:
        selectors.get_service_authority_by_extrainfo(extra)
        is_sa = True
    except ServiceAuthority.DoesNotExist:
        pass

    warden = None
    try:
        warden = selectors.get_warden_by_staff_id(extra)
        is_warden_flag = True
    except Warden.DoesNotExist:
        pass

    is_complaint_admin_attr = selectors.is_complaint_admin(extra.id)

    if not (is_care or is_sp or is_complaint_admin_attr or is_sa or is_warden_flag):
        return None, "Not authorized to generate report."

    complaints = None

    if is_sp and service_provider:
        complaints = selectors.get_complaints_for_report_service_provider(service_provider.type)

    if is_care and not is_sp and not is_warden_flag:
        caretaker = get_object_or_404(Caretaker, staff_id=extra)
        complaints = selectors.get_complaints_for_report_area(caretaker.area)

    if is_warden_flag and warden:
        warden_obj = get_object_or_404(Warden, staff_id=extra)
        complaints = selectors.get_complaints_for_report_area(warden_obj.area)

    if is_complaint_admin_attr:
        complaints = selectors.get_all_complaints()

    return complaints, None


# ---------------------------------------------------------------------------
# Get complaints for user  (api/ views helper)
# ---------------------------------------------------------------------------

def get_complaints_for_user(user):
    """
    Return the queryset of complaints visible to a user based on their role.
    """
    extra = selectors.get_extrainfo_by_user(user)

    if extra.user_type == 'student':
        return selectors.get_complaints_by_complainer(extra)
    elif extra.user_type == 'staff':
        caretaker = selectors.get_caretaker_by_staff_id(extra.id)
        return selectors.get_complaints_by_location(caretaker.area)
    elif extra.user_type == 'faculty':
        sp = selectors.get_service_provider_by_extrainfo(extra)
        return selectors.get_complaints_by_location(sp.type)
    return StudentComplain.objects.none()


# ---------------------------------------------------------------------------
# Get complaint detail  (api/ views helper, RR-20 fix)
# ---------------------------------------------------------------------------

def get_complaint_detail_for_api(complaint_id):
    """
    Return a dict with complaint detail, worker, complainer, and extra info.
    Fixes the original bug where 'worker_detail' variable was used instead
    of 'Workers' model.
    """
    complaint = selectors.get_complaint_by_id(complaint_id)

    worker_data = {}
    if complaint.worker_id is not None:
        worker = selectors.get_worker_by_id(complaint.worker_id_id)
        from .api.serializers import WorkersSerializer
        worker_data = WorkersSerializer(instance=worker).data

    complainer_user = selectors.get_user_by_username(complaint.complainer.user.username)
    complainer_extra = ExtraInfo.objects.get(user=complainer_user)

    return {
        'complaint': complaint,
        'worker_data': worker_data,
        'complainer_user': complainer_user,
        'complainer_extra_info': complainer_extra,
    }
