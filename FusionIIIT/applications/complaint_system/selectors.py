from applications.globals.models import ExtraInfo, HoldsDesignation, User
from django.shortcuts import get_object_or_404
from django.db.models import QuerySet
from applications.filetracking.models import File
from .models import (
    Caretaker, Warden, Complaint_Admin, ServiceProvider, 
    StudentComplain, Workers, AreaChoices, ComplaintTypeChoices, ServiceAuthority
)


def get_extrainfo_by_user(user) -> ExtraInfo:
    """Gets the ExtraInfo for a given User."""
    return ExtraInfo.objects.select_related("user", "department").filter(user=user).first()


def get_extrainfo_by_id(extra_info_id) -> ExtraInfo:
    """Gets ExtraInfo by its primary key."""
    return ExtraInfo.objects.get(id=extra_info_id)


def get_user_by_username(username: str) -> User:
    """Gets User by username."""
    return get_object_or_404(User, username=username)


def get_complaints_by_complainer(extrainfo: ExtraInfo) -> QuerySet[StudentComplain]:
    """Retrieves all complaints lodged by a specific user (complainer)."""
    return StudentComplain.objects.filter(complainer=extrainfo).order_by("-id")


def get_complaints_by_location(location: str) -> QuerySet[StudentComplain]:
    """Retrieves all complaints for a specific location (area)."""
    return StudentComplain.objects.filter(location=location).order_by("-id")


def get_complaints_by_type_and_status(complaint_type: str, statuses: list) -> QuerySet[StudentComplain]:
    """Retrieves complaints by their type and a list of accepted statuses."""
    return StudentComplain.objects.filter(complaint_type=complaint_type, status__in=statuses).order_by("-id")


def get_all_complaints() -> QuerySet[StudentComplain]:
    """Retrieves all complaints in the system."""
    return StudentComplain.objects.all()


def get_complaint_by_id(complaint_id) -> StudentComplain:
    """Retrieves a single complaint by its ID matching old views logic."""
    return StudentComplain.objects.get(id=complaint_id)


def get_complaint_detail_by_id(complaint_id) -> StudentComplain:
    """Retrieves a single complaint with select_related optimization for detail views."""
    return StudentComplain.objects.select_related(
        "complainer", "complainer__user", "complainer__department"
    ).get(id=complaint_id)


def get_caretaker_by_extrainfo(extrainfo: ExtraInfo) -> Caretaker:
    """Retrieves the Caretaker instance linked to an ExtraInfo."""
    return Caretaker.objects.select_related("staff_id").get(staff_id=extrainfo)


def get_caretaker_by_location(location: str):
    """Retrieves a single Caretaker for a specific location. Can return None."""
    return Caretaker.objects.filter(area=location).first()


def get_caretaker_by_id(caretaker_id) -> Caretaker:
    """Retrieves the Caretaker instance by its ID."""
    return Caretaker.objects.select_related("staff_id", "staff_id__user", "staff_id__department").get(id=caretaker_id)


def get_warden_by_extrainfo(extrainfo: ExtraInfo) -> Warden:
    """Retrieves the Warden instance linked to an ExtraInfo."""
    return Warden.objects.get(staff_id=extrainfo)


def get_service_provider_by_extrainfo(extrainfo: ExtraInfo) -> ServiceProvider:
    """Retrieves the ServiceProvider instance linked to an ExtraInfo."""
    return ServiceProvider.objects.select_related("ser_pro_id").get(ser_pro_id=extrainfo)


def get_service_providers_by_type(complaint_type: str) -> QuerySet[ServiceProvider]:
    """Retrieves ServiceProviders handling a specific complaint type."""
    return ServiceProvider.objects.filter(type=complaint_type)


def get_complaint_admin_by_extrainfo(extrainfo: ExtraInfo) -> Complaint_Admin:
    """Retrieves the Complaint_Admin instance linked to an ExtraInfo."""
    return Complaint_Admin.objects.get(sup_id=extrainfo)


def get_service_authority_by_extrainfo(extrainfo: ExtraInfo) -> ServiceAuthority:
    """Retrieves the ServiceAuthority instance linked to an ExtraInfo."""
    return ServiceAuthority.objects.get(ser_pro_id=extrainfo)


