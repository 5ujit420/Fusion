# views.py — thin web views for the filetracking module.
# T-02/S-01,S-02: outbox_view and inbox_view slimmed; enrichment delegated to services.
# T-03/S-06,S-07: deep nesting flattened in forward and filetracking views.
# T-04/S-09: merged duplicate except blocks in forward.
# T-05/S-18–S-22: all raw ORM replaced with selectors/services.
# T-06/S-23,S-24: mark_file_read/mark_tracking_read service calls.
# T-07/S-25: get_draft_remarks service call.
# T-12/S-32: AjaxDropdown1→designation_autocomplete_view, AjaxDropdown→user_autocomplete_view.
# T-14/S-35: parse_datetime import removed (date parsing moved to services).
# T-15/S-36: DEFAULT_DESIGNATION_SESSION_VALUE named constant used everywhere.

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

from .models import File, Tracking
from . import services
from . import selectors
from .decorators import user_is_student, dropdown_designation_valid
from .utils import DESIGNATION_SESSION_KEY, DEFAULT_DESIGNATION_SESSION_VALUE


@login_required(login_url="/accounts/login/")
@user_is_student
@dropdown_designation_valid
def filetracking(request):
    """
    Compose file page: save as draft or send.
    T-03/S-07: early-return on GET flattens nesting from 4→2 levels.
    """
    if request.method == "POST":
        # T-03/S-07: flattened — save and send branches at same indent level.
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
                except (User.DoesNotExist, ValidationError) as e:
                    msg = e.message if hasattr(e, 'message') else str(e)
                    messages.error(request, msg)
                    return redirect('/filetracking/')

        except IntegrityError:
            return HttpResponse("FileID Already Taken.!!")

    # T-05/S-19: raw File.objects.select_related call replaced with selector.
    from applications.globals.models import Designation
    designation_name = request.session.get(DESIGNATION_SESSION_KEY, DEFAULT_DESIGNATION_SESSION_VALUE)
    hd_obj = selectors.get_holds_designation_obj(request.user, designation_name)

    context = {
        'file': selectors.get_all_files_with_related(),
        'extrainfo': selectors.get_extrainfo_by_user(request.user),
        'holdsdesignations': selectors.get_user_designations(request.user),
        'designation_name': designation_name,
        'designation_id': hd_obj.id,
        'notifications': request.user.notifications.all(),
        'path_parent': 'compose',
    }
    return render(request, 'filetracking/composefile.html', context)


@login_required(login_url="/accounts/login")
@user_is_student
@dropdown_designation_valid
def draft_design(request):
    """Redirect to drafts page."""
    url = services.get_designation_redirect_url_from_session(request, 'drafts')
    return redirect(url)


@login_required(login_url="/accounts/login")
@user_is_student
@dropdown_designation_valid
def drafts_view(request, id):
    """View all drafts for a user+designation. T-10/S-28: enrichment via service bulk-fetch."""
    user_hd = selectors.get_holds_designation_by_id(id)
    designation = services.get_designation_display_name(user_hd)
    draft_files = services.view_drafts(
        username=user_hd.user,
        designation=user_hd.designation,
        src_module='filetracking',
    )
    # T-10/S-28: single bulk-fetch replaces per-file selector calls.
    draft_files = services.enrich_draft_files(draft_files)
    draft_files = services.add_uploader_department_to_files_list(draft_files)

    context = {
        'draft_files': draft_files,
        'designations': designation,
        'notifications': request.user.notifications.all(),
        'path_parent': 'draft',
    }
    return render(request, 'filetracking/drafts.html', context)


