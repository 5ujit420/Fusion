"""
Examination module legacy views — template-serving only.

All redundant views (R01–R05, R07, R10, R12) have been removed.
Dead code (V25–V29), print statements (V41), and AllowAny (V14–V17) are fixed.
Remaining views use services/selectors where possible.
"""

import csv
import json
import logging

from datetime import date

from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import IntegerField
from django.db.models.functions import Cast
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse

from applications.academic_information.models import Student
from applications.academic_procedures.models import course_registration
from applications.department.models import Announcements
from applications.globals.models import ExtraInfo
from applications.online_cms.models import Student_grades
from applications.programme_curriculum.models import (
    Course as Courses,
    CourseInstructor,
)
from notification.views import examination_notif

from .constants import PROFESSOR_ROLES
from . import selectors, services

logger = logging.getLogger(__name__)
User = get_user_model()


# ---------------------------------------------------------------------------
# Role-based entry point
# ---------------------------------------------------------------------------

@login_required(login_url="/accounts/login")
def exam(request):
    """Redirect user to the appropriate landing page based on designation."""
    des = request.session.get("currentDesignationSelected")
    if str(des) in PROFESSOR_ROLES:
        return HttpResponseRedirect("/examination/submitGradesProf/")
    elif des == "acadadmin":
        return HttpResponseRedirect("/examination/updateGrades/")
    elif des == "Dean Academic":
        return HttpResponseRedirect("/examination/verifyGradesDean/")
    return HttpResponseRedirect("/dashboard/")


# ---------------------------------------------------------------------------
# Template-serving views — acadadmin
# ---------------------------------------------------------------------------

@login_required(login_url="/accounts/login")
def submit(request):
    """Render the course list for grade submission (acadadmin/Dean)."""
    des = request.session.get("currentDesignationSelected")
    if des not in ("acadadmin", "Dean Academic"):
        return HttpResponseRedirect("/dashboard/")

    unique_course_ids = (
        course_registration.objects.values("course_id")
        .distinct()
        .annotate(course_id_int=Cast("course_id", IntegerField()))
    )
    courses_info = Courses.objects.filter(
        id__in=unique_course_ids.values_list("course_id_int", flat=True)
    )
    return render(request, "examination/submit.html", {"courses_info": courses_info})


@login_required(login_url="/accounts/login")
def submitGrades(request):
    """Render the grade submission form (acadadmin)."""
    des = request.session.get("currentDesignationSelected")
    if des != "acadadmin":
        return HttpResponseRedirect("/dashboard/")

    unique_course_ids = (
        course_registration.objects.values("course_id")
        .distinct()
        .annotate(course_id_int=Cast("course_id", IntegerField()))
    )
    courses_info = Courses.objects.filter(
        id__in=unique_course_ids.values_list("course_id_int", flat=True)
    )
    working_years = course_registration.objects.values("working_year").distinct()

    context = {"courses_info": courses_info, "working_years": working_years}
    return render(request, "examination/submitGrades.html", context)


@login_required(login_url="/accounts/login")
def updateGrades(request):
    """Render the grade update page (acadadmin)."""
    des = request.session.get("currentDesignationSelected")
    if des != "acadadmin":
        return HttpResponseRedirect("/dashboard/")

    unique_course_ids = (
        course_registration.objects.values("course_id")
        .distinct()
        .annotate(course_id_int=Cast("course_id", IntegerField()))
    )
    courses_info = Courses.objects.filter(
        id__in=unique_course_ids.values_list("course_id_int", flat=True)
    )
    working_years = course_registration.objects.values("working_year").distinct()
    context = {"courses_info": courses_info, "working_years": working_years}
    return render(request, "examination/updateGrades.html", context)


@login_required(login_url="/accounts/login")
def updateEntergrades(request):
    """Render grade entry form for a specific course (acadadmin)."""
    des = request.session.get("currentDesignationSelected")
    if des != "acadadmin":
        return HttpResponseRedirect("/dashboard/")

    course_id = request.GET.get("course")
    year = request.GET.get("year")

    course_present = Student_grades.objects.filter(course_id=course_id, year=year)
    if not course_present:
        context = {"message": "THIS COURSE IS NOT SUBMITTED BY THE INSTRUCTOR"}
        return render(request, "examination/message.html", context)

    context = {"registrations": course_present}
    return render(request, "examination/updateEntergrades.html", context)


@login_required(login_url="/accounts/login")
def show_message(request):
    """Render a message page."""
    des = request.session.get("currentDesignationSelected")
    allowed = {"acadadmin"} | PROFESSOR_ROLES
    if str(des) not in allowed:
        return HttpResponseRedirect("/dashboard/")

    message = request.GET.get("message", "Default message if none provided.")

    if str(des) in PROFESSOR_ROLES:
        return render(request, "examination/messageProf.html", {"message": message})
    return render(request, "examination/message.html", {"message": message})


