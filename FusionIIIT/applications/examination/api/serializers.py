"""
serializers.py — Input validation for examination API endpoints.

Serializers handle validation only; no business logic lives here.
"""

from rest_framework import serializers

from applications.examination.models import (
    PROFESSOR_ROLES,
    ADMIN_ROLES,
    DEAN_ROLES,
    ADMIN_OR_DEAN_ROLES,
    ALL_STAFF_ROLES,
    SemesterType,
)


# ---------------------------------------------------------------------------
# Reusable field-level validators
# ---------------------------------------------------------------------------

class RoleField(serializers.CharField):
    """CharField that validates against a set of allowed roles."""

    def __init__(self, allowed_roles, **kwargs):
        kwargs.setdefault("required", True)
        super().__init__(**kwargs)
        self._allowed_roles = allowed_roles

    def to_internal_value(self, data):
        value = super().to_internal_value(data)
        if value not in self._allowed_roles:
            raise serializers.ValidationError("Access denied.")
        return value


# ---------------------------------------------------------------------------
# Exam view
# ---------------------------------------------------------------------------

class ExamViewSerializer(serializers.Serializer):
    Role = serializers.CharField(required=True)


# ---------------------------------------------------------------------------
# Unique years
# ---------------------------------------------------------------------------

class UniqueRegistrationYearsSerializer(serializers.Serializer):
    programme_type = serializers.CharField(required=False, allow_blank=True)


# ---------------------------------------------------------------------------
# Download template / Check course students
# ---------------------------------------------------------------------------

class DownloadTemplateSerializer(serializers.Serializer):
    Role = RoleField(allowed_roles=ALL_STAFF_ROLES)
    course = serializers.CharField(required=True)
    year = serializers.CharField(required=True)
    semester_type = serializers.CharField(required=True)
    programme_type = serializers.CharField(required=False, allow_blank=True, default=None)

    def validate(self, attrs):
        if not attrs.get("course") or not attrs.get("year") or not attrs.get("semester_type"):
            raise serializers.ValidationError(
                "Course, academic year, and semester type are required."
            )
        return attrs


class CheckCourseStudentsSerializer(DownloadTemplateSerializer):
    pass


# ---------------------------------------------------------------------------
# Submit grades (acadadmin)
# ---------------------------------------------------------------------------

class SubmitGradesSerializer(serializers.Serializer):
    Role = RoleField(allowed_roles=ADMIN_ROLES)
    academic_year = serializers.CharField(required=False, allow_blank=True, default=None)
    semester_type = serializers.CharField(required=False, allow_blank=True, default=None)


# ---------------------------------------------------------------------------
# Upload grades (acadadmin)
# ---------------------------------------------------------------------------

class UploadGradesSerializer(serializers.Serializer):
    Role = RoleField(allowed_roles=ADMIN_ROLES)
    course_id = serializers.CharField(required=True)
    academic_year = serializers.CharField(required=True)
    semester_type = serializers.CharField(required=True)

    def validate(self, attrs):
        if not attrs.get("course_id") or not attrs.get("academic_year") or not attrs.get("semester_type"):
            raise serializers.ValidationError(
                "Course ID, Academic Year, and Semester Type are required."
            )
        return attrs


# ---------------------------------------------------------------------------
# Update grades (acadadmin)
# ---------------------------------------------------------------------------

class UpdateGradesSerializer(serializers.Serializer):
    Role = RoleField(allowed_roles=ADMIN_ROLES)
    academic_year = serializers.CharField(required=True)
    semester_type = serializers.CharField(required=True)

    def validate(self, attrs):
        if not attrs.get("academic_year") or not attrs.get("semester_type"):
            raise serializers.ValidationError(
                "Academic year and semester type are required."
            )
        return attrs


# ---------------------------------------------------------------------------
# Update enter grades (acadadmin)
# ---------------------------------------------------------------------------

class UpdateEnterGradesSerializer(serializers.Serializer):
    Role = RoleField(allowed_roles=ADMIN_ROLES)
    course = serializers.CharField(required=True)
    year = serializers.CharField(required=True)
    semester_type = serializers.CharField(required=False, allow_blank=True, default=None)

    def validate(self, attrs):
        if not attrs.get("course") or not attrs.get("year"):
            raise serializers.ValidationError("Both 'course' and 'year' are required.")
        return attrs


