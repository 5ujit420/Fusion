# decorators.py
# Custom view decorators for the filetracking module.
# T-16/S-38: Silent exception swallowing eliminated — all except blocks now log warnings.
# T-15/S-36: Uses named constants instead of 'default_value' magic string.

import logging

from django.shortcuts import render
from django.contrib.auth.models import User
from applications.globals.models import ExtraInfo, HoldsDesignation
from . import selectors
from .utils import DESIGNATION_SESSION_KEY, DEFAULT_DESIGNATION_SESSION_VALUE

logger = logging.getLogger(__name__)


def user_check(request):
    """
    Check if the user is a student.
    Returns True if user is a student, False otherwise.
    """
    try:
        user_details = ExtraInfo.objects.select_related('user', 'department').get(user=request.user)
        des = HoldsDesignation.objects.all().select_related().filter(user=request.user).first()
        if str(des.designation) == "student":
            return True
        else:
            return False
    except Exception:
        # T-16/S-38: Log the exception instead of silently swallowing it.
        logger.warning(
            "user_check failed for user '%s'",
            getattr(request, 'user', 'unknown'),
            exc_info=True,
        )
        return False


def user_is_student(view_func):
    def _wrapped_view(request, *args, **kwargs):
        if user_check(request):
            return render(request, 'filetracking/fileTrackingNotAllowed.html')
        else:
            return view_func(request, *args, **kwargs)
    return _wrapped_view


def dropdown_designation_valid(view_func):
    def _wrapped_view(request, *args, **kwargs):
        # T-15/S-36: Use named constants instead of inline magic strings.
        designation_name = request.session.get(DESIGNATION_SESSION_KEY, DEFAULT_DESIGNATION_SESSION_VALUE)
        username = request.user
        try:
            designation_id = selectors.get_holds_designation_obj(
                username, designation_name).id
        except Exception:
            # T-16/S-38: Log the exception instead of silently swallowing it.
            logger.warning(
                "dropdown_designation_valid failed for user '%s' with designation '%s'",
                username,
                designation_name,
                exc_info=True,
            )
            return render(request, 'filetracking/invalid_designation.html', {'curr_des': designation_name})
        else:
            return view_func(request, *args, **kwargs)
    return _wrapped_view
