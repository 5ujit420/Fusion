from datetime import datetime, timedelta
from typing import Dict, Iterable, Optional

from django.shortcuts import get_object_or_404

from applications.filetracking.sdk.methods import forward_file

from notification.views import complaint_system_notif

from . import selectors
from .models import (
    Complaint_Admin,
    ServiceAuthority,
    ServiceProvider,
    Warden,
    STATUS_DECLINED,
    STATUS_FORWARDED,
    STATUS_PENDING,
    STATUS_RESOLVED,
)


USER_COMPLAINT_FINISH_DAYS = {
    "Electricity": 2,
    "Carpenter": 2,
    "Plumber": 2,
    "Garbage": 1,
    "Dustbin": 1,
    "Internet": 4,
    "Other": 3,
}

STAFF_COMPLAINT_FINISH_DAYS = {
    "Electricity": 2,
    "carpenter": 2,
    "plumber": 2,
    "garbage": 1,
    "dustbin": 1,
    "internet": 4,
    "other": 3,
}

LOCATION_DESIGNATION_MAP = {
    "hall-1": "hall1caretaker",
    "hall-3": "hall3caretaker",
    "hall-4": "hall4caretaker",
    "CC1": "cc1convener",
    "CC2": "CC2 convener",
    "core_lab": "corelabcaretaker",
    "LHTC": "lhtccaretaker",
    "NR2": "nr2caretaker",
    "Maa Saraswati Hostel": "mshcaretaker",
    "Nagarjun Hostel": "nhcaretaker",
    "Panini Hostel": "phcaretaker",
}
DEFAULT_LOCATION_DESIGNATION = "rewacaretaker"


def get_finish_date(complaint_type, actor_scope):
    if actor_scope == "user":
        days = USER_COMPLAINT_FINISH_DAYS.get(complaint_type, 2)
    else:
        days = STAFF_COMPLAINT_FINISH_DAYS.get(complaint_type, 2)
    return (datetime.now() + timedelta(days=days)).date()


def get_designation_for_location(location):
    return LOCATION_DESIGNATION_MAP.get(location, DEFAULT_LOCATION_DESIGNATION)


def prepare_complaint_payload(data, complainer_id, actor_scope):
    payload = data.copy()
    payload["complainer"] = complainer_id
    payload["status"] = STATUS_PENDING
    payload["complaint_finish"] = get_finish_date(payload.get("complaint_type", ""), actor_scope)
    return payload


def notify_lodged_complaint(sender, complaint, location, notify_all):
    designation_name = get_designation_for_location(location)
    message = "A New Complaint has been lodged"
    if notify_all:
        caretakers = selectors.list_distinct_holds_designations(designation_name)
        for caretaker in caretakers:
            complaint_system_notif(
                sender,
                caretaker.user,
                "lodge_comp_alert",
                complaint.id,
                1,
                message,
            )
        return

    caretaker = selectors.get_single_designation_holder(designation_name)
    complaint_system_notif(sender, caretaker.user, "lodge_comp_alert", complaint.id, 1, message)


def route_user(extrainfo):
    role_flags = selectors.get_user_role_flags(extrainfo)
    if role_flags["is_service_provider"]:
        return {"user_type": "service_provider", "next_url": "/complaint/service_provider/"}
    if role_flags["is_complaint_admin"]:
        return {"user_type": "complaint_admin", "next_url": "/complaint/complaint_admin/"}
    if role_flags["is_caretaker"]:
        return {"user_type": "caretaker", "next_url": "/complaint/caretaker/"}
    if role_flags["is_warden"]:
        return {"user_type": "warden", "next_url": "/complaint/warden/"}
    if extrainfo and extrainfo.user_type in {"student", "staff", "faculty"}:
        return {"user_type": extrainfo.user_type, "next_url": "/complaint/user/"}
    return None


def update_caretaker_feedback(feedback, rating, caretaker_type):
    for caretaker in selectors.get_all_caretakers_by_area(caretaker_type):
        if caretaker.rating == 0:
            new_rating = rating
        else:
            new_rating = (caretaker.rating + rating) / 2
        caretaker.myfeedback = feedback
        caretaker.rating = new_rating
        caretaker.save()


def update_complaint_feedback_and_rating(complaint_id, feedback, rating, cast_rating_to_int):
    selectors.update_complaint(complaint_id, feedback=feedback, flag=rating)
    complaint = selectors.get_complaint_or_none(complaint_id, selectors.COMPLAINT_RELATED_FIELDS)
    caretaker = selectors.get_caretaker_by_area(complaint.location)
    if caretaker.rating == 0:
        new_rating = rating
    else:
        new_rating = (rating + caretaker.rating) / 2
        if cast_rating_to_int:
            new_rating = int(new_rating)
    caretaker.rating = new_rating
    caretaker.save()
    return complaint, caretaker


