from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^$', views.CheckUserRoleView.as_view(), name='check-user-roles'),

    # Complaint endpoints
    url(r'^complaints/$', views.ComplaintListView.as_view(), name='complaint-list-lodge'),
    url(r'^complaints/(?P<pk>\d+)/$', views.ComplaintDetailView.as_view(), name='complaint-detail'),
    url(r'^complaints/(?P<pk>\d+)/resolve/$', views.ResolvePendingView.as_view(), name='complaint-resolve'),
    url(r'^complaints/(?P<pk>\d+)/feedback/$', views.SubmitFeedbackView.as_view(), name='complaint-feedback'),
    url(r'^complaints/(?P<pk>\d+)/forward/$', views.ForwardComplaintView.as_view(), name='complaint-forward'),
    url(r'^complaints/(?P<pk>\d+)/status/(?P<status_str>\w+)/$', views.ChangeComplaintStatusView.as_view(), name='complaint-status-change'),

    # Reporting
    url(r'^report/$', views.GenerateReportView.as_view(), name='generate-report'),

    # Worker endpoints
    url(r'^workers/$', views.WorkerListView.as_view(), name='worker-list'),
    url(r'^workers/(?P<pk>\d+)/$', views.WorkerDetailView.as_view(), name='worker-detail'),

    # Caretaker endpoints
    url(r'^caretakers/$', views.CaretakerListView.as_view(), name='caretaker-list'),
    url(r'^caretakers/(?P<pk>\d+)/$', views.CaretakerDetailView.as_view(), name='caretaker-detail'),

    # Service Provider endpoints
    url(r'^service_providers/$', views.ServiceProviderListView.as_view(), name='service-provider-list'),
    url(r'^service_providers/(?P<pk>\d+)/$', views.ServiceProviderDetailView.as_view(), name='service-provider-detail'),
]