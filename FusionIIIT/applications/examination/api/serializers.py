from rest_framework import serializers

from applications.academic_procedures.models import course_registration
from applications.department.models import Announcements


class CourseRegistrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = course_registration
        fields = "__all__"


class AnnouncementsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Announcements
        fields = [
            "maker_id",
            "ann_date",
            "message",
            "batch",
            "department",
            "programme",
            "upload_announcement",
        ]


class BatchGradeRowSerializer(serializers.Serializer):
    student_id = serializers.CharField()
    semester_id = serializers.CharField()
    course_id = serializers.CharField()
    grade = serializers.CharField()
    remark = serializers.CharField(required=False, allow_blank=True, default="")


class AcademicYearSemesterSerializer(serializers.Serializer):
    academic_year = serializers.CharField(required=False, allow_blank=True)
    semester_type = serializers.CharField(required=False, allow_blank=True)


class CourseYearSerializer(serializers.Serializer):
    course = serializers.CharField()
    year = serializers.CharField()
    semester_type = serializers.CharField(required=False, allow_blank=True)