def resolve_pending_complaint(request_user, complaint_id, serializer, request_files, notify_on_decline):
    newstatus = serializer.validated_data["yesorno"]
    comment = serializer.validated_data.get("comment", "")
    int_status = STATUS_RESOLVED if newstatus == "Yes" else STATUS_DECLINED
    selectors.update_complaint(complaint_id, status=int_status, comment=comment)
    complaint = selectors.get_complaint(complaint_id)
    complaint.status = int_status
    complaint.comment = comment
    if "upload_resolved" in request_files:
        complaint.upload_resolved = request_files["upload_resolved"]
    complaint.save()

    complainer_details = selectors.get_complaint(complaint_id, ("complainer", "complainer__user"))
    if newstatus == "Yes":
        message = "Congrats! Your complaint has been resolved"
        notification_type = "comp_resolved_alert"
    else:
        if notify_on_decline:
            message = "Your complaint has been declined"
            notification_type = "comp_declined_alert"
        else:
            message = "Congrats! Your complaint has been resolved"
            notification_type = "comp_resolved_alert"

    complaint_system_notif(
        request_user,
        complainer_details.complainer.user,
        notification_type,
        complainer_details.id,
        0,
        message,
    )


def change_complaint_status(complaint, status_value):
    complaint.status = status_value
    if status_value in {"3", "2"}:
        complaint.worker_id = None
    complaint.save()


def forward_complaint(request_user, complaint):
    service_providers = selectors.list_service_providers_by_type(complaint.complaint_type)
    if not service_providers.exists():
        return {"error": "ServiceProvider does not exist for this complaint type"}, None, 404

    service_provider = service_providers.first()
    service_provider_details = service_provider.ser_pro_id
    complaint.status = STATUS_FORWARDED
    complaint.save()

    sup_designations = selectors.list_designation_holders_for_user_id(service_provider_details.user_id)
    user_ids = [designation.user_id for designation in sup_designations]
    users_by_id = {user.id: user for user in selectors.list_users_by_ids(user_ids)}
    for sup in sup_designations:
        recipient = users_by_id.get(sup.user_id)
        if recipient is not None:
            complaint_system_notif(
                request_user,
                recipient,
                "comp_assigned_alert",
                complaint.id,
                0,
                "A new complaint has been assigned to you",
            )

    files = selectors.list_files_for_complaint(complaint.id)
    if not files.exists():
        return {"error": "No files associated with this complaint"}, None, 206

    forward_file(
        file_id=files.first().id,
        receiver=service_provider_details.user.username,
        receiver_designation=sup_designations.first().designation,
        file_extra_JSON={},
        remarks="",
        file_attachment=None,
    )
    return {"success": "Complaint assigned to service_provider"}, service_provider, 200


def get_report_queryset(user):
    complaint_admin_user = None
    complaints = None

    try:
        complaint_admin_user = selectors.get_complaint_admin_for_user(user.extrainfo)
        complaints = selectors.list_all_complaints()
    except Complaint_Admin.DoesNotExist:
        complaint_admin_user = None

    if complaint_admin_user:
        return complaints

    is_caretaker = hasattr(user, "caretaker")
    is_service_provider = False
    is_complaint_admin = hasattr(user, "complaint_admin")

    try:
        service_provider = selectors.get_service_provider_for_user(user.extrainfo)
        is_service_provider = True
    except ServiceProvider.DoesNotExist:
        service_provider = None
        is_service_provider = False

    try:
        selectors.get_service_authority_for_user(user.extrainfo)
        is_service_authority = True
    except ServiceAuthority.DoesNotExist:
        is_service_authority = False

    try:
        warden = selectors.get_warden_for_user(user.extrainfo)
        is_warden = True
    except Warden.DoesNotExist:
        warden = None
        is_warden = False

    if (
        not is_caretaker
        and not is_service_provider
        and not is_complaint_admin
        and not is_service_provider
        and not is_service_provider
        and not is_service_authority
        and not is_warden
    ):
        return None

    if is_service_provider:
        complaints = selectors.list_complaints_for_type(service_provider.type).filter(status__in=[1, 2, 3])
    if is_caretaker and not is_service_provider and not is_warden:
        caretaker = get_object_or_404(selectors.Caretaker, staff_id=user.extrainfo)
        complaints = selectors.list_complaints_for_location(caretaker.area)
    if is_warden:
        warden = get_object_or_404(selectors.Warden, staff_id=user.extrainfo)
        complaints = selectors.list_complaints_for_location(warden.area)
    if is_complaint_admin:
        complaints = selectors.list_all_complaints()
    return complaints
