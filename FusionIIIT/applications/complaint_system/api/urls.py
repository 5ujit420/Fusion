# api/urls.py
# Clean routing using path() instead of deprecated url().
# Addresses: RR-19

from django.urls import path
from . import views

urlpatterns = [
    # Complaint endpoints
    path('user/detail/<int:detailcomp_id1>/', views.ComplaintDetailAPIView.as_view(), name='complain-detail-get-api'),
    path('studentcomplain/', views.StudentComplainAPIView.as_view(), name='complain-detail2-get-api'),
    path('newcomplain/', views.CreateComplainAPIView.as_view(), name='complain-post-api'),
    path('updatecomplain/<int:c_id>/', views.EditComplainAPIView.as_view(), name='complain-put-api'),
    path('removecomplain/<int:c_id>/', views.EditComplainAPIView.as_view(), name='complain-delete-api'),

    # Worker endpoints
    path('workers/', views.WorkerAPIView.as_view(), name='worker-get-api'),
    path('addworker/', views.WorkerAPIView.as_view(), name='worker-post-api'),
    path('removeworker/<int:w_id>/', views.EditWorkerAPIView.as_view(), name='worker-delete-api'),
    path('updateworker/<int:w_id>/', views.EditWorkerAPIView.as_view(), name='worker-put-api'),

    # Caretaker endpoints
    path('caretakers/', views.CaretakerAPIView.as_view(), name='caretaker-get-api'),
    path('addcaretaker/', views.CaretakerAPIView.as_view(), name='caretaker-post-api'),
    path('removecaretaker/<int:c_id>/', views.EditCaretakerAPIView.as_view(), name='caretaker-delete-api'),
    path('updatecaretaker/<int:c_id>/', views.EditCaretakerAPIView.as_view(), name='caretaker-put-api'),

    # Service Provider endpoints
    path('service_providers/', views.ServiceProviderAPIView.as_view(), name='service_provider-get-api'),
    path('addservice_provider/', views.ServiceProviderAPIView.as_view(), name='service_provider-post-api'),
    path('removeservice_provider/<int:s_id>/', views.EditServiceProviderAPIView.as_view(), name='service_provider-delete-api'),
    path('updateservice_provider/<int:s_id>/', views.EditServiceProviderAPIView.as_view(), name='service_provider-put-api'),
]
