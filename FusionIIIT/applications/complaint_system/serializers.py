from applications.globals.models import ExtraInfo, User
from rest_framework import serializers

from .models import (
    Caretaker,
    Complaint_Admin,
    ServiceProvider,
    StudentComplain,
    Warden,
    Workers,
)


class StudentComplainSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentComplain
        fields = "__all__"


class StudentComplainInputSerializer(StudentComplainSerializer):
    pass


class StudentComplainOutputSerializer(StudentComplainSerializer):
    pass


class CaretakerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Caretaker
        fields = "__all__"


class WardenSerializer(serializers.ModelSerializer):
    class Meta:
        model = Warden
        fields = "__all__"


class Complaint_AdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = Complaint_Admin
        fields = "__all__"


class ServiceProviderSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceProvider
        fields = "__all__"


class WorkersSerializer(serializers.ModelSerializer):
    class Meta:
        model = Workers
        fields = "__all__"


class ExtraInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExtraInfo
        fields = "__all__"


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = "__all__"


class FeedbackSerializer(serializers.Serializer):
    feedback = serializers.CharField()
    rating = serializers.IntegerField()


class ResolvePendingSerializer(serializers.Serializer):
    yesorno = serializers.ChoiceField(choices=[("Yes", "Yes"), ("No", "No")])
    comment = serializers.CharField(required=False, allow_blank=True)
    upload_resolved = serializers.ImageField(required=False, allow_null=True)
