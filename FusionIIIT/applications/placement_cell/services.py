"""
Services for placement_cell module.

All business logic is centralized here. Views delegate to service functions
instead of containing inline logic.

Audit refs: S01, S06-S20, S46, R07, R08, R11
"""
import datetime
import logging

from django.contrib import messages
from django.db.models import Q
from django.utils import timezone

from applications.academic_information.models import Student
from applications.globals.models import ExtraInfo
from notification.views import placement_cell_notif

from .models import (
    Achievement, ChairmanVisit, CompanyDetails, Conference, Course,
    Education, Experience, Extracurricular, Has, NotifyStudent, Patent,
    PlacementRecord, PlacementSchedule, PlacementStatus, Project,
    Publication, Reference, Role, Skill, StudentPlacement, StudentRecord,
    DEPT_CSE, DEPT_ECE, DEPT_ME,
)
from . import selectors

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Student entity CRUD  (S15, R07 — consolidated from duplicated blocks)
# ---------------------------------------------------------------------------

def create_education(student, data):
    """Create an Education record for a student."""
    education_obj = Education.objects.select_related('unique_id').create(
        unique_id=student,
        degree=data['degree'],
        grade=data['grade'],
        institute=data['institute'],
        stream=data['stream'],
        sdate=data['sdate'],
        edate=data['edate'],
    )
    education_obj.save()
    return education_obj


def create_skill_entry(student, data):
    """Create a Has (skill) record for a student."""
    has_obj = Has.objects.select_related('skill_id', 'unique_id').create(
        unique_id=student,
        skill_id=Skill.objects.get(skill=data['skill']),
        skill_rating=data['skill_rating'],
    )
    has_obj.save()
    return has_obj


def create_achievement(student, data):
    """Create an Achievement record for a student."""
    achievement_obj = Achievement.objects.select_related('unique_id').create(
        unique_id=student,
        achievement=data['achievement'],
        achievement_type=data['achievement_type'],
        description=data['description'],
        issuer=data['issuer'],
        date_earned=data['date_earned'],
    )
    achievement_obj.save()
    return achievement_obj


def create_publication(student, data):
    """Create a Publication record for a student."""
    publication_obj = Publication.objects.select_related('unique_id').create(
        unique_id=student,
        publication_title=data['publication_title'],
        publisher=data['publisher'],
        description=data['description'],
        publication_date=data['publication_date'],
    )
    publication_obj.save()
    return publication_obj


def create_patent(student, data):
    """Create a Patent record for a student."""
    patent_obj = Patent.objects.select_related('unique_id').create(
        unique_id=student,
        patent_name=data['patent_name'],
        patent_office=data['patent_office'],
        description=data['description'],
        patent_date=data['patent_date'],
    )
    patent_obj.save()
    return patent_obj


def create_course(student, data):
    """Create a Course record for a student."""
    course_obj = Course.objects.select_related('unique_id').create(
        unique_id=student,
        course_name=data['course_name'],
        license_no=data['license_no'],
        description=data['description'],
        sdate=data['sdate'],
        edate=data['edate'],
    )
    course_obj.save()
    return course_obj


def create_project(student, data):
    """Create a Project record for a student."""
    project_obj = Project.objects.create(
        unique_id=student,
        project_name=data['project_name'],
        project_status=data['project_status'],
        summary=data['summary'],
        project_link=data['project_link'],
        sdate=data['sdate'],
        edate=data['edate'],
    )
    project_obj.save()
    return project_obj


def create_experience(student, data):
    """Create an Experience record for a student."""
    experience_obj = Experience.objects.select_related('unique_id').create(
        unique_id=student,
        title=data['title'],
        status=data['status'],
        company=data['company'],
        location=data['location'],
        description=data['description'],
        sdate=data['sdate'],
        edate=data['edate'],
    )
    experience_obj.save()
    return experience_obj


# ---------------------------------------------------------------------------
# Student entity deletion  (S16, R08 — consolidated from 8 duplicated blocks)
# ---------------------------------------------------------------------------

