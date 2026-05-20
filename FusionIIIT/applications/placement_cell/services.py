"""
Placement Cell Services Layer

This module contains all business logic for the placement cell app.
Services are responsible for:
- Business rules and validation orchestration
- Coordinating between selectors and models
- Transaction management for complex operations

Layer contract: Views → Services → Selectors/Models → ORM
"""
import datetime
import logging
from django.db import transaction
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404

from applications.academic_information.models import Student
from applications.globals.models import ExtraInfo

from .models import (
    Achievement, Course, Education, Experience, Extracurricular, Conference,
    Has, Patent, PlacementRecord, Project, Publication, Reference, Skill,
    StudentPlacement, NotifyStudent, PlacementStatus, PlacementSchedule,
    ChairmanVisit, Role, CompanyDetails, Constants
)

from . import selectors

logger = logging.getLogger('django.server')


class PlacementStatisticsService:
    """Service for calculating placement statistics."""
    
    @staticmethod
    def calculate_statistics():
        """
        Calculate placement statistics including year-wise and department-wise counts.
        
        Returns:
            dict: Statistics data including years, records, and department counts
        """
        years, records, all_records = selectors.get_placement_statistics_data()
        studentrecord = selectors.get_student_record_list()
        
        # Initialize counters
        tcse = {}
        tece = {}
        tme = {}
        tadd = {}
        
        for y in years:
            tcse[y['year']] = 0
            tece[y['year']] = 0
            tme[y['year']] = 0
            tadd[y['year']] = 0
        
        # Calculate department-wise counts
        for r in records:
            for z in studentrecord:
                if z.record_id.year == r['year']:
                    dept_name = z.unique_id.id.department.name
                    if dept_name == "CSE":
                        tcse[r['year']] += 1
                    elif dept_name == "ECE":
                        tece[r['year']] += 1
                    elif dept_name == "ME":
                        tme[r['year']] += 1
                    tadd[r['year']] += 1
        
        return {
            'years': years,
            'records': records,
            'all_records': all_records,
            'tcse': tcse,
            'tece': tece,
            'tme': tme,
            'tadd': tadd,
        }
    
    @staticmethod
    def get_filtered_statistics(filters):
        """
        Get statistics with filters applied.
        
        Args:
            filters (dict): Filter criteria
            
        Returns:
            dict: Filtered statistics
        """
        # Implementation for filtered statistics
        pass


