import logging
from datetime import datetime, timedelta

from notification.views import complaint_system_notif
from applications.filetracking.sdk.methods import forward_file

from .models import (
    Caretaker, Warden, StudentComplain, ServiceProvider,
    Complaint_Admin, ServiceAuthority, Workers, ComplaintStatus,
)
from . import selectors

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants: complaint type -> finish days
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
# Constants: location -> designation
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
# Helper: calculate complaint finish date
# ---------------------------------------------------------------------------

def calculate_complaint_finish_date(complaint_type):
    days = COMPLAINT_TYPE_DAYS.get(complaint_type, DEFAULT_FINISH_DAYS)
    return (datetime.now() + timedelta(days=days)).date()


# ---------------------------------------------------------------------------
# Helper: resolve location to caretaker designation
# ---------------------------------------------------------------------------

def resolve_location_to_designation(location):
    return LOCATION_DESIGNATION_MAP.get(location, DEFAULT_DESIGNATION)


# ---------------------------------------------------------------------------
# Helper: update caretaker rating
# ---------------------------------------------------------------------------

def _update_caretaker_rating(caretaker, new_rating):
    rate = caretaker.rating
    if rate == 0:
        caretaker.rating = new_rating
    else:
        caretaker.rating = int((new_rating + rate) / 2)
    caretaker.save()


# ---------------------------------------------------------------------------
# Determine user type
# ---------------------------------------------------------------------------

def determine_user_type(user):
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
# Lodge complaint
# ---------------------------------------------------------------------------

def lodge_complaint(user, validated_data, notify_single=False):
    extra = selectors.get_extrainfo_by_user(user)
    validated_data['complainer'] = extra.id
    validated_data['status'] = ComplaintStatus.PENDING

    comp_type = validated_data.get('complaint_type', '')
    validated_data['complaint_finish'] = calculate_complaint_finish_date(comp_type)

    from .api.serializers import StudentComplainSerializer
    serializer = StudentComplainSerializer(data=validated_data)
    serializer.is_valid(raise_exception=True)
    complaint = serializer.save()

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
    all_caretaker = selectors.get_caretakers_by_area(caretaker_type)
    for caretaker in all_caretaker:
        _update_caretaker_rating(caretaker, rating)
        caretaker.myfeedback = feedback
        caretaker.save()


# ---------------------------------------------------------------------------
# Submit complaint feedback
# ---------------------------------------------------------------------------

def submit_complaint_feedback(complaint_id, feedback, rating):
    selectors.update_complaint_feedback(complaint_id, feedback, rating)
    complaint = selectors.get_complaint_by_id(complaint_id)
    caretaker = selectors.get_caretaker_by_area(complaint.location)
    if caretaker:
        _update_caretaker_rating(caretaker, rating)


# ---------------------------------------------------------------------------
# Resolve complaint
# ---------------------------------------------------------------------------

def resolve_complaint(cid, yesorno, comment, upload_file, requesting_user):
    intstatus = ComplaintStatus.RESOLVED if yesorno == 'Yes' else ComplaintStatus.DECLINED

    complaint = selectors.get_complaint_by_id_basic(cid)
    complaint.status = intstatus
    complaint.comment = comment

    if upload_file:
        complaint.upload_resolved = upload_file

    complaint.save()

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
# Forward complaint to service provider
# ---------------------------------------------------------------------------

def forward_complaint_to_service_provider(comp_id, requesting_user):
    complaint = selectors.get_complaint_by_id_basic(comp_id)
    complaint_type = complaint.complaint_type

    service_providers = selectors.get_service_providers_by_type(complaint_type)
    if not service_providers.exists():
        return {'error': 'ServiceProvider does not exist for this complaint type'}, 404

    service_provider = service_providers.first()
    service_provider_details = selectors.get_extrainfo_by_id(service_provider.ser_pro_id.id)

    complaint.status = ComplaintStatus.FORWARDED
    complaint.save()

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
# Change complaint status
# ---------------------------------------------------------------------------

def change_complaint_status(complaint_id, new_status):
    complaint = selectors.get_complaint_by_id_basic(complaint_id)
    complaint.status = new_status
    if new_status in ('2', '3'):
        complaint.worker_id = None
    complaint.save()


# ---------------------------------------------------------------------------
# Remove worker
# ---------------------------------------------------------------------------

def remove_worker(work_id):
    worker = selectors.get_worker_by_id(work_id)
    assigned = selectors.get_complaints_assigned_to_worker(worker)
    if assigned == 0:
        worker.delete()
        return True, 'Worker removed successfully'
    return False, 'Worker is assigned to some complaints'


# ---------------------------------------------------------------------------
# Delete complaint
# ---------------------------------------------------------------------------

def delete_complaint(complaint_id, requesting_user):
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
# Generate report
# ---------------------------------------------------------------------------

def generate_report(user):
    extra = selectors.get_extrainfo_by_user(user)

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
        caretaker = selectors.get_caretaker_by_extrainfo(extra)
        complaints = selectors.get_complaints_for_report_area(caretaker.area)

    if is_warden_flag and warden:
        warden_obj = selectors.get_warden_by_extrainfo(extra)
        complaints = selectors.get_complaints_for_report_area(warden_obj.area)

    if is_complaint_admin_attr:
        complaints = selectors.get_all_complaints()

    return complaints, None


# ---------------------------------------------------------------------------
# Get complaints for user (api views helper)
# ---------------------------------------------------------------------------

