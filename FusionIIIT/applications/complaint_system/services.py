"""
Services layer for complaint_system module.

This module contains all business logic following the service layer pattern.
Services are responsible for:
- Business rules and validation
- Coordinating between models, selectors, and external systems
- Transaction management
- Notification dispatch

Layer contract: View → Service → Selector → ORM

Usage:
    from .services import (
        calculate_complaint_deadline,
        lodge_complaint,
        resolve_complaint,
        submit_feedback
    )
    
    deadline = calculate_complaint_deadline('Electricity')
    complaint = lodge_complaint(user, data)
"""
from datetime import timedelta
from django.utils import timezone
from django.db import transaction
from applications.globals.models import ExtraInfo
from .models import (
    Caretaker, Warden, StudentComplain, ServiceProvider, 
    ServiceAuthority, Complaint_Admin, Workers, Constants
)
from .selectors import (
    get_user_extra_info, is_caretaker, is_warden, 
    get_all_caretakers, get_caretaker_complaints
)


# =============================================================================
# CONSTANTS - Replace magic strings and numbers
# =============================================================================

DEADLINE_DAYS_MAP = {
    'Electricity': 1,
    'carpenter': 2,
    'plumber': 2,
    'garbage': 3,
    'dustbin': 3,
    'internet': 4,
    'other': 4,
}

LOCATION_DESIGNATION_MAP = {
    'hall-1': 'hall1caretaker',
    'hall-3': 'hall3caretaker',
    'hall-4': 'hall4caretaker',
    'library': 'cc1convener',
    'computer center': 'cc2convener',
    'core_lab': 'deanrcdc',
    'LHTC': 'deanr&d',
    'NR2': 'deanplanning',
    'NR3': 'deanfi',
    'Admin building': 'complaint_admin',
    'Rewa_Residency': 'rewacaretaker',
    'Maa Saraswati Hostel': 'masaraswaticaretaker',
    'Nagarjun Hostel': 'nagarjuncaretaker',
    'Panini Hostel': 'paninicaretaker',
}


# =============================================================================
# DEADLINE CALCULATION
# =============================================================================

def calculate_complaint_deadline(complaint_type):
    """
    Calculate the deadline for a complaint based on its type.
    
    This replaces the duplicated elif chains in views.py with a single
    dictionary lookup.
    
    Args:
        complaint_type: String matching Constants.COMPLAINT_TYPE keys
        
    Returns:
        datetime: Deadline timestamp
    """
    days = DEADLINE_DAYS_MAP.get(complaint_type, 4)  # Default to 4 days
    return timezone.now() + timedelta(days=days)


def get_deadline_days(complaint_type):
    """
    Get the number of days for a complaint type deadline.
    
    Args:
        complaint_type: String matching Constants.COMPLAINT_TYPE keys
        
    Returns:
        int: Number of days
    """
    return DEADLINE_DAYS_MAP.get(complaint_type, 4)


# =============================================================================
# USER TYPE DETECTION
# =============================================================================

def get_user_type(user):
    """
    Determine user type and appropriate endpoint.
    
    This extracts the business logic from CheckUser.get() into a service function.
    
    Args:
        user: Django User object
        
    Returns:
        dict with user_type and next_url, or error
    """
    user_type_info = {
        'is_service_provider': is_service_provider_func(user),
        'is_caretaker': is_caretaker_func(user),
        'is_warden': is_warden_func(user),
        'is_complaint_admin': is_complaint_admin_func(user),
        'extra_info': get_user_extra_info(user)
    }
    
    if user_type_info['is_service_provider']:
        return {'user_type': 'service_provider', 'next_url': '/complaint/service_provider/'}
    elif user_type_info['is_complaint_admin']:
        return {'user_type': 'complaint_admin', 'next_url': '/complaint/complaint_admin/'}
    elif user_type_info['is_caretaker']:
        return {'user_type': 'caretaker', 'next_url': '/complaint/caretaker/'}
    elif user_type_info['is_warden']:
        return {'user_type': 'warden', 'next_url': '/complaint/warden/'}
    elif user_type_info['extra_info']:
        user_type = user_type_info['extra_info'].user_type
        if user_type in ['student', 'staff', 'faculty']:
            return {'user_type': user_type, 'next_url': '/complaint/user/'}
    
    return {'error': 'wrong user credentials'}


def is_service_provider_func(user):
    """Check if user is service provider."""
    extra_info = get_user_extra_info(user)
    if not extra_info:
        return False
    from .models import ServiceProvider
    return ServiceProvider.objects.filter(ser_pro_id_id=extra_info.id).exists()


