from rest_framework import serializers

from applications.placement_cell.models import (
    Achievement, Course, Education, Experience, Has, Patent,
    Project, Publication, Skill, PlacementStatus, NotifyStudent,
    PlacementSchedule, PlacementRecord, ChairmanVisit
)

class SkillSerializer(serializers.ModelSerializer):
    class Meta:
        model = Skill
        fields = ('__all__')

class HasSerializer(serializers.ModelSerializer):
    class Meta:
        model = Has
        fields = ('skill_id', 'skill_rating')

class EducationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Education
        fields = ('__all__')

class CourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = ('__all__')

class ExperienceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Experience
        fields = ('__all__')

class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = ('__all__')

class AchievementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Achievement
        fields = ('__all__')

class PublicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Publication
        fields = ('__all__')

class PatentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Patent
        fields = ('__all__')

class NotifyStudentSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotifyStudent
        fields = ('__all__')

class PlacementStatusSerializer(serializers.ModelSerializer):
    notify_id = NotifyStudentSerializer()
    class Meta:
        model = PlacementStatus
        fields = ('notify_id', 'invitation', 'placed', 'timestamp', 'no_of_days')

class PlacementScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlacementSchedule
        fields = ('__all__')

class PlacementRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlacementRecord
        fields = ('__all__')

class ChairmanVisitSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChairmanVisit
        fields = ('__all__')

# Input Serializers for validation
class ScheduleInputSerializer(serializers.Serializer):
    placement_type = serializers.CharField()
    company_name = serializers.CharField()
    ctc = serializers.CharField(required=False, allow_blank=True)
    description = serializers.CharField(required=False, allow_blank=True)
    time_stamp = serializers.DateTimeField(required=False)
    title = serializers.CharField(required=False, allow_blank=True)
    location = serializers.CharField(required=False, allow_blank=True)
    role = serializers.CharField()
    resume = serializers.CharField(required=False, allow_blank=True)
    schedule_at = serializers.CharField(required=False, allow_blank=True)
    placement_date = serializers.DateField(required=False)

class RecordInputSerializer(serializers.Serializer):
    placement_type = serializers.CharField()
    student_name = serializers.CharField()
    ctc = serializers.CharField()
    year = serializers.CharField()
    test_type = serializers.CharField(required=False, allow_blank=True)
    test_score = serializers.CharField(required=False, allow_blank=True)

class VisitInputSerializer(serializers.Serializer):
    company_name = serializers.CharField()
    location = serializers.CharField()
    description = serializers.CharField(required=False, allow_blank=True)
    date = serializers.DateField()
    timestamp = serializers.DateTimeField(required=False)
