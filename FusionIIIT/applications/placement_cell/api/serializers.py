from rest_framework.authtoken.models import Token
from rest_framework import serializers

from applications.placement_cell.models import (Achievement, Course, Education,
                                                Experience, Has, Patent,
                                                Project, Publication, Skill,
                                                PlacementStatus, NotifyStudent)


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
        """Create Has object. Note: Business logic for skill creation should be in service layer."""
        skill_data = validated_data.pop('skill_id')
        
        # Get or create the skill - this should ideally be done in a service layer
        skill, created = Skill.objects.get_or_create(**skill_data)
        
        try:
            has_obj = Has.objects.create(skill_id=skill, **validated_data)
            return has_obj
        except Exception as e:
            # Log the error properly instead of silent failure
            import logging
            logger = logging.getLogger('django.server')
            logger.error(f"Failed to create Has object: {e}")
            raise serializers.ValidationError({'skill': 'This skill is already present for this student'})

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
