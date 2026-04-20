import io
import os
import zipfile
from datetime import datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core import serializers
from django.core.paginator import Paginator
from django.db import IntegrityError
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render, reverse
from django.utils.dateparse import parse_datetime
from django.views.decorators.http import require_POST
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

from applications.globals.models import ExtraInfo, HoldsDesignation
from notification.views import file_tracking_notif

from .decorators import dropdown_designation_valid, user_is_student
from .models import File, Tracking
from .selectors import (
    get_designation_suggestions,
    get_designations_for_user,
    get_extra_info_object_from_id,
    get_file_by_id,
    get_holds_designation_obj,
    get_tracking_for_file,
    get_user_suggestions,
)
from .sdk.methods import (
    add_uploader_department_to_files_list,
    archive_file as archive_file_sdk,
    create_draft,
    create_file,
    forward_file as forward_file_sdk,
    get_HoldsDesignation_obj,
    get_current_file_owner,
    get_current_file_owner_designation,
    get_designation_obj_from_name,
    get_designations,
    get_extra_info_object_from_id as sdk_get_extra_info_object_from_id,
    get_last_forw_tracking_for_user,
    get_last_recv_tracking_for_user,
    get_user_object_from_username,
    unarchive_file as unarchive_file_sdk,
    view_archived,
    view_drafts,
    view_inbox,
    view_outbox,
)
from .services import (
    DEFAULT_PAGE_SIZE,
    FILETRACKING_MODULE,
    SESSION_CURRENT_DESIGNATION_KEY,
    validate_upload_size,
)
from .utils import get_designation


def _get_selected_designation_name(request):
    return request.session.get(SESSION_CURRENT_DESIGNATION_KEY, "default_value")


def _get_selected_designation_id(request):
    return get_HoldsDesignation_obj(request.user, _get_selected_designation_name(request)).id


def _common_context(request, **extra):
    context = {
        "notifications": request.user.notifications.all(),
    }
    context.update(extra)
    return context


def _get_parent_path_from_referrer(request, default_value="inbox"):
    referrer = request.META.get("HTTP_REFERER")
    if not referrer:
        return default_value

    parts = referrer.strip("/").split("/")
    if len(parts) >= 2:
        return parts[-2]
    return default_value


@login_required(login_url="/accounts/login/")
@user_is_student
@dropdown_designation_valid
def filetracking(request):
    if request.method == "POST":
        try:
            subject = request.POST.get("title")
            description = request.POST.get("desc")
            design = request.POST.get("design")
            uploader_designation = get_object_or_404(get_designations_for_user(request.user), id=design).designation
            upload_file = request.FILES.get("myfile")

            if validate_upload_size(upload_file):
                messages.error(request, "File should not be greater than 10MB")
                return redirect("/filetracking")

            if "save" in request.POST:
                create_draft(
                    uploader=request.user,
                    uploader_designation=uploader_designation.name,
                    src_module=FILETRACKING_MODULE,
                    file_extra_JSON={"remarks": request.POST.get("remarks") or ""},
                    attached_file=upload_file,
                )
                messages.success(request, "File Draft Saved Successfully")

            if "send" in request.POST:
                receiver = request.POST.get("receiver")
                receive = request.POST.get("receive")
                try:
                    receiver_id = User.objects.get(username=receiver)
                    get_designation_obj_from_name(receive)
                except Exception:
                    messages.error(request, "Enter a valid Username" if not User.objects.filter(username=receiver).exists() else "Enter a valid Designation")
                    return redirect("/filetracking/")

                create_file(
                    uploader=request.user,
                    uploader_designation=uploader_designation.name,
                    receiver=receiver,
                    receiver_designation=receive,
                    subject=subject,
                    description=description,
                    src_module=FILETRACKING_MODULE,
                    attached_file=upload_file,
                    remarks=request.POST.get("remarks"),
                )
                file_tracking_notif(request.user, receiver_id, subject)
                messages.success(request, "File sent successfully")
        except IntegrityError:
            return HttpResponse("FileID Already Taken.!!")

    context = _common_context(
        request,
        file=File.objects.select_related("uploader__user", "uploader__department", "designation").all(),
        extrainfo=ExtraInfo.objects.select_related("user", "department").all(),
        holdsdesignations=HoldsDesignation.objects.select_related("user", "working", "designation").all(),
        designation_name=_get_selected_designation_name(request),
        designation_id=_get_selected_designation_id(request),
        path_parent="compose",
    )
    return render(request, "filetracking/composefile.html", context)


