import io
import logging
import zipfile

from django.contrib.auth.models import User
from django.core import serializers
from django.core.files.base import ContentFile
from django.forms import ValidationError
from rest_framework import permissions, status
from rest_framework.authentication import TokenAuthentication
from rest_framework.response import Response
from rest_framework.views import APIView

from applications.filetracking.api.serializers import (
    AjaxDropdownInputSerializer,
    CreateDraftInputSerializer,
    CreateFileInputSerializer,
    FileActionInputSerializer,
    ForwardFileInputSerializer,
)
from applications.filetracking.sdk.methods import (
    archive_file,
    create_draft,
    create_file,
    delete_file,
    forward_file,
    get_designations,
    unarchive_file,
    view_archived,
    view_drafts,
    view_file,
    view_history,
    view_inbox,
    view_outbox,
)
from notification.views import file_tracking_notif

logger = logging.getLogger(__name__)


def _zip_uploaded_files(attached_files, zip_filename):
    attached_files = list(attached_files or [])
    if not attached_files:
        return None

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_archive:
        for uploaded_file in attached_files:
            zip_archive.writestr(uploaded_file.name, uploaded_file.read())
    zip_buffer.seek(0)
    return ContentFile(zip_buffer.getvalue(), name=zip_filename)


class CreateFileView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = CreateFileInputSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"error": serializer.errors["non_field_errors"][0]}, status=status.HTTP_400_BAD_REQUEST)

        validated_data = serializer.validated_data
        current_user = request.user
        subject = validated_data.get("subject")
        attached_files = request.FILES.getlist("files")
        zip_file = _zip_uploaded_files(attached_files, f"attachments_{subject}.zip")

        try:
            file_id = create_file(
                uploader=current_user,
                uploader_designation=validated_data.get("designation"),
                receiver=validated_data.get("receiver_username"),
                receiver_designation=validated_data.get("receiver_designation"),
                subject=subject,
                description=validated_data.get("description"),
                src_module=validated_data.get("src_module"),
                attached_file=zip_file,
                remarks=validated_data.get("remarks"),
            )
            receiver = User.objects.get(username=validated_data.get("receiver_username"))
            file_tracking_notif(current_user, receiver, "File Received from " + str(current_user))
            return Response({"file_id": file_id}, status=status.HTTP_201_CREATED)
        except Exception as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


class ViewFileView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, file_id):
        try:
            file_details = view_file(int(file_id))
            return Response(file_details, status=status.HTTP_200_OK)
        except ValueError:
            return Response({"error": "Invalid file ID format."}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, file_id):
        try:
            success = delete_file(int(file_id))
            if success:
                return Response({"message": "File deleted successfully"}, status=status.HTTP_204_NO_CONTENT)
            return Response({"error": "File not found"}, status=status.HTTP_404_NOT_FOUND)
        except ValueError:
            return Response({"error": "Invalid file ID format"}, status=status.HTTP_400_BAD_REQUEST)
        except ValidationError as exc:
            return Response(exc.detail, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            logger.error("Unexpected error in DeleteFileView: %s", exc)
            return Response({"error": "An internal server error occurred"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ViewInboxView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        username = request.query_params.get("username") or request.user.username
        designation = request.query_params.get("designation")
        src_module = request.query_params.get("src_module")
        inbox_files = view_inbox(username, designation, src_module)
        return Response(inbox_files)


class ViewOutboxView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        username = request.query_params.get("username")
        designation = request.query_params.get("designation")
        src_module = request.query_params.get("src_module")

        if not username or not src_module:
            return Response({"error": "Missing required query parameters: username and src_module."}, status=400)

        outbox_files = view_outbox(username, designation, src_module)
        return Response(outbox_files)


class ViewHistoryView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, file_id):
        try:
            tracking_array = view_history(file_id)
            return Response(tracking_array)
        except Exception as exc:
            logger.error("An unexpected error occurred: %s", exc)
            return Response({"error": "Internal server error."}, status=500)


class ForwardFileView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, file_id):
        serializer = ForwardFileInputSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"error": serializer.errors["non_field_errors"][0]}, status=status.HTTP_400_BAD_REQUEST)

        validated_data = serializer.validated_data
        attached_files = request.FILES.getlist("files")
        zip_file = _zip_uploaded_files(attached_files, f"attachments_{validated_data.get('receiver')}.zip")

        try:
            new_tracking_id = forward_file(
                int(file_id),
                validated_data.get("receiver"),
                validated_data.get("receiver_designation"),
                validated_data.get("file_extra_JSON", {}),
                validated_data.get("remarks", ""),
                file_attachment=zip_file,
            )
            receiver_user = User.objects.get(username=validated_data.get("receiver"))
            file_tracking_notif(request.user, receiver_user, "File Forwarded from " + str(request.user))
            logger.info("Successfully forwarded file %s with tracking ID: %s", file_id, new_tracking_id)
            return Response({"tracking_ids": new_tracking_id}, status=status.HTTP_201_CREATED)
        except Exception as exc:
            logger.error("Error forwarding file %s: %s", file_id, str(exc))
            raise ValidationError(str(exc))


