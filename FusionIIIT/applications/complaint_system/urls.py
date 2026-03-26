# urls.py
# Clean routing for the complaint_system module.
# Addresses: RR-07 (duplicate imports), RR-10 (typo fix), RR-06 (merged status views)

from django.urls import path

from .views import (
    CheckUser,
    UserComplaintView,
    CaretakerFeedbackView,
    SubmitFeedbackView,
    ComplaintDetailView,
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
    ServiceProviderLodgeView,
    ServiceProviderView,
    FeedbackSuperView,
    CaretakerIdKnowMoreView,
    ServiceProviderComplaintDetailView,
    ServiceProviderResolvePendingView,
    ServiceProviderSubmitFeedbackView,
    GenerateReportView,
)

app_name = "complaint"

urlpatterns = [
    # User URLs
    path("", CheckUser.as_view(), name="complaint"),
    path("user/", UserComplaintView.as_view(), name="user-complaints"),
    path("user/caretakerfb/", CaretakerFeedbackView.as_view(), name="caretaker-feedback"),
    path("user/<int:complaint_id>/", SubmitFeedbackView.as_view(), name="submit-feedback"),
    path("user/detail/<int:detailcomp_id1>/", ComplaintDetailView.as_view(), name="detail"),

    # Caretaker URLs
    path('caretaker/lodge/', CaretakerLodgeView.as_view(), name='caretaker-lodge'),
    path('caretaker/', CaretakerView.as_view(), name='caretaker'),
    path('caretaker/feedback/<int:feedcomp_id>/', FeedbackCareView.as_view(), name='caretaker-feedback-detail'),
    path('caretaker/pending/<int:cid>/', ResolvePendingView.as_view(), name='caretaker-resolve'),
    path('caretaker/detail2/<int:detailcomp_id1>/', ComplaintDetailView.as_view(), name='caretaker-detail'),
    path('caretaker/search_complaint', SearchComplaintView.as_view(), name='caretaker-search'),
    path('caretaker/<int:complaint_id>/feedback/', SubmitFeedbackCaretakerView.as_view(), name='caretaker-submit-feedback'),
    path('caretaker/worker_id_know_more/<int:work_id>/removew/', RemoveWorkerView.as_view(), name='remove-worker'),
    path('caretaker/<int:comp_id1>/', ForwardComplaintView.as_view(), name='forward-complaint'),
    path('caretaker/deletecomplaint/<int:comp_id1>/', DeleteComplaintView.as_view(), name='delete-complaint'),
    path('caretaker/<int:complaint_id>/<str:status_value>/', ChangeStatusView.as_view(), name='caretaker-change-status'),

    # Service Provider URLs
    path('service_provider/lodge/', ServiceProviderLodgeView.as_view(), name='sp-lodge'),
    path('service_provider/', ServiceProviderView.as_view(), name='service-provider'),
    path('service_provider/feedback/<int:feedcomp_id>/', FeedbackSuperView.as_view(), name='sp-feedback-detail'),
    path('service_provider/caretaker_id_know_more/<int:caretaker_id>/', CaretakerIdKnowMoreView.as_view(), name='sp-caretaker-detail'),
    path('service_provider/detail/<int:detailcomp_id1>/', ServiceProviderComplaintDetailView.as_view(), name='sp-complaint-detail'),
    path('service_provider/pending/<int:cid>/', ServiceProviderResolvePendingView.as_view(), name='sp-resolve'),
    path('service_provider/<int:complaint_id>/', ServiceProviderSubmitFeedbackView.as_view(), name='sp-submit-feedback'),
    path('service_provider/<int:complaint_id>/<str:status_value>/', ChangeStatusView.as_view(), name='sp-change-status'),

    # Report
    path('generate-report/', GenerateReportView.as_view(), name='generate-report-api'),
]
