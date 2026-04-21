# urls.py
# Root URL routing for the filetracking module.
# Migrated from deprecated url() to path().

from django.urls import path, include

from . import views
from .api import urls as api_urls

app_name = 'filetracking'

urlpatterns = [
    path('', views.filetracking, name='filetracking'),
    path('draftdesign/', views.draft_design, name='draft_design'),
    path('drafts/<int:id>/', views.drafts_view, name='drafts_view'),
    path('outbox/<int:id>/', views.outbox_view, name='outbox_view'),
    path('inbox/', views.inbox_view, name='inbox_view'),
    path('outward/', views.outbox_view, name='outward'),
    path('inward/', views.inbox_view, name='inward'),
    path('confirmdelete/<int:id>/', views.confirmdelete, name='confirm_delete'),
    path('archive/<int:id>/', views.archive_view, name='archive_view'),
    path('finish/<int:id>/', views.archive_file_view, name='finish_file'),
    path('viewfile/<int:id>/', views.view_file_view, name='view_file_view'),
    path('forward/<int:id>/', views.forward, name='forward'),
    path('ajax/', views.AjaxDropdown1, name='ajax_dropdown1'),
    path('ajax_dropdown/', views.AjaxDropdown, name='ajax_dropdown'),
    path('delete/<int:id>/', views.delete, name='delete'),
    path('forward_inward/<int:id>/', views.forward_inward, name='forward_inward'),
    path('finish_design/', views.finish_design, name='finish_design'),
    path('finish_fileview/<int:id>/', views.finish_fileview, name='finish_fileview'),
    path('archive_design/', views.archive_design, name='archive_design'),
    path('archive_finish/<int:id>/', views.archive_finish, name='archive_finish'),
    path('unarchive/<int:id>/', views.unarchive_file, name='unarchive'),
    path('getdesignations/<str:username>/', views.get_designations_view, name='get_user_designations'),
    path('editdraft/<str:id>/', views.edit_draft_view, name='edit_draft'),
    path('download_file/<str:id>/', views.download_file, name='download_file'),

    # REST API urls
    path('api/', include(api_urls)),
]