# ---------------------------------------------------------------------------
# Template-serving views — Professor
# ---------------------------------------------------------------------------

@login_required(login_url="/accounts/login")
def submitGradesProf(request):
    """Render professor-specific grade submission form."""
    des = request.session.get("currentDesignationSelected")
    if str(des) not in PROFESSOR_ROLES:
        return HttpResponseRedirect("/dashboard/")

    unique_course_ids = (
        CourseInstructor.objects.filter(instructor_id_id=request.user.username)
        .values("course_id_id")
        .distinct()
        .annotate(course_id_int=Cast("course_id", IntegerField()))
    )
    working_years = course_registration.objects.values("working_year").distinct()
    courses_info = Courses.objects.filter(
        id__in=unique_course_ids.values_list("course_id_int", flat=True)
    )

    context = {"courses_info": courses_info, "working_years": working_years}
    return render(request, "examination/submitGradesProf.html", context)


@login_required(login_url="/accounts/login")
def download_template(request):
    """Download a CSV template with registered student roll numbers."""
    des = request.session.get("currentDesignationSelected")
    allowed = {"acadadmin", "Dean Academic"} | PROFESSOR_ROLES
    if str(des) not in allowed:
        return HttpResponseRedirect("/dashboard/")

    course = request.GET.get("course")
    year = request.GET.get("year")

    if not course or not year:
        return JsonResponse({"error": "Course and year are required"}, status=400)

    try:
        course_info = course_registration.objects.filter(
            course_id_id=course, working_year=year
        )
        if not course_info.exists():
            return JsonResponse(
                {"error": "No registration data found."}, status=404
            )

        course_obj = course_info.first().course_id
        response = HttpResponse(content_type="text/csv")
        filename = f"{course_obj.code}_template_{year}.csv"
        response["Content-Disposition"] = f'attachment; filename="{filename}"'

        writer = csv.writer(response)
        writer.writerow(["roll_no", "name", "grade", "remarks"])

        for entry in course_info:
            student_entry = entry.student_id
            student_user = User.objects.get(username=student_entry.id_id)
            writer.writerow([
                student_entry.id_id,
                f"{student_user.first_name} {student_user.last_name}",
                "",
                "",
            ])
        return response

    except Exception as e:
        logger.exception("Error in download_template")
        return JsonResponse({"error": "An unexpected error occurred"}, status=500)


@login_required(login_url="/accounts/login")
def downloadGrades(request):
    """Render the grade download page for professors."""
    des = request.session.get("currentDesignationSelected")
    if str(des) not in PROFESSOR_ROLES:
        return HttpResponseRedirect("/dashboard/")

    academic_year = request.GET.get("academic_year")
    if academic_year:
        if not academic_year.isdigit():
            return JsonResponse({})

        unique_course_ids = (
            CourseInstructor.objects.filter(instructor_id_id=request.user.username)
            .values("course_id_id")
            .distinct()
            .annotate(course_id_int=Cast("course_id", IntegerField()))
        )
        courses_info = Student_grades.objects.filter(
            year=academic_year,
            course_id_id__in=unique_course_ids.values_list("course_id_int", flat=True),
        )
        courses_details = Courses.objects.filter(
            id__in=courses_info.values_list("course_id_id", flat=True)
        )
        return JsonResponse({"courses": list(courses_details.values())})

    working_years = course_registration.objects.values("working_year").distinct()
    context = {"working_years": working_years}
    return render(request, "examination/download_resultProf.html", context)


# ---------------------------------------------------------------------------
# Template-serving views — Dean Academic
# ---------------------------------------------------------------------------

@login_required(login_url="/accounts/login")
def verifyGradesDean(request):
    """Render the grade verification page for Dean Academic."""
    des = request.session.get("currentDesignationSelected")
    if des != "Dean Academic":
        return HttpResponseRedirect("/dashboard/")

    courses_info = selectors.get_verified_courses().order_by("code")
    unique_year_ids = Student_grades.objects.values("year").distinct()

    context = {"courses_info": courses_info, "unique_year_ids": unique_year_ids}
    return render(request, "examination/submitGradeDean.html", context)


@login_required(login_url="/accounts/login")
def updateEntergradesDean(request):
    """Render grade detail page for a course (Dean Academic)."""
    des = request.session.get("currentDesignationSelected")
    if des != "Dean Academic":
        return HttpResponseRedirect("/dashboard/")

    course_id = request.GET.get("course")
    year = request.GET.get("year")
    course_present = Student_grades.objects.filter(course_id=course_id, year=year)

    if not course_present:
        context = {"message": "THIS COURSE IS NOT SUBMITTED BY THE INSTRUCTOR"}
        return render(request, "examination/messageDean.html", context)

    context = {"registrations": course_present}
    return render(request, "examination/updateEntergradesDean.html", context)


