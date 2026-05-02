# urls.py — root URL routing for the filetracking module.
# T-12/S-32: Updated autocomplete URL names to match renamed view functions.
# 5B: removed duplicate 'outward' and 'inward' aliases.

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
    path('confirmdelete/<int:id>/', views.confirmdelete, name='confirm_delete'),
    path('archive/<int:id>/', views.archive_view, name='archive_view'),
    path('finish/<int:id>/', views.archive_file_view, name='finish_file'),
    path('viewfile/<int:id>/', views.view_file_view, name='view_file_view'),
    path('forward/<int:id>/', views.forward, name='forward'),
    # T-12/S-32: snake_case names replacing AjaxDropdown1 / AjaxDropdown
    path('ajax/', views.designation_autocomplete_view, name='designation_autocomplete'),
    path('ajax_dropdown/', views.user_autocomplete_view, name='user_autocomplete'),
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
