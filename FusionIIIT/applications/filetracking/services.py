"""
Services module for filetracking app.
All business logic should be placed here.
Pattern: <action>_<entity> or create/update/delete/archive/forward_file
"""
import logging
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils import timezone
from applications.filetracking.models import File, Tracking
from applications.globals.models import ExtraInfo, HoldsDesignation, Designation
from notification.views import file_tracking_notif

logger = logging.getLogger(__name__)


def validate_file_size(upload_file, max_size_kb=10240):
    """
    Validate that uploaded file does not exceed maximum size.
    Default max size is 10MB (10240 KB).
    Raises ValidationError if file is too large.
    """
    if upload_file and upload_file.size / 1000 > max_size_kb:
        raise ValidationError(f"File should not be greater than {max_size_kb // 1024}MB")


def create_file_from_form(
    uploader,
    subject,
    description,
    designation_id,
    upload_file=None,
    form_remarks=None,
    send_to_receiver=False,
    receiver_username=None,
    receive_designation_name=None
):
    """
    Create a file from form data.
    
    Args:
        uploader: User object uploading the file
        subject: File subject/title
        description: File description
        designation_id: ID of HoldsDesignation for uploader
        upload_file: Optional uploaded file attachment
        form_remarks: Optional remarks for tracking
        send_to_receiver: If True, creates initial tracking entry (send action)
                         If False, saves as draft (save action)
        receiver_username: Username of receiver (required if send_to_receiver=True)
        receive_designation_name: Designation name of receiver (required if send_to_receiver=True)
    
    Returns:
        File object
    
    Raises:
        ValidationError: If validation fails
    """
    # Validate file size
    validate_file_size(upload_file)
    
    # Get uploader's extrainfo and designation
    uploader_extrainfo = uploader.extrainfo
    holds_designation = HoldsDesignation.objects.select_related(
        'user', 'working', 'designation'
    ).get(id=designation_id)
    designation = holds_designation.designation
    
    # Prepare extra JSON for file
    extra_json = {
        'remarks': form_remarks if form_remarks is not None else '',
    }
    
    # Create file
    file = File.objects.create(
        uploader=uploader_extrainfo,
        description=description,
        subject=subject,
        designation=designation,
        upload_file=upload_file,
        file_extra_JSON=extra_json
    )
    
    # If sending immediately, create tracking entry
    if send_to_receiver:
        if not receiver_username or not receive_designation_name:
            raise ValidationError("Receiver username and designation required for send action")
        
        try:
            receiver_user = User.objects.get(username=receiver_username)
        except User.DoesNotExist:
            raise ValidationError("Invalid receiver username")
        
        try:
            receive_designation = Designation.objects.get(name=receive_designation_name)
        except Designation.DoesNotExist:
            raise ValidationError("Invalid receive designation")
        
        # Create tracking entry
        Tracking.objects.create(
            file_id=file,
            current_id=uploader_extrainfo,
            current_design=holds_designation,
            receive_design=receive_designation,
            receiver_id=receiver_user,
            remarks=form_remarks,
            upload_file=upload_file,
        )
        
        # Send notification
        try:
            file_tracking_notif(uploader, receiver_user, subject)
        except Exception as e:
            logger.error(f"Failed to send notification for file {file.id}: {e}")
    
    return file


def forward_file_service(
    file_id,
    current_user,
    current_designation_id,
    receiver_username,
    receive_designation_name,
    remarks,
    upload_file=None,
    is_finish=False
):
    """
    Forward a file to another user/designation.
    
    Args:
        file_id: ID of file to forward
        current_user: User performing the forward
        current_designation_id: ID of current HoldsDesignation
        receiver_username: Username of receiver
        receive_designation_name: Name of receive designation
        remarks: Remarks for forwarding
        upload_file: Optional attachment
        is_finish: If True, marks file as finished
    
    Returns:
        dict with success status and message
    
    Raises:
        ValidationError: If validation fails
    """
    try:
        # Get file
        file = File.objects.get(id=file_id)
        
        # Get current designation
        current_design = HoldsDesignation.objects.select_related(
            'user', 'working', 'designation'
        ).get(id=current_designation_id)
        
        # Validate receiver
        try:
            receiver_user = User.objects.get(username=receiver_username)
        except User.DoesNotExist:
            return {
                'success': False,
                'error': 'Enter a valid Username',
                'context': {'file': file, 'current_design': current_design}
            }
        
        # Validate receive designation
        try:
            receive_design = Designation.objects.get(name=receive_designation_name)
        except Designation.DoesNotExist:
            return {
                'success': False,
                'error': 'Enter a valid Designation',
                'context': {'file': file, 'current_design': current_design}
            }
        
        # Create tracking entry
        tracking = Tracking.objects.create(
            file_id=file,
            current_id=current_user.extrainfo,
            current_design=current_design,
            receive_design=receive_design,
            receiver_id=receiver_user,
            remarks=remarks,
            upload_file=upload_file,
        )
        
        # Send notification
        try:
            file_tracking_notif(current_user, receiver_user, file.subject)
        except Exception as e:
            logger.error(f"Failed to send notification for forwarded file {file.id}: {e}")
        
        return {
            'success': True,
            'message': 'File forwarded successfully',
            'tracking': tracking
        }
        
    except File.DoesNotExist:
        return {
            'success': False,
            'error': 'File not found'
        }
    except Exception as e:
        logger.error(f"Error forwarding file {file_id}: {e}", exc_info=True)
        return {
            'success': False,
            'error': str(e)
        }


