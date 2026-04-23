from applications.filetracking.models import File, Tracking
from django.core.files import File as DjangoFile
from django.core.exceptions import ValidationError
from rest_framework import serializers


# Constants for validation
FILE_SIZE_LIMIT_KB = 10240  # 10MB
SUBJECT_MAX_LENGTH = 300
DESCRIPTION_MAX_LENGTH = 2500


class FileSerializer(serializers.ModelSerializer):
    """
    Serializer for File model with comprehensive validation.
    All field-level and object-level validation should be here.
    """
    
    class Meta:
        model = File
        fields = [
            'id', 'uploader', 'designation', 'subject', 'description',
            'upload_date', 'upload_file', 'is_read',
            'src_module', 'src_object_id', 'file_extra_JSON'
        ]
        read_only_fields = ['id', 'upload_date', 'uploader']
    
    def validate_subject(self, value):
        """Validate subject field."""
        if value and len(value) > SUBJECT_MAX_LENGTH:
            raise ValidationError(
                f'Subject cannot exceed {SUBJECT_MAX_LENGTH} characters'
            )
        return value
    
    def validate_description(self, value):
        """Validate description field."""
        if value and len(value) > DESCRIPTION_MAX_LENGTH:
            raise ValidationError(
                f'Description cannot exceed {DESCRIPTION_MAX_LENGTH} characters'
            )
        return value
    
    def validate_upload_file(self, value):
        """Validate uploaded file size."""
        if value:
            file_size_kb = value.size / 1000
            if file_size_kb > FILE_SIZE_LIMIT_KB:
                raise ValidationError(
                    f'File should not be greater than {FILE_SIZE_LIMIT_KB // 1024}MB'
                )
        return value
    
    def validate(self, data):
        """Object-level validation."""
        # Add any cross-field validation here if needed
        return data


class TrackingSerializer(serializers.ModelSerializer):
    """
    Serializer for Tracking model with validation.
    """
    
    class Meta:
        model = Tracking
        fields = [
            'id', 'file_id', 'current_id', 'current_design',
            'receiver_id', 'receive_design', 'receive_date',
            'forward_date', 'remarks', 'upload_file', 'is_read',
            'tracking_extra_JSON'
        ]
        read_only_fields = ['id', 'receive_date', 'forward_date']
    
    def validate_remarks(self, value):
        """Validate remarks field."""
        if value and len(value) > 500:
            raise ValidationError('Remarks cannot exceed 500 characters')
        return value
    
    def validate_upload_file(self, value):
        """Validate uploaded file size."""
        if value:
            file_size_kb = value.size / 1000
            if file_size_kb > FILE_SIZE_LIMIT_KB:
                raise ValidationError(
                    f'File should not be greater than {FILE_SIZE_LIMIT_KB // 1024}MB'
                )
        return value


class FileHeaderSerializer(serializers.ModelSerializer):
    '''
    This serializes everything except the attachments of a file and whether it is read or not
    '''
    class Meta:
        model = File
        fields = [
            'id', 'uploader', 'designation', 'subject', 'description',
            'upload_date', 'src_module', 'src_object_id', 'file_extra_JSON'
        ]
        read_only_fields = ['id', 'upload_date', 'uploader']
    
    def validate_subject(self, value):
        """Validate subject field."""
        if value and len(value) > SUBJECT_MAX_LENGTH:
            raise ValidationError(
                f'Subject cannot exceed {SUBJECT_MAX_LENGTH} characters'
            )
        return value
    
    def validate_description(self, value):
        """Validate description field."""
        if value and len(value) > DESCRIPTION_MAX_LENGTH:
            raise ValidationError(
                f'Description cannot exceed {DESCRIPTION_MAX_LENGTH} characters'
            )
        return value
