# services.py
# T-01: All business logic extracted from views (CS-07, CS-08, CS-24, CS-25).
# T-02: compute_complaint_deadline + resolve_caretaker_designation (CS-11, CS-12, RD-01, RD-02).
# T-10: calculate_new_rating replaces 4 inline computations (CS-13, RD-11).
# T-21: assign_complaint_to_service_provider isolates filetracking SDK (CS-20, CS-08).
# T-08: send_complaint_notification wraps notif call with logging (CS-37, CS-38).

import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants (T-02, CS-05, CS-35, CS-36)
# ---------------------------------------------------------------------------

# Days to resolve by complaint type.  Both capitalisation variants kept
# to preserve existing behaviour in UserComplaintView (bug: 'Carpenter' vs 'carpenter').
COMPLAINT_DEADLINE_DAYS = {
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

# Maps location value (from form) to HoldsDesignation name (CS-35, RD-02).
LOCATION_DESIGNATION_MAP = {
    'hall-1':              'hall1caretaker',
    'hall-3':              'hall3caretaker',
    'hall-4':              'hall4caretaker',
    'CC1':                 'cc1convener',
    'CC2':                 'CC2 convener',
    'core_lab':            'corelabcaretaker',
    'LHTC':                'lhtccaretaker',
    'NR2':                 'nr2caretaker',
    'Maa Saraswati Hostel': 'mshcaretaker',
    'Nagarjun Hostel':     'nhcaretaker',
    'Panini Hostel':       'phcaretaker',
}

# Maps user_type / role to redirect URL (CS-06).
ROLE_URLS = {
    'service_provider': '/complaint/service_provider/',
    'complaint_admin':  '/complaint/complaint_admin/',
    'caretaker':        '/complaint/caretaker/',
    'warden':           '/complaint/warden/',
    'student':          '/complaint/user/',
    'staff':            '/complaint/user/',
    'faculty':          '/complaint/user/',
}


# ---------------------------------------------------------------------------
# Deadline + designation helpers  (T-02)
# ---------------------------------------------------------------------------

def compute_complaint_deadline(comp_type):
    """Return finish date (date object) based on complaint type string."""
    days = COMPLAINT_DEADLINE_DAYS.get(comp_type, 2)
    return (datetime.now() + timedelta(days=days)).date()


def resolve_caretaker_designation(location):
    """Map a location string to the corresponding HoldsDesignation name."""
    return LOCATION_DESIGNATION_MAP.get(location, 'rewacaretaker')


# ---------------------------------------------------------------------------
# Rating helpers  (T-10, CS-13)
# ---------------------------------------------------------------------------

def calculate_new_rating(existing_rating, new_rating):
    """Return updated integer rating (average if existing > 0, else new)."""
    if existing_rating == 0:
        return new_rating
    return int((existing_rating + new_rating) / 2)


def update_caretaker_rating(area, new_rating):
    """Lookup caretaker by area and update its rating. Returns Caretaker or None."""
    from .models import Caretaker
    caretaker = Caretaker.objects.filter(area=area).first()
    if caretaker:
        caretaker.rating = calculate_new_rating(caretaker.rating, new_rating)
        caretaker.save()
    return caretaker


# ---------------------------------------------------------------------------
# Role determination  (T-04, CS-03)
# ---------------------------------------------------------------------------

def determine_user_role(extra_info):
    """
    Return {'role': str, 'next_url': str} for the authenticated user,
    or None if no matching role is found.
    """
    from . import selectors  # late import avoids circular dependency

    if selectors.is_service_provider(extra_info):
        role = 'service_provider'
    elif selectors.is_complaint_admin(extra_info):
        role = 'complaint_admin'
    elif selectors.is_caretaker(extra_info):
        role = 'caretaker'
    elif selectors.is_warden(extra_info):
        role = 'warden'
    else:
        role = getattr(extra_info, 'user_type', None)

    if role and role in ROLE_URLS:
        return {'role': role, 'next_url': ROLE_URLS[role]}
    return None


# ---------------------------------------------------------------------------
# Notification wrapper  (T-08, T-21, CS-37, CS-38)
# ---------------------------------------------------------------------------

def send_complaint_notification(sender, recipient_user, notif_type,
                                complaint_id, student_flag, message):
    """Dispatch a complaint notification, logging any failure."""
    try:
        from notification.views import complaint_system_notif
        complaint_system_notif(
            sender, recipient_user, notif_type, complaint_id, student_flag, message
        )
    except Exception as exc:
        logger.exception('Notification dispatch failed [%s → %s]: %s',
                         notif_type, getattr(recipient_user, 'username', '?'), exc)


def notify_caretakers_multi(request_user, complaint, location):
    """Notify ALL caretakers with the designation for location (UserComplaintView)."""
    from applications.globals.models import HoldsDesignation
    dsgn = resolve_caretaker_designation(location)
    caretakers = (
        HoldsDesignation.objects
        .select_related('user', 'working', 'designation')
        .filter(designation__name=dsgn)
        .distinct('user')
    )
    for caretaker_hd in caretakers:
        send_complaint_notification(
            request_user, caretaker_hd.user,
            'lodge_comp_alert', complaint.id, 1,
            'A New Complaint has been lodged',
        )


def notify_caretaker_single(request_user, complaint, location):
    """Notify the FIRST caretaker with the designation for location (Caretaker/SP Lodge)."""
    from applications.globals.models import HoldsDesignation
    dsgn = resolve_caretaker_designation(location)
    try:
        caretaker_hd = (
            HoldsDesignation.objects
            .select_related('user', 'working', 'designation')
            .get(designation__name=dsgn)
        )
        send_complaint_notification(
            request_user, caretaker_hd.user,
            'lodge_comp_alert', complaint.id, 1,
            'A New Complaint has been lodged',
        )
    except Exception as exc:
        logger.exception('Single caretaker notification failed: %s', exc)


# ---------------------------------------------------------------------------
# Complaint lifecycle  (T-06, CS-24)
# ---------------------------------------------------------------------------

def resolve_complaint(complaint_id, yesorno, comment, image_file=None):
    """
    Mark a complaint resolved or declined.
    Returns (complaint, int_status).  Raises StudentComplain.DoesNotExist.
    """
    from .models import (
        StudentComplain,
        COMPLAINT_STATUS_RESOLVED,
        COMPLAINT_STATUS_DECLINED,
    )
    complaint = StudentComplain.objects.select_related('complainer').get(id=complaint_id)
    int_status = COMPLAINT_STATUS_RESOLVED if yesorno == 'Yes' else COMPLAINT_STATUS_DECLINED
    complaint.status = int_status
    complaint.comment = comment
    if image_file:
        complaint.upload_resolved = image_file
    complaint.save()
    return complaint, int_status


# ---------------------------------------------------------------------------
# Complaint assignment + file forwarding  (T-21, CS-20, CS-25)
# ---------------------------------------------------------------------------

def assign_complaint_to_service_provider(complaint_id, request_user):
    """
    Forward complaint to service provider:
    - Updates complaint status to ASSIGNED.
    - Sends notifications.
    - Forwards attached file via filetracking SDK.
    Returns (complaint, has_files: bool).
    """
    from applications.globals.models import HoldsDesignation, User
    from applications.filetracking.sdk.methods import forward_file
    from applications.filetracking.models import File
    from .models import StudentComplain, COMPLAINT_STATUS_ASSIGNED
    from . import selectors

    complaint = StudentComplain.objects.get(id=complaint_id)
    service_provider = selectors.get_service_provider_by_type(complaint.complaint_type)
    if service_provider is None:
        raise ValueError(f'No service provider for type: {complaint.complaint_type}')

    sp_extra_info = selectors.get_service_provider_extra_info(service_provider)
    sp_user = User.objects.get(id=sp_extra_info.user_id)

    complaint.status = COMPLAINT_STATUS_ASSIGNED
    complaint.save()

    sup_designations = (
        HoldsDesignation.objects
        .filter(user=sp_extra_info.user_id)
        .distinct('user_id')
    )
    for sup in sup_designations:
        send_complaint_notification(
            request_user, User.objects.get(id=sup.user_id),
            'comp_assigned_alert', complaint_id, 0,
            'A new complaint has been assigned to you',
        )

    files = File.objects.filter(src_object_id=complaint_id)
    if not files.exists():
        return complaint, False

    forward_file(
        file_id=files.first().id,
        receiver=sp_user.username,
        receiver_designation=sup_designations.first().designation,
        file_extra_JSON={},
        remarks='',
        file_attachment=None,
    )
    return complaint, True


# ---------------------------------------------------------------------------
# Worker management  (CS-25)
# ---------------------------------------------------------------------------

def remove_worker(work_id):
    """Remove worker if unassigned. Returns True if removed, False if still assigned."""
    from .models import Workers, StudentComplain
    worker = Workers.objects.get(id=work_id)
    if StudentComplain.objects.filter(worker_id=worker).exists():
        return False
    worker.delete()
    return True


# ---------------------------------------------------------------------------
# Status change  (T-07, CS-14, CS-36)
# ---------------------------------------------------------------------------

def change_complaint_status(complaint_id, new_status):
    """Change complaint status; clear worker on terminal statuses."""
    from .models import StudentComplain, COMPLAINT_STATUS_RESOLVED, COMPLAINT_STATUS_DECLINED
    complaint = StudentComplain.objects.get(id=complaint_id)
    complaint.status = new_status
    if str(new_status) in (
        str(COMPLAINT_STATUS_RESOLVED),
        str(COMPLAINT_STATUS_DECLINED),
    ):
        complaint.worker_id = None
    complaint.save()
    return complaint
