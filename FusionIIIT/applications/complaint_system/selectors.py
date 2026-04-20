from .models import StudentComplain, Caretaker, Warden, ServiceProvider

def get_student_complaints(user_extrainfo):
    return StudentComplain.objects.filter(
        complainer=user_extrainfo
    ).select_related('complainer', 'complainer__user', 'complainer__department', 'worker_id').order_by('-id')

def get_complaints_by_location(location):
    return StudentComplain.objects.filter(
        location=location
    ).select_related('complainer', 'complainer__user', 'complainer__department', 'worker_id').order_by('-id')

def get_complaints_by_type_and_status(complaint_type, statuses):
    if not isinstance(statuses, list):
        statuses = [statuses]
    return StudentComplain.objects.filter(
        complaint_type=complaint_type, 
        status__in=statuses
    ).select_related('complainer', 'complainer__user', 'complainer__department', 'worker_id').order_by('-id')

def get_complaint_detail(complaint_id):
    return StudentComplain.objects.select_related(
        'complainer', 'complainer__user', 'complainer__department', 'worker_id'
    ).get(id=complaint_id)

def get_all_complaints():
    return StudentComplain.objects.select_related(
        'complainer', 'complainer__user', 'complainer__department', 'worker_id'
    ).all().order_by('-id')

def get_pending_complaints_by_location(location):
    return StudentComplain.objects.filter(
        location=location, status=0
    ).select_related('complainer', 'complainer__user', 'complainer__department', 'worker_id').order_by('-id')
