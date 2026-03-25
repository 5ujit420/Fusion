# api/serializers.py
# Validation + serialization for the filetracking API layer.
# Fixes: V-25, V-26

from rest_framework import serializers
from ..models import File, Tracking, MAX_FILE_SIZE_BYTES


class FileSerializer(serializers.ModelSerializer):
    class Meta:
        model = File
        fields = '__all__'


class TrackingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tracking
        fields = '__all__'


class FileHeaderSerializer(serializers.ModelSerializer):
    """Subset of File fields for list views (excludes upload_file, is_read)."""
    class Meta:
        model = File
        fields = ['id', 'uploader', 'designation', 'subject', 'description',
                  'upload_date', 'src_module', 'src_object_id', 'file_extra_JSON']


# ---------------------------------------------------------------------------
# Input serializers — compose / forward / draft
# ---------------------------------------------------------------------------

class FileCreateInputSerializer(serializers.Serializer):
    """Input for creating and sending a file."""
    uploader = serializers.CharField()
    uploader_designation = serializers.CharField()
    receiver = serializers.CharField()
    receiver_designation = serializers.CharField()
    subject = serializers.CharField(required=False, default='')
    description = serializers.CharField(required=False, default='')
    src_module = serializers.CharField(required=False, default='filetracking')
    src_object_id = serializers.CharField(required=False, default='')
    file_extra_JSON = serializers.JSONField(required=False, default=dict)
    file_attachment = serializers.FileField(required=False, default=None)

    def validate_file_attachment(self, value):
        if value and value.size > MAX_FILE_SIZE_BYTES:
            raise serializers.ValidationError("File should not be greater than 10 MB")
        return value


class DraftCreateInputSerializer(serializers.Serializer):
    """Input for creating a draft."""
    uploader = serializers.CharField()
    uploader_designation = serializers.CharField()
    src_module = serializers.CharField(required=False, default='filetracking')
    src_object_id = serializers.CharField(required=False, default='')
    file_extra_JSON = serializers.JSONField(required=False, default=dict)
    file_attachment = serializers.FileField(required=False, default=None)


class ForwardFileInputSerializer(serializers.Serializer):
    """Input for forwarding a file."""
    receiver = serializers.CharField()
    receiver_designation = serializers.CharField()
    file_extra_JSON = serializers.JSONField(required=False, default=dict)
    remarks = serializers.CharField(required=False, default='')
    file_attachment = serializers.FileField(required=False, default=None)

    def validate_file_attachment(self, value):
        if value and value.size > MAX_FILE_SIZE_BYTES:
            raise serializers.ValidationError("File should not be greater than 10 MB")
        return value


class ArchiveInputSerializer(serializers.Serializer):
    """Input for archiving a file."""
    file_id = serializers.IntegerField()


# ---------------------------------------------------------------------------
# Query serializers — inbox / outbox / draft / archive  (V-25, V-26)
# ---------------------------------------------------------------------------

class InboxQuerySerializer(serializers.Serializer):
    username = serializers.CharField()
    designation = serializers.CharField()
    src_module = serializers.CharField(required=False, default='filetracking')


class OutboxQuerySerializer(serializers.Serializer):
    username = serializers.CharField()
    designation = serializers.CharField()
    src_module = serializers.CharField(required=False, default='filetracking')


class DraftQuerySerializer(serializers.Serializer):
    """V-25: Query params validation for DraftFileView.get()."""
    username = serializers.CharField()
    designation = serializers.CharField()
    src_module = serializers.CharField(required=False, default='filetracking')


class ArchiveQuerySerializer(serializers.Serializer):
    """V-26: Query params validation for ArchiveFileView.get()."""
    username = serializers.CharField()
    designation = serializers.CharField()
    src_module = serializers.CharField(required=False, default='filetracking')
