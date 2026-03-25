# selectors.py
# All database queries for the filetracking module.
# Fixes: V-01, V-02, V-05, V-19, V-33, V-35, R-05, R-06

from django.contrib.auth.models import User
from applications.globals.models import ExtraInfo, HoldsDesignation, Designation
from .models import File, Tracking


# ---------------------------------------------------------------------------
# Tracking selectors  (R-05 — unified, R-06 — merged owner queries)
# ---------------------------------------------------------------------------

TRACKING_SELECT_RELATED = (
    'file_id__uploader__user',
    'file_id__uploader__department',
    'file_id__designation',
    'current_id__user',
    'current_id__department',
    'current_design__user',
    'current_design__working',
    'current_design__designation',
    'receiver_id',
    'receive_design',
)


def get_tracking_for_file(file_or_id):
    """Return all tracking entries for a file with full select_related.
    Accepts a File object or an integer PK.  (R-05: unified)"""
    return (
        Tracking.objects.select_related(*TRACKING_SELECT_RELATED)
        .filter(file_id=file_or_id)
        .order_by('receive_date')
    )


def get_tracking_history(file_id):
    """Return tracking history ordered by most recent first (V-35: select_related)."""
    return (
        Tracking.objects.select_related('receiver_id', 'receive_design')
        .filter(file_id=file_id)
        .order_by('-receive_date')
    )


def get_latest_tracking(file_id):
    """Return the most recent tracking entry for a file."""
    return (
        Tracking.objects.select_related('receiver_id', 'receive_design',
                                        'current_id__user', 'current_design__designation')
        .filter(file_id=file_id)
        .order_by('-receive_date')
        .first()
    )


def get_tracking_for_uploader(uploader_extrainfo, is_read=False):
    """Return tracking for files uploaded by a user."""
    return (
        Tracking.objects.select_related(*TRACKING_SELECT_RELATED)
        .filter(file_id__uploader=uploader_extrainfo, is_read=is_read)
        .order_by('-forward_date')
    )


def get_tracking_by_receiver(receiver_user, receive_design, src_module, is_read=False):
    """Return tracking entries where the user is the receiver."""
    return (
        Tracking.objects.select_related('file_id')
        .filter(
            receiver_id=receiver_user,
            receive_design=receive_design,
            file_id__src_module=src_module,
            file_id__is_read=is_read,
        )
        .order_by('-receive_date')
    )


def get_tracking_by_sender(sender_extrainfo, sender_holds_designation, src_module, is_read=False):
    """Return tracking entries where the user is the sender."""
    return (
        Tracking.objects.select_related('file_id')
        .filter(
            current_id=sender_extrainfo,
            current_design=sender_holds_designation,
            file_id__src_module=src_module,
            file_id__is_read=is_read,
        )
        .order_by('-receive_date')
    )


def get_last_recv_tracking(file_id, receiver_user, receive_design):
    """Return the last tracking where a specific user+designation received a file."""
    return (
        Tracking.objects.filter(
            file_id=file_id,
            receiver_id=receiver_user,
            receive_design=receive_design,
        )
        .order_by('-receive_date')
        .first()
    )


def get_last_forw_tracking(file_id, sender_extrainfo, sender_holds_designation):
    """Return the last tracking where a specific user forwarded a file."""
    return (
        Tracking.objects.filter(
            file_id=file_id,
            current_id=sender_extrainfo,
            current_design=sender_holds_designation,
        )
        .order_by('-forward_date')
        .first()
    )


# ---------------------------------------------------------------------------
# Tracking write selectors  (V-19: ORM writes moved from services)
# ---------------------------------------------------------------------------

def create_tracking(**kwargs):
    """Create a Tracking entry. (V-19)"""
    return Tracking.objects.create(**kwargs)


def update_tracking_read_status(file_or_id, is_read=True):
    """Mark tracking entries for a file as read/unread. (V-04, V-19)"""
    return Tracking.objects.filter(file_id=file_or_id).update(is_read=is_read)


# ---------------------------------------------------------------------------
# File selectors  (V-01, V-02, V-19)
# ---------------------------------------------------------------------------

def get_all_files_with_related():
    """Return all files with uploader and designation prefetched (V-01)."""
    return File.objects.select_related(
        'uploader__user', 'uploader__department', 'designation'
    ).all()


def get_file_by_id(file_id):
    """Return a single File by PK, or raise File.DoesNotExist."""
    return File.objects.get(id=file_id)


def get_file_by_id_with_related(file_id):
    """Return a File with uploader and designation prefetched (V-02)."""
    return File.objects.select_related(
        'uploader__user', 'uploader__department', 'designation'
    ).get(id=file_id)


