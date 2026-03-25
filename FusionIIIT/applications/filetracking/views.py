# views.py
# Thin web views for the filetracking module.
# All business logic delegated to services.py, all queries to selectors.py.
# Fixes: V-01 to V-17, V-20 to V-24, V-27, V-28, V-33, V-36, R-01 to R-04, R-11

from django.db import IntegrityError
from django.http import HttpResponse, JsonResponse
from django.contrib import messages
from django.shortcuts import render, get_object_or_404, redirect, reverse
from django.contrib.auth.decorators import login_required
from django.core import serializers as django_serializers
from django.contrib.auth.models import User
from django.views.decorators.http import require_POST
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator

from applications.globals.models import Designation           # V-17, V-20: top-level

from .models import File, Tracking, DEFAULT_DESIGNATION, LOGIN_URL  # V-27, V-28
from . import services
from . import selectors
from .decorators import user_is_student, dropdown_designation_valid


# ---------------------------------------------------------------------------
# Helper  (R-11)
# ---------------------------------------------------------------------------

def _ajax_autocomplete(request, query_func, result_key):
    """Shared AJAX autocomplete pattern. (R-11)"""
    if request.method == 'POST':
        value = request.POST.get('value')
        results = query_func(value)
        results_json = django_serializers.serialize('json', list(results))
        return HttpResponse(JsonResponse({result_key: results_json}), content_type='application/json')
    return HttpResponse(status=405)


# ---------------------------------------------------------------------------
# Compose / Send  (V-01, V-20, V-23, V-24, R-04)
# ---------------------------------------------------------------------------

@login_required(login_url=LOGIN_URL)                          # V-28
@user_is_student
@dropdown_designation_valid
def filetracking(request):
    """
    Compose file page: save as draft or send.
    V-01: ORM moved to selectors.  V-23/V-24: validation added.
    V-20: Designation imported at top. R-04: session pattern extracted.
    """
    if request.method == "POST":
        try:
            if 'save' in request.POST:
                services.save_draft_file(
                    uploader_user=request.user,
                    title=request.POST.get('title'),
                    description=request.POST.get('desc'),
                    design_id=request.POST.get('design'),
                    upload_file=request.FILES.get('myfile'),
                    remarks=request.POST.get('remarks'),
                )
                messages.success(request, 'File Draft Saved Successfully')

            if 'send' in request.POST:
                try:
                    services.send_file(
                        uploader_user=request.user,
                        title=request.POST.get('title'),
                        description=request.POST.get('desc'),
                        design_id=request.POST.get('design'),
                        receiver_username=request.POST.get('receiver'),
                        receiver_designation_name=request.POST.get('receive'),
                        upload_file=request.FILES.get('myfile'),
                        remarks=request.POST.get('remarks'),
                    )
                    messages.success(request, 'File sent successfully')
                except User.DoesNotExist:
                    messages.error(request, 'Enter a valid Username')
                    return redirect('/filetracking/')
                except Designation.DoesNotExist:                # V-20: now valid
                    messages.error(request, 'Enter a valid Designation')
                    return redirect('/filetracking/')
                except ValidationError as e:
                    messages.error(request, str(e.message if hasattr(e, 'message') else e))
                    return redirect('/filetracking')

        except IntegrityError:
            message = "FileID Already Taken.!!"
            return HttpResponse(message)

    # R-04: consolidated session pattern
    designation_name, hd_obj = services.get_session_designation(request)

    context = {
        'file': selectors.get_all_files_with_related(),        # V-01: selector
        'extrainfo': selectors.get_extrainfo_by_user(request.user),
        'holdsdesignations': selectors.get_user_designations(request.user),
        'designation_name': designation_name,
        'designation_id': hd_obj.id,
        'notifications': selectors.get_user_notifications(request.user),  # V-33
        'path_parent': 'compose',
    }
    return render(request, 'filetracking/composefile.html', context)


