"""
Selectors layer for complaint_system module.

This module contains all database read queries following the selector pattern.
Selectors are responsible for:
- Encapsulating complex ORM queries
- Providing reusable query functions
- Optimizing database access with proper select_related/prefetch_related

Usage:
    from .selectors import get_user_extra_info, is_service_provider
    
    user_info = get_user_extra_info(user)
    if is_service_provider(user):
        ...
"""
from django.db.models import Q
from applications.globals.models import ExtraInfo
from .models import (
    Caretaker, Warden, SectionIncharge, Workers, 
    StudentComplain, ServiceProvider, ServiceAuthority, Complaint_Admin
)


def get_user_extra_info(user):
    """
    Get ExtraInfo for a user with optimized related fields.
    
    Args:
        user: Django User object
        
    Returns:
        ExtraInfo object or None
    """
    return ExtraInfo.objects.select_related('user', 'department').filter(user=user).first()


def is_service_provider(user):
    """
    Check if user is a service provider.
    
    Args:
        user: Django User object
        
    Returns:
        bool
    """
    extra_info = get_user_extra_info(user)
    if not extra_info:
        return False
    return ServiceProvider.objects.filter(ser_pro_id_id=extra_info.id).exists()


def is_caretaker(user):
    """
    Check if user is a caretaker.
    
    Args:
        user: Django User object
        
    Returns:
        bool
    """
    extra_info = get_user_extra_info(user)
    if not extra_info:
        return False
    return Caretaker.objects.filter(staff_id_id=extra_info.id).exists()


def is_warden(user):
    """
    Check if user is a warden.
    
    Args:
        user: Django User object
        
    Returns:
        bool
    """
    extra_info = get_user_extra_info(user)
    if not extra_info:
        return False
    return Warden.objects.filter(staff_id_id=extra_info.id).exists()


def is_complaint_admin(user):
    """
    Check if user is a complaint admin.
    
    Args:
        user: Django User object
        
    Returns:
        bool
    """
    extra_info = get_user_extra_info(user)
    if not extra_info:
        return False
    return Complaint_Admin.objects.filter(sup_id_id=extra_info.id).exists()


def get_user_type_info(user):
    """
    Determine all user type flags in a single check.
    
    This replaces the loop-based checking in CheckUser.get() with
    efficient exists() queries.
    
    Args:
        user: Django User object
        
    Returns:
        dict with boolean flags for each user type
    """
    extra_info = get_user_extra_info(user)
    if not extra_info:
        return {
            'is_service_provider': False,
            'is_caretaker': False,
            'is_warden': False,
            'is_complaint_admin': False,
            'extra_info': None
        }
    
    # Use exists() instead of fetching all objects and looping
    return {
        'is_service_provider': ServiceProvider.objects.filter(ser_pro_id_id=extra_info.id).exists(),
        'is_caretaker': Caretaker.objects.filter(staff_id_id=extra_info.id).exists(),
        'is_warden': Warden.objects.filter(staff_id_id=extra_info.id).exists(),
        'is_complaint_admin': Complaint_Admin.objects.filter(sup_id_id=extra_info.id).exists(),
        'extra_info': extra_info
    }


def get_caretaker_complaints(caretaker_id):
    """
    Get complaints for a caretaker's area.
    
    Args:
        caretaker_id: Caretaker ID
        
    Returns:
        QuerySet of StudentComplain ordered by -id
    """
    caretaker = Caretaker.objects.get(id=caretaker_id)
    return StudentComplain.objects.filter(
        location=caretaker.area
    ).order_by('-id')


def get_warden_complaints(warden_id):
    """
    Get complaints for a warden's area.
    
    Args:
        warden_id: Warden ID
        
    Returns:
        QuerySet of StudentComplain ordered by -id
    """
    warden = Warden.objects.get(id=warden_id)
    return StudentComplain.objects.filter(
        location=warden.area
    ).order_by('-id')


def get_service_provider_complaints(provider_id):
    """
    Get complaints for a service provider based on their type.
    
    Args:
        provider_id: ServiceProvider ID
        
    Returns:
        QuerySet of StudentComplain filtered by type and status
    """
    provider = ServiceProvider.objects.get(id=provider_id)
    return StudentComplain.objects.filter(
        complaint_type=provider.type,
        status__in=[0, 1]
    ).order_by('-id')


def get_complaints_by_area(area):
    """
    Get complaints filtered by area.
    
    Args:
        area: Area string
        
    Returns:
        QuerySet of StudentComplain
    """
    return StudentComplain.objects.filter(location=area).order_by('-id')


