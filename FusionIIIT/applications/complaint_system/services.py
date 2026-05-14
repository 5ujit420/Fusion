from datetime import datetime, timedelta

from applications.globals.models import HoldsDesignation
from notification.views import complaint_system_notif

from .models import Caretaker

FINISH_TIME_BY_TYPE = {
    'electricity': 2,
    'carpenter': 2,
    'plumber': 2,
    'garbage': 1,
    'dustbin': 1,
    'internet': 4,
    'other': 3,
}

LOCATION_TO_DESIGNATION = {
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


def get_complaint_finish_date(complaint_type):
    if not complaint_type:
        return (datetime.now() + timedelta(days=2)).date()
    return (datetime.now() + timedelta(days=FINISH_TIME_BY_TYPE.get(complaint_type.lower(), 2))).date()


def get_designation_name_for_location(location):
    return LOCATION_TO_DESIGNATION.get(location, DEFAULT_DESIGNATION)


def get_caretakers_by_designation(designation_name):
    return HoldsDesignation.objects.select_related('user', 'working', 'designation').filter(
        designation__name=designation_name
    )


def notify_caretakers(request_user, caretakers, complaint_id, student=1, message='A New Complaint has been lodged'):
    for caretaker in caretakers:
        complaint_system_notif(request_user, caretaker.user, 'lodge_comp_alert', complaint_id, student, message)


def compute_rating(existing_rating, new_rating, integer=False):
    if existing_rating == 0:
        return int(new_rating) if integer else new_rating
    result = (existing_rating + new_rating) / 2
    return int(result) if integer else result


def update_area_caretaker_feedback(area, feedback, rating, integer=False):
    caretakers = Caretaker.objects.filter(area=area).order_by('-id')
    for caretaker in caretakers:
        caretaker.myfeedback = feedback
        caretaker.rating = compute_rating(caretaker.rating, rating, integer=integer)
        caretaker.save()


def update_caretaker_rating_for_location(location, rating, integer=True):
    caretaker = Caretaker.objects.filter(area=location).first()
    if not caretaker:
        return None
    caretaker.rating = compute_rating(caretaker.rating, rating, integer=integer)
    caretaker.save()
    return caretaker
