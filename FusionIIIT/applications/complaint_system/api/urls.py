# api/urls.py
# T-19 / RD-12: Migrated from deprecated django.conf.urls.url() to django.urls.path().
# All regex patterns converted to Django 2+ type converters.

from django.urls import path
from . import views

urlpatterns = [
    # Complaint endpoints
    path('user/detail/<int:detailcomp_id1>/',        views.complaint_details_api,      name='complain-detail-get-api'),
    path('studentcomplain/',                          views.student_complain_api,        name='complain-detail2-get-api'),
    path('newcomplain/',                              views.create_complain_api,         name='complain-post-api'),
    path('updatecomplain/<int:c_id>/',               views.edit_complain_api,           name='complain-put-api'),
    path('removecomplain/<int:c_id>/',               views.edit_complain_api,           name='complain-delete-api'),

    # Worker endpoints
    path('workers/',                                  views.worker_api,                  name='worker-get-api'),
    path('addworker/',                                views.worker_api,                  name='worker-post-api'),
    path('removeworker/<int:w_id>/',                 views.edit_worker_api,             name='worker-delete-api'),
    path('updateworker/<int:w_id>/',                 views.edit_worker_api,             name='worker-put-api'),

    # Caretaker endpoints
    path('caretakers/',                               views.caretaker_api,               name='caretaker-get-api'),
    path('addcaretaker/',                             views.caretaker_api,               name='caretaker-post-api'),
    path('removecaretaker/<int:c_id>/',              views.edit_caretaker_api,          name='caretaker-delete-api'),
    path('updatecaretaker/<int:c_id>/',              views.edit_caretaker_api,          name='caretaker-put-api'),

    # Service-provider endpoints
    path('service_providers/',                        views.service_provider_api,        name='service-provider-get-api'),
    path('addservice_provider/',                      views.service_provider_api,        name='service-provider-post-api'),
    path('removeservice_provider/<int:s_id>/',       views.edit_service_provider_api,   name='service-provider-delete-api'),
    path('updateservice_provider/<int:s_id>/',       views.edit_service_provider_api,   name='service-provider-put-api'),
]