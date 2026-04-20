# urls.py
# T-07 / CS-14 / RD-03: ChangeStatusView + ChangeStatusSuperView merged → ChangeComplaintStatusView.
# T-16 / CS-33 / RD-09: Single consolidated import block (4 duplicate blocks removed).
# T-24: URL patterns listed under complaint/ namespace (app_name = 'complaint').
# Missing URL names added to all previously-unnamed patterns.
# ComplaintDetailView is now a single canonical class (duplicate definition removed in views.py).

from django.urls import path

from .views import (
    # User / general
    CheckUser,
    UserComplaintView,
    CaretakerFeedbackView,
    SubmitFeedbackView,
    ComplaintDetailView,
    # Caretaker
    CaretakerLodgeView,
    CaretakerView,
    FeedbackCareView,
    ResolvePendingView,
    SearchComplaintView,
    SubmitFeedbackCaretakerView,
    # Service provider
    ServiceProviderLodgeView,
    ServiceProviderView,
    FeedbackSuperView,
    CaretakerIdKnowMoreView,
    ServiceProviderComplaintDetailView,
    ServiceProviderResolvePendingView,
    ServiceProviderSubmitFeedbackView,
    # Worker / admin / misc
    RemoveWorkerView,
    ForwardCompaintView,
    DeleteComplaintView,
    ChangeComplaintStatusView,      # T-07: merged single view
    GenerateReportView,
)

app_name = 'complaint'

urlpatterns = [
    # --- User / student ---
    path('',                                                    CheckUser.as_view(),                        name='complaint'),
    path('user/',                                               UserComplaintView.as_view(),                name='user-complaints'),
    path('user/caretakerfb/',                                   CaretakerFeedbackView.as_view(),            name='caretaker-feedback'),
    path('user/<int:complaint_id>/',                            SubmitFeedbackView.as_view(),               name='submit-feedback'),
    path('user/detail/<int:detailcomp_id1>/',                   ComplaintDetailView.as_view(),              name='detail'),

    # --- Caretaker ---
    path('caretaker/lodge/',                                    CaretakerLodgeView.as_view(),               name='caretaker-lodge'),
    path('caretaker/',                                          CaretakerView.as_view(),                    name='caretaker'),
    path('caretaker/feedback/<int:feedcomp_id>/',               FeedbackCareView.as_view(),                 name='caretaker-feedback-detail'),
    path('caretaker/pending/<int:cid>/',                        ResolvePendingView.as_view(),               name='caretaker-resolve-pending'),
    path('caretaker/detail2/<int:detailcomp_id1>/',             ComplaintDetailView.as_view(),              name='caretaker-complaint-detail'),
    path('caretaker/search_complaint/',                         SearchComplaintView.as_view(),              name='caretaker-search-complaint'),
    path('caretaker/<int:complaint_id>/feedback/',              SubmitFeedbackCaretakerView.as_view(),      name='caretaker-submit-feedback'),
    path('caretaker/worker_id_know_more/<int:work_id>/removew/',RemoveWorkerView.as_view(),                 name='remove-worker'),
    path('caretaker/<int:comp_id1>/',                           ForwardCompaintView.as_view(),              name='assign-worker'),
    path('caretaker/deletecomplaint/<int:comp_id1>/',           DeleteComplaintView.as_view(),              name='delete-complaint'),
    # T-07: single view, both caretaker and service-provider use it
    path('caretaker/<int:complaint_id>/<str:complaint_new_status>/',         ChangeComplaintStatusView.as_view(), name='change-status-caretaker'),

    # --- Service provider ---
    path('service_provider/lodge/',                                         ServiceProviderLodgeView.as_view(),             name='service-provider-lodge'),
    path('service_provider/',                                               ServiceProviderView.as_view(),                  name='service-provider'),
    path('service_provider/feedback/<int:feedcomp_id>/',                    FeedbackSuperView.as_view(),                    name='service-provider-feedback'),
    path('service_provider/caretaker_id_know_more/<int:caretaker_id>/',     CaretakerIdKnowMoreView.as_view(),              name='caretaker-know-more'),
    path('service_provider/detail/<int:detailcomp_id1>/',                   ServiceProviderComplaintDetailView.as_view(),   name='detail3'),
    path('service_provider/pending/<int:cid>/',                             ServiceProviderResolvePendingView.as_view(),     name='service-provider-resolve'),
    path('service_provider/<int:complaint_id>/',                            ServiceProviderSubmitFeedbackView.as_view(),    name='service-provider-submit-feedback'),
    path('service_provider/<int:complaint_id>/<str:complaint_new_status>/', ChangeComplaintStatusView.as_view(),            name='change-status-service-provider'),

    # --- Report ---
    path('generate-report/',                                    GenerateReportView.as_view(),               name='generate-report-api'),
]