# sdk/methods.py
# Backward-compatible SDK layer for external modules.
# R-10: Added deprecation notice. This module should be the ONLY entry point
# for external modules. Plan to remove once all dependents migrate to direct
# service/selector imports.

"""
.. deprecated::
    This module is a backward-compatibility shim. External modules should
    migrate to importing ``filetracking.services`` and ``filetracking.selectors``
    directly. This layer will be removed in a future release.

Known dependents:
    - ps1
    - research_procedures
    - otheracademic
    - iwdModuleV2
    - hr2
    - health_center
    - gymkhana
    - complaint_system
    - programme_curriculum
    - office_module
"""

import warnings
from .. import services
from .. import selectors


def _deprecation_warning(func_name):
    """Issue a deprecation warning for SDK calls."""
    warnings.warn(
        f"filetracking.sdk.methods.{func_name}() is deprecated. "
        f"Use filetracking.services or filetracking.selectors directly.",
        DeprecationWarning,
        stacklevel=3,
    )


# ---- File creation ----

def create_file(uploader, uploader_designation, receiver, receiver_designation,
                subject="", description="", src_module="filetracking",
                src_object_id="", file_extra_JSON=None, attached_file=None):
    """Create and send a file. Delegates to services.create_file_via_sdk()."""
    _deprecation_warning('create_file')
    return services.create_file_via_sdk(
        uploader=uploader,
        uploader_designation=uploader_designation,
        receiver=receiver,
        receiver_designation=receiver_designation,
        subject=subject,
        description=description,
        src_module=src_module,
        src_object_id=src_object_id,
        file_extra_JSON=file_extra_JSON,
        attached_file=attached_file,
    )


def create_draft(uploader, uploader_designation, src_module="filetracking",
                 src_object_id="", file_extra_JSON=None, attached_file=None):
    """Create a draft file. Delegates to services.create_draft_via_sdk()."""
    _deprecation_warning('create_draft')
    return services.create_draft_via_sdk(
        uploader=uploader,
        uploader_designation=uploader_designation,
        src_module=src_module,
        src_object_id=src_object_id,
        file_extra_JSON=file_extra_JSON,
        attached_file=attached_file,
    )


# ---- File views ----

def view_file(file_id):
    """View file details."""
    _deprecation_warning('view_file')
    return services.view_file_details(file_id)


def view_inbox(username, designation, src_module):
    """View inbox files."""
    _deprecation_warning('view_inbox')
    return services.view_inbox(username, designation, src_module)


def view_outbox(username, designation, src_module):
    """View outbox files."""
    _deprecation_warning('view_outbox')
    return services.view_outbox(username, designation, src_module)


def view_drafts(username, designation, src_module):
    """View draft files."""
    _deprecation_warning('view_drafts')
    return services.view_drafts(username, designation, src_module)


def view_archived(username, designation, src_module):
    """View archived files."""
    _deprecation_warning('view_archived')
    return services.view_archived(username, designation, src_module)


def view_history(file_id):
    """View tracking history."""
    _deprecation_warning('view_history')
    return services.view_history(file_id)


# ---- File operations ----

def forward_file(file_id, receiver, receiver_designation, file_extra_JSON,
                 remarks="", file_attachment=None):
    """Forward a file."""
    _deprecation_warning('forward_file')
    return services.forward_file(
        file_id, receiver, receiver_designation, file_extra_JSON,
        remarks=remarks, file_attachment=file_attachment,
    )


def archive_file(file_id):
    """Archive a file."""
    _deprecation_warning('archive_file')
    return services.archive_file_sdk(file_id)


def unarchive_file(file_id):
    """Unarchive a file."""
    _deprecation_warning('unarchive_file')
    return services.unarchive_file(file_id)


def delete_file(file_id):
    """Delete a file."""
    _deprecation_warning('delete_file')
    return services.delete_file(file_id)


# ---- Selectors (read-only) ----

def get_current_file_owner(file_id):
    """Get current file owner."""
    _deprecation_warning('get_current_file_owner')
    return selectors.get_current_file_owner(file_id)


def get_current_file_owner_designation(file_id):
    """Get current file owner's designation."""
    _deprecation_warning('get_current_file_owner_designation')
    return selectors.get_current_file_owner_designation(file_id)