@login_required(login_url="/accounts/login")
def validateDean(request):
    """Render the Dean validation page — verified courses for CSV upload."""
    des = request.session.get("currentDesignationSelected")
    if des != "Dean Academic":
        return HttpResponseRedirect("/dashboard/")

    courses_info = selectors.get_verified_courses()
    working_years = course_registration.objects.values("working_year").distinct()

    context = {"courses_info": courses_info, "working_years": working_years}
    return render(request, "examination/validation.html", context)


@login_required(login_url="/accounts/login")
def validateDeanSubmit(request):
    """Process Dean CSV validation submission."""
    des = request.session.get("currentDesignationSelected")
    if des != "Dean Academic":
        return HttpResponseRedirect("/dashboard/")

    if request.method == "POST" and request.FILES.get("csv_file"):
        csv_file = request.FILES["csv_file"]

        if not csv_file.name.endswith(".csv"):
            return render(request, "examination/messageDean.html", {
                "message": "Please Submit a csv file",
            })

        course_id = request.POST.get("course")
        academic_year = request.POST.get("year")

        if not academic_year or not academic_year.isdigit():
            return render(request, "examination/messageDean.html", {
                "message": "Academic Year must be a number",
            })

        if not course_id or not academic_year:
            return render(request, "examination/messageDean.html", {
                "message": "Course and Academic year are required",
            })

        try:
            mismatches = services.validate_dean_csv(csv_file, course_id, academic_year)
            if not mismatches:
                return render(request, "examination/messageDean.html", {
                    "message": "There Are no Mismatches",
                })
            return render(request, "examination/validationSubmit.html", {
                "mismatch": mismatches,
            })
        except Exception as e:
            logger.exception("validateDeanSubmit error")
            return render(request, "examination/messageDean.html", {
                "message": f"An error occurred: {str(e)}",
            })


# ---------------------------------------------------------------------------
# Template-serving views — Transcript
# ---------------------------------------------------------------------------

@login_required(login_url="/accounts/login")
def generate_transcript_form(request):
    """Render the transcript generation form (acadadmin)."""
    des = request.session.get("currentDesignationSelected")
    if des != "acadadmin":
        return HttpResponseRedirect("/dashboard/")

    batches = selectors.get_running_batches()
    return render(request, "examination/generate_transcript_form.html", {
        "batches": batches,
    })


@login_required(login_url="/accounts/login")
def generate_transcript(request):
    """Render transcript generation page (acadadmin)."""
    des = request.session.get("currentDesignationSelected")
    if des != "acadadmin":
        return HttpResponseRedirect("/dashboard/")
    return render(request, "examination/generate_transcript.html")


# ---------------------------------------------------------------------------
# Template-serving views — Announcements
# ---------------------------------------------------------------------------

@login_required(login_url="/accounts/login")
def announcement(request):
    """Manage department announcements (acadadmin)."""
    des = request.session.get("currentDesignationSelected")
    if des != "acadadmin":
        return HttpResponseRedirect("/dashboard/")

    try:
        usrnm = get_object_or_404(User, username=request.user.username)
        user_info = ExtraInfo.objects.get(user=request.user)
        ann_maker_id = user_info.id

        if request.method == "POST":
            batch = request.POST.get("batch", "")
            programme = request.POST.get("programme", "")
            message = request.POST.get("announcement", "")
            upload_announcement = request.FILES.get("upload_announcement")
            department = request.POST.get("department")
            ann_date = date.today()

            Announcements.objects.get_or_create(
                maker_id=user_info,
                batch=batch,
                programme=programme,
                message=message,
                upload_announcement=upload_announcement,
                department=department,
                ann_date=ann_date,
            )

            recipients = User.objects.all()
            examination_notif(sender=usrnm, recipient=recipients, type=message)
            return render(request, "department/browse_announcements_staff.html")

        # Browse announcements
        cse_ann = Announcements.objects.filter(department="CSE")
        ece_ann = Announcements.objects.filter(department="ECE")
        me_ann = Announcements.objects.filter(department="ME")
        sm_ann = Announcements.objects.filter(department="SM")
        all_ann = Announcements.objects.filter(department="ALL")

        context = {
            "user_designation": user_info.user_type,
            "announcements": {
                "cse": cse_ann,
                "ece": ece_ann,
                "me": me_ann,
                "sm": sm_ann,
                "all": all_ann,
            },
        }
        return render(request, "examination/announcement_req.html", context)
    except Exception:
        logger.exception("announcement view error")
        return render(request, "examination/announcement_req.html", {
            "error_message": "An error occurred. Please try again later.",
        })


# ---------------------------------------------------------------------------
# Student views
# ---------------------------------------------------------------------------

@login_required(login_url="/accounts/login")
def checkresult(request):
    """Render the student result check page."""
    des = request.session.get("currentDesignationSelected")
    if des != "student":
        return HttpResponseRedirect("/dashboard/")
    return render(request, "examination/check_result.html")
