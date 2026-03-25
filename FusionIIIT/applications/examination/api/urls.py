"""
Examination API URL configuration.

Migrated from ``url()`` to ``path()`` (V40).
Standardized to kebab-case where possible (V36).
"""

from django.urls import path
from . import views

urlpatterns = [
    # Role-based routing
    path('exam-view/', views.exam_view, name='exam_view'),

    # Academic year / semester lists
    path('unique-stu-grades-years/', views.UniqueStudentGradeYearsView.as_view(), name='unique-stu-grades-years'),
    path('student/result-semesters/', views.StudentSemesterListView.as_view(), name='get_student_semesters'),

    # Acadadmin — grade management
    path('update-grades/', views.UpdateGradesAPI.as_view(), name='update_grades'),
    path('update-enter-grades/', views.UpdateEnterGradesAPI.as_view(), name='update_enter_grades'),
    path('moderate-student-grades/', views.ModerateStudentGradesAPI.as_view(), name='moderate_student_grades'),
    path('upload-grades/', views.UploadGradesAPI.as_view(), name='upload_grades'),

    # Professor endpoints
    path('submit-grades-prof/', views.SubmitGradesProfAPI.as_view(), name='submitGradesProf'),
    path('upload-grades-prof/', views.UploadGradesProfAPI.as_view(), name='upload_grades_prof'),
    path('download-grades/', views.DownloadGradesAPI.as_view(), name='downloadGrades'),
    path('preview-grades/', views.PreviewGradesAPI.as_view(), name='preview_grades'),
    path('download-template/', views.DownloadTemplateAPI.as_view(), name='download_template'),

    # PDF / Excel generation
    path('generate-pdf/', views.GeneratePDFAPI.as_view(), name='generate_pdf'),
    path('generate-student-result-pdf/', views.GenerateStudentResultPDFAPI.as_view(), name='generate_student_result_pdf'),
    path('generate-result/', views.GenerateResultAPI.as_view(), name='generate_result'),
    path('generate-transcript/', views.GenerateTranscript.as_view(), name='generate_transcript'),

    # Dean Academic endpoints
    path('verify-grades-dean/', views.VerifyGradesDeanView.as_view(), name='verify_grades_dean'),
    path('update-enter-grades-dean/', views.UpdateEnterGradesDeanView.as_view(), name='update_enter_grades_dean'),
    path('validate-dean/', views.ValidateDeanView.as_view(), name='validate_dean'),
    path('validate-dean-submit/', views.ValidateDeanSubmitView.as_view(), name='validate_dean_submit'),

    # Student endpoints
    path('check-result/', views.CheckResultView.as_view(), name='check_result'),

    # Result announcements
    path('result-announcements/', views.ResultAnnouncementListAPI.as_view(), name='result-announcements'),
    path('update-announcement/', views.UpdateAnnouncementAPI.as_view(), name='update-announcement'),
    path('create-announcement/', views.CreateAnnouncementAPI.as_view(), name='create-announcement'),

    # Grade status / summary
    path('grade-status/', views.GradeStatusAPI.as_view(), name='grade_status'),
    path('grade-summary/', views.GradeSummaryAPI.as_view(), name='grade_summary'),
]