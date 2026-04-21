# decorators.py
# Custom view decorators for the filetracking module.
# V-31: Fixed bare `except:` to `except Exception:`.

from django.shortcuts import render
from django.contrib.auth.models import User
from applications.globals.models import ExtraInfo, HoldsDesignation
from . import selectors


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
    except Exception:  # V-31: was bare `except:`
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
        designation_name = request.session.get('currentDesignationSelected', 'default_value')
        username = request.user
        try:
            designation_id = selectors.get_holds_designation_obj(
                username, designation_name).id
        except Exception:  # V-31: was bare `except:`
            return render(request, 'filetracking/invalid_designation.html', {'curr_des': designation_name})
        else:
            return view_func(request, *args, **kwargs)
    return _wrapped_view
