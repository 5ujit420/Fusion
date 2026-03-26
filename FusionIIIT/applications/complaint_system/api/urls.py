from django.urls import path
from . import views

app_name = "complaint"

urlpatterns = [
    # User URLs
    path("", views.CheckUser.as_view(), name="complaint"),
    path("user/", views.UserComplaintView.as_view(), name="user-complaints"),
    path("user/caretakerfb/", views.CaretakerFeedbackView.as_view(), name="caretaker-feedback"),
    path("user/<int:complaint_id>/", views.SubmitFeedbackView.as_view(), name="submit-feedback"),
    path("user/detail/<int:detailcomp_id1>/", views.ComplaintDetailView.as_view(), name="detail"),

    # Caretaker URLs
    path('caretaker/lodge/', views.CaretakerLodgeView.as_view(), name='caretaker-lodge'),
    path('caretaker/', views.CaretakerView.as_view(), name='caretaker'),
    path('caretaker/feedback/<int:feedcomp_id>/', views.FeedbackCareView.as_view(), name='caretaker-feedback-detail'),
    path('caretaker/pending/<int:cid>/', views.ResolvePendingView.as_view(), name='caretaker-resolve'),
    path('caretaker/detail2/<int:detailcomp_id1>/', views.ComplaintDetailView.as_view(), name='caretaker-detail'),
    path('caretaker/search_complaint', views.SearchComplaintView.as_view(), name='caretaker-search'),
    path('caretaker/<int:complaint_id>/feedback/', views.SubmitFeedbackCaretakerView.as_view(), name='caretaker-submit-feedback'),
    path('caretaker/worker_id_know_more/<int:work_id>/removew/', views.RemoveWorkerView.as_view(), name='remove-worker'),
    path('caretaker/<int:comp_id1>/', views.ForwardComplaintView.as_view(), name='forward-complaint'),
    path('caretaker/deletecomplaint/<int:comp_id1>/', views.DeleteComplaintView.as_view(), name='delete-complaint'),
    path('caretaker/<int:complaint_id>/<str:status_value>/', views.ChangeStatusView.as_view(), name='caretaker-change-status'),

    # Service Provider URLs
    path('service_provider/lodge/', views.ServiceProviderLodgeView.as_view(), name='sp-lodge'),
    path('service_provider/', views.ServiceProviderView.as_view(), name='service-provider'),
    path('service_provider/feedback/<int:feedcomp_id>/', views.FeedbackSuperView.as_view(), name='sp-feedback-detail'),
    path('service_provider/caretaker_id_know_more/<int:caretaker_id>/', views.CaretakerIdKnowMoreView.as_view(), name='sp-caretaker-detail'),
    path('service_provider/detail/<int:detailcomp_id1>/', views.ServiceProviderComplaintDetailView.as_view(), name='sp-complaint-detail'),
    path('service_provider/pending/<int:cid>/', views.ServiceProviderResolvePendingView.as_view(), name='sp-resolve'),
    path('service_provider/<int:complaint_id>/', views.ServiceProviderSubmitFeedbackView.as_view(), name='sp-submit-feedback'),
    path('service_provider/<int:complaint_id>/<str:status_value>/', views.ChangeStatusView.as_view(), name='sp-change-status'),

    # Report
    path('generate-report/', views.GenerateReportView.as_view(), name='generate-report-api'),

    # Token-auth CRUD API endpoints
    path('api/user/detail/<int:detailcomp_id1>/', views.ComplaintDetailAPIView.as_view(), name='complain-detail-get-api'),
    path('api/studentcomplain/', views.StudentComplainAPIView.as_view(), name='complain-detail2-get-api'),
    path('api/newcomplain/', views.CreateComplainAPIView.as_view(), name='complain-post-api'),
    path('api/updatecomplain/<int:c_id>/', views.EditComplainAPIView.as_view(), name='complain-put-api'),
    path('api/removecomplain/<int:c_id>/', views.EditComplainAPIView.as_view(), name='complain-delete-api'),

    # Worker API endpoints
    path('api/workers/', views.WorkerAPIView.as_view(), name='worker-get-api'),
    path('api/addworker/', views.WorkerAPIView.as_view(), name='worker-post-api'),
    path('api/removeworker/<int:w_id>/', views.EditWorkerAPIView.as_view(), name='worker-delete-api'),
    path('api/updateworker/<int:w_id>/', views.EditWorkerAPIView.as_view(), name='worker-put-api'),

    # Caretaker API endpoints
    path('api/caretakers/', views.CaretakerAPIView.as_view(), name='caretaker-get-api'),
    path('api/addcaretaker/', views.CaretakerAPIView.as_view(), name='caretaker-post-api'),
    path('api/removecaretaker/<int:c_id>/', views.EditCaretakerAPIView.as_view(), name='caretaker-delete-api'),
    path('api/updatecaretaker/<int:c_id>/', views.EditCaretakerAPIView.as_view(), name='caretaker-put-api'),

    # Service Provider API endpoints
    path('api/service_providers/', views.ServiceProviderAPIView.as_view(), name='service_provider-get-api'),
    path('api/addservice_provider/', views.ServiceProviderAPIView.as_view(), name='service_provider-post-api'),
    path('api/removeservice_provider/<int:s_id>/', views.EditServiceProviderAPIView.as_view(), name='service_provider-delete-api'),
    path('api/updateservice_provider/<int:s_id>/', views.EditServiceProviderAPIView.as_view(), name='service_provider-put-api'),
]
