# api/serializers.py
# T-12 / T-18 / CS-31: Renamed all *Serializers → *Serializer (singular, consistent).
# T-18: Canonical serializers now live in root serializers.py; this file provides
#        api-layer-specific classes that re-export or add api/views.py-specific shapes.

from rest_framework import serializers
from applications.complaint_system.models import Caretaker, StudentComplain, ServiceProvider, Workers
from applications.globals.models import ExtraInfo, User


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


class ExtraInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExtraInfo
        fields = '__all__'


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = '__all__'