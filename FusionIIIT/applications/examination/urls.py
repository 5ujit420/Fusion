"""
Examination module URL configuration.

Migrated from ``url()`` to ``path()`` (V40).
Removed routes for deleted redundant views.
Removed commented-out dead routes.
"""

from django.urls import path, include
from . import views

app_name = "examination"

urlpatterns = [
    # API routes
    path("api/", include("applications.examination.api.urls")),

    # Entry point
    path("", views.exam, name="exam"),

    # Acadadmin views
    path("submit/", views.submit, name="submit"),
    path("submitGrades/", views.submitGrades, name="submitGrades"),
    path("updateGrades/", views.updateGrades, name="updateGrades"),
    path("updateEntergrades/", views.updateEntergrades, name="updateEntergrades"),
    path("message/", views.show_message, name="message"),
    path("announcement/", views.announcement, name="announcement"),

    # Transcript
    path("generate_transcript/", views.generate_transcript, name="generate_transcript"),
    path("generate_transcript_form/", views.generate_transcript_form, name="generate_transcript_form"),

    # Professor views
    path("submitGradesProf/", views.submitGradesProf, name="submitGradesProf"),
    path("download_template/", views.download_template, name="download_template"),
    path("downloadGrades/", views.downloadGrades, name="downloadGrades"),

    # Dean Academic views
    path("verifyGradesDean/", views.verifyGradesDean, name="verifyGradesDean"),
    path("updateEntergradesDean/", views.updateEntergradesDean, name="updateEnterGradesDean"),
    path("validateDean/", views.validateDean, name="validateDean"),
    path("validateDeanSubmit/", views.validateDeanSubmit, name="validateDeanSubmit"),

    # Student views
    path("checkresult/", views.checkresult, name="checkresult"),
]