def archive_file_service(file_id, user):
    """
    Archive a file.
    
    Args:
        file_id: ID of file to archive
        user: User archiving the file
    
    Returns:
        dict with success status and message
    """
    try:
        file = File.objects.get(id=file_id)
        
        # Check permission - only uploader can archive
        if file.uploader.user != user:
            return {
                'success': False,
                'error': 'Permission denied'
            }
        
        # Mark as read (archived)
        file.is_read = True
        file.save()
        
        return {
            'success': True,
            'message': 'File archived successfully'
        }
        
    except File.DoesNotExist:
        return {
            'success': False,
            'error': 'File not found'
        }
    except Exception as e:
        logger.error(f"Error archiving file {file_id}: {e}", exc_info=True)
        return {
            'success': False,
            'error': str(e)
        }


def unarchive_file_service(file_id, user):
    """
    Unarchive a file.
    
    Args:
        file_id: ID of file to unarchive
        user: User unarchiving the file
    
    Returns:
        dict with success status and message
    """
    try:
        file = File.objects.get(id=file_id)
        
        # Check permission - only uploader can unarchive
        if file.uploader.user != user:
            return {
                'success': False,
                'error': 'Permission denied'
            }
        
        # Mark as not read (active)
        file.is_read = False
        file.save()
        
        return {
            'success': True,
            'message': 'File unarchived successfully'
        }
        
    except File.DoesNotExist:
        return {
            'success': False,
            'error': 'File not found'
        }
    except Exception as e:
        logger.error(f"Error unarchiving file {file_id}: {e}", exc_info=True)
        return {
            'success': False,
            'error': str(e)
        }


def update_draft_and_send(
    file_id,
    user,
    subject,
    description,
    designation_id,
    receiver_username,
    receive_designation_name,
    remarks,
    upload_file=None
):
    """
    Update a draft file and send it.
    
    Args:
        file_id: ID of draft file to update
        user: User updating the draft
        subject: Updated subject
        description: Updated description
        designation_id: ID of designation
        receiver_username: Username of receiver
        receive_designation_name: Name of receive designation
        remarks: Remarks for tracking
        upload_file: Optional new attachment
    
    Returns:
        dict with success status and message
    """
    try:
        file = File.objects.get(id=file_id)
        
        # Check permission
        if file.uploader.user != user:
            return {
                'success': False,
                'error': 'Permission denied'
            }
        
        # Update file
        file.subject = subject
        file.description = description
        
        # Get designation
        holds_designation = HoldsDesignation.objects.select_related(
            'user', 'working', 'designation'
        ).get(id=designation_id)
        file.designation = holds_designation.designation
        
        # Update file if new upload
        if upload_file:
            validate_file_size(upload_file)
            file.upload_file = upload_file
        
        file.save()
        
        # Create tracking entry
        receiver_user = User.objects.get(username=receiver_username)
        receive_designation = Designation.objects.get(name=receive_designation_name)
        
        Tracking.objects.create(
            file_id=file,
            current_id=user.extrainfo,
            current_design=holds_designation,
            receive_design=receive_designation,
            receiver_id=receiver_user,
            remarks=remarks,
            upload_file=upload_file,
        )
        
        # Send notification
        try:
            file_tracking_notif(user, receiver_user, subject)
        except Exception as e:
            logger.error(f"Failed to send notification for draft {file.id}: {e}")
        
        return {
            'success': True,
            'message': 'Draft updated and sent successfully'
        }
        
    except File.DoesNotExist:
        return {
            'success': False,
            'error': 'File not found'
        }
    except User.DoesNotExist:
        return {
            'success': False,
            'error': 'Invalid receiver username'
        }
    except Designation.DoesNotExist:
        return {
            'success': False,
            'error': 'Invalid designation'
        }
    except ValidationError as ve:
        return {
            'success': False,
            'error': str(ve)
        }
    except Exception as e:
        logger.error(f"Error updating draft {file_id}: {e}", exc_info=True)
        return {
            'success': False,
            'error': str(e)
        }


def delete_file_service(file_id, user):
    """
    Delete a file and all its tracking entries.
    
    Args:
        file_id: ID of file to delete
        user: User deleting the file
    
    Returns:
        dict with success status and message
    """
    try:
        file = File.objects.get(id=file_id)
        
        # Check permission - only uploader can delete
        if file.uploader.user != user:
            return {
                'success': False,
                'error': 'Permission denied'
            }
        
        # Delete file (tracking entries will be deleted via CASCADE)
        file.delete()
        
        return {
            'success': True,
            'message': 'File deleted successfully'
        }
        
    except File.DoesNotExist:
        return {
            'success': False,
            'error': 'File not found'
        }
    except Exception as e:
        logger.error(f"Error deleting file {file_id}: {e}", exc_info=True)
        return {
            'success': False,
            'error': str(e)
        }
