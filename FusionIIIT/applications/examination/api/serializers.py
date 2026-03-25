"""
Examination module serializers.

Fixes: V23 (AuthenticationSerializer wrong model), V24 (missing input serializers).
"""

from rest_framework import serializers
from applications.academic_procedures.models import course_registration
from applications.department.models import Announcements
from applications.examination.models import Authentication


# ---------------------------------------------------------------------------
# Existing model serializers (fixed)
# ---------------------------------------------------------------------------

class CourseRegistrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = course_registration
        fields = '__all__'


class AnnouncementsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Announcements
        fields = [
            'maker_id', 'ann_date', 'message', 'batch',
            'department', 'programme', 'upload_announcement',
        ]


class AuthenticationSerializer(serializers.ModelSerializer):
    """Fixed: was incorrectly pointing to Announcements model (V23)."""
    class Meta:
        model = Authentication
        fields = '__all__'


# ---------------------------------------------------------------------------
# Input validation serializers (V24)
# ---------------------------------------------------------------------------

class AcademicYearSemesterInputSerializer(serializers.Serializer):
    """Validates academic_year + semester_type pair used by many endpoints."""
    academic_year = serializers.CharField(required=True)
    semester_type = serializers.CharField(required=True)


class UploadGradesInputSerializer(serializers.Serializer):
    """Validates upload-grades request parameters."""
    course_id = serializers.IntegerField(required=True)
    academic_year = serializers.CharField(required=True)
    semester_type = serializers.CharField(required=True)
    programme_type = serializers.CharField(required=False, allow_blank=True, default='')
    csv_file = serializers.FileField(required=True)


class GenerateResultInputSerializer(serializers.Serializer):
    """Validates generate-result (Excel) request parameters."""
    semester = serializers.IntegerField(required=True)
    specialization = serializers.CharField(required=True)
    batch = serializers.IntegerField(required=True)
    semester_type = serializers.CharField(required=False, allow_blank=True, default='')
    academic_year = serializers.CharField(required=False, allow_blank=True, default='')


class SemesterInputSerializer(serializers.Serializer):
    """Validates semester_no + semester_type for check-result endpoints."""
    semester_no = serializers.IntegerField(required=True)
    semester_type = serializers.CharField(required=True)


class AnnouncementInputSerializer(serializers.Serializer):
    """Validates create-announcement request parameters."""
    batch = serializers.IntegerField(required=True)
    semester = serializers.IntegerField(required=True)


class CourseYearInputSerializer(serializers.Serializer):
    """Validates course + year for dean update endpoints."""
    course = serializers.IntegerField(required=True)
    year = serializers.CharField(required=True)
    semester_type = serializers.CharField(required=False, allow_blank=True, default='')