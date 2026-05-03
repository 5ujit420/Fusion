"""
api/serializers.py — placement_cell

Tasks addressed:
    T07 / S17, S26, S28 — input serializers for all 8 resume sections
    T08 / S27            — EducationInputSerializer.validate_edate replaces
                           the broken Education.clean() model method
"""
from rest_framework import serializers
from rest_framework.authtoken.models import Token  # noqa: F401 (kept for compat)

from applications.placement_cell.models import (
    Achievement, Course, Education,
    Experience, Has, Patent,
    Project, Publication, Skill,
    PlacementStatus, NotifyStudent,
)


# ---------------------------------------------------------------------------
# Read serializers  (existing — preserved for API responses)
# ---------------------------------------------------------------------------

class SkillSerializer(serializers.ModelSerializer):

    class Meta:
        model = Skill
        fields = '__all__'


class HasSerializer(serializers.ModelSerializer):
    skill_id = SkillSerializer()

    class Meta:
        model = Has
        fields = ('skill_id', 'skill_rating')

    def create(self, validated_data):
        skill = validated_data.pop('skill_id')
        skill_id, created = Skill.objects.get_or_create(**skill)
        try:
            has_obj = Has.objects.create(skill_id=skill_id, **validated_data)
        except Exception:
            raise serializers.ValidationError({'skill': 'This skill is already present'})
        return has_obj


class EducationSerializer(serializers.ModelSerializer):

    class Meta:
        model = Education
        fields = '__all__'


class CourseSerializer(serializers.ModelSerializer):

    class Meta:
        model = Course
        fields = '__all__'


class ExperienceSerializer(serializers.ModelSerializer):

    class Meta:
        model = Experience
        fields = '__all__'


class ProjectSerializer(serializers.ModelSerializer):

    class Meta:
        model = Project
        fields = '__all__'


class AchievementSerializer(serializers.ModelSerializer):

    class Meta:
        model = Achievement
        fields = '__all__'


class PublicationSerializer(serializers.ModelSerializer):

    class Meta:
        model = Publication
        fields = '__all__'


class PatentSerializer(serializers.ModelSerializer):

    class Meta:
        model = Patent
        fields = '__all__'


class NotifyStudentSerializer(serializers.ModelSerializer):

    class Meta:
        model = NotifyStudent
        fields = '__all__'


class PlacementStatusSerializer(serializers.ModelSerializer):
    notify_id = NotifyStudentSerializer()

    class Meta:
        model = PlacementStatus
        fields = ('notify_id', 'invitation', 'placed', 'timestamp', 'no_of_days')


# ---------------------------------------------------------------------------
# T07 / S17, S26, S28: Input serializers — validation centralised here.
# Views pass request.POST to these serializers instead of extracting fields
# manually.  Field defaults enforce S28 (eliminate repeated if-else chains).
# ---------------------------------------------------------------------------

class EducationInputSerializer(serializers.Serializer):
    """T07 / T08: Validates resume education section; enforces sdate < edate."""
    institute = serializers.CharField(max_length=250, default='')
    degree = serializers.CharField(max_length=40, default='')
    grade = serializers.CharField(max_length=10, default='')
    stream = serializers.CharField(max_length=150, default='', allow_blank=True)
    sdate = serializers.DateField()
    edate = serializers.DateField(required=False, allow_null=True)

    def validate(self, data):
        """T08 / S27: Date order enforcement, replacing the broken clean()."""
        sdate = data.get('sdate')
        edate = data.get('edate')
        if sdate and edate and sdate > edate:
            raise serializers.ValidationError(
                {'edate': 'End date must be on or after start date.'}
            )
        return data


class SkillInputSerializer(serializers.Serializer):
    skill = serializers.CharField(max_length=30)
    skill_rating = serializers.IntegerField(default=80, min_value=0, max_value=100)


class AchievementInputSerializer(serializers.Serializer):
    achievement = serializers.CharField(max_length=100, default='')
    achievement_type = serializers.ChoiceField(choices=[('EDUCATIONAL', 'Educational'),
                                                        ('OTHER', 'Other')],
                                               default='OTHER')
    description = serializers.CharField(max_length=1000, default='', allow_blank=True)
    issuer = serializers.CharField(max_length=200, default='')
    date_earned = serializers.DateField()


class PublicationInputSerializer(serializers.Serializer):
    publication_title = serializers.CharField(max_length=100, default='')
    description = serializers.CharField(max_length=250, default='', allow_blank=True)
    publisher = serializers.CharField(max_length=250, default='')
    publication_date = serializers.DateField()


class PatentInputSerializer(serializers.Serializer):
    patent_name = serializers.CharField(max_length=100, default='')
    description = serializers.CharField(max_length=250, default='', allow_blank=True)
    patent_office = serializers.CharField(max_length=250, default='')
    patent_date = serializers.DateField()


class CourseInputSerializer(serializers.Serializer):
    course_name = serializers.CharField(max_length=100, default='')
    description = serializers.CharField(max_length=250, default='', allow_blank=True)
    license_no = serializers.CharField(max_length=100, default='', allow_blank=True)
    sdate = serializers.DateField()
    edate = serializers.DateField(required=False, allow_null=True)


class ProjectInputSerializer(serializers.Serializer):
    project_name = serializers.CharField(max_length=50, default='')
    project_status = serializers.ChoiceField(choices=[('ONGOING', 'Ongoing'),
                                                      ('COMPLETED', 'Completed')],
                                             default='COMPLETED')
    summary = serializers.CharField(max_length=1000, default='', allow_blank=True)
    project_link = serializers.CharField(max_length=200, default='', allow_blank=True)
    sdate = serializers.DateField()
    edate = serializers.DateField(required=False, allow_null=True)


class ExperienceInputSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=100, default='')
    status = serializers.ChoiceField(choices=[('ONGOING', 'Ongoing'),
                                              ('COMPLETED', 'Completed')],
                                     default='COMPLETED')
    company = serializers.CharField(max_length=200, default='')
    location = serializers.CharField(max_length=200, default='')
    description = serializers.CharField(max_length=500, default='', allow_blank=True)
    sdate = serializers.DateField()
    edate = serializers.DateField(required=False, allow_null=True)
