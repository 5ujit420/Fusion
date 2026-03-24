# api/urls.py
# Clean URL routing using path() instead of deprecated url().

from django.urls import path
from .views import (
    CreateFileView,
    ViewFileView,
    ViewInboxView,
    ViewOutboxView,
    ViewHistoryView,
    ForwardFileView,
    DraftFileView,
    CreateDraftFile,
    GetDesignationsView,
    CreateArchiveFile,
    ArchiveFileView,
)

urlpatterns = [
    path('file/', CreateFileView.as_view(), name='create_file'),
    path('file/<int:file_id>/', ViewFileView.as_view(), name='view_file'),
    path('inbox/', ViewInboxView.as_view(), name='view_inbox'),
    path('outbox/', ViewOutboxView.as_view(), name='view_outbox'),
    path('history/<int:file_id>/', ViewHistoryView.as_view(), name='view_history'),
    path('forwardfile/<int:file_id>/', ForwardFileView.as_view(), name='forward_file'),
    path('draft/', DraftFileView.as_view(), name='view_drafts'),
    path('createdraft/', CreateDraftFile.as_view(), name='create_draft'),
    path('createarchive/', CreateArchiveFile.as_view(), name='archive_file'),
    path('archive/', ArchiveFileView.as_view(), name='view_archived'),
    path('designations/<str:username>/', GetDesignationsView.as_view(), name='get_designations'),
]