# Mapping of entity type keys to their model classes
_ENTITY_MODEL_MAP = {
    'deleteskill': (Has, ('skill_id', 'unique_id')),
    'deleteedu': (Education, ('unique_id',)),
    'deletecourse': (Course, None),
    'deleteexp': (Experience, None),
    'deletepro': (Project, None),
    'deleteach': (Achievement, None),
    'deletepub': (Publication, ('unique_id',)),
    'deletepat': (Patent, None),
}


def delete_student_entity(entity_type, pk):
    """Delete a student entity by type and primary key."""
    if entity_type not in _ENTITY_MODEL_MAP:
        raise ValueError(f"Unknown entity type: {entity_type}")

    model_cls, select_related_fields = _ENTITY_MODEL_MAP[entity_type]
    qs = model_cls.objects
    if select_related_fields:
        qs = qs.select_related(*select_related_fields)
    obj = qs.get(Q(pk=pk))
    obj.delete()
    return True


# ---------------------------------------------------------------------------
# Profile update  (S27)
# ---------------------------------------------------------------------------

def update_student_profile(user, data):
    """Update a student's ExtraInfo profile."""
    extrainfo_obj = ExtraInfo.objects.get(user=user)
    extrainfo_obj.about_me = data.get('about', extrainfo_obj.about_me)
    extrainfo_obj.age = data.get('age', extrainfo_obj.age)
    extrainfo_obj.address = data.get('address', extrainfo_obj.address)
    extrainfo_obj.phone_no = data.get('contact', extrainfo_obj.phone_no)
    extrainfo_obj.profile_picture = data.get('pic', extrainfo_obj.profile_picture)
    extrainfo_obj.save()
    return extrainfo_obj


# ---------------------------------------------------------------------------
# Invitation management  (S07)
# ---------------------------------------------------------------------------

def update_invitation_response(status_pk, response):
    """Update placement status invitation to ACCEPTED or REJECTED."""
    PlacementStatus.objects.select_related('unique_id', 'notify_id').filter(
        pk=status_pk
    ).update(invitation=response, timestamp=timezone.now())


def delete_invitation_status_entry(pk):
    """Delete a placement invitation status entry."""
    PlacementStatus.objects.select_related('unique_id', 'notify_id').get(
        pk=pk
    ).delete()


def check_invitation_dates(placementstatus):
    """Check and expire pending invitations past their deadline.
    Preserves original logic from check_invitation_date()."""
    try:
        for ps in placementstatus:
            if ps.invitation == 'PENDING':
                dt = ps.timestamp + datetime.timedelta(days=ps.no_of_days)
                if dt < datetime.datetime.now():
                    ps.invitation = 'IGNORE'
                    ps.save()
    except Exception as e:
        logger.error('Error checking invitation dates: %s', e)


# ---------------------------------------------------------------------------
# Schedule management  (S17, S18)
# ---------------------------------------------------------------------------

def create_placement_schedule(data, files=None):
    """Create a new placement schedule with associated NotifyStudent and Role.

    Consolidates logic from both `placement` view and `placement_schedule_save`.
    """
    company_name = data.get('company_name', '')
    placement_date = data.get('placement_date')
    location = data.get('location', '')
    ctc = data.get('ctc', 0)
    time = data.get('time')
    attached_file = data.get('attached_file')
    placement_type = data.get('placement_type', 'PLACEMENT')
    role_offered = data.get('role', '')
    description = data.get('description', '')
    schedule_at = data.get('schedule_at')
    timestamp = data.get('timestamp')

    # Ensure company exists
    try:
        CompanyDetails.objects.filter(company_name=company_name)[0]
    except (IndexError, CompanyDetails.DoesNotExist):
        CompanyDetails.objects.create(company_name=company_name)

    # Ensure role exists
    try:
        role = Role.objects.filter(role=role_offered)[0]
    except (IndexError, Role.DoesNotExist):
        role = Role.objects.create(role=role_offered)
        role.save()

    notify = NotifyStudent.objects.create(
        placement_type=placement_type,
        company_name=company_name,
        description=description,
        ctc=ctc,
        timestamp=timestamp or timezone.now(),
    )

    schedule = PlacementSchedule.objects.select_related('notify_id').create(
        notify_id=notify,
        title=company_name,
        description=description,
        placement_date=placement_date,
        attached_file=attached_file,
        role=role,
        location=location,
        time=time or schedule_at,
    )

    notify.save()
    schedule.save()
    return schedule