def get_complaints_for_user(user):
    extra = selectors.get_extrainfo_by_user(user)

    if extra.user_type == 'student':
        return selectors.get_complaints_by_complainer(extra)
    elif extra.user_type == 'staff':
        caretaker = selectors.get_caretaker_by_staff_id(extra.id)
        return selectors.get_complaints_by_location(caretaker.area)
    elif extra.user_type == 'faculty':
        sp = selectors.get_service_provider_by_extrainfo(extra)
        return selectors.get_complaints_by_location(sp.type)
    return selectors.get_empty_complaints_queryset()


# ---------------------------------------------------------------------------
# Get complaint detail (api views helper)
# ---------------------------------------------------------------------------

def get_complaint_detail_for_api(complaint_id):
    complaint = selectors.get_complaint_by_id(complaint_id)

    worker_data = {}
    if complaint.worker_id is not None:
        worker = selectors.get_worker_by_id(complaint.worker_id_id)
        from .api.serializers import WorkersSerializer
        worker_data = WorkersSerializer(instance=worker).data

    complainer_user = selectors.get_user_by_username(complaint.complainer.user.username)
    complainer_extra = selectors.get_extrainfo_by_id(complainer_user.id)

    return {
        'complaint': complaint,
        'worker_data': worker_data,
        'complainer_user': complainer_user,
        'complainer_extra_info': complainer_extra,
    }


# ---------------------------------------------------------------------------
# Create worker
# ---------------------------------------------------------------------------

def create_worker(validated_data):
    from .api.serializers import WorkersSerializer
    serializer = WorkersSerializer(data=validated_data)
    serializer.is_valid(raise_exception=True)
    return serializer.save(), serializer.data


# ---------------------------------------------------------------------------
# Update worker
# ---------------------------------------------------------------------------

def update_worker(worker_id, validated_data):
    worker = selectors.get_worker_by_id(worker_id)
    from .api.serializers import WorkersSerializer
    serializer = WorkersSerializer(worker, data=validated_data)
    serializer.is_valid(raise_exception=True)
    return serializer.save(), serializer.data


# ---------------------------------------------------------------------------
# Delete worker
# ---------------------------------------------------------------------------

def delete_worker(worker_id):
    worker = selectors.get_worker_by_id(worker_id)
    worker.delete()
    return True


# ---------------------------------------------------------------------------
# Create complaint (API)
# ---------------------------------------------------------------------------

def create_complaint(validated_data):
    from .api.serializers import StudentComplainSerializer
    serializer = StudentComplainSerializer(data=validated_data)
    serializer.is_valid(raise_exception=True)
    return serializer.save(), serializer.data


# ---------------------------------------------------------------------------
# Update complaint (API)
# ---------------------------------------------------------------------------

def update_complaint(complaint_id, validated_data):
    complaint = selectors.get_complaint_by_id_basic(complaint_id)
    from .api.serializers import StudentComplainSerializer
    serializer = StudentComplainSerializer(complaint, data=validated_data)
    serializer.is_valid(raise_exception=True)
    return serializer.save(), serializer.data


# ---------------------------------------------------------------------------
# Delete complaint by ID (API, no auth check)
# ---------------------------------------------------------------------------

def delete_complaint_by_id(complaint_id):
    complaint = selectors.get_complaint_by_id_basic(complaint_id)
    complaint.delete()
    return True


# ---------------------------------------------------------------------------
# Create caretaker
# ---------------------------------------------------------------------------

def create_caretaker(validated_data):
    from .api.serializers import CaretakerSerializer
    serializer = CaretakerSerializer(data=validated_data)
    serializer.is_valid(raise_exception=True)
    return serializer.save(), serializer.data


# ---------------------------------------------------------------------------
# Update caretaker
# ---------------------------------------------------------------------------

def update_caretaker(caretaker_id, validated_data):
    caretaker = selectors.get_caretaker_by_pk(caretaker_id)
    from .api.serializers import CaretakerSerializer
    serializer = CaretakerSerializer(caretaker, data=validated_data)
    serializer.is_valid(raise_exception=True)
    return serializer.save(), serializer.data


# ---------------------------------------------------------------------------
# Delete caretaker
# ---------------------------------------------------------------------------

def delete_caretaker(caretaker_id):
    caretaker = selectors.get_caretaker_by_pk(caretaker_id)
    caretaker.delete()
    return True


# ---------------------------------------------------------------------------
# Create service provider
# ---------------------------------------------------------------------------

def create_service_provider(validated_data):
    from .api.serializers import ServiceProviderSerializer
    serializer = ServiceProviderSerializer(data=validated_data)
    serializer.is_valid(raise_exception=True)
    return serializer.save(), serializer.data


# ---------------------------------------------------------------------------
# Update service provider
# ---------------------------------------------------------------------------

def update_service_provider(sp_id, validated_data):
    sp = selectors.get_service_provider_by_pk(sp_id)
    from .api.serializers import ServiceProviderSerializer
    serializer = ServiceProviderSerializer(sp, data=validated_data)
    serializer.is_valid(raise_exception=True)
    return serializer.save(), serializer.data


# ---------------------------------------------------------------------------
# Delete service provider
# ---------------------------------------------------------------------------

def delete_service_provider(sp_id):
    sp = selectors.get_service_provider_by_pk(sp_id)
    sp.delete()
    return True