def get_user_complaints(user):
    """
    Get all complaints filed by a user.
    
    Args:
        user: Django User object
        
    Returns:
        QuerySet of StudentComplain ordered by -id
    """
    extra_info = get_user_extra_info(user)
    if not extra_info:
        return StudentComplain.objects.none()
    return StudentComplain.objects.filter(complainer=extra_info).order_by('-id')


def get_active_complaints():
    """
    Get all active (non-resolved) complaints.
    
    Returns:
        QuerySet of StudentComplain with status 0 or 1
    """
    return StudentComplain.objects.filter(status__in=[0, 1]).order_by('-id')


def get_pending_complaints():
    """
    Get all pending complaints (status = 0).
    
    Returns:
        QuerySet of StudentComplain with status 0
    """
    return StudentComplain.objects.filter(status=0).order_by('-id')


def get_resolved_complaints():
    """
    Get all resolved complaints (status = 2).
    
    Returns:
        QuerySet of StudentComplain with status 2
    """
    return StudentComplain.objects.filter(status=2).order_by('-id')


def get_complaint_detail(complaint_id):
    """
    Get a single complaint with optimized related fields.
    
    Args:
        complaint_id: Complaint ID
        
    Returns:
        StudentComplain object or None
    """
    return StudentComplain.objects.select_related(
        'complainer',
        'complainer__user',
        'complainer__department',
        'worker_id'
    ).filter(id=complaint_id).first()


def get_workers_for_caretaker(caretaker):
    """
    Get all workers under a caretaker's section incharge.
    
    Args:
        caretaker: Caretaker object
        
    Returns:
        QuerySet of Workers
    """
    # Get section incharges for the caretaker's area work types
    from .models import SectionIncharge
    return Workers.objects.filter(
        secincharge_id__in=SectionIncharge.objects.all()
    )


def get_all_caretakers():
    """
    Get all caretakers with optimized queries.
    
    Returns:
        QuerySet of Caretaker with select_related
    """
    return Caretaker.objects.select_related('staff_id', 'staff_id__user', 'staff_id__department')


def get_all_wardens():
    """
    Get all wardens with optimized queries.
    
    Returns:
        QuerySet of Warden with select_related
    """
    return Warden.objects.select_related('staff_id', 'staff_id__user', 'staff_id__department')


def get_all_service_providers():
    """
    Get all service providers with optimized queries.
    
    Returns:
        QuerySet of ServiceProvider with select_related
    """
    return ServiceProvider.objects.select_related('ser_pro_id', 'ser_pro_id__user', 'ser_pro_id__department')


def get_all_complaint_admins():
    """
    Get all complaint admins with optimized queries.
    
    Returns:
        QuerySet of Complaint_Admin with select_related
    """
    return Complaint_Admin.objects.select_related('sup_id', 'sup_id__user', 'sup_id__department')


def get_all_workers():
    """
    Get all workers with optimized queries.
    
    Returns:
        QuerySet of Workers with select_related
    """
    return Workers.objects.select_related('secincharge_id')


def get_complaint_statistics():
    """
    Get complaint statistics for reporting.
    
    Returns:
        dict with counts
    """
    total = StudentComplain.objects.count()
    pending = StudentComplain.objects.filter(status=0).count()
    assigned = StudentComplain.objects.filter(status=1).count()
    resolved = StudentComplain.objects.filter(status=2).count()
    rejected = StudentComplain.objects.filter(status=3).count()
    
    return {
        'total': total,
        'pending': pending,
        'assigned': assigned,
        'resolved': resolved,
        'rejected': rejected
    }


def get_complaints_by_type(complaint_type):
    """
    Get complaints filtered by type.
    
    Args:
        complaint_type: Type string (e.g., 'Electricity', 'plumber')
        
    Returns:
        QuerySet of StudentComplain
    """
    return StudentComplain.objects.filter(complaint_type=complaint_type).order_by('-id')


def get_complaints_by_status(status):
    """
    Get complaints filtered by status.
    
    Args:
        status: Status integer (0=pending, 1=assigned, 2=resolved, 3=rejected)
        
    Returns:
        QuerySet of StudentComplain
    """
    return StudentComplain.objects.filter(status=status).order_by('-id')


def get_recent_complaints(limit=10):
    """
    Get most recent complaints.
    
    Args:
        limit: Number of complaints to return
        
    Returns:
        QuerySet of StudentComplain
    """
    return StudentComplain.objects.order_by('-complaint_date')[:limit]