@login_required(login_url="/accounts/login")
@user_is_student
@dropdown_designation_valid
def draft_design(request):
    dropdown_holds_designation = get_HoldsDesignation_obj(request.user, _get_selected_designation_name(request))
    return redirect("/filetracking/drafts/" + str(dropdown_holds_designation.id))


@login_required(login_url="/accounts/login")
@user_is_student
@dropdown_designation_valid
def drafts_view(request, id):
    user_holds_designation_obj = get_object_or_404(get_designations_for_user(request.user), pk=id)
    designation = str(user_holds_designation_obj).split(" - ")[1]
    draft_files = view_drafts(
        username=user_holds_designation_obj.user,
        designation=user_holds_designation_obj.designation,
        src_module=FILETRACKING_MODULE,
    )

    for draft_file in draft_files:
        draft_file["upload_date"] = parse_datetime(draft_file["upload_date"])
        draft_file["uploader"] = sdk_get_extra_info_object_from_id(draft_file["uploader"])

    draft_files = add_uploader_department_to_files_list(draft_files)
    context = _common_context(
        request,
        draft_files=draft_files,
        designations=designation,
        path_parent="draft",
    )
    return render(request, "filetracking/drafts.html", context)


@login_required(login_url="/accounts/login")
@user_is_student
@dropdown_designation_valid
def outbox_view(request):
    dropdown_design = _get_selected_designation_name(request)
    user_holds_designation_obj = get_HoldsDesignation_obj(request.user, dropdown_design)
    designation = str(user_holds_designation_obj).split(" - ")[1]

    outward_files = view_outbox(
        username=user_holds_designation_obj.user,
        designation=user_holds_designation_obj.designation,
        src_module=FILETRACKING_MODULE,
    )

    for outward_file in outward_files:
        last_forward_tracking = get_last_forw_tracking_for_user(
            file_id=outward_file["id"],
            username=user_holds_designation_obj.user,
            designation=user_holds_designation_obj.designation,
        )
        if last_forward_tracking is not None:
            outward_file["sent_to_user"] = last_forward_tracking.receiver_id
            outward_file["sent_to_design"] = last_forward_tracking.receive_design
            outward_file["last_sent_date"] = last_forward_tracking.forward_date
        outward_file["upload_date"] = parse_datetime(outward_file["upload_date"])
        outward_file["uploader"] = sdk_get_extra_info_object_from_id(outward_file["uploader"])

    subject_query = request.GET.get("subject", "")
    sent_to_query = request.GET.get("sent_to", "")
    date_query = request.GET.get("date", "")

    if subject_query:
        outward_files = [item for item in outward_files if subject_query.lower() in item["subject"].lower()]
    if sent_to_query:
        outward_files = [
            item for item in outward_files
            if item.get("sent_to_user") and sent_to_query.lower() in item["sent_to_user"].username.lower()
        ]
    if date_query:
        try:
            search_date = datetime.strptime(date_query, "%Y-%m-%d")
            outward_files = [
                item for item in outward_files
                if item.get("last_sent_date") and item["last_sent_date"].date() == search_date.date()
            ]
        except ValueError:
            outward_files = []

    page_obj = Paginator(outward_files, DEFAULT_PAGE_SIZE).get_page(request.GET.get("page"))
    return render(
        request,
        "filetracking/outbox.html",
        _common_context(
            request,
            page_obj=page_obj,
            viewer_designation=designation,
            path_parent="outbox",
        ),
    )


