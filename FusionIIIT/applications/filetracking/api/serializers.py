from rest_framework import serializers

from applications.filetracking.models import File, Tracking


class FileSerializer(serializers.ModelSerializer):
    class Meta:
        model = File
        fields = "__all__"


class TrackingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tracking
        fields = "__all__"


class FileHeaderSerializer(serializers.ModelSerializer):
    """
    Maintains the legacy payload shape for file header rows.
    """

    class Meta:
        model = File
        fields = "__all__"


class CreateFileInputSerializer(serializers.Serializer):
    designation = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    receiver_username = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    receiver_designation = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    subject = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    description = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    src_module = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    remarks = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    def validate(self, attrs):
        required_fields = (
            "designation",
            "receiver_username",
            "receiver_designation",
            "subject",
            "description",
            "src_module",
        )
        if any(attrs.get(field) is None for field in required_fields):
            raise serializers.ValidationError("One or more required fields are missing.")
        return attrs


class ForwardFileInputSerializer(serializers.Serializer):
    receiver = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    receiver_designation = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    file_extra_JSON = serializers.JSONField(required=False)
    remarks = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    def validate(self, attrs):
        if not attrs.get("receiver") or not attrs.get("receiver_designation"):
            raise serializers.ValidationError("Missing required fields: receiver and receiver_designation")
        attrs.setdefault("file_extra_JSON", {})
        attrs.setdefault("remarks", "")
        return attrs


class CreateDraftInputSerializer(serializers.Serializer):
    designation = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    src_module = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    src_object_id = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    file_extra_JSON = serializers.JSONField(required=False)
    subject = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    description = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    remarks = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    def validate(self, attrs):
        if attrs.get("designation") is None or attrs.get("src_module") is None:
            raise serializers.ValidationError("One or more required fields are missing.")
        attrs.setdefault("src_object_id", "")
        attrs.setdefault("file_extra_JSON", {})
        attrs.setdefault("subject", "")
        attrs.setdefault("description", "")
        attrs.setdefault("remarks", "")
        return attrs


class FileActionInputSerializer(serializers.Serializer):
    file_id = serializers.IntegerField(required=False, allow_null=True)

    def validate(self, attrs):
        if attrs.get("file_id") is None:
            raise serializers.ValidationError("Missing file_id")
        return attrs


class UsernameLookupSerializer(serializers.Serializer):
    username = serializers.CharField(required=True)


class AjaxDropdownInputSerializer(serializers.Serializer):
    value = serializers.CharField(required=False, allow_blank=True, default="")