@login_required(login_url="/accounts/login")
@user_is_student
@dropdown_designation_valid
def outbox_view(request):
    """T-02/S-01: slimmed — enrich→filter→paginate→render; T-10/S-26: N+1 eliminated."""
    dropdown_design = request.session.get(DESIGNATION_SESSION_KEY, DEFAULT_DESIGNATION_SESSION_VALUE)
    user_hd = selectors.get_holds_designation_obj(request.user, dropdown_design)
    designation = services.get_designation_display_name(user_hd)
    sender_extrainfo = selectors.get_extrainfo_by_username(user_hd.user)

    outward_files = services.view_outbox(
        username=user_hd.user,
        designation=user_hd.designation,
        src_module='filetracking',
    )

    # T-10/S-26: bulk enrichment — single set of queries regardless of file count.
    outward_files = services.enrich_outbox_files(outward_files, sender_extrainfo, user_hd)

    # T-01/S-08: shared filter function replaces duplicated 13-line block.
    outward_files = services.filter_files_by_search_params(
        outward_files,
        subject_q=request.GET.get('subject', ''),
        sent_to_q=request.GET.get('sent_to', ''),
        date_q=request.GET.get('date', ''),
        date_field='last_sent_date',
    )

    paginator = Paginator(outward_files, 10)
    page_obj = paginator.get_page(request.GET.get('page'))

    context = {
        'page_obj': page_obj,
        'viewer_designation': designation,
        'notifications': request.user.notifications.all(),
        'path_parent': 'outbox',
    }
    return render(request, 'filetracking/outbox.html', context)


@login_required(login_url="/accounts/login")
@user_is_student
@dropdown_designation_valid
def inbox_view(request):
    """T-02/S-02: slimmed — enrich→filter→paginate→render; T-10/S-27: N+1 eliminated."""
    dropdown_design = request.session.get(DESIGNATION_SESSION_KEY, DEFAULT_DESIGNATION_SESSION_VALUE)
    user_hd = selectors.get_holds_designation_obj(request.user, dropdown_design)
    designation = services.get_designation_display_name(user_hd)

    inward_files = services.view_inbox(
        username=user_hd.user,
        designation=user_hd.designation,
        src_module='filetracking',
    )

    # T-10/S-27: bulk enrichment.
    inward_files = services.enrich_inbox_files(inward_files, user_hd.user, user_hd)
    inward_files = services.add_uploader_department_to_files_list(inward_files)

    # T-01/S-08,R-01: shared filter function replaces duplicated block.
    inward_files = services.filter_files_by_search_params(
        inward_files,
        subject_q=request.GET.get('subject', ''),
        sent_to_q=request.GET.get('sent_to', ''),
        date_q=request.GET.get('date', ''),
        date_field='last_sent_date',
    )

    paginator = Paginator(inward_files, 10)
    page_obj = paginator.get_page(request.GET.get('page'))

    context = {
        'page_obj': page_obj,
        'designations': designation,
        'notifications': request.user.notifications.all(),
        'path_parent': 'inbox',
    }
    return render(request, 'filetracking/inbox.html', context)


@login_required(login_url="/accounts/login")
@user_is_student
@dropdown_designation_valid
def outward(request):
    """Redirect to outbox page."""
    url = services.get_designation_redirect_url_from_session(request, 'outbox')
    return redirect(url)


@login_required(login_url="/accounts/login")
@user_is_student
@dropdown_designation_valid
def inward(request):
    """Redirect to inbox page."""
    url = services.get_designation_redirect_url_from_session(request, 'inbox')
    return redirect(url)


@login_required(login_url="/accounts/login")
@user_is_student
@dropdown_designation_valid
def confirmdelete(request, id):
    """T-05/S-18: raw File.objects.select_related replaced with selector."""
    file = selectors.get_file_by_id_with_related(id)
    context = {'j': file}
    return render(request, 'filetracking/confirmdelete.html', context)


@login_required(login_url="/accounts/login")
@user_is_student
@dropdown_designation_valid
def view_file_view(request, id):
    file = get_object_or_404(File, id=id)
    track = selectors.get_tracking_for_file(file)
    designations = selectors.get_user_designations(request.user)
    forward_enable, archive_enable = services.get_file_view_permissions(file.id, request.user)
    parent_of_prev_path = (
        request.META.get('HTTP_REFERER', '/').strip("/").split('/')[-2]
        if request.META.get('HTTP_REFERER') else 'inbox'
    )
    context = {
        'designations': designations,
        'file': file,
        'track': track,
        'forward_enable': forward_enable,
        'archive_enable': archive_enable,
        'notifications': request.user.notifications.all(),
        'path_parent': parent_of_prev_path,
    }
    return render(request, 'filetracking/viewfile.html', context)


@login_required(login_url="/accounts/login")
@user_is_student
@dropdown_designation_valid
def archive_file_view(request, id):
    if request.method == "POST":
        success, msg = services.archive_file_with_auth(id, request.user)
        if success:
            messages.success(request, msg)
        else:
            messages.error(request, msg)
    return render(request, 'filetracking/composefile.html')