def get_draft_files(uploader_extrainfo, designation, src_module):
    """Return files with no tracking (drafts)."""
    return (
        File.objects.filter(
            tracking__isnull=True,
            uploader=uploader_extrainfo,
            designation=designation,
            src_module=src_module,
        )
        .order_by('-upload_date')
    )


# ---------------------------------------------------------------------------
# File write selectors  (V-19: ORM writes moved from services)
# ---------------------------------------------------------------------------

def create_file(**kwargs):
    """Create a File entry. (V-19)"""
    return File.objects.create(**kwargs)


def update_file_read_status(file_id, is_read=True):
    """Set is_read flag on a File. (V-03, V-08, V-19, R-08)"""
    return File.objects.filter(id=file_id).update(is_read=is_read)


def delete_file_by_id(file_id):
    """Delete a file by PK. (V-19)"""
    return File.objects.filter(id=file_id).delete()


# ---------------------------------------------------------------------------
# User / ExtraInfo / Designation selectors
# ---------------------------------------------------------------------------

def get_user_by_username(username):
    """Return a User object by username."""
    return User.objects.get(username=username)


def get_extrainfo_by_user(user):
    """Return ExtraInfo for a User."""
    return ExtraInfo.objects.select_related('user', 'department').get(user=user)


def get_extrainfo_by_username(username):
    """Return ExtraInfo from a username string."""
    user = get_user_by_username(username)
    return ExtraInfo.objects.get(user=user)


def get_extrainfo_by_id(extra_id):
    """Return ExtraInfo by its PK."""
    return ExtraInfo.objects.get(id=extra_id)


def get_designation_by_name(designation_name):
    """Return a Designation by name."""
    return Designation.objects.get(name=designation_name)


def get_designation_by_id(pk):
    """Return a Designation by PK. (V-05)"""
    return Designation.objects.get(id=pk)


def get_holds_designation(user, designation):
    """Return a HoldsDesignation for a user+designation pair."""
    return HoldsDesignation.objects.get(user=user, designation=designation)


def get_holds_designation_by_id(pk):
    """Return a HoldsDesignation by PK with select_related."""
    return HoldsDesignation.objects.select_related(
        'user', 'working', 'designation'
    ).get(pk=pk)


def get_holds_designation_obj(username, designation_name):
    """Return a HoldsDesignation from username + designation name strings."""
    user_obj = get_user_by_username(username)
    des_obj = get_designation_by_name(designation_name)
    return HoldsDesignation.objects.get(user=user_obj, designation=des_obj)


def get_user_designations(user):
    """Return all HoldsDesignation objects for a user."""
    return HoldsDesignation.objects.select_related(
        'user', 'working', 'designation'
    ).filter(user=user)


def get_designation_names_for_user(username):
    """Return a list of designation names held by a user."""
    user = get_user_by_username(username)
    designations_held = HoldsDesignation.objects.filter(user=user)
    return [hd.designation.name for hd in designations_held]


def get_designations_starting_with(prefix):
    """Return Designation objects whose name starts with prefix."""
    return Designation.objects.filter(name__startswith=prefix)


def get_users_starting_with(prefix):
    """Return User objects whose username starts with prefix."""
    return User.objects.filter(username__startswith=prefix)


# ---------------------------------------------------------------------------
# Ownership helpers  (R-06: merged into single call)
# ---------------------------------------------------------------------------

def get_current_file_owner_info(file_id):
    """Return (owner_user, owner_designation) from the latest tracking in one query.
    (R-06: merged get_current_file_owner + get_current_file_owner_designation)"""
    latest = get_latest_tracking(file_id)
    if latest is None:
        return None, None
    return latest.receiver_id, latest.receive_design


def get_current_file_owner(file_id):
    """Return the User who is the latest recipient of the file."""
    owner, _ = get_current_file_owner_info(file_id)
    return owner


def get_current_file_owner_designation(file_id):
    """Return the Designation of the latest recipient."""
    _, designation = get_current_file_owner_info(file_id)
    return designation


def get_last_file_sender(file_id):
    """Return the User who last forwarded/sent the file."""
    latest = get_latest_tracking(file_id)
    if latest is None:
        return None
    return latest.current_id.user


def get_last_file_sender_designation(file_id):
    """Return the Designation of the last sender (ordered by receive_date asc -> first)."""
    latest = Tracking.objects.select_related(
        'current_design__designation'
    ).filter(file_id=file_id).order_by('receive_date').first()
    if latest is None:
        return None
    return latest.current_design.designation


# ---------------------------------------------------------------------------
# Notification selector  (V-33)
# ---------------------------------------------------------------------------

def get_user_notifications(user):
    """Return notifications for a user. (V-33)"""
    return user.notifications.all()
