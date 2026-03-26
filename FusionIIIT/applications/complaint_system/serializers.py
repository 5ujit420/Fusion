# serializers.py
# Consolidated serializers for the complaint_system module.
# Addresses: RR-18 (rating validation)

from rest_framework import serializers
from applications.globals.models import ExtraInfo, User
from .models import (
    StudentComplain, Caretaker, Warden, Complaint_Admin,
    Workers, ServiceProvider, Constants,
)


class StudentComplainSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentComplain
        fields = '__all__'

    def validate_complaint_type(self, value):
        """Validate complaint_type against allowed choices."""
        valid_types = [choice[0] for choice in Constants.COMPLAINT_TYPE]
        if value not in valid_types:
            raise serializers.ValidationError(
                f"Invalid complaint type '{value}'. Must be one of: {valid_types}"
            )
        return value

    def validate_location(self, value):
        """Validate location against allowed choices."""
        valid_locations = [choice[0] for choice in Constants.AREA]
        if value not in valid_locations:
            raise serializers.ValidationError(
                f"Invalid location '{value}'. Must be one of: {valid_locations}"
            )
        return value


class CaretakerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Caretaker
        fields = '__all__'


class WardenSerializer(serializers.ModelSerializer):
    class Meta:
        model = Warden
        fields = '__all__'


class Complaint_AdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = Complaint_Admin
        fields = '__all__'


class FeedbackSerializer(serializers.Serializer):
    """RR-18: Proper input validation for feedback submissions."""
    feedback = serializers.CharField()
    rating = serializers.IntegerField(min_value=0, max_value=5)


class ResolvePendingSerializer(serializers.Serializer):
    yesorno = serializers.ChoiceField(choices=[('Yes', 'Yes'), ('No', 'No')])
    comment = serializers.CharField(required=False, allow_blank=True)
    upload_resolved = serializers.ImageField(required=False, allow_null=True)


class WorkersSerializer(serializers.ModelSerializer):
    class Meta:
        model = Workers
        fields = '__all__'


class ServiceProviderSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceProvider
        fields = '__all__'


class ExtraInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExtraInfo
        fields = '__all__'


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = '__all__'
