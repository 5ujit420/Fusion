from django.conf.urls import url
from . import views

app_name = 'placement'

urlpatterns = [
    url(r'^$', views.PlacementStatisticsView.as_view(), name='placement'),
    url(r'^get_reference_list/$', views.GetReferenceListView.as_view(), name='get_reference_list'),
    url(r'^checking_roles/$', views.CheckingRolesView.as_view(), name='checking_roles'),
    url(r'^companyname_dropdown/$', views.CompanyNameDropdownView.as_view(), name='companyname_dropdown'),
    url(r'^student_records/invitation_status$', views.InvitationStatusView.as_view(), name='invitation_status'),
    url(r'^student_records/delete_invitation_status$', views.DeleteInvitationStatusView.as_view(), name='delete_invitation_status'),
    url(r'^student_records/$', views.StudentRecordsView.as_view(), name='student_records'),
    url(r'^manage_records/$', views.ManageRecordsView.as_view(), name='manage_records'),
    url(r'^statistics/$', views.PlacementStatisticsView.as_view(), name='placement_statistics'),
    url(r'^delete_placement_statistics/$', views.DeletePlacementStatisticsView.as_view(), name='delete_placement_statistics'),
    url(r'^cv/(?P<username>[a-zA-Z0-9\.]{1,20})/$', views.CVView.as_view(), name="cv"),
    url(r'^add_placement_schedule/$', views.AddPlacementScheduleView.as_view(), name='add_placement_schedule'),
    url(r'^placement_schedule_save/$', views.PlacementScheduleSaveView.as_view(), name='placement_schedule_save'),
    url(r'^delete_placement_record/$', views.DeletePlacementRecordView.as_view(), name='delete_placement_record'),
    url(r'^add_placement_record/$', views.AddPlacementRecordView.as_view(), name='add_placement_record'),
    url(r'^placement_record_save/$', views.PlacementRecordSaveView.as_view(), name='placement_record_save'),
    url(r'^add_placement_visit/$', views.AddPlacementVisitView.as_view(), name='add_placement_visit'),
    url(r'^placement_visit_save/$', views.PlacementVisitSaveView.as_view(), name='placement_visit_save'),
]