@login_required(login_url="/accounts/login")
@user_is_student
@dropdown_designation_valid
def inbox_view(request):
    dropdown_design = _get_selected_designation_name(request)
    user_holds_designation_obj = get_HoldsDesignation_obj(request.user, dropdown_design)
    designation = str(user_holds_designation_obj).split(" - ")[1]
    inward_files = view_inbox(
        username=user_holds_designation_obj.user,
        designation=user_holds_designation_obj.designation,
        src_module=FILETRACKING_MODULE,
    )

    for inward_file in inward_files:
        inward_file["upload_date"] = parse_datetime(inward_file["upload_date"])
        last_recv_tracking = get_last_recv_tracking_for_user(
            file_id=inward_file["id"],
            username=user_holds_designation_obj.user,
            designation=user_holds_designation_obj.designation,
        )
        inward_file["receive_date"] = last_recv_tracking.receive_date
        inward_file["uploader"] = sdk_get_extra_info_object_from_id(inward_file["uploader"])
        current_owner = get_current_file_owner(inward_file["id"])
        inward_file["is_forwarded"] = bool(current_owner and str(current_owner.username) != str(user_holds_designation_obj.user))

    inward_files = add_uploader_department_to_files_list(inward_files)

    subject_query = request.GET.get("subject", "")
    sent_to_query = request.GET.get("sent_to", "")
    date_query = request.GET.get("date", "")

    if subject_query:
        inward_files = [item for item in inward_files if subject_query.lower() in item["subject"].lower()]
    if sent_to_query:
        inward_files = [
            item for item in inward_files
            if item.get("sent_to_user") and sent_to_query.lower() in item["sent_to_user"].username.lower()
        ]
    if date_query:
        try:
            search_date = datetime.strptime(date_query, "%Y-%m-%d")
            inward_files = [
                item for item in inward_files
                if item.get("last_sent_date") and item["last_sent_date"].date() == search_date.date()
            ]
        except ValueError:
            inward_files = []

    page_obj = Paginator(inward_files, DEFAULT_PAGE_SIZE).get_page(request.GET.get("page"))
    return render(
        request,
        "filetracking/inbox.html",
        _common_context(
            request,
            page_obj=page_obj,
            designations=designation,
            path_parent="inbox",
        ),
    )


@login_required(login_url="/accounts/login")
@user_is_student
@dropdown_designation_valid
def confirmdelete(request, id):
    return render(
        request,
        "filetracking/confirmdelete.html",
        {"j": get_file_by_id(id)},
    )


@login_required(login_url="/accounts/login")
@user_is_student
@dropdown_designation_valid
def view_file(request, id):
    file_obj = get_file_by_id(id)
    track = get_tracking_for_file(file_obj)
    current_owner = get_current_file_owner(file_obj.id)
    last_receiver_designation = get_current_file_owner_designation(file_obj.id)
    file_uploader = get_user_object_from_username(file_obj.uploader.user.username)

    forward_enable = current_owner == request.user and file_obj.is_read is False
    archive_enable = (
        current_owner == request.user
        and last_receiver_designation is not None
        and last_receiver_designation.name == file_obj.designation.name
        and file_uploader == request.user
        and file_obj.is_read is False
    )

    context = _common_context(
        request,
        designations=get_designation(request.user),
        file=file_obj,
        track=track,
        forward_enable=forward_enable,
        archive_enable=archive_enable,
        path_parent=_get_parent_path_from_referrer(request),
    )
    return render(request, "filetracking/viewfile.html", context)


@login_required(login_url="/accounts/login")
@user_is_student
@dropdown_designation_valid
def archive_file(request, id):
    if request.method == "POST":
        file_obj = get_file_by_id(id)
        current_owner = get_current_file_owner(file_obj.id)
        file_uploader = get_user_object_from_username(file_obj.uploader.user.username)
        if current_owner == request.user and file_uploader == request.user:
            archive_file_sdk(file_obj.id)
            messages.success(request, "File Archived")
        else:
            messages.error(request, "Unauthorized access")
        return render(request, "filetracking/composefile.html")


@login_required(login_url="/accounts/login")
@user_is_student
@dropdown_designation_valid
def forward(request, id):
    file_obj = get_file_by_id(id)
    track = get_tracking_for_file(file_obj)
    designation_name = _get_selected_designation_name(request)

    if request.method == "POST":
        if "finish" in request.POST:
            archive_file_sdk(file_obj.id)
        if "send" in request.POST:
            receiver = request.POST.get("receiver")
            receive = request.POST.get("receive")
            try:
                receiver_id = User.objects.get(username=receiver)
                get_designation_obj_from_name(receive)
            except Exception:
                messages.error(
                    request,
                    "Enter a valid destination" if not User.objects.filter(username=receiver).exists() else "Enter a valid Designation",
                )
                return render(
                    request,
                    "filetracking/forward.html",
                    _common_context(
                        request,
                        designations=get_designation(request.user),
                        file=file_obj,
                        track=track,
                        designation_name=designation_name,
                        designation_id=_get_selected_designation_id(request),
                        path_parent="inbox",
                    ),
                )

            track.update(is_read=True)
            forward_file_sdk(
                file_obj.id,
                receiver,
                receive,
                remarks=request.POST.get("remarks"),
                file_attachment=request.FILES.get("myfile"),
            )
            file_tracking_notif(request.user, receiver_id, file_obj.subject)
            messages.success(request, "File sent successfully")
            return redirect(reverse("filetracking:filetracking"))

    return render(
        request,
        "filetracking/forward.html",
        _common_context(
            request,
            designations=get_designation(request.user),
            file=file_obj,
            track=track,
            designation_name=designation_name,
            designation_id=_get_selected_designation_id(request),
            path_parent="inbox",
        ),
    )


