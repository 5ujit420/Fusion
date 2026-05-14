from applications.globals.models import ExtraInfo

from .models import Caretaker, Complaint_Admin, ServiceProvider, Warden, StudentComplain


def get_extra_info_for_user(user):
    return ExtraInfo.objects.select_related('user', 'department').filter(user=user).first()


def is_complaint_admin(extra_info):
    return Complaint_Admin.objects.filter(sup_id=extra_info).exists()


def is_service_provider(extra_info):
    return ServiceProvider.objects.filter(ser_pro_id=extra_info).exists()


def is_caretaker(extra_info):
    return Caretaker.objects.filter(staff_id=extra_info).exists()


def is_warden(extra_info):
    return Warden.objects.filter(staff_id=extra_info).exists()


def get_user_complaints(extra_info):
    return StudentComplain.objects.filter(complainer=extra_info).order_by('-id')
