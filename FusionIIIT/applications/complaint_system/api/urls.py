# api/urls.py
# Clean URL routing for the complaint_system module.
# All URLs use `path()` (not deprecated `url()`).

from django.urls import path
from .views import (
    # User views
    CheckUserView,
    UserComplaintView,
    CaretakerFeedbackView,
    SubmitFeedbackView,
    ComplaintDetailView,
    # Caretaker views
    CaretakerLodgeView,
    CaretakerView,
    FeedbackCareView,
    ResolvePendingView,
    SearchComplaintView,
    SubmitFeedbackCaretakerView,
    RemoveWorkerView,
    ForwardComplaintView,
    DeleteComplaintView,
    ChangeStatusView,
    # Service Provider views
    ServiceProviderLodgeView,
    ServiceProviderView,
    FeedbackSuperView,
    CaretakerIdKnowMoreView,
    ServiceProviderComplaintDetailView,
    ServiceProviderResolvePendingView,
    ServiceProviderSubmitFeedbackView,
    # Report
    GenerateReportView,
    # Mobile / Token-auth API views
    ComplaintDetailAPIView,
    StudentComplainAPIView,
    CreateComplainAPIView,
    EditComplainAPIView,
    WorkerAPIView,
    EditWorkerAPIView,
    CaretakerAPIView,
    EditCaretakerAPIView,
    ServiceProviderAPIView,
    EditServiceProviderAPIView,
)

app_name = "complaint"

urlpatterns = [
    # ----- User endpoints -----
    path('', CheckUserView.as_view(), name='complaint'),
    path('user/', UserComplaintView.as_view(), name='user-complaints'),
    path('user/caretakerfb/', CaretakerFeedbackView.as_view(), name='caretaker-feedback'),
    path('user/<int:complaint_id>/', SubmitFeedbackView.as_view(), name='submit-feedback'),
    path('user/detail/<int:detailcomp_id1>/', ComplaintDetailView.as_view(), name='detail'),

    # ----- Caretaker endpoints -----
    path('caretaker/lodge/', CaretakerLodgeView.as_view(), name='caretaker-lodge'),
    path('caretaker/', CaretakerView.as_view(), name='caretaker'),
    path('caretaker/feedback/<int:feedcomp_id>/', FeedbackCareView.as_view(), name='caretaker-feedback-detail'),
    path('caretaker/pending/<int:cid>/', ResolvePendingView.as_view(), name='caretaker-resolve'),
    path('caretaker/detail2/<int:detailcomp_id1>/', ComplaintDetailView.as_view(), name='caretaker-detail'),
    path('caretaker/search_complaint/', SearchComplaintView.as_view(), name='caretaker-search'),
    path('caretaker/<int:complaint_id>/feedback/', SubmitFeedbackCaretakerView.as_view(), name='caretaker-submit-feedback'),
    path('caretaker/worker_id_know_more/<int:work_id>/removew/', RemoveWorkerView.as_view(), name='remove-worker'),
    path('caretaker/<int:comp_id1>/', ForwardComplaintView.as_view(), name='assign_worker'),
    path('caretaker/deletecomplaint/<int:comp_id1>/', DeleteComplaintView.as_view(), name='delete-complaint'),
    path('caretaker/<int:complaint_id>/<str:status_value>/', ChangeStatusView.as_view(), name='change-status'),

    # ----- Service Provider endpoints -----
    path('service_provider/lodge/', ServiceProviderLodgeView.as_view(), name='sp-lodge'),
    path('service_provider/', ServiceProviderView.as_view(), name='service-provider'),
    path('service_provider/feedback/<int:feedcomp_id>/', FeedbackSuperView.as_view(), name='sp-feedback'),
    path('service_provider/caretaker_id_know_more/<int:caretaker_id>/', CaretakerIdKnowMoreView.as_view(), name='sp-caretaker-knowmore'),
    path('service_provider/detail/<int:detailcomp_id1>/', ServiceProviderComplaintDetailView.as_view(), name='detail3'),
    path('service_provider/pending/<int:cid>/', ServiceProviderResolvePendingView.as_view(), name='sp-resolve'),
    path('service_provider/<int:complaint_id>/', ServiceProviderSubmitFeedbackView.as_view(), name='sp-feedback-submit'),
    path('service_provider/<int:complaint_id>/<str:status_value>/', ChangeStatusView.as_view(), name='change-status-super'),

    # ----- Report -----
    path('generate-report/', GenerateReportView.as_view(), name='generate-report-api'),

    # ----- Mobile / Token-auth API endpoints -----
    path('api/user/detail/<int:detailcomp_id1>/', ComplaintDetailAPIView.as_view(), name='complain-detail-get-api'),
    path('api/studentcomplain/', StudentComplainAPIView.as_view(), name='complain-detail2-get-api'),
    path('api/newcomplain/', CreateComplainAPIView.as_view(), name='complain-post-api'),
    path('api/updatecomplain/<int:c_id>/', EditComplainAPIView.as_view(), name='complain-put-api'),
    path('api/removecomplain/<int:c_id>/', EditComplainAPIView.as_view(), name='complain-delete-api'),

    path('api/workers/', WorkerAPIView.as_view(), name='worker-get-api'),
    path('api/addworker/', WorkerAPIView.as_view(), name='worker-post-api'),
    path('api/removeworker/<int:w_id>/', EditWorkerAPIView.as_view(), name='worker-delete-api'),
    path('api/updateworker/<int:w_id>/', EditWorkerAPIView.as_view(), name='worker-put-api'),

    path('api/caretakers/', CaretakerAPIView.as_view(), name='caretaker-get-api'),
    path('api/addcaretaker/', CaretakerAPIView.as_view(), name='caretaker-post-api'),
    path('api/removecaretaker/<int:c_id>/', EditCaretakerAPIView.as_view(), name='caretaker-delete-api'),
    path('api/updatecaretaker/<int:c_id>/', EditCaretakerAPIView.as_view(), name='caretaker-put-api'),

    path('api/service_providers/', ServiceProviderAPIView.as_view(), name='service_provider-get-api'),
    path('api/addservice_provider/', ServiceProviderAPIView.as_view(), name='service_provider-post-api'),
    path('api/removeservice_provider/<int:s_id>/', EditServiceProviderAPIView.as_view(), name='service_provider-delete-api'),
    path('api/updateservice_provider/<int:s_id>/', EditServiceProviderAPIView.as_view(), name='service_provider-put-api'),
]