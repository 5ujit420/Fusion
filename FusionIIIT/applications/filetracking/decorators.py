# decorators.py
# Custom view decorators for the filetracking module.
# Fixes: R-12 — uses selectors instead of direct ORM

from django.shortcuts import render
from applications.globals.models import HoldsDesignation
from . import selectors
from .models import DEFAULT_DESIGNATION


def user_check(request):
    """
    Check if the user is a student.
    Returns True if user is a student, False otherwise.
    R-12: uses selectors.get_extrainfo_by_user() instead of direct ORM.
    """
    try:
        user_details = selectors.get_extrainfo_by_user(request.user)   # R-12
        des = HoldsDesignation.objects.all().select_related().filter(user=request.user).first()
        if str(des.designation) == "student":
            return True
        else:
            return False
    except Exception:
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
        designation_name = request.session.get('currentDesignationSelected', DEFAULT_DESIGNATION)  # V-27
        username = request.user
        try:
            designation_id = selectors.get_holds_designation_obj(
                username, designation_name).id
        except Exception:
            return render(request, 'filetracking/invalid_designation.html', {'curr_des': designation_name})
        else:
            return view_func(request, *args, **kwargs)
    return _wrapped_view