# ---------------------------------------------------------------------------
# Moderate student grades
# ---------------------------------------------------------------------------

class ModerateStudentGradesSerializer(serializers.Serializer):
    Role = RoleField(allowed_roles=ADMIN_OR_DEAN_ROLES)
    student_ids = serializers.ListField(child=serializers.CharField(), required=True)
    semester_ids = serializers.ListField(child=serializers.CharField(), required=True)
    course_ids = serializers.ListField(child=serializers.CharField(), required=True)
    grades = serializers.ListField(child=serializers.CharField(), required=True)
    remarks = serializers.ListField(child=serializers.CharField(), required=False, default=[])
    allow_resubmission = serializers.CharField(required=False, default="NO")

    def validate(self, attrs):
        s = attrs["student_ids"]
        sem = attrs["semester_ids"]
        c = attrs["course_ids"]
        g = attrs["grades"]
        if not s or not sem or not c or not g:
            raise serializers.ValidationError("Invalid or incomplete grade data provided.")
        if len(s) != len(sem) or len(sem) != len(c) or len(c) != len(g):
            raise serializers.ValidationError("Invalid or incomplete grade data provided.")
        return attrs


# ---------------------------------------------------------------------------
# Generate transcript
# ---------------------------------------------------------------------------

class GenerateTranscriptSerializer(serializers.Serializer):
    Role = RoleField(allowed_roles=ADMIN_ROLES)
    student = serializers.CharField(required=True)
    semester = serializers.CharField(required=True)

    def validate(self, attrs):
        if not attrs.get("student") or not attrs.get("semester"):
            raise serializers.ValidationError("Student ID and Semester are required.")
        return attrs


# ---------------------------------------------------------------------------
# Generate transcript form
# ---------------------------------------------------------------------------

class GenerateTranscriptFormGetSerializer(serializers.Serializer):
    role = serializers.CharField(required=True)

    def validate_role(self, value):
        if value != "acadadmin":
            raise serializers.ValidationError("Access denied. Invalid or missing role.")
        return value


class GenerateTranscriptFormPostSerializer(serializers.Serializer):
    Role = RoleField(allowed_roles=ADMIN_ROLES)
    batch = serializers.CharField(required=True)
    specialization = serializers.CharField(required=False, allow_blank=True, default=None)
    semester = serializers.CharField(required=True)

    def validate(self, attrs):
        if not attrs.get("batch") or not attrs.get("semester"):
            raise serializers.ValidationError("batch, and semester are required fields.")
        return attrs


# ---------------------------------------------------------------------------
# Generate result
# ---------------------------------------------------------------------------

class GenerateResultSerializer(serializers.Serializer):
    Role = RoleField(allowed_roles=ADMIN_ROLES)
    semester = serializers.IntegerField(required=True)
    batch = serializers.CharField(required=True)
    specialization = serializers.CharField(required=False, allow_blank=True, default=None)
    semester_type = serializers.CharField(required=False, allow_blank=True, default=None)

    def validate(self, attrs):
        if not attrs.get("semester") or not attrs.get("batch"):
            raise serializers.ValidationError("Semester and Batch are required.")
        return attrs


# ---------------------------------------------------------------------------
# Submit API
# ---------------------------------------------------------------------------

class SubmitAPISerializer(serializers.Serializer):
    Role = RoleField(allowed_roles=ADMIN_OR_DEAN_ROLES)


# ---------------------------------------------------------------------------
# Download excel
# ---------------------------------------------------------------------------

class DownloadExcelSerializer(serializers.Serializer):
    student_ids = serializers.ListField(child=serializers.CharField(), required=True)
    semester_ids = serializers.ListField(child=serializers.CharField(), required=True)
    course_ids = serializers.ListField(child=serializers.CharField(), required=True)
    grades = serializers.ListField(child=serializers.CharField(), required=True)

    def validate(self, attrs):
        s = attrs["student_ids"]
        sem = attrs["semester_ids"]
        c = attrs["course_ids"]
        g = attrs["grades"]
        if not s or not sem or not c or not g:
            raise serializers.ValidationError("Invalid or incomplete grade data provided.")
        if len(s) != len(sem) or len(sem) != len(c) or len(c) != len(g):
            raise serializers.ValidationError("Invalid or incomplete grade data provided.")
        return attrs


