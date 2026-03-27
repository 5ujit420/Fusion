# api/views.py
# Thin API views for the filetracking module.
# All logic delegated to services.py, all queries to selectors.py.
# Fixes: V-12–V-21, V-27, V-28, V-32–V-34, V-44, V-45

import logging

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework.authentication import TokenAuthentication

from ..models import File, Tracking
from .serializers import (
    FileCreateInputSerializer,
    DraftCreateInputSerializer,
    ForwardFileInputSerializer,
    InboxQuerySerializer,
    OutboxQuerySerializer,
    ArchiveInputSerializer,
    DraftQuerySerializer,
    ArchiveQuerySerializer,
)
from .. import services

# V-27: Fix logger import (was `from venv import logger`)
logger = logging.getLogger(__name__)


class CreateFileView(APIView):
    """V-12: Delegates to services.create_file_via_sdk()."""
    authentication_classes = [TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = FileCreateInputSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        try:
            uploaded_file = request.FILES.get('file')
            file_id = services.create_file_via_sdk(
                uploader=request.user.username,
                uploader_designation=serializer.validated_data['designation'],
                receiver=serializer.validated_data['receiver_username'],
                receiver_designation=serializer.validated_data['receiver_designation'],
                subject=serializer.validated_data['subject'],
                description=serializer.validated_data.get('description', ''),
                attached_file=uploaded_file,
            )
            return Response({'file_id': file_id}, status=status.HTTP_201_CREATED)
        except Exception as e:
            logger.error(f"Error creating file: {e}")
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ViewFileView(APIView):
    """V-13: Delegates to services.view_file_details() and services.delete_file()."""
    authentication_classes = [TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, file_id):
        try:
            file_details = services.view_file_details(int(file_id))
            return Response(file_details, status=status.HTTP_200_OK)
        except ValueError:
            return Response({'error': 'Invalid file ID format.'}, status=status.HTTP_400_BAD_REQUEST)
        except File.DoesNotExist:
            return Response({'error': 'File not found.'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error viewing file {file_id}: {e}")
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, file_id):
        """V-28: Fixed bare `return` → proper error response."""
        try:
            success = services.delete_file(int(file_id))
            if success:
                return Response({'message': 'File deleted successfully'},
                                status=status.HTTP_204_NO_CONTENT)
            else:
                return Response({'error': 'Failed to delete file'},
                                status=status.HTTP_400_BAD_REQUEST)
        except ValueError:
            return Response({'error': 'Invalid file ID format'},
                            status=status.HTTP_400_BAD_REQUEST)
        except File.DoesNotExist:
            return Response({'error': 'File not found'},
                            status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Unexpected error in DeleteFileView: {e}")
            return Response({'error': 'An internal server error occurred'},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ViewInboxView(APIView):
    """V-14, V-26: Delegates to services.view_inbox() with validation."""
    authentication_classes = [TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        serializer = InboxQuerySerializer(data=request.query_params)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        inbox_files = services.view_inbox(
            username=serializer.validated_data['username'],
            designation=serializer.validated_data.get('designation', ''),
            src_module=serializer.validated_data['src_module'],
        )
        return Response(inbox_files)


class ViewOutboxView(APIView):
    """V-15: Delegates to services.view_outbox() with validation."""
    authentication_classes = [TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        serializer = OutboxQuerySerializer(data=request.query_params)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        outbox_files = services.view_outbox(
            username=serializer.validated_data['username'],
            designation=serializer.validated_data.get('designation', ''),
            src_module=serializer.validated_data['src_module'],
        )
        return Response(outbox_files)


class ViewHistoryView(APIView):
    """V-16: Delegates to services.view_history_enriched()."""
    authentication_classes = [TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, file_id):
        try:
            tracking_array = services.view_history_enriched(file_id)
            return Response(tracking_array)
        except Tracking.DoesNotExist:
            return Response({'error': f'File with ID {file_id} not found.'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}")
            return Response({'error': 'Internal server error.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ForwardFileView(APIView):
    """V-17, V-44: Delegates to services.forward_file() with serializer validation."""
    authentication_classes = [TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, file_id):
        serializer = ForwardFileInputSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        try:
            file_attachment = request.FILES.get('file_attachment')
            new_tracking_id = services.forward_file(
                int(file_id),
                serializer.validated_data['receiver'],
                serializer.validated_data['receiver_designation'],
                request.data.get('file_extra_JSON', {}),
                serializer.validated_data.get('remarks', ''),
                file_attachment,
            )
            return Response({'tracking_id': new_tracking_id}, status=status.HTTP_201_CREATED)
        except Exception as e:
            logger.error(f"Error forwarding file {file_id}: {str(e)}")
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class CreateDraftFile(APIView):
    """V-18: Delegates to services.create_draft_via_sdk()."""
    authentication_classes = [TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = DraftCreateInputSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        try:
            file_id = services.create_draft_via_sdk(
                uploader=serializer.validated_data['uploader'],
                uploader_designation=serializer.validated_data['uploader_designation'],
                src_module=serializer.validated_data.get('src_module', 'filetracking'),
                src_object_id=serializer.validated_data.get('src_object_id', ''),
                file_extra_JSON=request.data.get('file_extra_JSON', {}),
                attached_file=request.FILES.get('attached_file'),
            )
            return Response({'file_id': file_id}, status=status.HTTP_201_CREATED)
        except Exception as e:
            logger.error(f"Error creating draft: {e}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class DraftFileView(APIView):
    """V-19, V-45: Delegates to services.view_drafts() with serializer validation."""
    authentication_classes = [TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        serializer = DraftQuerySerializer(data=request.query_params)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        try:
            draft_files = services.view_drafts(
                username=serializer.validated_data['username'],
                designation=serializer.validated_data['designation'],
                src_module=serializer.validated_data['src_module'],
            )
            return Response(draft_files, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error viewing drafts: {e}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ArchiveFileView(APIView):
    """V-20, V-45: Delegates to services.view_archived() with serializer validation."""
    authentication_classes = [TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        serializer = ArchiveQuerySerializer(data=request.query_params)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        try:
            archived_files = services.view_archived(
                username=serializer.validated_data['username'],
                designation=serializer.validated_data.get('designation', ''),
                src_module=serializer.validated_data['src_module'],
            )
            return Response(archived_files, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error viewing archives: {e}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CreateArchiveFile(APIView):
    """V-20: Delegates to services.archive_file_sdk()."""
    authentication_classes = [TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = ArchiveInputSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        try:
            success = services.archive_file_sdk(serializer.validated_data['file_id'])
            if success:
                return Response({'success': True})
            else:
                return Response({'error': 'File does not exist'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error archiving file: {e}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class GetDesignationsView(APIView):
    """V-21: Re-enabled authentication (was commented out)."""
    authentication_classes = [TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, username, *args, **kwargs):
        user_designations = services.get_designations(username)
        return Response({'designations': user_designations})