def get_all_caretakers() -> QuerySet[Caretaker]:
    """Retrieves all Caretakers."""
    return Caretaker.objects.all()


def get_caretakers_by_area(area: str) -> QuerySet[Caretaker]:
    """Retrieves all Caretakers assigned to a specific area."""
    return Caretaker.objects.filter(area=area).order_by("-id")


def get_all_wardens() -> QuerySet[Warden]:
    """Retrieves all Wardens."""
    return Warden.objects.all()


def get_all_complaint_admins() -> QuerySet[Complaint_Admin]:
    """Retrieves all Complaint Admins."""
    return Complaint_Admin.objects.all()


def get_all_service_providers() -> QuerySet[ServiceProvider]:
    """Retrieves all ServiceProviders."""
    return ServiceProvider.objects.all()


def get_all_workers() -> QuerySet[Workers]:
    """Retrieves all Workers."""
    return Workers.objects.all()


def get_worker_by_id(worker_id) -> Workers:
    """Retrieves a single Worker by id."""
    return Workers.objects.get(id=worker_id)


def get_assigned_complaints_count_for_worker(worker: Workers) -> int:
    """Counts how many complaints are currently assigned to a worker."""
    return StudentComplain.objects.filter(worker_id=worker).count()


def get_holds_designations_by_name(designation_name: str) -> QuerySet[HoldsDesignation]:
    """Retrieves user designations by the name of the designation."""
    return HoldsDesignation.objects.select_related(
        "user", "working", "designation"
    ).filter(designation__name=designation_name).distinct("user")


def get_holds_designations_by_user(user_id) -> QuerySet[HoldsDesignation]:
    """Retrieves all designations held by a specific user via distinct('user_id')."""
    return HoldsDesignation.objects.filter(user=user_id).distinct("user_id")


def get_files_for_complaint(complaint_id) -> QuerySet[File]:
    """Retrieves file attachments linked to a complaint from filetracking sdk."""
    return File.objects.filter(src_object_id=complaint_id)


def check_user_roles(extrainfo: ExtraInfo) -> dict:
    """
    Checks the user's roles across Caretaker, Warden, ServiceProvider, and Admin.
    Replaces the manual iteration blocks in CheckUser view.
    """
    
    # We query the existence using DB optimized `.exists()` rather than Python loops
    is_caretaker = Caretaker.objects.filter(staff_id=extrainfo).exists()
    is_warden = Warden.objects.filter(staff_id=extrainfo).exists()
    is_service_provider = ServiceProvider.objects.filter(ser_pro_id=extrainfo).exists()
    is_complaint_admin = Complaint_Admin.objects.filter(sup_id=extrainfo).exists()

    return {
        "is_caretaker": is_caretaker,
        "is_warden": is_warden,
        "is_service_provider": is_service_provider,
        "is_complaint_admin": is_complaint_admin,
        "user_type": extrainfo.user_type, # 'student', 'staff', 'faculty'
    }

def get_report_complaints_for_user(user, extrainfo: ExtraInfo) -> QuerySet[StudentComplain]:
    """
    Generates the queryset for the generate-report endpoint, filtering purely by user role.
    Extracts the massive conditional block from GenerateReportView.get().
    """
    roles = check_user_roles(extrainfo)

    if roles["is_complaint_admin"]:
        # Admin sees all complaints
        return StudentComplain.objects.all()

    if roles["is_service_provider"]:
        # Service provider sees complaints matching their type
        service_provider = get_service_provider_by_extrainfo(extrainfo)
        return StudentComplain.objects.filter(complaint_type=service_provider.type, status__in=[1, 2, 3])

    if roles["is_caretaker"] and not roles["is_warden"]:
        # Caretaker sees complaints in their area
        caretaker = get_caretaker_by_extrainfo(extrainfo)
        return StudentComplain.objects.filter(location=caretaker.area)

    if roles["is_warden"]:
        # Warden sees complaints in their area
        warden = get_warden_by_extrainfo(extrainfo)
        return StudentComplain.objects.filter(location=warden.area)

    return StudentComplain.objects.none()