# ---------------------------------------------------------------------------
# Submit grades prof
# ---------------------------------------------------------------------------

class SubmitGradesProfSerializer(serializers.Serializer):
    Role = RoleField(allowed_roles=PROFESSOR_ROLES)
    academic_year = serializers.CharField(required=True)
    semester_type = serializers.CharField(required=True)
    programme_type = serializers.CharField(required=False, allow_blank=True, default=None)

    def validate(self, attrs):
        if not attrs.get("academic_year") or not attrs.get("semester_type"):
            raise serializers.ValidationError(
                "Academic year and semester type are required."
            )
        return attrs


# ---------------------------------------------------------------------------
# Upload grades prof
# ---------------------------------------------------------------------------

class UploadGradesProfSerializer(serializers.Serializer):
    Role = RoleField(allowed_roles=PROFESSOR_ROLES)
    course_id = serializers.CharField(required=True)
    academic_year = serializers.CharField(required=True)
    semester_type = serializers.CharField(required=True)
    programme_type = serializers.CharField(required=False, allow_blank=True, default=None)

    def validate(self, attrs):
        if not attrs.get("course_id") or not attrs.get("academic_year") or not attrs.get("semester_type"):
            raise serializers.ValidationError(
                "Course ID, Academic Year, and Semester Type are required."
            )
        return attrs


# ---------------------------------------------------------------------------
# Download grades
# ---------------------------------------------------------------------------

class DownloadGradesSerializer(serializers.Serializer):
    Role = RoleField(allowed_roles=PROFESSOR_ROLES)
    academic_year = serializers.CharField(required=True)
    semester_type = serializers.CharField(required=True)
    programme_type = serializers.CharField(required=False, allow_blank=True, default=None)

    def validate(self, attrs):
        if not attrs.get("academic_year") or not attrs.get("semester_type"):
            raise serializers.ValidationError(
                "Academic year and semester type are required."
            )
        return attrs


# ---------------------------------------------------------------------------
# Generate PDF
# ---------------------------------------------------------------------------

class GeneratePDFSerializer(serializers.Serializer):
    Role = serializers.CharField(required=False, allow_blank=True, default=None)
    course_id = serializers.CharField(required=False)
    academic_year = serializers.CharField(required=False)
    semester_type = serializers.CharField(required=False)
    programme_type = serializers.CharField(required=False, allow_blank=True, default=None)
    student_info = serializers.DictField(required=False, default=None)
    courses = serializers.ListField(required=False, default=None)
    spi = serializers.FloatField(required=False, default=0)
    cpi = serializers.FloatField(required=False, default=0)
    su = serializers.IntegerField(required=False, default=0)
    tu = serializers.IntegerField(required=False, default=0)
    semester_no = serializers.IntegerField(required=False, default=1)
    semester_label = serializers.CharField(required=False, allow_blank=True, default="")


# ---------------------------------------------------------------------------
# Verify grades dean
# ---------------------------------------------------------------------------

class VerifyGradesDeanSerializer(serializers.Serializer):
    Role = RoleField(allowed_roles=DEAN_ROLES)
    academic_year = serializers.CharField(required=True)
    semester_type = serializers.CharField(required=True)

    def validate(self, attrs):
        if not attrs.get("academic_year") or not attrs.get("semester_type"):
            raise serializers.ValidationError(
                "Both academic_year and semester_type are required."
            )
        return attrs


# ---------------------------------------------------------------------------
# Update enter grades dean
# ---------------------------------------------------------------------------

class UpdateEnterGradesDeanSerializer(serializers.Serializer):
    Role = RoleField(allowed_roles=DEAN_ROLES)
    course = serializers.CharField(required=False)
    year = serializers.CharField(required=False)
    semester_type = serializers.CharField(required=False, allow_blank=True, default=None)


# ---------------------------------------------------------------------------
# Validate dean
# ---------------------------------------------------------------------------

class ValidateDeanSerializer(serializers.Serializer):
    Role = RoleField(allowed_roles=DEAN_ROLES)


