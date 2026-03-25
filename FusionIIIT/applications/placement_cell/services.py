from django.utils import timezone
from applications.placement_cell.models import (
    PlacementRecord, ChairmanVisit, PlacementSchedule, Role, NotifyStudent,
    PlacementStatus, Skill, Has, Education, Course, Experience, Project,
    Achievement, Publication, Patent
)
from .selectors import get_student_records, get_skill_by_name

def save_placement_schedule(data):
    role, _ = Role.objects.get_or_create(role=data.get('role'))
    notify = NotifyStudent.objects.create(
        placement_type=data.get('placement_type'),
        company_name=data.get('company_name'),
        description=data.get('description'),
        ctc=data.get('ctc'),
        timestamp=data.get('time_stamp')
    )
    schedule = PlacementSchedule.objects.create(
        notify_id=notify,
        title=data.get('title') or data.get('company_name'),
        description=data.get('description'),
        placement_date=data.get('placement_date'),
        attached_file=data.get('resume'),
        role=role,
        location=data.get('location'),
        time=data.get('schedule_at')
    )
    return schedule

def delete_placement_record(record_id):
    PlacementRecord.objects.filter(id=record_id).delete()

def save_placement_record(data):
    record = PlacementRecord.objects.create(
        placement_type=data.get('placement_type'),
        name=data.get('student_name'),
        ctc=data.get('ctc'),
        year=data.get('year'),
        test_type=data.get('test_type'),
        test_score=data.get('test_score')
    )
    return record

def save_chairman_visit(data):
    visit = ChairmanVisit.objects.create(
        company_name=data.get('company_name'),
        location=data.get('location'),
        visiting_date=data.get('date'),
        description=data.get('description'),
        timestamp=data.get('timestamp')
    )
    return visit

def update_invitation_status(pk, action):
    status_obj = PlacementStatus.objects.filter(pk=pk).first()
    if status_obj:
        if action == 'ACCEPT':
            status_obj.invitation = 'ACCEPTED'
        elif action == 'REJECT':
            status_obj.invitation = 'REJECTED'
        status_obj.timestamp = timezone.now()
        status_obj.save()
    return status_obj

def delete_invitation_status(pk):
    PlacementStatus.objects.filter(pk=pk).delete()

def create_has_skill(user, skill_name, skill_rating):
    student = get_student_records(user)
    skill, _ = Skill.objects.get_or_create(skill=skill_name)
    has_obj = Has.objects.create(
        unique_id=student,
        skill_id=skill,
        skill_rating=skill_rating
    )
    return has_obj
    
def calculate_placement_statistics():
    # Return abstracted statistics mapped natively from queries
    return PlacementRecord.objects.values('year', 'placement_type').order_by('-year')

def get_placement_schedule_list():
    return PlacementSchedule.objects.select_related('notify_id', 'role').all()