class StudentProfileService:
    """Service for managing student profile data."""
    
    @staticmethod
    @transaction.atomic
    def update_profile(user, profile_data, skills_data=None):
        """
        Update student profile information.
        
        Args:
            user (User): Django user
            profile_data (dict): Profile fields to update
            skills_data (list, optional): List of skill dictionaries
            
        Returns:
            ExtraInfo: Updated ExtraInfo object
        """
        try:
            extra_info = selectors.get_extra_info_by_user(user)
            student = selectors.get_student_by_id(extra_info.id)
            
            # Update profile fields
            if 'about_me' in profile_data:
                extra_info.about_me = profile_data['about_me']
            if 'age' in profile_data:
                extra_info.age = profile_data['age']
            if 'address' in profile_data:
                extra_info.address = profile_data['address']
            if 'phone_no' in profile_data:
                extra_info.phone_no = profile_data['phone_no']
            if 'profile_picture' in profile_data:
                extra_info.profile_picture = profile_data['profile_picture']
            
            extra_info.save()
            
            # Handle skills if provided
            if skills_data:
                StudentProfileService._update_skills(student, skills_data)
            
            return extra_info
            
        except Exception as e:
            logger.error(f"Error updating profile: {e}")
            raise
    
    @staticmethod
    @transaction.atomic
    def _update_skills(student, skills_data):
        """
        Update student skills.
        
        Args:
            student (Student): Student object
            skills_data (list): List of {skill, skill_rating} dicts
        """
        for skill_data in skills_data:
            skill_name = skill_data.get('skill')
            skill_rating = skill_data.get('skill_rating', 80)
            
            if skill_name:
                skill_obj = selectors.get_skill_by_name(skill_name)
                
                try:
                    Has.objects.create(
                        skill_id=skill_obj,
                        unique_id=student,
                        skill_rating=skill_rating
                    )
                except Exception as e:
                    logger.warning(f"Skill creation failed: {e}")
                    # Skill might already exist for this student
    
    @staticmethod
    @transaction.atomic
    def add_education(student, education_data):
        """
        Add education record for a student.
        
        Args:
            student (Student): Student object
            education_data (dict): Education fields
            
        Returns:
            Education: Created Education object
        """
        return Education.objects.create(
            unique_id=student,
            degree=education_data.get('degree', ''),
            grade=education_data.get('grade', ''),
            institute=education_data.get('institute', ''),
            stream=education_data.get('stream', ''),
            sdate=education_data.get('sdate'),
            edate=education_data.get('edate'),
        )
    
    @staticmethod
    @transaction.atomic
    def add_achievement(student, achievement_data):
        """
        Add achievement record for a student.
        
        Args:
            student (Student): Student object
            achievement_data (dict): Achievement fields
            
        Returns:
            Achievement: Created Achievement object
        """
        return Achievement.objects.create(
            unique_id=student,
            achievement=achievement_data.get('achievement', ''),
            achievement_type=achievement_data.get('achievement_type', 'OTHER'),
            description=achievement_data.get('description', ''),
            issuer=achievement_data.get('issuer', ''),
            date_earned=achievement_data.get('date_earned'),
        )
    
    @staticmethod
    @transaction.atomic
    def add_publication(student, publication_data, coauthors=None):
        """
        Add publication record for a student.
        
        Args:
            student (Student): Student object
            publication_data (dict): Publication fields
            coauthors (list, optional): List of coauthor names
            
        Returns:
            Publication: Created Publication object
        """
        from .models import Coauthor
        
        publication = Publication.objects.create(
            unique_id=student,
            publication_title=publication_data.get('publication_title', ''),
            description=publication_data.get('description', ''),
            publisher=publication_data.get('publisher', ''),
            publication_date=publication_data.get('publication_date'),
        )
        
        if coauthors:
            for coauthor_name in coauthors:
                Coauthor.objects.create(
                    publication_id=publication,
                    coauthor_name=coauthor_name
                )
        
        return publication
    
    @staticmethod
    @transaction.atomic
    def add_patent(student, patent_data, coinventors=None):
        """
        Add patent record for a student.
        
        Args:
            student (Student): Student object
            patent_data (dict): Patent fields
            coinventors (list, optional): List of coinventor names
            
        Returns:
            Patent: Created Patent object
        """
        from .models import Coinventor
        
        patent = Patent.objects.create(
            unique_id=student,
            patent_name=patent_data.get('patent_name', ''),
            description=patent_data.get('description', ''),
            patent_office=patent_data.get('patent_office', ''),
            patent_date=patent_data.get('patent_date'),
        )
        
        if coinventors:
            for coinventor_name in coinventors:
                Coinventor.objects.create(
                    patent_id=patent,
                    coinventor_name=coinventor_name
                )
        
        return patent
    
    @staticmethod
    @transaction.atomic
    def add_course(student, course_data):
        """
        Add course record for a student.
        
        Args:
            student (Student): Student object
            course_data (dict): Course fields
            
        Returns:
            Course: Created Course object
        """
        return Course.objects.create(
            unique_id=student,
            course_name=course_data.get('course_name', ''),
            description=course_data.get('description', ''),
            license_no=course_data.get('license_no', ''),
            sdate=course_data.get('sdate'),
            edate=course_data.get('edate'),
        )
    
    @staticmethod
    @transaction.atomic
    def add_project(student, project_data):
        """
        Add project record for a student.
        
        Args:
            student (Student): Student object
            project_data (dict): Project fields
            
        Returns:
            Project: Created Project object
        """
        return Project.objects.create(
            unique_id=student,
            project_name=project_data.get('project_name', ''),
            project_status=project_data.get('project_status', 'COMPLETED'),
            summary=project_data.get('summary', ''),
            project_link=project_data.get('project_link', ''),
            sdate=project_data.get('sdate'),
            edate=project_data.get('edate'),
        )
    
    @staticmethod
    @transaction.atomic
    def add_experience(student, experience_data):
        """
        Add experience record for a student.
        
        Args:
            student (Student): Student object
            experience_data (dict): Experience fields
            
        Returns:
            Experience: Created Experience object
        """
        return Experience.objects.create(
            unique_id=student,
            title=experience_data.get('title', ''),
            status=experience_data.get('status', 'COMPLETED'),
            description=experience_data.get('description', ''),
            company=experience_data.get('company', ''),
            location=experience_data.get('location', ''),
            sdate=experience_data.get('sdate'),
            edate=experience_data.get('edate'),
        )
    
    @staticmethod
    @transaction.atomic
    def add_extracurricular(student, extracurricular_data):
        """
        Add extracurricular activity record for a student.
        
        Args:
            student (Student): Student object
            extracurricular_data (dict): Extracurricular fields
            
        Returns:
            Extracurricular: Created Extracurricular object
        """
        return Extracurricular.objects.create(
            unique_id=student,
            event_name=extracurricular_data.get('event_name', ''),
            event_type=extracurricular_data.get('event_type', 'OTHER'),
            description=extracurricular_data.get('description', ''),
            name_of_position=extracurricular_data.get('name_of_position', ''),
            date_earned=extracurricular_data.get('date_earned'),
        )
    
    @staticmethod
    @transaction.atomic
    def add_conference(student, conference_data):
        """
        Add conference record for a student.
        
        Args:
            student (Student): Student object
            conference_data (dict): Conference fields
            
        Returns:
            Conference: Created Conference object
        """
        return Conference.objects.create(
            unique_id=student,
            conference_name=conference_data.get('conference_name', ''),
            description=conference_data.get('description', ''),
            sdate=conference_data.get('sdate'),
            edate=conference_data.get('edate'),
        )
    
    @staticmethod
    def get_cv_generation_context(student, reference_ids=None, checks=None):
        """
        Get context data for CV generation.
        
        Args:
            student (Student): Student object
            reference_ids (list, optional): List of reference IDs to include
            checks (dict, optional): Dictionary of what to include
            
        Returns:
            dict: Context data for CV template
        """
        cv_data = selectors.get_student_cv_data(student.id)
        
        # Get references if requested
        if reference_ids:
            from .models import Reference
            references = Reference.objects.filter(id__in=reference_ids)
        else:
            references = []
        
        cv_data['references'] = references
        cv_data['referencecheck'] = '1' if len(references) > 0 else '0'
        
        # Apply inclusion checks
        if checks:
            for key, value in checks.items():
                cv_data[key] = value
        
        return cv_data


