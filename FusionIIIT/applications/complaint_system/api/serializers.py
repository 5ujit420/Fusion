from rest_framework import serializers

from applications.complaint_system.models import (
    Caretaker, StudentComplain, ServiceProvider, Workers, Warden, Complaint_Admin, SectionIncharge, ServiceAuthority
)
from applications.globals.models import ExtraInfo, User

# ---------------------------------------------------------------------------
# Base Model Serializers (Replacing SA-10 duplicate mapping)
# ---------------------------------------------------------------------------

class StudentComplainSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentComplain
        fields = '__all__'


class WorkersSerializer(serializers.ModelSerializer):
    class Meta:
        model = Workers
        fields = '__all__'


class CaretakerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Caretaker
        fields = '__all__'


class ServiceProviderSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceProvider
        fields = '__all__'


class WardenSerializer(serializers.ModelSerializer):
    class Meta:
        model = Warden
        fields = '__all__'


class ComplaintAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = Complaint_Admin
        fields = '__all__'


class SectionInchargeSerializer(serializers.ModelSerializer):
    class Meta:
        model = SectionIncharge
        fields = '__all__'
        

class ServiceAuthoritySerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceAuthority
        fields = '__all__'


class ExtraInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExtraInfo
        fields = '__all__'


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = '__all__'


# ---------------------------------------------------------------------------
# Input Validation Serializers (SA-13)
# ---------------------------------------------------------------------------

class FeedbackSerializer(serializers.Serializer):
    """
    Validates integer rating inputs, enforcing data typing and structural boundaries
    before hitting mathematical operations in services.py.
    """
    feedback = serializers.CharField(max_length=500, required=False, allow_blank=True, default='')
    rating = serializers.IntegerField(min_value=1, max_value=5, default=0)


class ResolvePendingSerializer(serializers.Serializer):
    """
    Validates resolution branching and optional file attachments.
    """
    yesorno = serializers.ChoiceField(choices=[('Yes', 'Yes'), ('No', 'No')])
    comment = serializers.CharField(required=False, allow_blank=True, default="None")
    upload_resolved = serializers.ImageField(required=False, allow_null=True)


class ChangeStatusSerializer(serializers.Serializer):
    """
    Validates the status integer from URL/POST body.
    """
    status = serializers.ChoiceField(choices=[('0', '0'), ('1', '1'), ('2', '2'), ('3', '3')])