@login_required(login_url=LOGIN_URL)                          # V-28
@user_is_student
@dropdown_designation_valid
def draft_design(request):
    """Redirect to drafts page (R-04)."""
    url = services.get_designation_redirect_url_from_session(request, 'drafts')
    return redirect(url)


@login_required(login_url=LOGIN_URL)                          # V-28
@user_is_student
@dropdown_designation_valid
def drafts_view(request, id):
    """View all drafts for a user+designation. V-09: enrichment via service."""
    user_hd = selectors.get_holds_designation_by_id(id)
    designation = services.get_designation_display_name(user_hd)
    draft_files = services.view_drafts(
        username=user_hd.user,
        designation=user_hd.designation,
        src_module='filetracking',
    )

    draft_files = services.enrich_draft_files(draft_files)     # V-09

    context = {
        'draft_files': draft_files,
        'designations': designation,
        'notifications': selectors.get_user_notifications(request.user),  # V-33
        'path_parent': 'draft',
    }
    return render(request, 'filetracking/drafts.html', context)


# ---------------------------------------------------------------------------
# Outbox / Inbox  (V-10, V-11, V-12, V-13, R-01, R-04)
# ---------------------------------------------------------------------------

@login_required(login_url=LOGIN_URL)                          # V-28
@user_is_student
@dropdown_designation_valid
def outbox_view(request):
    """V-10: enrichment via service. R-01: filter via service."""
    designation_name, user_hd = services.get_session_designation(request)  # R-04
    designation = services.get_designation_display_name(user_hd)

    outward_files = services.view_outbox(
        username=user_hd.user,
        designation=user_hd.designation,
        src_module='filetracking',
    )
    outward_files = services.enrich_outbox_files(outward_files, user_hd)  # V-10

    # R-01: consolidated filtering
    outward_files = services.filter_files_by_search(
        outward_files,
        subject_query=request.GET.get('subject', ''),
        sent_to_query=request.GET.get('sent_to', ''),
        date_query=request.GET.get('date', ''),
    )

    paginator = Paginator(outward_files, 10)
    page_obj = paginator.get_page(request.GET.get('page'))

    context = {
        'page_obj': page_obj,
        'viewer_designation': designation,
        'notifications': selectors.get_user_notifications(request.user),  # V-33
        'path_parent': 'outbox',
    }
    return render(request, 'filetracking/outbox.html', context)


@login_required(login_url=LOGIN_URL)                          # V-28
@user_is_student
@dropdown_designation_valid
def inbox_view(request):
    """V-11: enrichment via service. R-01: filter via service."""
    designation_name, user_hd = services.get_session_designation(request)  # R-04
    designation = services.get_designation_display_name(user_hd)

    inward_files = services.view_inbox(
        username=user_hd.user,
        designation=user_hd.designation,
        src_module='filetracking',
    )
    inward_files = services.enrich_inbox_files(inward_files, user_hd)  # V-11

    # R-01: consolidated filtering
    inward_files = services.filter_files_by_search(
        inward_files,
        subject_query=request.GET.get('subject', ''),
        sent_to_query=request.GET.get('sent_to', ''),
        date_query=request.GET.get('date', ''),
    )

    paginator = Paginator(inward_files, 10)
    page_obj = paginator.get_page(request.GET.get('page'))

    context = {
        'page_obj': page_obj,
        'designations': designation,
        'notifications': selectors.get_user_notifications(request.user),  # V-33
        'path_parent': 'inbox',
    }
    return render(request, 'filetracking/inbox.html', context)


# ---------------------------------------------------------------------------
# Redirect helpers  (R-03: already consolidated)
# ---------------------------------------------------------------------------

@login_required(login_url=LOGIN_URL)                          # V-28
@user_is_student
@dropdown_designation_valid
def outward(request):
    """Redirect to outbox page."""
    url = services.get_designation_redirect_url_from_session(request, 'outbox')
    return redirect(url)


@login_required(login_url=LOGIN_URL)                          # V-28
@user_is_student
@dropdown_designation_valid
def inward(request):
    """Redirect to inbox page."""
    url = services.get_designation_redirect_url_from_session(request, 'inbox')
    return redirect(url)