class InvitationManagementService:
    """Service for managing placement invitations."""
    
    @staticmethod
    def check_and_update_expired_invitations(notify_id=None):
        """
        Check for expired invitations and update their status.
        
        Args:
            notify_id (int, optional): Specific notify ID to check
            
        Returns:
            int: Number of updated invitations
        """
        if notify_id:
            queryset = selectors.get_placement_status_with_details(
                notify_id=notify_id
            )
        else:
            queryset = selectors.get_placement_status_with_details()
        
        return selectors.check_and_update_invitation_dates(queryset)
    
    @staticmethod
    @transaction.atomic
    def send_invite(student, notify_student, no_of_days=10):
        """
        Send placement invitation to a student.
        
        Args:
            student (Student): Student object
            notify_student (NotifyStudent): NotifyStudent object
            no_of_days (int): Days to respond
            
        Returns:
            PlacementStatus: Created PlacementStatus object
        """
        return PlacementStatus.objects.create(
            notify_id=notify_student,
            unique_id=student,
            invitation='PENDING',
            placed='NOT PLACED',
            no_of_days=no_of_days,
        )
    
    @staticmethod
    @transaction.atomic
    def update_invitation_status(placement_status, new_status):
        """
        Update invitation status.
        
        Args:
            placement_status (PlacementStatus): PlacementStatus object
            new_status (str): New status value
            
        Returns:
            PlacementStatus: Updated object
        """
        valid_statuses = ['ACCEPTED', 'REJECTED', 'PENDING', 'IGNORE']
        if new_status not in valid_statuses:
            raise ValidationError(f"Invalid status. Must be one of: {valid_statuses}")
        
        placement_status.invitation = new_status
        placement_status.save()
        
        return placement_status
    
    @staticmethod
    @transaction.atomic
    def update_placed_status(placement_status, placed_type):
        """
        Update placed status.
        
        Args:
            placement_status (PlacementStatus): PlacementStatus object
            placed_type (str): Placed type
            
        Returns:
            PlacementStatus: Updated object
        """
        valid_placed_types = ['PLACED', 'NOT PLACED']
        if placed_type not in valid_placed_types:
            raise ValidationError(f"Invalid placed type. Must be one of: {valid_placed_types}")
        
        placement_status.placed = placed_type
        if placed_type == 'PLACED':
            # Update student's overall placement status
            try:
                student_placement = StudentPlacement.objects.get(
                    unique_id=placement_status.unique_id
                )
                student_placement.placed_type = 'PLACED'
                student_placement.placement_date = datetime.date.today()
                student_placement.package = placement_status.notify_id.ctc
                student_placement.save()
            except StudentPlacement.DoesNotExist:
                pass
        
        placement_status.save()
        
        return placement_status


