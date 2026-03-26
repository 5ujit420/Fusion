# permissions.py
# Custom DRF permission classes for the complaint_system module.
# Addresses: RR-13

from rest_framework.permissions import BasePermission
from . import selectors


class IsCaretaker(BasePermission):
    """Allow access only to users who are caretakers."""
    message = 'You must be a caretaker to perform this action.'

    def has_permission(self, request, view):
        extra = selectors.get_extrainfo_by_user(request.user)
        if extra is None:
            return False
        return selectors.is_caretaker(extra.id)


class IsServiceProvider(BasePermission):
    """Allow access only to users who are service providers."""
    message = 'You must be a service provider to perform this action.'

    def has_permission(self, request, view):
        extra = selectors.get_extrainfo_by_user(request.user)
        if extra is None:
            return False
        return selectors.is_service_provider(extra.id)


class IsCaretakerOrServiceProvider(BasePermission):
    """Allow access to caretakers or service providers."""
    message = 'You must be a caretaker or service provider to perform this action.'

    def has_permission(self, request, view):
        extra = selectors.get_extrainfo_by_user(request.user)
        if extra is None:
            return False
        return selectors.is_caretaker(extra.id) or selectors.is_service_provider(extra.id)


class IsComplaintOwnerOrStaff(BasePermission):
    """Allow access if the user owns the complaint, or is a caretaker/admin."""
    message = 'You are not authorized to perform this action on this complaint.'

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated


class IsReportAuthorized(BasePermission):
    """Allow access only to users authorized to generate reports."""
    message = 'Not authorized to generate report.'

    def has_permission(self, request, view):
        extra = selectors.get_extrainfo_by_user(request.user)
        if extra is None:
            return False
        return (
            selectors.is_caretaker(extra.id)
            or selectors.is_service_provider(extra.id)
            or selectors.is_complaint_admin(extra.id)
            or selectors.is_warden(extra.id)
        )
