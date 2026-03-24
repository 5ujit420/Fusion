# api/serializers.py
# Consolidated serializers for the complaint_system module.
# Fixes: V-21, V-22, V-23, V-24, V-25, R-09

from rest_framework import serializers
from applications.globals.models import ExtraInfo, User
from ..models import (
    StudentComplain, Caretaker, Warden, Complaint_Admin,
    Workers, ServiceProvider, Constants,
)


class StudentComplainSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentComplain
        fields = [
            'id', 'complainer', 'complaint_date', 'complaint_finish',
            'complaint_type', 'location', 'specific_location', 'details',
            'status', 'remarks', 'flag', 'reason', 'feedback',
            'worker_id', 'upload_complaint', 'comment', 'upload_resolved',
        ]

    def validate_complaint_type(self, value):
        """V-23: Validate complaint_type against allowed choices."""
        valid_types = [choice[0] for choice in Constants.COMPLAINT_TYPE]
        if value not in valid_types:
            raise serializers.ValidationError(
                f"Invalid complaint type '{value}'. Must be one of: {valid_types}"
            )
        return value

    def validate_location(self, value):
        """V-23: Validate location against allowed choices."""
        valid_locations = [choice[0] for choice in Constants.AREA]
        if value not in valid_locations:
            raise serializers.ValidationError(
                f"Invalid location '{value}'. Must be one of: {valid_locations}"
            )
        return value


class CaretakerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Caretaker
        fields = ['id', 'staff_id', 'area', 'rating', 'myfeedback']


class WardenSerializer(serializers.ModelSerializer):
    class Meta:
        model = Warden
        fields = ['id', 'staff_id', 'area', 'rating', 'myfeedback']


class Complaint_AdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = Complaint_Admin
        fields = ['id', 'sup_id']


class FeedbackSerializer(serializers.Serializer):
    """V-24, V-25: Proper input validation for feedback submissions."""
    feedback = serializers.CharField()
    rating = serializers.IntegerField(min_value=0, max_value=5)


class ResolvePendingSerializer(serializers.Serializer):
    yesorno = serializers.ChoiceField(choices=[('Yes', 'Yes'), ('No', 'No')])
    comment = serializers.CharField(required=False, allow_blank=True)
    upload_resolved = serializers.ImageField(required=False, allow_null=True)


class WorkersSerializer(serializers.ModelSerializer):
    class Meta:
        model = Workers
        fields = ['id', 'secincharge_id', 'name', 'age', 'phone', 'worker_type']


class ServiceProviderSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceProvider
        fields = ['id', 'ser_pro_id', 'type']


class ExtraInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExtraInfo
        fields = '__all__'


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = '__all__'