"""
Selectors module for filetracking app.
All read-side ORM queries should be placed here.
Pattern: get_<entity>_by_<criteria> or filter_<entities>_by_<criteria>
"""
from django.contrib.auth.models import User
from applications.filetracking.models import File, Tracking
from applications.globals.models import ExtraInfo, HoldsDesignation, Designation


def get_file_by_id(file_id):
    """Get a single file by ID."""
    return File.objects.get(id=file_id)


def get_all_files():
    """Get all files with related uploader and designation info."""
    return File.objects.select_related(
        'uploader__user', 
        'uploader__department', 
        'designation'
    ).all()


def get_files_for_user(user):
    """Get all files uploaded by a user."""
    return File.objects.filter(uploader=user.extrainfo)


def get_tracking_by_file_id(file_id):
    """Get all tracking entries for a file with full relations."""
    return Tracking.objects.select_related(
        'file_id',
        'current_id__user',
        'current_id__department',
        'current_design__user',
        'current_design__working',
        'current_design__designation',
        'receiver_id',
        'receive_design'
    ).filter(file_id=file_id)


def get_tracking_with_full_relations(file_id):
    """Get tracking entries optimized for view operations."""
    return Tracking.objects.select_related(
        'file_id',
        'current_id',
        'current_design',
        'receiver_id',
        'receive_design'
    ).filter(file_id=file_id)


def get_extrainfo_all():
    """Get all ExtraInfo records with relations."""
    return ExtraInfo.objects.select_related('user', 'department').all()


def get_holdsdesignations_all():
    """Get all HoldsDesignation records with relations."""
    return HoldsDesignation.objects.select_related(
        'user', 
        'working', 
        'designation'
    ).all()


def get_designation_by_id(designation_id):
    """Get a designation by ID."""
    return Designation.objects.get(id=designation_id)


def get_designation_by_name(name):
    """Get a designation by name."""
    return Designation.objects.get(name=name)


def get_holdsdesignation_by_id(hd_id):
    """Get a HoldsDesignation record by ID with full relations."""
    return HoldsDesignation.objects.select_related(
        'user', 
        'working', 
        'designation'
    ).get(id=hd_id)


def get_user_by_username(username):
    """Get a User object by username."""
    return User.objects.get(username=username)


def get_user_with_extrainfo(username):
    """Get User with extrainfo in a single query."""
    return User.objects.select_related('extrainfo').get(username=username)


def get_inbox_files(user, current_designation_id):
    """
    Get files received by user in their inbox.
    Optimized with select_related to avoid N+1 queries.
    """
    return Tracking.objects.select_related(
        'file_id__uploader__user',
        'file_id__uploader__department',
        'file_id__designation',
        'current_design__designation',
        'receiver_id__extrainfo'
    ).filter(
        receiver_id=user,
        receive_design=current_designation_id
    ).order_by('-receive_date')


def get_outbox_files(user, current_designation_id):
    """
    Get files sent by user from their outbox.
    Optimized with select_related to avoid N+1 queries.
    """
    return Tracking.objects.select_related(
        'file_id__uploader__user',
        'file_id__uploader__department',
        'file_id__designation',
        'current_design__designation',
        'receiver_id__extrainfo'
    ).filter(
        file_id__uploader=user.extrainfo,
        current_design=current_designation_id
    ).order_by('-receive_date')


def get_draft_files(user, holds_designation_id):
    """Get draft files created by user for a specific designation."""
    return File.objects.filter(
        uploader=user.extrainfo,
        designation_id=holds_designation_id
    ).order_by('-upload_date')


def get_archived_files(user):
    """Get archived files for a user."""
    return File.objects.filter(
        uploader=user.extrainfo,
        is_read=True  # Assuming archived files are marked as read
    ).order_by('-upload_date')


def get_history_for_file(file_id):
    """Get complete history of a file with all tracking entries."""
    return Tracking.objects.select_related(
        'file_id',
        'current_id',
        'current_design',
        'receiver_id',
        'receive_design'
    ).filter(file_id=file_id).order_by('receive_date')


def get_current_file_owner(file):
    """Get the current owner of a file based on latest tracking."""
    latest_tracking = Tracking.objects.filter(
        file_id=file
    ).select_related('receiver_id').order_by('-receive_date').first()
    
    if latest_tracking:
        return latest_tracking.receiver_id
    return file.uploader.user


def filter_files_by_search(files_queryset, search_params):
    """
    Apply search filters to a files queryset.
    Supports subject, description, and uploader filters.
    """
    if search_params.get('subject'):
        files_queryset = files_queryset.filter(
            subject__icontains=search_params['subject']
        )
    if search_params.get('description'):
        files_queryset = files_queryset.filter(
            description__icontains=search_params['description']
        )
    if search_params.get('uploader'):
        files_queryset = files_queryset.filter(
            uploader__user__username__icontains=search_params['uploader']
        )
    return files_queryset