class CreateDraftFile(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = CreateDraftInputSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"error": serializer.errors["non_field_errors"][0]}, status=status.HTTP_400_BAD_REQUEST)

        validated_data = serializer.validated_data
        file_extra_json = validated_data.get("file_extra_JSON", {})
        if validated_data.get("subject"):
            file_extra_json["subject"] = validated_data.get("subject")
        if validated_data.get("description"):
            file_extra_json["description"] = validated_data.get("description")
        if validated_data.get("remarks"):
            file_extra_json["remarks"] = validated_data.get("remarks")

        draft_file_ids = []
        try:
            for uploaded_file in request.FILES.getlist("files", []):
                file_id = create_draft(
                    uploader=request.user,
                    uploader_designation=validated_data.get("designation"),
                    src_module=validated_data.get("src_module"),
                    src_object_id=validated_data.get("src_object_id", ""),
                    file_extra_JSON=file_extra_json,
                    attached_file=uploaded_file,
                )
                draft_file_ids.append(file_id)
            return Response({"file_ids": draft_file_ids}, status=status.HTTP_201_CREATED)
        except Exception as exc:
            return Response({"error": str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class DraftFileView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        username = request.query_params.get("username")
        designation = request.query_params.get("designation")
        src_module = request.query_params.get("src_module")
        try:
            return Response(view_drafts(username, designation, src_module), status=status.HTTP_200_OK)
        except Exception as exc:
            return Response({"error": str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ArchiveFileView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        username = request.query_params.get("username")
        designation = request.query_params.get("designation", "")
        src_module = request.query_params.get("src_module")
        try:
            return Response(view_archived(username, designation, src_module), status=status.HTTP_200_OK)
        except Exception as exc:
            return Response({"error": str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CreateArchiveFile(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = FileActionInputSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"error": serializer.errors["non_field_errors"][0]}, status=status.HTTP_400_BAD_REQUEST)

        try:
            success = archive_file(serializer.validated_data["file_id"])
            if success:
                return Response({"success": True})
            return Response({"error": "File does not exist"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as exc:
            return Response({"error": str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UnArchiveFile(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = FileActionInputSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"error": serializer.errors["non_field_errors"][0]}, status=status.HTTP_400_BAD_REQUEST)

        try:
            success = unarchive_file(serializer.validated_data["file_id"])
            if success:
                return Response({"success": True})
            return Response({"error": "File does not exist"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as exc:
            return Response({"error": str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class GetDesignationsView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, username, *args, **kwargs):
        return Response({"designations": get_designations(username)})


class AjaxDropdownView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = AjaxDropdownInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=False)
        value = serializer.validated_data.get("value", "") if serializer.validated_data else request.data.get("value", "")
        users = User.objects.filter(username__startswith=value)
        users_json = serializers.serialize("json", users)
        return Response({"users": users_json})