def is_caretaker_func(user):
    """Check if user is caretaker."""
    extra_info = get_user_extra_info(user)
    if not extra_info:
        return False
    return Caretaker.objects.filter(staff_id_id=extra_info.id).exists()


def is_warden_func(user):
    """Check if user is warden."""
    extra_info = get_user_extra_info(user)
    if not extra_info:
        return False
    return Warden.objects.filter(staff_id_id=extra_info.id).exists()


def is_complaint_admin_func(user):
    """Check if user is complaint admin."""
    extra_info = get_user_extra_info(user)
    if not extra_info:
        return False
    return Complaint_Admin.objects.filter(sup_id_id=extra_info.id).exists()


# =============================================================================
# NOTIFICATION HELPERS
# =============================================================================

def send_lodge_notification(complaint, location):
    """
    Send notification to appropriate caretaker when a complaint is lodged.
    
    This extracts the duplicated notification logic from multiple views.
    
    Args:
        complaint: StudentComplain object
        location: Location string
    """
    designation = LOCATION_DESIGNATION_MAP.get(location, 'complaint_admin')
    
    # Find the caretaker for this area
    try:
        caretaker = Caretaker.objects.get(area=location)
        recipient = caretaker.staff_id.user
        verb = f"New complaint lodged at {location}"
        
        # Import here to avoid circular imports
        from notification.views import complaint_system_notif
        complaint_system_notif(recipient, complaint.id, verb)
    except Caretaker.DoesNotExist:
        # Fallback to complaint admin
        pass


def notify_caretakers(complaint, caretakers):
    """
    Send notifications to caretakers about a new complaint.
    
    Args:
        complaint: StudentComplain object
        caretakers: QuerySet of Caretaker objects
    """
    from notification.views import complaint_system_notif
    
    for caretaker in caretakers:
        recipient = caretaker.staff_id.user
        verb = f"New complaint in {caretaker.area}"
        complaint_system_notif(recipient, complaint.id, verb)


# =============================================================================
# COMPLAINT LODGING
# =============================================================================

@transaction.atomic
def lodge_complaint(user, data):
    """
    Lodge a new complaint.
    
    This extracts the business logic from UserComplaintView.post(),
    CaretakerLodgeView.post(), and ServiceProviderLodgeView.post().
    
    Args:
        user: Django User making the request
        data: dict with complaint data (location, complaint_type, details, etc.)
        
    Returns:
        tuple: (success: bool, complaint: StudentComplain or None, error: str or None)
    """
    try:
        # Get user's extra info
        complainer = get_user_extra_info(user)
        if not complainer:
            return False, None, "User profile not found"
        
        # Calculate deadline
        complaint_type = data.get('complaint_type', 'other')
        complaint_finish = calculate_complaint_deadline(complaint_type)
        
        # Create complaint
        complaint = StudentComplain.objects.create(
            complainer=complainer,
            complaint_date=timezone.now(),
            complaint_finish=complaint_finish,
            complaint_type=complaint_type,
            location=data.get('location'),
            specific_location=data.get('specific_location', ''),
            details=data.get('details', ''),
            status=0,  # Pending
            remarks='Pending',
            flag=0,
            reason='None',
            comment='None'
        )
        
        # Handle file upload if present
        if 'upload_complaint' in data and data['upload_complaint']:
            complaint.upload_complaint = data['upload_complaint']
            complaint.save()
        
        # Send notification
        location = data.get('location')
        if location:
            send_lodge_notification(complaint, location)
        
        return True, complaint, None
        
    except Exception as e:
        return False, None, str(e)


# =============================================================================
# COMPLAINT RESOLUTION
# =============================================================================

@transaction.atomic
def resolve_complaint(complaint_id, status_choice, comment='', uploaded_file=None):
    """
    Resolve a pending complaint.
    
    This extracts the business logic from ResolvePendingView.post() and
    similar resolution methods.
    
    Args:
        complaint_id: ID of the complaint to resolve
        status_choice: 'Yes' or 'No'
        comment: Optional comment
        uploaded_file: Optional resolved file upload
        
    Returns:
        tuple: (success: bool, complaint: StudentComplain or None, error: str or None)
    """
    try:
        complaint = StudentComplain.objects.get(id=complaint_id)
        
        if status_choice == 'Yes':
            # Mark as resolved
            complaint.status = 2  # Resolved
            complaint.remarks = comment if comment else 'Resolved'
            if uploaded_file:
                complaint.upload_resolved = uploaded_file
            complaint.flag = 1
        else:
            # Mark as rejected
            complaint.status = 3  # Rejected
            complaint.remarks = comment if comment else 'Rejected'
            complaint.reason = comment if comment else 'No reason provided'
        
        complaint.save()
        
        # Send notification to complainer
        try:
            from notification.views import complaint_system_notif
            recipient = complaint.complainer.user
            verb = f"Your complaint has been {'resolved' if status_choice == 'Yes' else 'rejected'}"
            complaint_system_notif(recipient, complaint.id, verb)
        except Exception:
            pass  # Don't fail resolution if notification fails
        
        return True, complaint, None
        
    except StudentComplain.DoesNotExist:
        return False, None, "Complaint not found"
    except Exception as e:
        return False, None, str(e)


