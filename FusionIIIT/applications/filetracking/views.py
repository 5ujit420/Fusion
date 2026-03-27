# views.py
# Thin web views for the filetracking module.
# All business logic delegated to services.py, all queries to selectors.py.
# Fixes: V-04–V-11, V-22–V-24, V-29–V-31, V-35, V-36, V-40, V-43, V-44, V-46, R-01–R-04

from django.db import IntegrityError  # V-29: was `from sqlite3 import IntegrityError`
from django.http import HttpResponse, JsonResponse
from django.contrib import messages
from django.shortcuts import render, get_object_or_404, redirect, reverse
from django.contrib.auth.decorators import login_required
from django.core import serializers as django_serializers
from django.contrib.auth.models import User
from django.views.decorators.http import require_POST
from django.utils.dateparse import parse_datetime
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator

from datetime import datetime

from applications.globals.models import Designation

from .models import (
    File, Tracking,
    SRC_MODULE_DEFAULT, SESSION_DESIGNATION_KEY, SESSION_DESIGNATION_FALLBACK,
    PAGINATION_PAGE_SIZE,
)
from . import services
from . import selectors
from .decorators import user_is_student, dropdown_designation_valid


@login_required(login_url="/accounts/login/")
@user_is_student
@dropdown_designation_valid
def filetracking(request):
    """
    Compose file page: save as draft or send.
    V-04, R-01 — delegates to services.save_draft_file() / services.send_file().
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
                except User.DoesNotExist:  # V-30: specific exception
                    messages.error(request, 'Enter a valid Username')
                    return redirect('/filetracking/')
                except Designation.DoesNotExist:  # V-30, V-46: Designation now imported
                    messages.error(request, 'Enter a valid Designation')
                    return redirect('/filetracking/')
                except ValidationError as e:
                    messages.error(request, str(e.message if hasattr(e, 'message') else e))
                    return redirect('/filetracking')

        except IntegrityError:
            message = "FileID Already Taken.!!"
            return HttpResponse(message)

    # V-40, V-43: Uses selectors for all DB queries
    designation_name = request.session.get(SESSION_DESIGNATION_KEY, SESSION_DESIGNATION_FALLBACK)
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
    """Redirect to drafts page (R-04)."""
    url = services.get_designation_redirect_url_from_session(request, 'drafts')
    return redirect(url)


@login_required(login_url="/accounts/login")
@user_is_student
@dropdown_designation_valid
def drafts_view(request, id):
    """View all drafts for a user+designation."""
    user_hd = selectors.get_holds_designation_by_id(id)
    designation = services.get_designation_display_name(user_hd)
    draft_files = services.view_drafts(
        username=user_hd.user,
        designation=user_hd.designation,
        src_module=SRC_MODULE_DEFAULT,
    )

    for f in draft_files:
        f['upload_date'] = parse_datetime(f['upload_date'])
        f['uploader'] = selectors.get_extrainfo_by_id(f['uploader'])

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
    """V-05: Delegates to services.view_outbox()."""
    dropdown_design = request.session.get(SESSION_DESIGNATION_KEY, SESSION_DESIGNATION_FALLBACK)
    user_hd = selectors.get_holds_designation_obj(request.user, dropdown_design)
    designation = services.get_designation_display_name(user_hd)

    outward_files = services.view_outbox(
        username=user_hd.user,
        designation=user_hd.designation,
        src_module=SRC_MODULE_DEFAULT,
    )

    for f in outward_files:
        last_forw = selectors.get_last_forw_tracking(
            file_id=f['id'],
            sender_extrainfo=selectors.get_extrainfo_by_username(user_hd.user),
            sender_holds_designation=user_hd,
        )
        f['sent_to_user'] = last_forw.receiver_id if last_forw else None
        f['sent_to_design'] = last_forw.receive_design if last_forw else None
        f['last_sent_date'] = last_forw.forward_date if last_forw else None
        f['upload_date'] = parse_datetime(f['upload_date'])
        f['uploader'] = selectors.get_extrainfo_by_id(f['uploader'])

    # Search filtering
    subject_query = request.GET.get('subject', '')
    sent_to_query = request.GET.get('sent_to', '')
    date_query = request.GET.get('date', '')

    if subject_query:
        outward_files = [f for f in outward_files if subject_query.lower() in f['subject'].lower()]
    if sent_to_query:
        outward_files = [f for f in outward_files if f['sent_to_user'] and sent_to_query.lower() in f['sent_to_user'].username.lower()]
    if date_query:
        try:
            search_date = datetime.strptime(date_query, '%Y-%m-%d')
            outward_files = [f for f in outward_files if f['last_sent_date'] and f['last_sent_date'].date() == search_date.date()]
        except ValueError:
            outward_files = []

    paginator = Paginator(outward_files, PAGINATION_PAGE_SIZE)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

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
    """V-06: Delegates to services.view_inbox()."""
    dropdown_design = request.session.get(SESSION_DESIGNATION_KEY, SESSION_DESIGNATION_FALLBACK)
    user_hd = selectors.get_holds_designation_obj(request.user, dropdown_design)
    designation = services.get_designation_display_name(user_hd)

    inward_files = services.view_inbox(
        username=user_hd.user,
        designation=user_hd.designation,
        src_module=SRC_MODULE_DEFAULT,
    )

    for f in inward_files:
        f['upload_date'] = parse_datetime(f['upload_date'])
        last_recv = selectors.get_last_recv_tracking(
            file_id=f['id'],
            receiver_user=user_hd.user,
            receive_design=user_hd.designation,
        )
        f['receive_date'] = last_recv.receive_date if last_recv else None
        f['uploader'] = selectors.get_extrainfo_by_id(f['uploader'])
        current_owner = selectors.get_current_file_owner(f['id'])
        f['is_forwarded'] = (str(current_owner.username) != str(user_hd.user)) if current_owner else True

    inward_files = services.add_uploader_department_to_files_list(inward_files)

    subject_query = request.GET.get('subject', '')
    sent_to_query = request.GET.get('sent_to', '')
    date_query = request.GET.get('date', '')

    if subject_query:
        inward_files = [f for f in inward_files if subject_query.lower() in f['subject'].lower()]
    if sent_to_query:
        inward_files = [f for f in inward_files if sent_to_query.lower() in f.get('sent_to_user', {}).username.lower()]
    if date_query:
        try:
            search_date = datetime.strptime(date_query, '%Y-%m-%d')
            inward_files = [f for f in inward_files if f.get('last_sent_date') and f['last_sent_date'].date() == search_date.date()]
        except ValueError:
            inward_files = []

    paginator = Paginator(inward_files, PAGINATION_PAGE_SIZE)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

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
    """Redirect to outbox page (R-04)."""
    url = services.get_designation_redirect_url_from_session(request, 'outbox')
    return redirect(url)


@login_required(login_url="/accounts/login")
@user_is_student
@dropdown_designation_valid
def inward(request):
    """Redirect to inbox page (R-04)."""
    url = services.get_designation_redirect_url_from_session(request, 'inbox')
    return redirect(url)


@login_required(login_url="/accounts/login")
@user_is_student
@dropdown_designation_valid
def confirmdelete(request, id):
    """Confirm deletion page. V-43: Uses selector."""
    file = selectors.get_file_by_id_with_related(id)
    context = {'j': file}
    return render(request, 'filetracking/confirmdelete.html', context)


@login_required(login_url="/accounts/login")
@user_is_student
@dropdown_designation_valid
def view_file_view(request, id):
    """V-11: Delegates permission logic to services.get_file_view_permissions()."""
    file = get_object_or_404(File, id=id)
    track = selectors.get_tracking_for_file(file)
    designations = selectors.get_user_designations(request.user)

    forward_enable, archive_enable = services.get_file_view_permissions(file.id, request.user)

    parent_of_prev_path = request.META.get('HTTP_REFERER', '/').strip("/").split('/')[-2] if request.META.get('HTTP_REFERER') else 'inbox'
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
    """V-10: Delegates to services.archive_file_with_auth()."""
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
    """V-07, R-02, V-44: Delegates forwarding logic to services."""
    file = get_object_or_404(File, id=id)
    track = selectors.get_tracking_for_file(file)
    designations = selectors.get_user_designations(request.user)

    designation_name = request.session.get(SESSION_DESIGNATION_KEY, SESSION_DESIGNATION_FALLBACK)
    hd_obj = selectors.get_holds_designation_obj(request.user, designation_name)
    designation_id = hd_obj.id

    if request.method == "POST":
        if 'finish' in request.POST:
            services.mark_file_read(file)
        if 'send' in request.POST:
            services.mark_tracking_as_read(track)
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
            except User.DoesNotExist:  # V-30
                messages.error(request, 'Enter a valid destination')
                context = {
                    'designations': designations, 'file': file, 'track': track,
                    'designation_name': designation_name, 'designation_id': designation_id,
                    'notifications': request.user.notifications.all(), 'path_parent': 'inbox',
                }
                return render(request, 'filetracking/forward.html', context)
            except Designation.DoesNotExist:  # V-30, V-46
                messages.error(request, 'Enter a valid Designation')
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
    """Redirect to archive page (R-04)."""
    url = services.get_designation_redirect_url_from_session(request, 'archive')
    return redirect(url)


@login_required(login_url="/accounts/login")
@user_is_student
@dropdown_designation_valid
def archive_view(request, id):
    """Archive listing page. V-43: Uses selectors for DB queries."""
    user_hd = selectors.get_holds_designation_by_id(id)
    designation = services.get_designation_display_name(user_hd)

    archive_files = services.view_archived(
        username=user_hd.user,
        designation=user_hd.designation,
        src_module=SRC_MODULE_DEFAULT,
    )

    for f in archive_files:
        f['upload_date'] = parse_datetime(f['upload_date'])
        f['designation'] = selectors.get_designation_by_id(f['designation'])
        f['uploader'] = selectors.get_extrainfo_by_id(f['uploader'])

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
    """View archive finish page. V-43: Uses selectors."""
    file1 = get_object_or_404(File, id=id)
    track = selectors.get_tracking_for_file(file1)
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
    """V-44: Business logic delegated to services.mark_file_as_finished()."""
    file1 = get_object_or_404(File, id=id)
    track = selectors.get_tracking_for_file(file1)
    if request.method == "POST":
        if 'Finished' in request.POST:
            services.mark_file_as_finished(id)
            messages.success(request, 'File Archived')
    context = {
        'file': file1, 'track': track, 'fileid': id,
        'notifications': request.user.notifications.all(),
    }
    return render(request, 'filetracking/finish.html', context)


@login_required(login_url="/accounts/login")  # V-22: Added @login_required
def ajax_dropdown_designations(request):
    """Designation autocomplete. V-22, V-46: Renamed from AjaxDropdown1."""
    if request.method == 'POST':
        value = request.POST.get('value')
        hold = selectors.get_designations_starting_with(value)
        holds = django_serializers.serialize('json', list(hold))
        context = {'holds': holds}
        return HttpResponse(JsonResponse(context), content_type='application/json')


@login_required(login_url="/accounts/login")  # V-22: Added @login_required
def ajax_dropdown_users(request):
    """Username autocomplete. V-22, V-46: Renamed from AjaxDropdown."""
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
    """V-23: Added ownership check via services.delete_file_with_auth()."""
    try:
        services.delete_file_with_auth(id, request.user)
    except ValidationError as e:
        messages.error(request, str(e))
    return redirect('/filetracking/draftdesign/')


@login_required(login_url="/accounts/login")  # V-24: Added @login_required
@user_is_student
@dropdown_designation_valid
def forward_inward(request, id):
    """V-24: Added @login_required."""
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
    """V-36: Fixed unreachable except — uses services.unarchive_file() (R-08)."""
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
    """V-08, R-02: Delegates to services.edit_and_send_draft()."""
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
            except User.DoesNotExist:  # V-30
                messages.error(request, 'Enter a valid destination')
                return redirect(reverse('filetracking:filetracking'))
            except Designation.DoesNotExist:  # V-30, V-46
                messages.error(request, 'Enter a valid Designation')
                return redirect(reverse('filetracking:filetracking'))

    designations = selectors.get_user_designations(request.user)
    designation_name = request.session.get(SESSION_DESIGNATION_KEY, SESSION_DESIGNATION_FALLBACK)
    hd_obj = selectors.get_holds_designation_obj(request.user, designation_name)

    remarks = None
    if file.file_extra_JSON and file.file_extra_JSON.get('remarks'):
        remarks = file.file_extra_JSON['remarks']

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
    """V-09: Delegates to services.generate_file_download()."""
    zip_data, output_filename = services.generate_file_download(id)
    response = HttpResponse(zip_data, content_type='application/zip')
    response['Content-Disposition'] = f'attachment; filename="{output_filename}.zip"'
    return response
