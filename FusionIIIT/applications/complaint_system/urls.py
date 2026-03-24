from django.conf.urls import url, include

app_name = 'complaint_system'

urlpatterns = [
    url(r'^api/', include('applications.complaint_system.api.urls')),
]