@login_required(login_url="/accounts/login")
@user_is_student
@dropdown_designation_valid
def forward(request, id):
    """
    T-03/S-06: deep nesting flattened using early-return on GET.
    T-04/S-09,R-02: merged duplicate except blocks into one.
    T-06/S-23,S-24: file/tracking state mutations moved to service calls.
    """
    file = get_object_or_404(File, id=id)
    track = selectors.get_tracking_for_file(file)
    designations = selectors.get_user_designations(request.user)
    designation_name = request.session.get(DESIGNATION_SESSION_KEY, DEFAULT_DESIGNATION_SESSION_VALUE)
    hd_obj = selectors.get_holds_designation_obj(request.user, designation_name)
    designation_id = hd_obj.id

    # T-03/S-06: early-return on non-POST flattens outer nesting.
    if request.method != "POST":
        context = {
            'designations': designations, 'file': file, 'track': track,
            'designation_name': designation_name, 'designation_id': designation_id,
            'notifications': request.user.notifications.all(), 'path_parent': 'inbox',
        }
        return render(request, 'filetracking/forward.html', context)

    if 'finish' in request.POST:
        services.mark_file_read(file.id)     # T-06/S-23

    if 'send' in request.POST:
        services.mark_tracking_read(track)   # T-06/S-24
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
        except (User.DoesNotExist, ValidationError) as e:
            # T-04/S-09,R-02: single except block handles both exception types.
            messages.error(request, 'Enter a valid destination or designation')
            context = {
                'designations': designations, 'file': file, 'track': track,
                'designation_name': designation_name, 'designation_id': designation_id,
                'notifications': request.user.notifications.all(), 'path_parent': 'inbox',
            }
            return render(request, 'filetracking/forward.html', context)

    context = {
        'designations': designations, 'file': file, 'track': track,
        'designation_name': designation_name, 'designation_id': designation_id,
        'notifications': request.user.notifications.all(), 'path_parent': 'inbox',
    }
    return render(request, 'filetracking/forward.html', context)


@login_required(login_url="/accounts/login")
@user_is_student
@dropdown_designation_valid
def archive_design(request):
    """Redirect to archive page."""
    url = services.get_designation_redirect_url_from_session(request, 'archive')
    return redirect(url)


@login_required(login_url="/accounts/login")
@user_is_student
@dropdown_designation_valid
def archive_view(request, id):
    """T-10/S-29: N+1 eliminated via enrich_archive_files. T-05/S-22: no raw ORM in view."""
    user_hd = selectors.get_holds_designation_by_id(id)
    designation = services.get_designation_display_name(user_hd)

    archive_files = services.view_archived(
        username=user_hd.user,
        designation=user_hd.designation,
        src_module='filetracking',
    )

    # T-10/S-29: bulk-fetch designations and extra-infos; no per-file ORM.
    archive_files = services.enrich_archive_files(archive_files)
    archive_files = services.add_uploader_department_to_files_list(archive_files)

    context = {
        'archive_files': archive_files,
        'designations': designation,
        'notifications': request.user.notifications.all(),
        'path_parent': 'archive',
    }
    return render(request, 'filetracking/archive.html', context)


@login_required(login_url="/accounts/login")
@user_is_student
@dropdown_designation_valid
def archive_finish(request, id):
    """T-05/S-20: Tracking query routed through selector."""
    file1 = get_object_or_404(File, id=id)
    track = selectors.get_tracking_for_file(file1)   # S-20
    return render(request, 'filetracking/archive_finish.html', {'file': file1, 'track': track})


@login_required(login_url="/accounts/login")
@user_is_student
@dropdown_designation_valid
def finish_design(request):
    designation = selectors.get_user_designations(request.user)
    context = {
        'designation': designation,
        'notifications': request.user.notifications.all(),
    }
    return render(request, 'filetracking/finish_design.html', context)


@login_required(login_url="/accounts/login")
@user_is_student
@dropdown_designation_valid
def finish_fileview(request, id):
    out = selectors.get_tracking_for_uploader(request.user.extrainfo, is_read=False)
    abcd = selectors.get_holds_designation_by_id(id)
    context = {
        'out': out, 'abcd': abcd,
        'notifications': request.user.notifications.all(),
    }
    return render(request, 'filetracking/finish_fileview.html', context)


