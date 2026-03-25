# api/views.py
# Thin DRF API views for the filetracking module.
# Fixes: V-25, V-26, V-38

import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework.authentication import TokenAuthentication

from .. import services
from .serializers import (
    FileCreateInputSerializer,
    DraftCreateInputSerializer,
    ForwardFileInputSerializer,
    InboxQuerySerializer,
    OutboxQuerySerializer,
    DraftQuerySerializer,      # V-25
    ArchiveQuerySerializer,     # V-26
    ArchiveInputSerializer,
)

logger = logging.getLogger(__name__)


class CreateFileView(APIView):
    """POST api/file/ — Create and send a new file."""
    authentication_classes = [TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = FileCreateInputSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'error': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        try:
            data = serializer.validated_data
            file_id = services.create_file_via_sdk(
                uploader=data['uploader'],
                uploader_designation=data['uploader_designation'],
                receiver=data['receiver'],
                receiver_designation=data['receiver_designation'],
                subject=data.get('subject', ''),
                description=data.get('description', ''),
                src_module=data.get('src_module', 'filetracking'),
                src_object_id=data.get('src_object_id', ''),
                file_extra_JSON=data.get('file_extra_JSON', {}),
                attached_file=data.get('file_attachment'),
            )
            return Response({'file_id': file_id}, status=status.HTTP_201_CREATED)
        except Exception as e:
            logger.exception("CreateFileView error")
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ViewFileView(APIView):
    """GET/DELETE api/file/<file_id>/ — View or delete a file."""
    authentication_classes = [TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, file_id):
        try:
            file_data = services.view_file_details(file_id)
            return Response({'file': file_data})
        except Exception as e:
            logger.exception("ViewFileView.get error")
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, file_id):
        try:
            services.delete_file_with_auth(file_id, request.user)
            return Response({'message': 'File deleted successfully'})
        except Exception as e:
            logger.exception("ViewFileView.delete error")
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ViewInboxView(APIView):
    """GET api/inbox/ — List inbox files."""
    authentication_classes = [TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        serializer = InboxQuerySerializer(data=request.query_params)
        if not serializer.is_valid():
            return Response({'error': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        try:
            data = serializer.validated_data
            inbox_files = services.view_inbox(
                username=data['username'],
                designation=data['designation'],
                src_module=data.get('src_module', 'filetracking'),
            )
            return Response({'inbox': inbox_files})
        except Exception as e:
            logger.exception("ViewInboxView error")
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ViewOutboxView(APIView):
    """GET api/outbox/ — List outbox files."""
    authentication_classes = [TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        serializer = OutboxQuerySerializer(data=request.query_params)
        if not serializer.is_valid():
            return Response({'error': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        try:
            data = serializer.validated_data
            outbox_files = services.view_outbox(
                username=data['username'],
                designation=data['designation'],
                src_module=data.get('src_module', 'filetracking'),
            )
            return Response({'outbox': outbox_files})
        except Exception as e:
            logger.exception("ViewOutboxView error")
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ViewHistoryView(APIView):
    """GET api/history/<file_id>/ — View tracking history."""
    authentication_classes = [TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, file_id):
        try:
            history = services.view_history(int(file_id))
            return Response({'history': history})
        except (ValueError, TypeError):
            return Response({'error': 'Invalid file_id'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.exception("ViewHistoryView error")
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ForwardFileView(APIView):
    """POST api/forwardfile/<file_id>/ — Forward a file."""
    authentication_classes = [TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, file_id):
        serializer = ForwardFileInputSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'error': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        try:
            data = serializer.validated_data
            tracking_id = services.forward_file(
                file_id=file_id,
                receiver=data['receiver'],
                receiver_designation=data['receiver_designation'],
                file_extra_JSON=data.get('file_extra_JSON', {}),
                remarks=data.get('remarks', ''),
                file_attachment=data.get('file_attachment'),
            )
            return Response({'tracking_id': tracking_id}, status=status.HTTP_201_CREATED)
        except Exception as e:
            logger.exception("ForwardFileView error")
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class DraftFileView(APIView):
    """GET api/draft/ — List draft files. (V-25: uses DraftQuerySerializer)"""
    authentication_classes = [TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        serializer = DraftQuerySerializer(data=request.query_params)  # V-25
        if not serializer.is_valid():
            return Response({'error': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        try:
            data = serializer.validated_data
            drafts = services.view_drafts(
                username=data['username'],
                designation=data['designation'],
                src_module=data.get('src_module', 'filetracking'),
            )
            return Response({'drafts': drafts})
        except Exception as e:
            logger.exception("DraftFileView error")
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class CreateDraftFile(APIView):
    """POST api/createdraft/ — Create a draft file."""
    authentication_classes = [TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = DraftCreateInputSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'error': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        try:
            data = serializer.validated_data
            file_id = services.create_draft_via_sdk(
                uploader=data['uploader'],
                uploader_designation=data['uploader_designation'],
                src_module=data.get('src_module', 'filetracking'),
                src_object_id=data.get('src_object_id', ''),
                file_extra_JSON=data.get('file_extra_JSON', {}),
                attached_file=data.get('file_attachment'),
            )
            return Response({'file_id': file_id}, status=status.HTTP_201_CREATED)
        except Exception as e:
            logger.exception("CreateDraftFile error")
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class CreateArchiveFile(APIView):
    """POST api/createarchive/ — Archive a file."""
    authentication_classes = [TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = ArchiveInputSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'error': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        try:
            data = serializer.validated_data
            services.archive_file_sdk(data['file_id'])
            return Response({'message': 'File archived successfully'})
        except Exception as e:
            logger.exception("CreateArchiveFile error")
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ArchiveFileView(APIView):
    """GET api/archive/ — List archived files. (V-26: uses ArchiveQuerySerializer)"""
    authentication_classes = [TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        serializer = ArchiveQuerySerializer(data=request.query_params)  # V-26
        if not serializer.is_valid():
            return Response({'error': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        try:
            data = serializer.validated_data
            archive_files = services.view_archived(
                username=data['username'],
                designation=data['designation'],
                src_module=data.get('src_module', 'filetracking'),
            )
            return Response({'archive': archive_files})
        except Exception as e:
            logger.exception("ArchiveFileView error")
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class GetDesignationsView(APIView):
    """GET api/designations/<username>/ — List designations for a user."""
    authentication_classes = [TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, username):
        try:
            designations = services.get_designations(username)
            return Response({'designations': designations})
        except Exception as e:
            logger.exception("GetDesignationsView error")
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