# ---------------------------------------------------------------------------
# Validate dean submit
# ---------------------------------------------------------------------------

class ValidateDeanSubmitSerializer(serializers.Serializer):
    Role = RoleField(allowed_roles=DEAN_ROLES)
    course = serializers.CharField(required=True)
    year = serializers.CharField(required=True)

    def validate(self, attrs):
        if not attrs.get("course") or not attrs.get("year"):
            raise serializers.ValidationError("Course and Academic Year are required.")
        return attrs


# ---------------------------------------------------------------------------
# Check result
# ---------------------------------------------------------------------------

class CheckResultSerializer(serializers.Serializer):
    semester_no = serializers.IntegerField(required=True)
    semester_type = serializers.CharField(required=True)

    def validate(self, attrs):
        if attrs.get("semester_no") is None or not attrs.get("semester_type"):
            raise serializers.ValidationError(
                "semester_no and semester_type are required."
            )
        return attrs


# ---------------------------------------------------------------------------
# Preview grades
# ---------------------------------------------------------------------------

class PreviewGradesSerializer(serializers.Serializer):
    Role = RoleField(allowed_roles=ALL_STAFF_ROLES - DEAN_ROLES)
    course_id = serializers.CharField(required=True)
    academic_year = serializers.CharField(required=True)
    semester_type = serializers.CharField(required=True)
    programme_type = serializers.CharField(required=False, allow_blank=True, default=None)

    def validate(self, attrs):
        if not attrs.get("course_id") or not attrs.get("academic_year") or not attrs.get("semester_type"):
            raise serializers.ValidationError(
                "course_id, academic_year and semester_type are required."
            )
        return attrs


# ---------------------------------------------------------------------------
# Result announcements
# ---------------------------------------------------------------------------

class ResultAnnouncementListSerializer(serializers.Serializer):
    role = serializers.CharField(required=True)

    def validate_role(self, value):
        if value not in ADMIN_OR_DEAN_ROLES:
            raise serializers.ValidationError("Access denied.")
        return value


class UpdateAnnouncementSerializer(serializers.Serializer):
    Role = RoleField(allowed_roles=ADMIN_OR_DEAN_ROLES)
    id = serializers.IntegerField(required=True)
    announced = serializers.BooleanField(required=True)


class CreateAnnouncementSerializer(serializers.Serializer):
    Role = RoleField(allowed_roles=ADMIN_OR_DEAN_ROLES)
    batch = serializers.IntegerField(required=True)
    semester = serializers.IntegerField(required=True)

    def validate(self, attrs):
        if not attrs.get("batch") or not attrs.get("semester"):
            raise serializers.ValidationError("Batch and Semester are required.")
        return attrs


# ---------------------------------------------------------------------------
# Grade status
# ---------------------------------------------------------------------------

class GradeStatusSerializer(serializers.Serializer):
    Role = RoleField(allowed_roles=ADMIN_OR_DEAN_ROLES)
    academic_year = serializers.CharField(required=True)
    semester_type = serializers.CharField(required=True)

    def validate(self, attrs):
        if not attrs.get("academic_year") or not attrs.get("semester_type"):
            raise serializers.ValidationError(
                "Academic year and semester type are required."
            )
        return attrs


# ---------------------------------------------------------------------------
# Grade summary
# ---------------------------------------------------------------------------

class GradeSummarySerializer(GradeStatusSerializer):
    pass


# ---------------------------------------------------------------------------
# Student result PDF
# ---------------------------------------------------------------------------

class GenerateStudentResultPDFSerializer(serializers.Serializer):
    student_info = serializers.DictField(required=False, default=None)
    courses = serializers.ListField(required=False, default=None)
    spi = serializers.FloatField(required=False, default=0)
    cpi = serializers.FloatField(required=False, default=0)
    su = serializers.IntegerField(required=False, default=0)
    tu = serializers.IntegerField(required=False, default=0)
    semester_no = serializers.IntegerField(required=False, default=1)
    semester_type = serializers.CharField(required=False, allow_blank=True, default="")
    semester_label = serializers.CharField(required=False, allow_blank=True, default="")
    is_transcript = serializers.BooleanField(required=False, default=False)
    document_type = serializers.CharField(required=False, allow_blank=True, default="")