def delete_placement_schedule(pk):
    """Delete a placement schedule and its associated NotifyStudent."""
    placement_schedule = PlacementSchedule.objects.select_related('notify_id').get(pk=pk)
    NotifyStudent.objects.get(pk=placement_schedule.notify_id.id).delete()
    placement_schedule.delete()


# ---------------------------------------------------------------------------
# Send invites  (S11)
# ---------------------------------------------------------------------------

def send_placement_invite(notify, students, no_of_days, sender_user):
    """Send placement invitations to a list of students."""
    PlacementStatus.objects.bulk_create([
        PlacementStatus(
            notify_id=notify,
            unique_id=student,
            no_of_days=no_of_days,
        ) for student in students
    ])
    for st in students:
        placement_cell_notif(sender_user, st.id.user, "")


# ---------------------------------------------------------------------------
# Debar / undebar  (S11)
# ---------------------------------------------------------------------------

def debar_student(spid):
    """Debar a student from placement."""
    sr = StudentPlacement.objects.get(Q(pk=spid))
    sr.debar = "DEBAR"
    sr.save()


def undebar_student(spid):
    """Remove debar status from a student."""
    sr = StudentPlacement.objects.get(Q(pk=spid))
    sr.debar = "NOT DEBAR"
    sr.save()


# ---------------------------------------------------------------------------
# Placement Record management  (S19, S20, R11)
# ---------------------------------------------------------------------------

def add_student_record(placement_type, data):
    """Add a PlacementRecord and linked StudentRecord.

    Used by manage_records for PLACEMENT, PBI, and HIGHER STUDIES.
    """
    placementr = PlacementRecord.objects.create(
        year=data.get('year', 0),
        ctc=data.get('ctc', 0),
        placement_type=placement_type,
        name=data.get('name', ''),
        test_type=data.get('test_type', ''),
        test_score=data.get('test_score', 0),
    )

    rollno = data.get('rollno', '')
    student = selectors.get_student_by_rollno(rollno)

    studentr = StudentRecord.objects.select_related('unique_id', 'record_id').create(
        record_id=placementr,
        unique_id=student,
    )
    studentr.save()
    placementr.save()
    return placementr, studentr


def delete_placement_record(record_id, include_student_record=True):
    """Delete a PlacementRecord and optionally its StudentRecord.

    Consolidates delete_placement_statistics and delete_placement_record views (R11).
    """
    if include_student_record:
        try:
            student_record = StudentRecord.objects.get(pk=record_id)
            PlacementRecord.objects.get(id=student_record.record_id.id).delete()
            student_record.delete()
        except (StudentRecord.DoesNotExist, PlacementRecord.DoesNotExist) as e:
            logger.error("Error deleting student record: %s", e)
            raise
    else:
        PlacementRecord.objects.filter(id=record_id).delete()


def save_placement_record(data):
    """Save a new PlacementRecord directly (from placement_record_save view)."""
    record = PlacementRecord.objects.create(
        placement_type=data.get('placement_type', 'PLACEMENT'),
        name=data.get('student_name', ''),
        ctc=data.get('ctc', 0),
        year=data.get('year', 0),
        test_type=data.get('test_type', ''),
        test_score=data.get('test_score', 0),
    )
    record.save()
    return record


# ---------------------------------------------------------------------------
# Chairman Visit  (S20)
# ---------------------------------------------------------------------------

def save_chairman_visit(data):
    """Save a new ChairmanVisit record."""
    record = ChairmanVisit.objects.create(
        company_name=data.get('company_name', ''),
        location=data.get('location', ''),
        visiting_date=data.get('date'),
        description=data.get('description', ''),
        timestamp=data.get('timestamp'),
    )
    record.save()
    return record