@login_required(login_url=LOGIN_URL)                          # V-28
@user_is_student
@dropdown_designation_valid
def archive_design(request):
    """Redirect to archive page."""
    url = services.get_designation_redirect_url_from_session(request, 'archive')
    return redirect(url)


# ---------------------------------------------------------------------------
# File views  (V-02, V-21)
# ---------------------------------------------------------------------------

@login_required(login_url=LOGIN_URL)                          # V-28
@user_is_student
@dropdown_designation_valid
def confirmdelete(request, id):
    """Confirm deletion page. V-02: uses selector."""
    file = selectors.get_file_by_id_with_related(id)           # V-02
    context = {'j': file}
    return render(request, 'filetracking/confirmdelete.html', context)


@login_required(login_url=LOGIN_URL)                          # V-28
@user_is_student
@dropdown_designation_valid
def view_file_view(request, id):
    """View file details. V-21: safe referer parsing."""
    file = get_object_or_404(File, id=id)
    track = selectors.get_tracking_for_file(file)
    designations = selectors.get_user_designations(request.user)

    forward_enable, archive_enable = services.get_file_view_permissions(file.id, request.user)

    # V-21: safe referer parsing
    try:
        parent_of_prev_path = request.META.get('HTTP_REFERER', '/').strip("/").split('/')[-2]
    except (IndexError, ValueError):
        parent_of_prev_path = 'inbox'

    context = {
        'designations': designations,
        'file': file,
        'track': track,
        'forward_enable': forward_enable,
        'archive_enable': archive_enable,
        'notifications': selectors.get_user_notifications(request.user),  # V-33
        'path_parent': parent_of_prev_path,
    }
    return render(request, 'filetracking/viewfile.html', context)


@login_required(login_url=LOGIN_URL)                          # V-28
@user_is_student
@dropdown_designation_valid
def archive_file_view(request, id):
    """Archive a file via POST."""
    if request.method == "POST":
        success, msg = services.archive_file_with_auth(id, request.user)
        if success:
            messages.success(request, msg)
        else:
            messages.error(request, msg)
    return render(request, 'filetracking/composefile.html')


# ---------------------------------------------------------------------------
# Forward  (V-03, V-04, V-20, R-02, R-04)
# ---------------------------------------------------------------------------

@login_required(login_url=LOGIN_URL)                          # V-28
@user_is_student
@dropdown_designation_valid
def forward(request, id):
    """Forward a file. V-03/V-04: read-status via services. R-02: merged exception blocks."""
    file = get_object_or_404(File, id=id)
    track = selectors.get_tracking_for_file(file)
    designations = selectors.get_user_designations(request.user)

    designation_name, hd_obj = services.get_session_designation(request)  # R-04
    designation_id = hd_obj.id

    if request.method == "POST":
        if 'finish' in request.POST:
            services.mark_file_as_read(file.id)                # V-03
        if 'send' in request.POST:
            services.mark_tracking_as_read(file)               # V-04
            try:
                services.forward_file_from_view(
                    file_obj=file,
                    requesting_user=request.user,
                    sender_design_id=request.POST.get('sender'),
                    receiver_username=request.POST.get('receiver'),
                    receiver_designation_name=request.POST.get('receive'),
                    upload_file=request.FILES.get('myfile'),
                    remarks=request.POST.get('remarks'),
                )
                messages.success(request, 'File sent successfully')
                return redirect(reverse('filetracking:filetracking'))
            except (User.DoesNotExist, Designation.DoesNotExist):     # R-02, V-20
                messages.error(request, 'Enter a valid destination')
                context = {
                    'designations': designations, 'file': file, 'track': track,
                    'designation_name': designation_name, 'designation_id': designation_id,
                    'notifications': selectors.get_user_notifications(request.user),
                    'path_parent': 'inbox',
                }
                return render(request, 'filetracking/forward.html', context)

    context = {
        'designations': designations, 'file': file, 'track': track,
        'designation_name': designation_name, 'designation_id': designation_id,
        'notifications': selectors.get_user_notifications(request.user),  # V-33
        'path_parent': 'inbox',
    }
    return render(request, 'filetracking/forward.html', context)


