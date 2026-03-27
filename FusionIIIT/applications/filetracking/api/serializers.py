# api/serializers.py
# Validation + serialization for the filetracking module.
# Fixes: V-25, V-26, V-37, V-38, V-45

from rest_framework import serializers
from ..models import File, Tracking, MAX_FILE_SIZE_BYTES


class FileSerializer(serializers.ModelSerializer):
    """V-37: Explicit field list instead of __all__."""
    class Meta:
        model = File
        fields = [
            'id', 'uploader', 'designation', 'subject', 'description',
            'upload_date', 'upload_file', 'is_read', 'src_module',
            'src_object_id', 'file_extra_JSON',
        ]


class TrackingSerializer(serializers.ModelSerializer):
    """V-38: Explicit field list instead of __all__."""
    class Meta:
        model = Tracking
        fields = [
            'id', 'file_id', 'current_id', 'current_design', 'receiver_id',
            'receive_design', 'receive_date', 'forward_date', 'remarks',
            'upload_file', 'is_read', 'tracking_extra_JSON',
        ]


class FileHeaderSerializer(serializers.ModelSerializer):
    """Serializes everything except upload_file and is_read."""
    class Meta:
        model = File
        exclude = ['upload_file', 'is_read']


# ---------------------------------------------------------------------------
# Input validation serializers  (V-25, V-26)
# ---------------------------------------------------------------------------

class FileCreateInputSerializer(serializers.Serializer):
    """V-25: Input validation for CreateFileView."""
    designation = serializers.CharField(required=True)
    receiver_username = serializers.CharField(required=True)
    receiver_designation = serializers.CharField(required=True)
    subject = serializers.CharField(required=True, max_length=100)
    description = serializers.CharField(required=False, allow_blank=True, max_length=400)


class DraftCreateInputSerializer(serializers.Serializer):
    """Input validation for CreateDraftFile."""
    uploader = serializers.CharField(required=True)
    uploader_designation = serializers.CharField(required=True)
    src_module = serializers.CharField(required=False, default='filetracking')
    src_object_id = serializers.CharField(required=False, default='')


class ForwardFileInputSerializer(serializers.Serializer):
    """Input validation for ForwardFileView."""
    receiver = serializers.CharField(required=True)
    receiver_designation = serializers.CharField(required=True)
    remarks = serializers.CharField(required=False, allow_blank=True, default="")


class InboxQuerySerializer(serializers.Serializer):
    """V-26: Input validation for ViewInboxView query params."""
    username = serializers.CharField(required=True)
    designation = serializers.CharField(required=False, allow_blank=True)
    src_module = serializers.CharField(required=True)


class OutboxQuerySerializer(serializers.Serializer):
    """Input validation for ViewOutboxView query params."""
    username = serializers.CharField(required=True)
    designation = serializers.CharField(required=False, allow_blank=True)
    src_module = serializers.CharField(required=True)


class ArchiveInputSerializer(serializers.Serializer):
    """Input validation for CreateArchiveFile."""
    file_id = serializers.IntegerField(required=True)


class DraftQuerySerializer(serializers.Serializer):
    """V-45: Input validation for DraftFileView query params."""
    username = serializers.CharField(required=True)
    designation = serializers.CharField(required=True)
    src_module = serializers.CharField(required=True)


class ArchiveQuerySerializer(serializers.Serializer):
    """V-45: Input validation for ArchiveFileView query params."""
    username = serializers.CharField(required=True)
    designation = serializers.CharField(required=False, allow_blank=True, default='')
    src_module = serializers.CharField(required=True)
