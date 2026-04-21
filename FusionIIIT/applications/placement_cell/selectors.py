from django.db.models import Count, Q
from .models import PlacementRecord, StudentRecord

def get_placement_years():
    return PlacementRecord.objects.filter(~Q(placement_type="HIGHER STUDIES")) \
        .values('year').annotate(year_count=Count('year'))

def get_placement_records_summary():
    return PlacementRecord.objects.values('name', 'year', 'ctc', 'placement_type') \
        .annotate(Count('name'), Count('year'), Count('placement_type'), Count('ctc'))

def get_student_records_with_department():
    # Fix for N+1 Query Problem: Missing select_related
    return StudentRecord.objects.select_related(
        'unique_id__id__department', 'record_id'
    ).all()

def get_student_placement_records(first_name, last_name, rollno, cname, ctc, year=None, placement_type="PLACEMENT"):
    # Fix for Repeated Filter Chains
    from applications.academic_information.models import Student
    from applications.globals.models import ExtraInfo
    from django.contrib.auth.models import User
    
    user_query = Q(first_name__icontains=first_name, last_name__icontains=last_name)
    extrainfo_query = Q(user__in=User.objects.filter(user_query), id__icontains=rollno)
    student_query = Q(id__in=ExtraInfo.objects.filter(extrainfo_query))
    
    placement_query = Q(placement_type=placement_type, name__icontains=cname, ctc__gte=ctc)
    if year:
        placement_query &= Q(year=year)
        
    return StudentRecord.objects.select_related('unique_id__id__department', 'record_id').filter(
        Q(record_id__in=PlacementRecord.objects.filter(placement_query)) &
        Q(unique_id__in=Student.objects.filter(student_query))
    )