class ScheduleManagementService:
    """Service for managing placement schedules."""
    
    @staticmethod
    @transaction.atomic
    def create_schedule(notify_student, schedule_data):
        """
        Create a placement schedule.
        
        Args:
            notify_student (NotifyStudent): NotifyStudent object
            schedule_data (dict): Schedule fields
            
        Returns:
            PlacementSchedule: Created object
        """
        role = None
        if schedule_data.get('role_id'):
            role = selectors.get_role_by_id(schedule_data['role_id'])
        
        return PlacementSchedule.objects.create(
            notify_id=notify_student,
            title=schedule_data.get('title', ''),
            placement_date=schedule_data.get('placement_date'),
            location=schedule_data.get('location', ''),
            description=schedule_data.get('description', ''),
            time=schedule_data.get('time'),
            role=role,
            attached_file=schedule_data.get('attached_file'),
            schedule_at=schedule_data.get('schedule_at'),
        )
    
    @staticmethod
    @transaction.atomic
    def update_schedule(schedule_id, schedule_data):
        """
        Update a placement schedule.
        
        Args:
            schedule_id (int): Schedule ID
            schedule_data (dict): Fields to update
            
        Returns:
            PlacementSchedule: Updated object
        """
        schedule = get_object_or_404(PlacementSchedule, id=schedule_id)
        
        for field, value in schedule_data.items():
            if hasattr(schedule, field):
                setattr(schedule, field, value)
        
        schedule.save()
        return schedule
    
    @staticmethod
    @transaction.atomic
    def delete_schedule(schedule_id):
        """
        Delete a placement schedule.
        
        Args:
            schedule_id (int): Schedule ID
            
        Returns:
            bool: True if deleted
        """
        schedule = get_object_or_404(PlacementSchedule, id=schedule_id)
        schedule.delete()
        return True
    
    @staticmethod
    def get_schedules_for_notify(notify_id):
        """
        Get all schedules for a notify student.
        
        Args:
            notify_id (int): NotifyStudent ID
            
        Returns:
            QuerySet: PlacementSchedule objects
        """
        return PlacementSchedule.objects.filter(
            notify_id=notify_id
        ).select_related('notify_id', 'role')


class RecordManagementService:
    """Service for managing placement records."""
    
    @staticmethod
    @transaction.atomic
    def create_placement_record(record_data):
        """
        Create a placement record.
        
        Args:
            record_data (dict): Record fields
            
        Returns:
            PlacementRecord: Created object
        """
        return PlacementRecord.objects.create(
            placement_type=record_data.get('placement_type', 'PLACEMENT'),
            name=record_data.get('name', ''),
            ctc=record_data.get('ctc', 0),
            year=record_data.get('year', 0),
            test_score=record_data.get('test_score'),
            test_type=record_data.get('test_type', ''),
        )
    
    @staticmethod
    @transaction.atomic
    def create_student_record(record_id, student):
        """
        Create a student record linking student to placement record.
        
        Args:
            record_id (PlacementRecord): PlacementRecord object
            student (Student): Student object
            
        Returns:
            StudentRecord: Created object
        """
        return StudentRecord.objects.create(
            record_id=record_id,
            unique_id=student,
        )
    
    @staticmethod
    @transaction.atomic
    def delete_placement_record(record_id):
        """
        Delete a placement record.
        
        Args:
            record_id (int): Record ID
            
        Returns:
            bool: True if deleted
        """
        record = get_object_or_404(PlacementRecord, id=record_id)
        record.delete()
        return True
    
    @staticmethod
    def search_placement_records(filters):
        """
        Search placement records by filters.
        
        Args:
            filters (dict): Search criteria
            
        Returns:
            QuerySet: Filtered PlacementRecord objects
        """
        return selectors.get_placement_record_by_filters(filters)


