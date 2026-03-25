"""
Examination module DRF permission classes.

Replaces insecure client-supplied ``request.data["Role"]`` checks
with server-side role resolution via the ``HoldsDesignation`` model.
Fixes audit violations: V14–V18.
"""

from rest_framework.permissions import BasePermission
from applications.globals.models import HoldsDesignation, Designation

from .constants import (
    ROLE_ACADADMIN,
    ROLE_DEAN_ACADEMIC,
    PROFESSOR_ROLES,
)


# ---------------------------------------------------------------------------
# Internal helper
# ---------------------------------------------------------------------------

def _user_holds_designation(user, designation_name: str) -> bool:
    """Return True if *user* currently holds the named designation."""
    return HoldsDesignation.objects.filter(
        user=user,
        designation__name=designation_name,
    ).exists()


def _user_holds_any_designation(user, designation_names) -> bool:
    """Return True if *user* currently holds any of the named designations."""
    return HoldsDesignation.objects.filter(
        user=user,
        designation__name__in=designation_names,
    ).exists()


# ---------------------------------------------------------------------------
# Permission classes
# ---------------------------------------------------------------------------

class IsAcadAdmin(BasePermission):
    """Allows access only to users holding the ``acadadmin`` designation."""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return _user_holds_designation(request.user, ROLE_ACADADMIN)


class IsDeanAcademic(BasePermission):
    """Allows access only to users holding the ``Dean Academic`` designation."""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return _user_holds_designation(request.user, ROLE_DEAN_ACADEMIC)


class IsProfessor(BasePermission):
    """Allows access to Associate / Assistant Professors and Professors."""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return _user_holds_any_designation(request.user, PROFESSOR_ROLES)


class IsAcadAdminOrDean(BasePermission):
    """Allows access to ``acadadmin`` **or** ``Dean Academic``."""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return _user_holds_any_designation(
            request.user, {ROLE_ACADADMIN, ROLE_DEAN_ACADEMIC}
        )


class IsAcadAdminOrProfessor(BasePermission):
    """Allows access to ``acadadmin`` **or** any professor role."""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return _user_holds_any_designation(
            request.user, {ROLE_ACADADMIN} | PROFESSOR_ROLES
        )


class IsAcadAdminOrDeanOrProfessor(BasePermission):
    """Allows access to ``acadadmin``, ``Dean Academic``, or any professor role."""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return _user_holds_any_designation(
            request.user, {ROLE_ACADADMIN, ROLE_DEAN_ACADEMIC} | PROFESSOR_ROLES
        )