@login_required(login_url="/accounts/login")
@user_is_student
@dropdown_designation_valid
def archive_design(request):
    dropdown_holds_designation = get_HoldsDesignation_obj(request.user, _get_selected_designation_name(request))
    return redirect("/filetracking/archive/" + str(dropdown_holds_designation.id))


@login_required(login_url="/accounts/login")
@user_is_student
@dropdown_designation_valid
def archive_view(request, id):
    user_holds_designation_obj = get_object_or_404(get_designations_for_user(request.user), pk=id)
    designation = str(user_holds_designation_obj).split(" - ")[1]
    archive_files = view_archived(
        username=user_holds_designation_obj.user,
        designation=user_holds_designation_obj.designation,
        src_module=FILETRACKING_MODULE,
    )

    for archive_file_obj in archive_files:
        archive_file_obj["upload_date"] = parse_datetime(archive_file_obj["upload_date"])
        archive_file_obj["designation"] = get_designation_obj_from_name(archive_file_obj["uploader_designation"])
        archive_file_obj["uploader"] = sdk_get_extra_info_object_from_id(archive_file_obj["uploader"])

    archive_files = add_uploader_department_to_files_list(archive_files)
    return render(
        request,
        "filetracking/archive.html",
        _common_context(
            request,
            archive_files=archive_files,
            designations=designation,
            path_parent="archive",
        ),
    )


@login_required(login_url="/accounts/login")
@user_is_student
@dropdown_designation_valid
def archive_finish(request, id):
    file_obj = get_file_by_id(id)
    return render(request, "filetracking/archive_finish.html", {"file": file_obj, "track": get_tracking_for_file(file_obj)})


@login_required(login_url="/accounts/login")
@user_is_student
@dropdown_designation_valid
def finish_design(request):
    return render(
        request,
        "filetracking/finish_design.html",
        _common_context(request, designation=get_designations_for_user(request.user)),
    )


@login_required(login_url="/accounts/login")
@user_is_student
@dropdown_designation_valid
def finish_fileview(request, id):
    return render(
        request,
        "filetracking/finish_fileview.html",
        _common_context(
            request,
            out=Tracking.objects.select_related(
                "file_id__uploader__user",
                "file_id__uploader__department",
                "file_id__designation",
                "current_id__user",
                "current_id__department",
                "current_design__user",
                "current_design__working",
                "current_design__designation",
                "receiver_id",
                "receive_design",
            ).filter(file_id__uploader=request.user.extrainfo, is_read=False).order_by("-forward_date"),
            abcd=get_object_or_404(get_designations_for_user(request.user), pk=id),
        ),
    )


@login_required(login_url="/accounts/login")
@user_is_student
@dropdown_designation_valid
def finish(request, id):
    file_obj = get_file_by_id(id)
    track = get_tracking_for_file(file_obj)

    if request.method == "POST" and "Finished" in request.POST:
        archive_file_sdk(id)
        track.update(is_read=True)
        messages.success(request, "File Archived")

    return render(
        request,
        "filetracking/finish.html",
        _common_context(request, file=file_obj, track=track, fileid=id),
    )


def AjaxDropdown1(request):
    if request.method == "POST":
        holds = serializers.serialize("json", list(get_designation_suggestions(request.POST.get("value"))))
        return HttpResponse(JsonResponse({"holds": holds}), content_type="application/json")


def AjaxDropdown(request):
    if request.method == "POST":
        users = serializers.serialize("json", list(get_user_suggestions(request.POST.get("value"))))
        return HttpResponse(JsonResponse({"users": users}), content_type="application/json")


@login_required(login_url="/accounts/login")
@user_is_student
@dropdown_designation_valid
def delete(request, id):
    get_file_by_id(id).delete()
    return redirect("/filetracking/draftdesign/")


@user_is_student
@dropdown_designation_valid
def forward_inward(request, id):
    file_obj = get_file_by_id(id)
    file_obj.is_read = True
    return render(
        request,
        "filetracking/forward.html",
        _common_context(
            request,
            designations=get_designation(request.user),
            file=file_obj,
            track=get_tracking_for_file(file_obj),
        ),
    )


def get_designations_view(request, username):
    return JsonResponse(get_designations(username), safe=False)