# ---------------------------------------------------------------------------
# Archive views  (V-05, V-06, V-07, V-08, V-14)
# ---------------------------------------------------------------------------

@login_required(login_url=LOGIN_URL)                          # V-28
@user_is_student
@dropdown_designation_valid
def archive_view(request, id):
    """Archive listing page. V-14: enrichment via service. V-05: designation via selector."""
    user_hd = selectors.get_holds_designation_by_id(id)
    designation = services.get_designation_display_name(user_hd)

    archive_files = services.view_archived(
        username=user_hd.user,
        designation=user_hd.designation,
        src_module='filetracking',
    )

    archive_files = services.enrich_archive_files(archive_files)   # V-14, V-05

    context = {
        'archive_files': archive_files,
        'designations': designation,
        'notifications': selectors.get_user_notifications(request.user),  # V-33
        'path_parent': 'archive',
    }
    return render(request, 'filetracking/archive.html', context)


@login_required(login_url=LOGIN_URL)                          # V-28
@user_is_student
@dropdown_designation_valid
def archive_finish(request, id):
    """V-06: uses selector instead of direct ORM."""
    file1 = get_object_or_404(File, id=id)
    track = selectors.get_tracking_for_file(file1)             # V-06
    return render(request, 'filetracking/archive_finish.html', {'file': file1, 'track': track})


@login_required(login_url=LOGIN_URL)                          # V-28
@user_is_student
@dropdown_designation_valid
def finish_design(request):
    designation = selectors.get_user_designations(request.user)
    context = {
        'designation': designation,
        'notifications': selectors.get_user_notifications(request.user),  # V-33
    }
    return render(request, 'filetracking/finish_design.html', context)


@login_required(login_url=LOGIN_URL)                          # V-28
@user_is_student
@dropdown_designation_valid
def finish_fileview(request, id):
    out = selectors.get_tracking_for_uploader(request.user.extrainfo, is_read=False)
    abcd = selectors.get_holds_designation_by_id(id)
    context = {
        'out': out, 'abcd': abcd,
        'notifications': selectors.get_user_notifications(request.user),  # V-33
    }
    return render(request, 'filetracking/finish_fileview.html', context)


@login_required(login_url=LOGIN_URL)                          # V-28
@user_is_student
@dropdown_designation_valid
def finish(request, id):
    """V-07, V-08: uses selector and service for ORM ops."""
    file1 = get_object_or_404(File, id=id)
    track = selectors.get_tracking_for_file(file1)             # V-07
    if request.method == "POST":
        if 'Finished' in request.POST:
            services.archive_file_and_tracking(file1.id)       # V-08
            messages.success(request, 'File Archived')
    context = {
        'file': file1, 'track': track, 'fileid': id,
        'notifications': selectors.get_user_notifications(request.user),  # V-33
    }
    return render(request, 'filetracking/finish.html')


# ---------------------------------------------------------------------------
# AJAX autocomplete  (V-36: renamed, R-11: consolidated, V-22: login_required)
# ---------------------------------------------------------------------------

@login_required(login_url=LOGIN_URL)                          # V-22, V-28
def ajax_designation_autocomplete(request):
    """Designation autocomplete. V-36: renamed from AjaxDropdown1. R-11: shared helper."""
    return _ajax_autocomplete(request, selectors.get_designations_starting_with, 'holds')


@login_required(login_url=LOGIN_URL)                          # V-22, V-28
def ajax_user_autocomplete(request):
    """Username autocomplete. V-36: renamed from AjaxDropdown. R-11: shared helper."""
    return _ajax_autocomplete(request, selectors.get_users_starting_with, 'users')