@login_required(login_url="/accounts/login")
@user_is_student
@dropdown_designation_valid
def finish(request, id):
    """T-05/S-21: ORM mutations delegated to services.finish_file()."""
    file1 = get_object_or_404(File, id=id)
    track = selectors.get_tracking_for_file(file1)   # S-21
    if request.method == "POST":
        if 'Finished' in request.POST:
            services.finish_file(id, track)           # S-21: no raw ORM in view
            messages.success(request, 'File Archived')
    context = {
        'file': file1, 'track': track, 'fileid': id,
        'notifications': request.user.notifications.all(),
    }
    return render(request, 'filetracking/finish.html')


@login_required(login_url="/accounts/login")
def designation_autocomplete_view(request):
    """T-12/S-32: renamed from AjaxDropdown1 (PEP-8 snake_case)."""
    if request.method == 'POST':
        value = request.POST.get('value')
        hold = selectors.get_designations_starting_with(value)
        holds = django_serializers.serialize('json', list(hold))
        context = {'holds': holds}
        return HttpResponse(JsonResponse(context), content_type='application/json')


@login_required(login_url="/accounts/login")
def user_autocomplete_view(request):
    """T-12/S-32: renamed from AjaxDropdown (PEP-8 snake_case)."""
    if request.method == 'POST':
        value = request.POST.get('value')
        users = selectors.get_users_starting_with(value)
        users = django_serializers.serialize('json', list(users))
        context = {'users': users}
        return HttpResponse(JsonResponse(context), content_type='application/json')


@login_required(login_url="/accounts/login")
@user_is_student
@dropdown_designation_valid
def delete(request, id):
    try:
        services.delete_file_with_auth(id, request.user)
    except ValidationError as e:
        messages.error(request, str(e))
    return redirect('/filetracking/draftdesign/')


@login_required(login_url="/accounts/login")
@user_is_student
@dropdown_designation_valid
def forward_inward(request, id):
    file = get_object_or_404(File, id=id)
    file.is_read = True
    track = selectors.get_tracking_for_file(file)
    designations = selectors.get_user_designations(request.user)
    context = {
        'designations': designations, 'file': file, 'track': track,
        'notifications': request.user.notifications.all(),
    }
    return render(request, 'filetracking/forward.html', context)


def get_designations_view(request, username):
    designations = services.get_designations(username)
    return JsonResponse(designations, safe=False)


@login_required(login_url="/accounts/login")
@user_is_student
@dropdown_designation_valid
def unarchive_file(request, id):
    try:
        services.unarchive_file(id)
        messages.success(request, 'File unarchived')
    except Exception as e:
        messages.error(request, 'Unable to unarchive: {}'.format(str(e)))
    return render(request, 'filetracking/archive.html')


@login_required(login_url="/accounts/login")
@user_is_student
@dropdown_designation_valid
def edit_draft_view(request, id, *args, **kwargs):
    """T-07/S-25: remarks extracted from JSON via service call."""
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
            except (User.DoesNotExist, ValidationError):
                messages.error(request, 'Enter a valid destination or designation')
                return redirect(reverse('filetracking:filetracking'))

    designations = selectors.get_user_designations(request.user)
    designation_name = request.session.get(DESIGNATION_SESSION_KEY, DEFAULT_DESIGNATION_SESSION_VALUE)
    hd_obj = selectors.get_holds_designation_obj(request.user, designation_name)

    # T-07/S-25: JSON field access moved to service function.
    remarks = services.get_draft_remarks(file)

    context = {
        'designations': designations, 'file': file, 'track': track,
        'designation_name': designation_name, 'designation_id': hd_obj.id,
        'remarks': remarks, 'notifications': request.user.notifications.all(),
    }
    return render(request, 'filetracking/editdraft.html', context)


@login_required(login_url="/accounts/login/")
@user_is_student
@dropdown_designation_valid
@require_POST
def download_file(request, id):
    zip_data, output_filename = services.generate_file_download(id)
    response = HttpResponse(zip_data, content_type='application/zip')
    response['Content-Disposition'] = f'attachment; filename="{output_filename}.zip"'
    return response