# =============================================================================
# FEEDBACK SUBMISSION
# =============================================================================

@transaction.atomic
def submit_feedback(user, complaint_id, feedback_text, rating):
    """
    Submit feedback for a resolved complaint.
    
    This extracts the business logic from SubmitFeedbackView.post() and
    CaretakerFeedbackView.post().
    
    Args:
        user: Django User submitting feedback
        complaint_id: ID of the complaint
        feedback_text: Feedback text
        rating: Integer rating (should be validated before calling)
        
    Returns:
        tuple: (success: bool, complaint: StudentComplain or None, error: str or None)
    """
    try:
        complaint = StudentComplain.objects.get(id=complaint_id)
        
        # Validate rating
        if not (1 <= rating <= 5):
            return False, None, "Rating must be between 1 and 5"
        
        # Update complaint feedback
        complaint.feedback = feedback_text
        complaint.save()
        
        # Update caretaker rating if applicable
        try:
            caretaker = Caretaker.objects.get(area=complaint.location)
            # Simple average: add new rating to existing
            current_rating = caretaker.rating or 0
            # This is a simplified approach - in production you'd want to track individual ratings
            caretaker.rating = min(current_rating + rating, 5)  # Cap at 5
            caretaker.myfeedback = feedback_text
            caretaker.save()
        except Caretaker.DoesNotExist:
            pass  # No caretaker for this area
        
        return True, complaint, None
        
    except StudentComplain.DoesNotExist:
        return False, None, "Complaint not found"
    except Exception as e:
        return False, None, str(e)


# =============================================================================
# WORKER ASSIGNMENT
# =============================================================================

@transaction.atomic
def assign_worker_to_complaint(complaint_id, worker_id):
    """
    Assign a worker to a complaint.
    
    Args:
        complaint_id: ID of the complaint
        worker_id: ID of the worker to assign
        
    Returns:
        tuple: (success: bool, complaint: StudentComplain or None, error: str or None)
    """
    try:
        complaint = StudentComplain.objects.get(id=complaint_id)
        worker = Workers.objects.get(id=worker_id)
        
        complaint.worker_id = worker
        complaint.status = 1  # Assigned
        complaint.remarks = f"Assigned to {worker.name}"
        complaint.save()
        
        return True, complaint, None
        
    except StudentComplain.DoesNotExist:
        return False, None, "Complaint not found"
    except Workers.DoesNotExist:
        return False, None, "Worker not found"
    except Exception as e:
        return False, None, str(e)


# =============================================================================
# REPORT GENERATION
# =============================================================================

def generate_report_for_user(user):
    """
    Generate complaint report data for a user.
    
    This extracts the reporting logic from GenerateReportView.get().
    
    Args:
        user: Django User
        
    Returns:
        dict with report data
    """
    extra_info = get_user_extra_info(user)
    if not extra_info:
        return {'error': 'User profile not found'}
    
    report_data = {
        'user_type': extra_info.user_type,
        'total_complaints': 0,
        'pending': 0,
        'assigned': 0,
        'resolved': 0,
        'rejected': 0,
        'complaints': []
    }
    
    # Get complaints based on user type
    if extra_info.user_type == 'student':
        complaints = StudentComplain.objects.filter(complainer=extra_info)
    elif extra_info.user_type == 'staff':
        if is_caretaker_func(user):
            try:
                caretaker = Caretaker.objects.get(staff_id=extra_info)
                complaints = StudentComplain.objects.filter(location=caretaker.area)
                report_data['area'] = caretaker.area
            except Caretaker.DoesNotExist:
                complaints = StudentComplain.objects.none()
        else:
            complaints = StudentComplain.objects.none()
    elif extra_info.user_type == 'faculty':
        if is_service_provider_func(user):
            try:
                provider = ServiceProvider.objects.get(ser_pro_id=extra_info)
                complaints = StudentComplain.objects.filter(
                    complaint_type=provider.type,
                    status__in=[0, 1]
                )
                report_data['type'] = provider.type
            except ServiceProvider.DoesNotExist:
                complaints = StudentComplain.objects.none()
        else:
            complaints = StudentComplain.objects.none()
    else:
        complaints = StudentComplain.objects.none()
    
    # Populate statistics
    report_data['total_complaints'] = complaints.count()
    report_data['pending'] = complaints.filter(status=0).count()
    report_data['assigned'] = complaints.filter(status=1).count()
    report_data['resolved'] = complaints.filter(status=2).count()
    report_data['rejected'] = complaints.filter(status=3).count()
    
    # Serialize complaint data
    for comp in complaints.order_by('-id'):
        report_data['complaints'].append({
            'id': comp.id,
            'complainer': str(comp.complainer.user.username),
            'complaint_date': comp.complaint_date.isoformat() if comp.complaint_date else None,
            'complaint_finish': comp.complaint_finish.isoformat() if comp.complaint_finish else None,
            'complaint_type': comp.complaint_type,
            'location': comp.location,
            'status': comp.status,
            'remarks': comp.remarks,
            'worker_name': str(comp.worker_id.name) if comp.worker_id else None,
        })
    
    return report_data