class ChairmanVisitService:
    """Service for managing chairman visits."""
    
    @staticmethod
    @transaction.atomic
    def create_visit(visit_data):
        """
        Create a chairman visit record.
        
        Args:
            visit_data (dict): Visit fields
            
        Returns:
            ChairmanVisit: Created object
        """
        return ChairmanVisit.objects.create(
            company_name=visit_data.get('company_name', ''),
            location=visit_data.get('location', ''),
            visiting_date=visit_data.get('visiting_date'),
            description=visit_data.get('description', ''),
        )
    
    @staticmethod
    def get_all_visits():
        """
        Get all chairman visits.
        
        Returns:
            QuerySet: ChairmanVisit objects
        """
        return selectors.get_chairman_visits()


class NotificationService:
    """Service for managing placement notifications."""
    
    @staticmethod
    @transaction.atomic
    def create_notification(notification_data):
        """
        Create a placement notification for students.
        
        Args:
            notification_data (dict): Notification fields
            
        Returns:
            NotifyStudent: Created object
        """
        return NotifyStudent.objects.create(
            placement_type=notification_data.get('placement_type', 'PLACEMENT'),
            company_name=notification_data.get('company_name', ''),
            ctc=notification_data.get('ctc'),
            description=notification_data.get('description', ''),
        )
    
    @staticmethod
    def get_notifications(filters=None):
        """
        Get notifications with optional filters.
        
        Args:
            filters (dict, optional): Filter criteria
            
        Returns:
            QuerySet: NotifyStudent objects
        """
        if filters:
            return selectors.get_notify_student_by_filters(filters)
        return NotifyStudent.objects.all()


class StudentDebarmentService:
    """Service for managing student debarment."""
    
    @staticmethod
    @transaction.atomic
    def debar_student(student_id, reason=''):
        """
        Debar a student from placements.
        
        Args:
            student_id (str): Student ID
            reason (str): Reason for debarment
            
        Returns:
            StudentPlacement: Updated object
        """
        student = selectors.get_student_by_id(student_id)
        
        try:
            student_placement = StudentPlacement.objects.get(unique_id=student)
            student_placement.debar = 'DEBAR'
            student_placement.save()
        except StudentPlacement.DoesNotExist:
            student_placement = StudentPlacement.objects.create(
                unique_id=student,
                debar='DEBAR',
            )
        
        return student_placement
    
    @staticmethod
    @transaction.atomic
    def undebar_student(student_id):
        """
        Remove debarment from a student.
        
        Args:
            student_id (str): Student ID
            
        Returns:
            StudentPlacement: Updated object
        """
        student = selectors.get_student_by_id(student_id)
        
        try:
            student_placement = StudentPlacement.objects.get(unique_id=student)
            student_placement.debar = 'NOT DEBAR'
            student_placement.save()
        except StudentPlacement.DoesNotExist:
            pass
        
        return student_placement


def calculate_student_roll(profile, now=None):
    """
    Calculate student roll number based on batch and current year.
    
    Args:
        profile (ExtraInfo): Student's extra info
        now (datetime, optional): Current datetime
        
    Returns:
        int: Roll number
    """
    if now is None:
        now = datetime.datetime.now()
    
    student_info = get_object_or_404(Student, Q(id=profile.id))
    batch = student_info.batch
    
    if int(str(profile.id)[:2]) == 20:
        if now.month > 4:
            roll = 1 + now.year - int(str(profile.id)[:4])
        else:
            roll = now.year - int(str(profile.id)[:4])
    else:
        if now.month > 4:
            roll = 1 + now.year - int("20" + str(profile.id)[0:2])
        else:
            roll = now.year - int("20" + str(profile.id)[0:2])
    
    return roll
