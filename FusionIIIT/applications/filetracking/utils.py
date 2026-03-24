# utils.py
# Shared utility functions for the filetracking module.
# R-03: Extracted from repeated patterns in views.

from .models import File, Tracking
from applications.globals.models import ExtraInfo, HoldsDesignation, Designation
from django.contrib.auth.models import User
from . import selectors


def get_designation(userid):
    """Return all HoldsDesignation objects for a user. Legacy compatibility."""
    return selectors.get_user_designations(userid)