# ---------------------------------------------------------------------------
# Statistics computation  (S46 — preserves triple-nested loop logic)
# ---------------------------------------------------------------------------

def compute_department_statistics(years, records, studentrecord):
    """Compute department-wise placement statistics.

    Preserves the original logic that counts CSE/ECE/ME students per
    company per year, but encapsulated in a service function.
    """
    invitecheck = 0
    for r in records:
        r['name__count'] = 0
        r['year__count'] = 0
        r['placement_type__count'] = 0

    tcse = dict()
    tece = dict()
    tme = dict()
    tadd = dict()

    for y in years:
        tcse[y['year']] = 0
        tece[y['year']] = 0
        tme[y['year']] = 0
        for r in records:
            if r['year'] == y['year']:
                if r['placement_type'] != "HIGHER STUDIES":
                    for z in studentrecord:
                        if (z.record_id.name == r['name'] and
                                z.record_id.year == r['year'] and
                                z.unique_id.id.department.name == DEPT_CSE):
                            tcse[y['year']] = tcse[y['year']] + 1
                            r['name__count'] = r['name__count'] + 1
                        if (z.record_id.name == r['name'] and
                                z.record_id.year == r['year'] and
                                z.unique_id.id.department.name == DEPT_ECE):
                            tece[y['year']] = tece[y['year']] + 1
                            r['year__count'] = r['year__count'] + 1
                        if (z.record_id.name == r['name'] and
                                z.record_id.year == r['year'] and
                                z.unique_id.id.department.name == DEPT_ME):
                            tme[y['year']] = tme[y['year']] + 1
                            r['placement_type__count'] = r['placement_type__count'] + 1
        tadd[y['year']] = tcse[y['year']] + tece[y['year']] + tme[y['year']]
        y['year__count'] = [tadd[y['year']], tcse[y['year']], tece[y['year']], tme[y['year']]]

    return years, records


# ---------------------------------------------------------------------------
# Student form submission dispatcher (S15, R07 — handles POST branching)
# ---------------------------------------------------------------------------

def handle_student_form_submissions(request, student):
    """Process all student form submissions from the schedule/placement view.

    Consolidates the 10+ duplicated form-handling blocks.
    """
    from .forms import (
        AddAchievement, AddCourse, AddEducation, AddExperience,
        AddPatent, AddProject, AddPublication, AddSkill,
    )

    if 'educationsubmit' in request.POST:
        form = AddEducation(request.POST)
        if form.is_valid():
            create_education(student, form.cleaned_data)

    if 'profilesubmit' in request.POST:
        update_student_profile(request.user, {
            'about': request.POST.get('about'),
            'age': request.POST.get('age'),
            'address': request.POST.get('address'),
            'contact': request.POST.get('contact'),
            'pic': request.POST.get('pic'),
        })

    if 'skillsubmit' in request.POST:
        form = AddSkill(request.POST)
        if form.is_valid():
            create_skill_entry(student, form.cleaned_data)

    if 'achievementsubmit' in request.POST:
        form = AddAchievement(request.POST)
        if form.is_valid():
            create_achievement(student, form.cleaned_data)

    if 'publicationsubmit' in request.POST:
        form = AddPublication(request.POST)
        if form.is_valid():
            create_publication(student, form.cleaned_data)

    if 'patentsubmit' in request.POST:
        form = AddPatent(request.POST)
        if form.is_valid():
            create_patent(student, form.cleaned_data)

    if 'coursesubmit' in request.POST:
        form = AddCourse(request.POST)
        if form.is_valid():
            create_course(student, form.cleaned_data)

    if 'projectsubmit' in request.POST:
        form = AddProject(request.POST)
        if form.is_valid():
            create_project(student, form.cleaned_data)

    if 'experiencesubmit' in request.POST:
        form = AddExperience(request.POST)
        if form.is_valid():
            create_experience(student, form.cleaned_data)

    # Handle deletions  (S16, R08)
    for entity_type in _ENTITY_MODEL_MAP:
        if entity_type in request.POST:
            pk = request.POST[entity_type]
            delete_student_entity(entity_type, pk)