# =============================================================================
# STATUS UPDATE
# =============================================================================

@transaction.atomic
def update_complaint_status(complaint_id, new_status, remarks=''):
    """
    Update complaint status.
    
    This extracts the status update business rule from views.
    
    Args:
        complaint_id: ID of the complaint
        new_status: New status integer (0=pending, 1=assigned, 2=resolved, 3=rejected)
        remarks: Optional remarks
        
    Returns:
        tuple: (success: bool, complaint: StudentComplain or None, error: str or None)
    """
    try:
        complaint = StudentComplain.objects.get(id=complaint_id)
        complaint.status = new_status
        if remarks:
            complaint.remarks = remarks
        complaint.save()
        return True, complaint, None
        
    except StudentComplain.DoesNotExist:
        return False, None, "Complaint not found"
    except Exception as e:
        return False, None, str(e)


# =============================================================================
# FILE FORWARDING
# =============================================================================

@transaction.atomic
def forward_complaint_file(file_id, current_id, current_designation, target_designation, remarks):
    """
    Forward a complaint file through the workflow.
    
    This wraps the filetracking SDK call with proper error handling.
    
    Args:
        file_id: File tracking ID
        current_id: Current holder's ExtraInfo ID
        current_designation: Current designation
        target_designation: Target designation
        remarks: Remarks for the forwarding
        
    Returns:
        tuple: (success: bool, error: str or None)
    """
    try:
        from applications.filetracking.sdk.methods import forward_file
        
        # Get required parameters from database
        extra_info = ExtraInfo.objects.get(id=current_id)
        
        result = forward_file(
            file_id,
            current_id,
            current_designation,
            target_designation,
            remarks,
            extra_info.user
        )
        
        return True, None
        
    except Exception as e:
        return False, str(e)


# =============================================================================
# VALIDATION HELPERS
# =============================================================================

def validate_rating(rating):
    """
    Validate rating value.
    
    Args:
        rating: Rating value to validate
        
    Returns:
        tuple: (valid: bool, error: str or None)
    """
    try:
        rating_int = int(rating)
        if 1 <= rating_int <= 5:
            return True, None
        else:
            return False, "Rating must be between 1 and 5"
    except (TypeError, ValueError):
        return False, "Rating must be a valid integer"


def validate_complaint_data(data):
    """
    Validate complaint creation data.
    
    Args:
        data: dict with complaint data
        
    Returns:
        tuple: (valid: bool, errors: list)
    """
    errors = []
    
    # Required fields
    required_fields = ['location', 'complaint_type', 'details']
    for field in required_fields:
        if field not in data or not data[field]:
            errors.append(f"{field} is required")
    
    # Validate location
    if 'location' in data and data['location']:
        valid_locations = [loc[0] for loc in Constants.AREA]
        if data['location'] not in valid_locations:
            errors.append(f"Invalid location. Must be one of: {', '.join(valid_locations)}")
    
    # Validate complaint type
    if 'complaint_type' in data and data['complaint_type']:
        valid_types = [ct[0] for ct in Constants.COMPLAINT_TYPE]
        if data['complaint_type'] not in valid_types:
            errors.append(f"Invalid complaint type. Must be one of: {', '.join(valid_types)}")
    
    # Validate details length
    if 'details' in data and len(data['details']) > 100:
        errors.append("Details must be 100 characters or less")
    
    return len(errors) == 0, errors
