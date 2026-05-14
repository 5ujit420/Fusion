from rest_framework import serializers
from applications.complaint_system.serializers import (
    StudentComplainSerializer as StudentComplainSerializers,
    WorkersSerializer as WorkersSerializers,
    CaretakerSerializer as CaretakerSerializers,
    ServiceProviderSerializer as ServiceProviderSerializers,
)
from applications.globals.models import ExtraInfo, User

class ExtraInfoSerializers(serializers.ModelSerializer):
    class Meta:
        model = ExtraInfo
        fields = '__all__'


class UserSerializers(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = '__all__'