def unarchive_file(request, id):
    try:
        unarchive_file_sdk(id)
        messages.success(request, "File unarchived")
    except Exception as exc:
        messages.error(request, "Unable to unarchive: {}".format(str(exc)))
    return render(request, "filetracking/archive.html")


@login_required(login_url="/accounts/login")
@user_is_student
@dropdown_designation_valid
def edit_draft_view(request, id, *args, **kwargs):
    file_obj = get_file_by_id(id)
    track = get_tracking_for_file(file_obj)

    if request.method == "POST" and "send" in request.POST:
        file_obj.subject = request.POST.get("subject")
        file_obj.description = request.POST.get("description")
        file_obj.save()
        track.update(is_read=True)

        receiver = request.POST.get("receiver")
        receive = request.POST.get("receive")
        try:
            receiver_id = User.objects.get(username=receiver)
            get_designation_obj_from_name(receive)
        except Exception:
            messages.error(
                request,
                "Enter a valid destination" if not User.objects.filter(username=receiver).exists() else "Enter a valid Designation",
            )
            return redirect(reverse("filetracking:filetracking"))

        upload_file = request.FILES.get("myfile")
        if upload_file is None and file_obj.upload_file:
            upload_file = file_obj.upload_file

        forward_file_sdk(
            file_obj.id,
            receiver,
            receive,
            remarks=request.POST.get("remarks"),
            file_attachment=upload_file,
        )
        file_tracking_notif(request.user, receiver_id, file_obj.subject)
        messages.success(request, "File sent successfully")
        return render(request, "filetracking/composefile.html")

    remarks = None
    if file_obj.file_extra_JSON and file_obj.file_extra_JSON.get("remarks"):
        remarks = file_obj.file_extra_JSON["remarks"]

    return render(
        request,
        "filetracking/editdraft.html",
        _common_context(
            request,
            designations=get_designation(request.user),
            file=file_obj,
            track=track,
            designation_name=_get_selected_designation_name(request),
            designation_id=_get_selected_designation_id(request),
            remarks=remarks,
        ),
    )


@login_required(login_url="/accounts/login/")
@user_is_student
@dropdown_designation_valid
@require_POST
def download_file(request, id):
    file_obj = get_file_by_id(id)
    track = get_tracking_for_file(file_obj)

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []
    styles = getSampleStyleSheet()
    style_heading = styles["Heading1"]
    style_paragraph = styles["BodyText"]

    elements.append(Paragraph(f"<center><b>Subject - {file_obj.subject}</b></center>", style_heading))
    elements.append(Spacer(1, 12))
    elements.append(Paragraph(f"<b>Description:</b> {file_obj.description}", style_paragraph))
    elements.append(Spacer(1, 12))

    for tracking_row in track:
        sent_by = f"<b>Sent by:</b> {tracking_row.current_design} - {tracking_row.forward_date.strftime('%B %d, %Y %I:%M %p')}"
        received_by = f"<b>Received by:</b> {tracking_row.receiver_id} - {tracking_row.receive_design}"
        elements.append(Paragraph(f"{sent_by} &nbsp;&nbsp;&nbsp;&nbsp;&nbsp; {received_by}", style_paragraph))
        elements.append(Spacer(1, 12))
        elements.append(
            Paragraph(
                f"<b>Remarks:</b> {tracking_row.remarks}" if tracking_row.remarks else "<b>Remarks:</b> No Remarks",
                style_paragraph,
            )
        )
        elements.append(Spacer(1, 12))
        attachment = (
            f"<b>Attachment:</b> {os.path.basename(tracking_row.upload_file.name)}"
            if tracking_row.upload_file
            else "<b>Attachment:</b> No attachments"
        )
        elements.append(Paragraph(attachment, style_paragraph))
        elements.append(Paragraph('<hr width="100%" style="border-top: 1px solid #ccc;">', style_paragraph))
        elements.append(Spacer(2, 12))

    doc.build(elements)
    pdf_data = buffer.getvalue()
    buffer.close()

    formal_filename = f"{file_obj.uploader.department.name}-{file_obj.upload_date.year}-{file_obj.upload_date.month}-#{file_obj.id}"
    output_filename = f"iiitdmj-fts-{formal_filename}"

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zip_file:
        zip_file.writestr(output_filename + ".pdf", pdf_data)
        for tracking_row in track:
            if tracking_row.upload_file:
                zip_file.write(tracking_row.upload_file.path, os.path.basename(tracking_row.upload_file.name))

    response = HttpResponse(zip_buffer.getvalue(), content_type="application/zip")
    response["Content-Disposition"] = f'attachment; filename="{output_filename}.zip"'
    return response
