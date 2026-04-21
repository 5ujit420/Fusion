# sdk/methods.py
# Thin compatibility wrapper — delegates all logic to services.py and selectors.py.
# External modules importing from this file (e.g. complaint_system) continue to work.
# V-41: Redistributed logic to services.py, selectors.py, utils.py.

from applications.filetracking import services
from applications.filetracking import selectors


# ---------------------------------------------------------------------------
# Public SDK API — delegates to services
# ---------------------------------------------------------------------------

def create_file(uploader, uploader_designation, receiver, receiver_designation,
                subject="", description="", src_module="filetracking",
                src_object_id="", file_extra_JSON=None, attached_file=None):
    if file_extra_JSON is None:
        file_extra_JSON = {}
    return services.create_file_via_sdk(
        uploader, uploader_designation, receiver, receiver_designation,
        subject, description, src_module, src_object_id,
        file_extra_JSON, attached_file
    )


def create_draft(uploader, uploader_designation, src_module="filetracking",
                 src_object_id="", file_extra_JSON=None, attached_file=None):
    if file_extra_JSON is None:
        file_extra_JSON = {}
    return services.create_draft_via_sdk(
        uploader, uploader_designation, src_module, src_object_id,
        file_extra_JSON, attached_file
    )


def view_file(file_id):
    return services.view_file_details(file_id)


def delete_file(file_id):
    return services.delete_file(file_id)


def view_inbox(username, designation, src_module):
    return services.view_inbox(username, designation, src_module)


def view_outbox(username, designation, src_module):
    return services.view_outbox(username, designation, src_module)


def view_archived(username, designation, src_module):
    return services.view_archived(username, designation, src_module)


def archive_file(file_id):
    return services.archive_file_sdk(file_id)


def unarchive_file(file_id):
    return services.unarchive_file(file_id)


def view_drafts(username, designation, src_module):
    return services.view_drafts(username, designation, src_module)


def forward_file(file_id, receiver, receiver_designation, file_extra_JSON,
                 remarks="", file_attachment=None):
    return services.forward_file(
        file_id, receiver, receiver_designation, file_extra_JSON,
        remarks, file_attachment
    )


def view_history(file_id):
    return services.view_history(file_id)


def get_designations(username):
    return services.get_designations(username)


# ---------------------------------------------------------------------------
# Helper functions — delegates to selectors
# ---------------------------------------------------------------------------

def get_current_file_owner(file_id):
    return selectors.get_current_file_owner(file_id)


def get_current_file_owner_designation(file_id):
    return selectors.get_current_file_owner_designation(file_id)


def get_last_file_sender(file_id):
    return selectors.get_last_file_sender(file_id)


def get_last_file_sender_designation(file_id):
    return selectors.get_last_file_sender_designation(file_id)


def get_user_object_from_username(username):
    return selectors.get_user_by_username(username)


def get_ExtraInfo_object_from_username(username):
    return selectors.get_extrainfo_by_username(username)


def uniqueList(l):
    return services.unique_list(l)


def add_uploader_department_to_files_list(files):
    return services.add_uploader_department_to_files_list(files)


def get_designation_obj_from_name(designation):
    return selectors.get_designation_by_name(designation)


def get_HoldsDesignation_obj(username, designation):
    return selectors.get_holds_designation_obj(username, designation)


def get_last_recv_tracking_for_user(file_id, username, designation):
    recv_user = selectors.get_user_by_username(username)
    recv_design = selectors.get_designation_by_name(designation)
    return selectors.get_last_recv_tracking(file_id, recv_user, recv_design)


def get_last_forw_tracking_for_user(file_id, username, designation):
    sender_extrainfo = selectors.get_extrainfo_by_username(username)
    sender_hd = selectors.get_holds_designation_obj(username, designation)
    return selectors.get_last_forw_tracking(file_id, sender_extrainfo, sender_hd)


def get_extra_info_object_from_id(id):
    return selectors.get_extrainfo_by_id(id)
