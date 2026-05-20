from django.db.models import Q
from .models import PlacementRecord, StudentRecord, PlacementStatus, NotifyStudent
from applications.academic_information.models import Student


def placement_records_filter(placement_type=None, name_contains=None, ctc_min=None, year=None):
    qs = PlacementRecord.objects.all()
    if placement_type:
        qs = qs.filter(placement_type=placement_type)
    if name_contains:
        qs = qs.filter(name__icontains=name_contains)
    if ctc_min is not None:
        qs = qs.filter(ctc__gte=ctc_min)
    if year is not None:
        qs = qs.filter(year=year)
    return qs


def student_records_for_placement(placement_qs=None, student_qs=None):
    if placement_qs is None:
        placement_qs = PlacementRecord.objects.all()
    if student_qs is None:
        student_qs = Student.objects.all()
    return StudentRecord.objects.select_related('unique_id', 'record_id').filter(
        Q(record_id__in=placement_qs), Q(unique_id__in=student_qs)
    )


def placementstatus_for_notify_filter(placement_type=None, company_name_contains=None, ctc_min=None, student_qs=None):
    notify_qs = NotifyStudent.objects.all()
    if placement_type:
        notify_qs = notify_qs.filter(placement_type=placement_type)
    if company_name_contains:
        notify_qs = notify_qs.filter(company_name__icontains=company_name_contains)
    if ctc_min is not None:
        notify_qs = notify_qs.filter(ctc__gte=ctc_min)
    if student_qs is None:
        student_qs = Student.objects.all()
    return PlacementStatus.objects.select_related('unique_id', 'notify_id').filter(
        Q(notify_id__in=notify_qs), Q(unique_id__in=student_qs)
    )