# Keep backward-compatible aliases for URLs
AjaxDropdown1 = ajax_designation_autocomplete                  # V-36: alias
AjaxDropdown = ajax_user_autocomplete                          # V-36: alias


# ---------------------------------------------------------------------------
# Delete / Forward inward  (V-15, V-22)
# ---------------------------------------------------------------------------

@login_required(login_url=LOGIN_URL)                          # V-28
@user_is_student
@dropdown_designation_valid
def delete(request, id):
    try:
        services.delete_file_with_auth(id, request.user)
    except ValidationError as e:
        messages.error(request, str(e))
    return redirect('/filetracking/draftdesign/')


@login_required(login_url=LOGIN_URL)                          # V-28
@user_is_student
@dropdown_designation_valid
def forward_inward(request, id):
    """V-15: Fixed dead mutation — now persists via service."""
    file = get_object_or_404(File, id=id)
    services.mark_file_as_read(file.id)                        # V-15: was `file.is_read = True` without save
    track = selectors.get_tracking_for_file(file)
    designations = selectors.get_user_designations(request.user)
    context = {
        'designations': designations, 'file': file, 'track': track,
        'notifications': selectors.get_user_notifications(request.user),  # V-33
    }
    return render(request, 'filetracking/forward.html', context)


@login_required(login_url=LOGIN_URL)                          # V-22, V-28
def get_designations_view(request, username):
    """V-22: Added @login_required."""
    designations = services.get_designations(username)
    return JsonResponse(designations, safe=False)


# ---------------------------------------------------------------------------
# Unarchive / Edit Draft / Download
# ---------------------------------------------------------------------------

@login_required(login_url=LOGIN_URL)                          # V-28
@user_is_student
@dropdown_designation_valid
def unarchive_file(request, id):
    try:
        services.unarchive_file(id)
        messages.success(request, 'File unarchived')
    except Exception as e:
        messages.error(request, 'Unable to unarchive: {}'.format(str(e)))
    return render(request, 'filetracking/archive.html')


@login_required(login_url=LOGIN_URL)                          # V-28
@user_is_student
@dropdown_designation_valid
def edit_draft_view(request, id, *args, **kwargs):
    """Edit and send a draft."""
    file = get_object_or_404(File, id=id)
    track = selectors.get_tracking_for_file(file)

    if request.method == "POST":
        if 'send' in request.POST:
            try:
                services.edit_and_send_draft(
                    file_obj=file,
                    track_qs=track,
                    requesting_user=request.user,
                    sender_design_id=request.POST.get('sender'),
                    receiver_username=request.POST.get('receiver'),
                    receiver_designation_name=request.POST.get('receive'),
                    upload_file=request.FILES.get('myfile'),
                    remarks=request.POST.get('remarks'),
                    subject=request.POST.get('subject'),
                    description=request.POST.get('description'),
                )
                messages.success(request, 'File sent successfully')
                return render(request, 'filetracking/composefile.html')
            except (User.DoesNotExist, Designation.DoesNotExist):  # R-02, V-20
                messages.error(request, 'Enter a valid destination')
                return redirect(reverse('filetracking:filetracking'))

    designations = selectors.get_user_designations(request.user)
    designation_name, hd_obj = services.get_session_designation(request)  # R-04

    remarks = None
    if file.file_extra_JSON and file.file_extra_JSON.get('remarks'):
        remarks = file.file_extra_JSON['remarks']

    context = {
        'designations': designations, 'file': file, 'track': track,
        'designation_name': designation_name, 'designation_id': hd_obj.id,
        'remarks': remarks,
        'notifications': selectors.get_user_notifications(request.user),  # V-33
    }
    return render(request, 'filetracking/editdraft.html', context)


@login_required(login_url=LOGIN_URL)                          # V-28
@user_is_student
@dropdown_designation_valid
@require_POST
def download_file(request, id):
    zip_data, output_filename = services.generate_file_download(id)
    response = HttpResponse(zip_data, content_type='application/zip')
    response['Content-Disposition'] = f'attachment; filename="{output_filename}.zip"'
    return response
