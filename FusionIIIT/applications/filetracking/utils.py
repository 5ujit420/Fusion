# utils.py
# Shared utility functions and constants for the filetracking module.
# T-15/S-36: DEFAULT_DESIGNATION_SESSION_VALUE named constant replaces all 'default_value' literals.

from .models import File, Tracking
from applications.globals.models import ExtraInfo, HoldsDesignation, Designation
from django.contrib.auth.models import User
from . import selectors


# ---------------------------------------------------------------------------
# Named constants  (T-15, S-36)
# ---------------------------------------------------------------------------

# Session key used to store the currently selected designation
DESIGNATION_SESSION_KEY = 'currentDesignationSelected'

# Default fallback value when the session key is absent
DEFAULT_DESIGNATION_SESSION_VALUE = 'default_value'


def get_designation(userid):
    """Return all HoldsDesignation objects for a user. Legacy compatibility."""
    return selectors.get_user_designations(userid)