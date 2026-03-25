"""
Examination module API views — thin request handlers.

All business logic lives in services.py, all DB queries in selectors.py,
all authorization in permissions.py.  Views only parse input, delegate,
and format responses.

Fixes audit violations: V01–V42, R01–R12.
"""

import logging
import traceback
from collections import OrderedDict
from decimal import Decimal, ROUND_HALF_UP

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import IntegerField
from django.db.models.functions import Cast
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes as perm_classes
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from applications.academic_information.models import Student
from applications.academic_procedures.models import course_registration
from applications.online_cms.models import Student_grades
from applications.programme_curriculum.models import (
    Course as Courses,
    Batch,
    CourseInstructor,
)
from applications.examination.models import authentication, ResultAnnouncement

from ..constants import (
    grade_conversion,
    ALLOWED_GRADES,
    ALL_GRADE_LETTERS,
    UG_PROGRAMMES,
    PG_PROGRAMMES,
    MAX_CSV_FILE_SIZE,
    PROFESSOR_ROLES,
)
from ..permissions import (
    IsAcadAdmin,
    IsAcadAdminOrDean,
    IsAcadAdminOrProfessor,
    IsAcadAdminOrDeanOrProfessor,
    IsDeanAcademic,
    IsProfessor,
)
from .. import selectors, services

logger = logging.getLogger(__name__)
User = get_user_model()


# ===========================================================================
# Routing / role-dispatch endpoint
# ===========================================================================

@api_view(["POST"])
@perm_classes([IsAuthenticated])
def exam_view(request):
    """Differentiate roles and provide redirection links."""
    role = request.data.get("Role")
    if not role:
        return Response(
            {"error": "Role parameter is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if role in PROFESSOR_ROLES:
        return Response({"redirect_url": "/examination/submitGradesProf/"})
    elif role == "acadadmin":
        return Response({"redirect_url": "/examination/updateGrades/"})
    elif role == "Dean Academic":
        return Response({"redirect_url": "/examination/verifyGradesDean/"})
    return Response({"redirect_url": "/dashboard/"})


# ===========================================================================
# Academic-year / semester list endpoints
# ===========================================================================

class UniqueStudentGradeYearsView(APIView):
    """GET: Return all distinct academic_year values from Student_grades."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        years = list(selectors.get_unique_academic_years())
        return Response({"academic_years": years}, status=status.HTTP_200_OK)


class StudentSemesterListView(APIView):
    """GET: Return semesters for which the authenticated student has grades."""

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        roll_number = request.user.username
        qs = (
            Student_grades.objects.filter(roll_no=roll_number)
            .values_list("semester", "semester_type")
            .distinct()
            .order_by("semester")
        )
        unique = OrderedDict()
        for sem_no, sem_type in qs:
            label = services.make_label(sem_no, sem_type or "")
            unique[(sem_no, sem_type)] = label

        semesters = [
            {"semester_no": no, "semester_type": typ, "label": lbl}
            for (no, typ), lbl in unique.items()
        ]
        return JsonResponse({"success": True, "semesters": semesters})


# ===========================================================================
# Grade CRUD endpoints — acadadmin
# ===========================================================================

class UpdateGradesAPI(APIView):
    """
    Fetch unverified courses for acadadmin.
    Replaces the legacy ``updateGrades`` FBV (R10).
    """

    permission_classes = [IsAuthenticated, IsAcadAdmin]

    def post(self, request):
        academic_year = request.data.get("academic_year")
        semester_type = request.data.get("semester_type")

        if not academic_year or not semester_type:
            return Response(
                {"error": "Academic year and semester type are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        working_year, _ = services.parse_academic_year(academic_year, semester_type)

        course_ids = (
            course_registration.objects.filter(
                session=academic_year, semester_type=semester_type
            )
            .values_list("course_id", flat=True)
            .distinct()
        )
        courses_info = Courses.objects.filter(id__in=course_ids).order_by("code")

        return Response(
            {"courses_info": list(courses_info.values())},
            status=status.HTTP_200_OK,
        )


class UpdateEnterGradesAPI(APIView):
    """Fetch student grade records for a specific course (acadadmin)."""

    permission_classes = [IsAuthenticated, IsAcadAdmin]

    def post(self, request):
        course_id = request.data.get("course")
        academic_year = request.data.get("year")
        semester_type = request.data.get("semester_type")

        qs = selectors.get_grades_for_course(course_id, academic_year, semester_type)
        if not qs.exists():
            return Response(
                {"message": "THIS COURSE IS NOT SUBMITTED BY THE INSTRUCTOR"},
                status=status.HTTP_404_NOT_FOUND,
            )

        verification = qs.first().verified
        if verification:
            return Response({"message": "THIS COURSE IS VERIFIED"})

        return Response(
            {"registrations": list(qs.values())},
            status=status.HTTP_200_OK,
        )


class ModerateStudentGradesAPI(APIView):
    """Verify (moderate) student grades — acadadmin or Dean."""

    permission_classes = [IsAuthenticated, IsAcadAdminOrDean]

    def post(self, request):
        student_ids = request.data.getlist("student_ids[]")
        semester_ids = request.data.getlist("semester_ids[]")
        course_ids = request.data.getlist("course_ids[]")
        grades = request.data.getlist("grades[]")
        allow_resubmission = request.data.get("allow_resubmission", "NO") == "YES"

        try:
            services.moderate_student_grades(
                student_ids, semester_ids, course_ids, grades, allow_resubmission
            )
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            {"message": "Grades moderated successfully."},
            status=status.HTTP_200_OK,
        )


class UploadGradesAPI(APIView):
    """Upload grades CSV — acadadmin."""

    permission_classes = [IsAuthenticated, IsAcadAdmin]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        csv_file = request.FILES.get("csv_file")
        course_id = request.data.get("course_id")
        academic_year = request.data.get("academic_year")
        semester_type = request.data.get("semester_type")

        if not course_id or not academic_year or not semester_type:
            return Response(
                {"error": "Course ID, Academic Year, and Semester Type are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            msg = services.upload_grades_from_csv(
                csv_file=csv_file,
                course_id=course_id,
                academic_year=academic_year,
                semester_type=semester_type,
            )
            return Response({"message": msg}, status=status.HTTP_200_OK)
        except PermissionError as e:
            return Response({"error": str(e)}, status=status.HTTP_403_FORBIDDEN)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


# ===========================================================================
# Professor endpoints
# ===========================================================================

class SubmitGradesProfAPI(APIView):
    """Fetch courses assigned to an instructor for a given session."""

    permission_classes = [IsAuthenticated, IsProfessor]

    def post(self, request):
        academic_year = request.data.get("academic_year")
        semester_type = request.data.get("semester_type")
        programme_type = request.data.get("programme_type")

        if not academic_year or not semester_type:
            return Response(
                {"success": False, "error": "Academic year and semester type are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        instructor_id = request.user.username
        working_year, _ = services.parse_academic_year(academic_year, semester_type)

        unique_course_ids = selectors.get_instructor_courses(
            instructor_id, working_year, semester_type
        )
        courses_query = Courses.objects.filter(
            id__in=unique_course_ids.values_list("course_id_int", flat=True)
        )

        student_ids_with_programme = None
        if programme_type:
            programme_list = selectors.get_programme_list(programme_type)
            if programme_list:
                student_ids_with_programme = Student.objects.filter(
                    programme__in=programme_list
                ).values_list("id", flat=True)

                course_ids_with_programme = (
                    course_registration.objects.filter(
                        course_id__in=courses_query.values_list("id", flat=True),
                        student_id__in=student_ids_with_programme,
                        session=academic_year,
                        semester_type=semester_type,
                    )
                    .values_list("course_id", flat=True)
                    .distinct()
                )
                courses_query = courses_query.filter(id__in=course_ids_with_programme)

        courses_data = []
        for course in courses_query.values():
            course_regs = course_registration.objects.filter(
                course_id=course["id"],
                session=academic_year,
                semester_type=semester_type,
            )
            if programme_type and student_ids_with_programme is not None:
                course_regs = course_regs.filter(student_id__in=student_ids_with_programme)
            course["student_count"] = course_regs.count()
            course["has_students"] = course["student_count"] > 0
            course["programme_type"] = programme_type
            courses_data.append(course)

        return Response({"courses_info": courses_data}, status=status.HTTP_200_OK)


class UploadGradesProfAPI(APIView):
    """Upload grades CSV by the assigned instructor."""

    permission_classes = [IsAuthenticated, IsProfessor]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        csv_file = request.FILES.get("csv_file")
        course_id = request.data.get("course_id")
        academic_year = request.data.get("academic_year")
        semester_type = request.data.get("semester_type")
        programme_type = request.data.get("programme_type")

        if not (course_id and academic_year and semester_type):
            return Response(
                {"error": "Course ID, Academic Year, and Semester Type are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            msg = services.upload_grades_from_csv(
                csv_file=csv_file,
                course_id=course_id,
                academic_year=academic_year,
                semester_type=semester_type,
                instructor_id=request.user.username,
                programme_type=programme_type,
            )
            return Response({"message": msg}, status=status.HTTP_200_OK)
        except PermissionError as e:
            return Response({"error": str(e)}, status=status.HTTP_403_FORBIDDEN)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class DownloadGradesAPI(APIView):
    """Return list of courses that have submitted grades for an instructor."""

    permission_classes = [IsAuthenticated, IsProfessor]

    def post(self, request):
        academic_year = request.data.get("academic_year")
        semester_type = request.data.get("semester_type")
        programme_type = request.data.get("programme_type")

        if not academic_year or not semester_type:
            return Response(
                {"success": False, "error": "Academic year and semester type are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            working_year, _ = services.parse_academic_year(academic_year, semester_type)
            instructor_id = request.user.username

            unique_course_ids = selectors.get_instructor_courses(
                instructor_id, working_year, semester_type
            )

            grades_qs = Student_grades.objects.filter(
                academic_year=academic_year,
                semester_type=semester_type,
                course_id_id__in=unique_course_ids.values_list("course_id_int", flat=True),
            )

            if programme_type:
                student_ids = selectors.get_students_by_programme_type(programme_type)
                if not student_ids.exists():
                    return Response(
                        {"error": "Invalid programme_type. Must be 'UG' or 'PG'."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                grades_qs = grades_qs.filter(roll_no__in=student_ids)

            course_ids = grades_qs.values_list("course_id_id", flat=True).distinct()
            courses_details = Courses.objects.filter(id__in=course_ids)

            return Response(
                {"courses": list(courses_details.values())},
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            logger.exception("DownloadGradesAPI error")
            return Response(
                {"error": "Internal server error."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class PreviewGradesAPI(APIView):
    """Preview a CSV file against registered students before uploading."""

    permission_classes = [IsAuthenticated, IsAcadAdminOrProfessor]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        csv_file = request.FILES.get("csv_file")
        if not csv_file:
            return Response(
                {"error": "No file provided. Please upload a CSV file."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not csv_file.name.endswith(".csv"):
            return Response(
                {"error": "Invalid file format. Please upload a CSV file."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        course_id = request.data.get("course_id")
        academic_year = request.data.get("academic_year")
        semester_type = request.data.get("semester_type")
        programme_type = request.data.get("programme_type")

        if not course_id or not academic_year or not semester_type:
            return Response(
                {"error": "course_id, academic_year and semester_type are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        registrations = course_registration.objects.filter(
            course_id=course_id,
            session=academic_year,
            semester_type=semester_type,
        )

        if programme_type:
            student_ids = selectors.get_students_by_programme_type(programme_type)
            if not student_ids.exists():
                return Response(
                    {"error": "Invalid programme_type. Must be 'UG' or 'PG'."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            registrations = registrations.filter(student_id__in=student_ids)

        registered_rollnos = set()
        for reg in registrations.select_related("student_id"):
            if hasattr(reg.student_id, "id_id"):
                registered_rollnos.add(reg.student_id.id_id)
            else:
                registered_rollnos.add(str(reg.student_id_id))

        try:
            from io import StringIO
            decoded_file = csv_file.read().decode("utf-8")
            io_string = StringIO(decoded_file)
            import csv
            reader = csv.DictReader(io_string)
        except Exception as e:
            return Response(
                {"error": f"Error reading CSV file: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        required_columns = ["roll_no", "name", "grade", "remarks", "semester"]
        if not all(col in (reader.fieldnames or []) for col in required_columns):
            return Response(
                {"error": f"CSV file must contain: {', '.join(required_columns)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        preview_rows = []
        for row in reader:
            roll_no = row["roll_no"]
            preview_rows.append({
                "roll_no": roll_no,
                "name": row["name"],
                "branch": row.get("branch", ""),
                "grades": row["grade"],
                "remarks": row["remarks"],
                "semester": row["semester"],
                "is_registered": roll_no in registered_rollnos,
            })

        return Response({"preview": preview_rows}, status=status.HTTP_200_OK)


# ===========================================================================
# PDF / Excel generation
# ===========================================================================

class GeneratePDFAPI(APIView):
    """Generate faculty course grade sheet PDF."""

    permission_classes = [IsAuthenticated, IsProfessor]

    def post(self, request):
        try:
            course_id = request.data.get("course_id")
            academic_year = request.data.get("academic_year")
            semester_type = request.data.get("semester_type")
            programme_type = request.data.get("programme_type")

            course_info = get_object_or_404(Courses, id=course_id)
            working_year, _ = services.parse_academic_year(academic_year, semester_type)

            grades = selectors.get_grades_for_course(course_id, academic_year, semester_type)

            ci = CourseInstructor.objects.filter(
                course_id_id=course_id,
                year=working_year,
                semester_type=semester_type,
                instructor_id_id=request.user.username,
            )
            if not ci.exists():
                return Response(
                    {"success": False, "error": "Course not found."},
                    status=status.HTTP_404_NOT_FOUND,
                )

            instructor = f"{request.user.first_name} {request.user.last_name}"

            return services.generate_course_grade_pdf(
                course_info, grades, instructor, academic_year,
                semester_type=semester_type, programme_type=programme_type,
            )
        except Exception as e:
            logger.exception("GeneratePDFAPI error")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class GenerateStudentResultPDFAPI(APIView):
    """Generate student result/transcript PDF."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            data = request.data
            student_info = data.get("student_info", {})
            courses = data.get("courses", [])

            if not student_info or not courses:
                # Fetch from database
                roll_number = request.user.username
                semester_no = data.get("semester_no")
                semester_type = data.get("semester_type")

                if semester_no is None or semester_type is None:
                    return JsonResponse(
                        {"success": False, "message": "semester_no and semester_type are required."},
                        status=400,
                    )

                try:
                    student = Student.objects.get(id_id=roll_number)
                except Student.DoesNotExist:
                    return JsonResponse(
                        {"success": False, "message": "Student record not found."},
                        status=404,
                    )

                ann = selectors.get_result_announcement(student.batch_id, semester_no)
                if not ann or not ann.announced:
                    return JsonResponse(
                        {"success": False, "message": "Results not announced yet."},
                        status=200,
                    )

                grades_info = selectors.get_student_grades_for_semester(
                    roll_number, semester_no, semester_type
                )

                academic_year = grades_info.first().academic_year if grades_info.exists() else None

                spi, su, _ = services.calculate_spi_for_student(student, semester_no, semester_type)
                cpi, tu, _ = services.calculate_cpi_for_student(student, semester_no, semester_type)

                student_info = {
                    "name": f"{student.id.user.first_name} {student.id.user.last_name}".strip(),
                    "rollNumber": student.id.user.username,
                    "roll_number": student.id.user.username,
                    "programme": student.programme,
                    "batch": str(student.batch_id) if student.batch_id else str(student.batch),
                    "branch": student.id.department.name if student.id.department else "",
                    "department": student.id.department.name if student.id.department else "",
                    "semester": student.curr_semester_no,
                    "academicYear": academic_year or "",
                    "academic_year": academic_year or "",
                }

                courses = [
                    {
                        "coursecode": g.course_id.code,
                        "courseid": g.course_id.id,
                        "coursename": g.course_id.name,
                        "credits": g.course_id.credit,
                        "grade": g.grade,
                        "points": Decimal(str(grade_conversion.get(g.grade, 0) * 10)).quantize(
                            Decimal("0.1"), rounding=ROUND_HALF_UP
                        ),
                    }
                    for g in grades_info
                ]
            else:
                spi = float(data.get("spi", 0))
                cpi = float(data.get("cpi", 0))
                su = int(data.get("su", 0))
                tu = int(data.get("tu", 0))

            semester_no = data.get("semester_no", 1)
            semester_type = data.get("semester_type", "")
            semester_label = data.get("semester_label", "")

            is_transcript = (
                data.get("is_transcript", False)
                or request.path.find("transcript") != -1
                or data.get("document_type") == "transcript"
            )

            return services.generate_student_result_pdf(
                student_info, courses, spi, cpi, su, tu,
                semester_no, semester_type, semester_label,
                is_transcript=is_transcript,
            )
        except Exception as e:
            logger.exception("GenerateStudentResultPDFAPI error")
            return JsonResponse({"error": f"PDF generation failed: {str(e)}"}, status=500)


class GenerateResultAPI(APIView):
    """Generate an Excel result sheet for a batch/branch/semester."""

    permission_classes = [IsAuthenticated, IsAcadAdmin]

    def post(self, request):
        try:
            data = request.data
            semester = data.get("semester")
            branch = data.get("specialization")
            batch = data.get("batch")
            semester_type = data.get("semester_type")
            academic_year = data.get("academic_year")

            wb = services.generate_result_excel(
                semester, branch, batch,
                semester_type=semester_type,
                academic_year=academic_year,
            )

            response = HttpResponse(
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            response["Content-Disposition"] = 'attachment; filename="student_grades.xlsx"'
            wb.save(response)
            return response
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.exception("GenerateResultAPI error")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class GenerateTranscript(APIView):
    """Generate a transcript Excel for a student up to a given semester."""

    permission_classes = [IsAuthenticated, IsAcadAdmin]

    def post(self, request):
        try:
            import json
            data = json.loads(request.body)
        except (json.JSONDecodeError, Exception):
            return Response(
                {"error": "Invalid JSON data."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        student_id = data.get("student")
        selected_semester = data.get("semester")
        semester_type = data.get("semester_type", "")
        batch_name = data.get("batch")
        branch = data.get("specialization")

        if not student_id or selected_semester is None:
            return Response(
                {"error": "student and semester are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            student = Student.objects.get(id_id=student_id)
        except Student.DoesNotExist:
            return Response(
                {"error": "Student not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        selected_semester = int(selected_semester)

        # Get registrations and grades up to selected semester
        registrations = (
            course_registration.objects.select_related("course_id", "semester_id")
            .filter(student_id=student, semester_id__semester_no__lte=selected_semester)
        )

        all_semester_data = {}
        for reg in registrations:
            sem_no = reg.semester_id.semester_no
            sem_type = getattr(reg, "semester_type", "")
            key = (sem_no, sem_type)

            if key not in all_semester_data:
                all_semester_data[key] = {
                    "semester_no": sem_no,
                    "semester_type": sem_type,
                    "courses": [],
                }

            related = services.gather_related_registrations(reg, selected_semester)
            course = reg.course_id
            grade_obj = (
                Student_grades.objects.filter(
                    roll_no=student_id, course_id=course, semester=sem_no
                ).first()
            )

            course_data = {
                "code": course.code,
                "name": course.name,
                "credit": course.credit,
                "grade": grade_obj.grade if grade_obj else "N/A",
                "remarks": grade_obj.remarks if grade_obj else "",
            }
            all_semester_data[key]["courses"].append(course_data)

        # Build Excel workbook
        wb = Workbook()
        ws = wb.active
        ws.title = "Transcript"

        ws["A1"] = "Student ID"
        ws["B1"] = student_id
        ws["A2"] = "Name"
        ws["B2"] = f"{student.id.user.first_name} {student.id.user.last_name}"

        row_idx = 4
        for (sem_no, sem_type), sem_data in sorted(all_semester_data.items()):
            ws.cell(row=row_idx, column=1).value = f"Semester {sem_no}"
            ws.cell(row=row_idx, column=1).font = Font(bold=True)
            row_idx += 1

            ws.cell(row=row_idx, column=1).value = "Course Code"
            ws.cell(row=row_idx, column=2).value = "Course Name"
            ws.cell(row=row_idx, column=3).value = "Credits"
            ws.cell(row=row_idx, column=4).value = "Grade"
            ws.cell(row=row_idx, column=5).value = "Remarks"
            for c in range(1, 6):
                ws.cell(row=row_idx, column=c).font = Font(bold=True)
            row_idx += 1

            for cd in sem_data["courses"]:
                ws.cell(row=row_idx, column=1).value = cd["code"]
                ws.cell(row=row_idx, column=2).value = cd["name"]
                ws.cell(row=row_idx, column=3).value = cd["credit"]
                ws.cell(row=row_idx, column=4).value = cd["grade"]
                ws.cell(row=row_idx, column=5).value = cd["remarks"]
                row_idx += 1

            spi, su, _ = services.calculate_spi_for_student(student, sem_no, sem_type)
            cpi, tu, _ = services.calculate_cpi_for_student(student, sem_no, sem_type)
            ws.cell(row=row_idx, column=1).value = f"SPI: {spi}"
            ws.cell(row=row_idx, column=2).value = f"CPI: {cpi}"
            row_idx += 2

        response = HttpResponse(
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response["Content-Disposition"] = f'attachment; filename="transcript_{student_id}.xlsx"'
        wb.save(response)
        return response


class DownloadTemplateAPI(APIView):
    """Download a CSV template pre-filled with registered student roll numbers."""

    permission_classes = [IsAuthenticated, IsAcadAdminOrDeanOrProfessor]

    def post(self, request):
        course_id = request.data.get("course_id")
        academic_year = request.data.get("academic_year")
        semester_type = request.data.get("semester_type")
        programme_type = request.data.get("programme_type")

        if not course_id or not academic_year or not semester_type:
            return Response(
                {"error": "course_id, academic_year and semester_type are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        working_year, _ = services.parse_academic_year(academic_year, semester_type)

        regs = course_registration.objects.filter(
            course_id_id=course_id,
            working_year=working_year,
            semester_type=semester_type,
        )

        if programme_type:
            student_ids = selectors.get_students_by_programme_type(programme_type)
            regs = regs.filter(student_id__in=student_ids)

        if not regs.exists():
            return Response(
                {"error": "No registration data found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        course_obj = regs.first().course_id
        import csv
        response = HttpResponse(content_type="text/csv")
        filename = f"{course_obj.code}_template_{working_year}.csv"
        response["Content-Disposition"] = f'attachment; filename="{filename}"'

        writer = csv.writer(response)
        writer.writerow(["roll_no", "name", "grade", "remarks", "semester"])

        for entry in regs:
            student_entry = entry.student_id
            student_user = User.objects.get(username=student_entry.id_id)
            writer.writerow([
                student_entry.id_id,
                f"{student_user.first_name} {student_user.last_name}",
                "",
                "",
                "",
            ])

        return response


# ===========================================================================
# Dean Academic endpoints
# ===========================================================================

class VerifyGradesDeanView(APIView):
    """Fetch courses with submitted grades for Dean Academic to verify."""

    permission_classes = [IsAuthenticated, IsDeanAcademic]

    def post(self, request):
        academic_year = request.data.get("academic_year")
        semester_type = request.data.get("semester_type")

        if not academic_year or not semester_type:
            return Response(
                {"error": "Both academic_year and semester_type are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        qs = Student_grades.objects.filter(
            academic_year=academic_year,
            semester_type=semester_type,
        )
        course_ids = qs.values_list("course_id_id", flat=True).distinct()
        courses = Courses.objects.filter(id__in=course_ids).order_by("code")

        return Response(
            {"courses_info": list(courses.values("id", "code", "name"))},
            status=status.HTTP_200_OK,
        )


class UpdateEnterGradesDeanView(APIView):
    """Fetch all student grades for a course (Dean Academic)."""

    permission_classes = [IsAuthenticated, IsDeanAcademic]

    def post(self, request):
        course_id = request.data.get("course")
        year = request.data.get("year")
        semester_type = request.data.get("semester_type")

        qs = Student_grades.objects.filter(
            course_id=course_id, academic_year=year, semester_type=semester_type
        )
        if not qs.exists():
            return Response(
                {"message": "THIS COURSE IS NOT SUBMITTED BY THE INSTRUCTOR"}
            )

        return Response(
            {"registrations": list(qs.values())},
            status=status.HTTP_200_OK,
        )


class ValidateDeanView(APIView):
    """Fetch verified courses and working years for Dean validation."""

    permission_classes = [IsAuthenticated, IsDeanAcademic]

    def post(self, request):
        courses_info = selectors.get_verified_courses()
        working_years = selectors.get_unique_registration_years()

        return Response(
            {
                "courses_info": list(courses_info.values()),
                "working_years": list(working_years),
            },
            status=status.HTTP_200_OK,
        )


class ValidateDeanSubmitView(APIView):
    """Validate a Dean's CSV against stored grades for mismatches."""

    permission_classes = [IsAuthenticated, IsDeanAcademic]

    def post(self, request):
        if "csv_file" not in request.FILES:
            return Response(
                {"error": "CSV file is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        csv_file = request.FILES["csv_file"]
        if not csv_file.name.endswith(".csv"):
            return Response(
                {"error": "Please submit a valid CSV file."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        course_id = request.data.get("course")
        academic_year = request.data.get("year")

        if not course_id or not academic_year:
            return Response(
                {"error": "Course and Academic Year are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            mismatches = services.validate_dean_csv(csv_file, course_id, academic_year)
            if not mismatches:
                return Response(
                    {"message": "There are no mismatches."},
                    status=status.HTTP_200_OK,
                )
            return Response(
                {"mismatches": mismatches},
                status=status.HTTP_200_OK,
            )
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.exception("ValidateDeanSubmitView error")
            return Response(
                {"error": f"An error occurred: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


# ===========================================================================
# Student endpoints
# ===========================================================================

class CheckResultView(APIView):
    """Retrieve student result including grades, SPI, and CPI."""

    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        roll_number = request.user.username
        semester_no = request.data.get("semester_no")
        semester_type = request.data.get("semester_type")

        if semester_no is None or semester_type is None:
            return JsonResponse(
                {"success": False, "message": "semester_no and semester_type are required."},
                status=400,
            )

        try:
            student = Student.objects.get(id_id=roll_number)
        except Student.DoesNotExist:
            return JsonResponse(
                {"success": False, "message": "Student record not found."},
                status=404,
            )

        ann = selectors.get_result_announcement(student.batch_id, semester_no)
        if not ann or not ann.announced:
            return JsonResponse(
                {"success": False, "message": "Results not announced yet."},
                status=200,
            )

        grades_info = selectors.get_student_grades_for_semester(
            roll_number, semester_no, semester_type
        )

        academic_year = grades_info.first().academic_year if grades_info.exists() else None

        spi, su, _ = services.calculate_spi_for_student(student, semester_no, semester_type)
        cpi, tu, _ = services.calculate_cpi_for_student(student, semester_no, semester_type)

        student_info = {
            "name": f"{student.id.user.first_name} {student.id.user.last_name}".strip(),
            "rollNumber": student.id.user.username,
            "roll_number": student.id.user.username,
            "programme": student.programme,
            "batch": str(student.batch_id) if student.batch_id else str(student.batch),
            "branch": student.id.department.name if student.id.department else "",
            "department": student.id.department.name if student.id.department else "",
            "semester": student.curr_semester_no,
            "academicYear": academic_year or "",
            "academic_year": academic_year or "",
        }

        return JsonResponse({
            "success": True,
            "student_info": student_info,
            "courses": [
                {
                    "coursecode": g.course_id.code,
                    "courseid": g.course_id.id,
                    "coursename": g.course_id.name,
                    "credits": g.course_id.credit,
                    "grade": g.grade,
                    "points": Decimal(str(grade_conversion.get(g.grade, 0) * 10)).quantize(
                        Decimal("0.1"), rounding=ROUND_HALF_UP
                    ),
                }
                for g in grades_info
            ],
            "spi": spi,
            "cpi": cpi,
            "su": su,
            "tu": tu,
        })


# ===========================================================================
# Result Announcement management (acadadmin / Dean)
# ===========================================================================

class ResultAnnouncementListAPI(APIView):
    """GET: List all result announcements and available batches."""

    permission_classes = [IsAuthenticated, IsAcadAdminOrDean]

    def get(self, request):
        announcements = selectors.get_all_announcements()
        ann_data = []
        for ann in announcements:
            batch = ann.batch
            batch_label = f"{batch.name} - {batch.discipline.acronym} {batch.year}"
            ann_data.append({
                "id": ann.id,
                "batch": {
                    "id": batch.id,
                    "name": batch.name,
                    "discipline": batch.discipline.acronym,
                    "year": batch.year,
                    "label": batch_label,
                },
                "semester": ann.semester,
                "announced": ann.announced,
                "created_at": ann.created_at,
            })

        batch_objs = selectors.get_running_batches()
        batch_options = []
        for b in batch_objs:
            label = f"{b.name} - {b.discipline.acronym} {b.year}"
            batch_options.append({"id": b.id, "label": label})

        return Response(
            {"announcements": ann_data, "batches": batch_options},
            status=status.HTTP_200_OK,
        )


class UpdateAnnouncementAPI(APIView):
    """POST: Toggle announcement status."""

    permission_classes = [IsAuthenticated, IsAcadAdminOrDean]

    def post(self, request):
        announcement_id = request.data.get("id")
        announced = request.data.get("announced")
        try:
            ann = ResultAnnouncement.objects.get(id=announcement_id)
            ann.announced = announced
            ann.save()
            return Response({"success": True}, status=status.HTTP_200_OK)
        except ResultAnnouncement.DoesNotExist:
            return Response(
                {"error": "Announcement not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            logger.exception("UpdateAnnouncementAPI error")
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class CreateAnnouncementAPI(APIView):
    """POST: Create or retrieve a result announcement."""

    permission_classes = [IsAuthenticated, IsAcadAdminOrDean]

    def post(self, request):
        try:
            batch_id = request.data.get("batch")
            semester = request.data.get("semester")
            if not batch_id or not semester:
                return Response(
                    {"error": "Batch and Semester are required."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            batch_obj = Batch.objects.filter(id=batch_id).first()
            if not batch_obj:
                return Response(
                    {"error": "Batch not found."},
                    status=status.HTTP_404_NOT_FOUND,
                )

            ann, created = ResultAnnouncement.objects.get_or_create(
                batch=batch_obj,
                semester=semester,
                defaults={"announced": False},
            )

            batch_label = f"{batch_obj.name} - {batch_obj.discipline.acronym} {batch_obj.year}"
            data = {
                "id": ann.id,
                "batch": {"id": batch_obj.id, "label": batch_label},
                "semester": ann.semester,
                "announced": ann.announced,
                "created_at": ann.created_at,
            }

            return Response(
                data,
                status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
            )
        except Exception as e:
            logger.exception("CreateAnnouncementAPI error")
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


# ===========================================================================
# Grade Status / Summary (acadadmin/Dean)
# ===========================================================================

class GradeStatusAPI(APIView):
    """Get grade submission/verification status for all courses in a session."""

    permission_classes = [IsAuthenticated, IsAcadAdminOrDean]

    def post(self, request):
        academic_year = request.data.get("academic_year")
        semester_type = request.data.get("semester_type")

        if not academic_year or not semester_type:
            return Response(
                {"error": "Academic year and semester type are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            working_year, _ = services.parse_academic_year(academic_year, semester_type)

            course_ids = (
                course_registration.objects.filter(
                    session=academic_year, semester_type=semester_type
                )
                .values_list("course_id", flat=True)
                .distinct()
            )
            courses = Courses.objects.filter(id__in=course_ids).order_by("code")

            # Bulk-fetch all lookups (V32, V33)
            instructor_map = selectors.get_instructor_map(course_ids, working_year, semester_type)
            instructor_ids = [inst.instructor_id_id for inst in instructor_map.values()]
            user_map = selectors.get_user_fullname_map(instructor_ids)
            submitted = selectors.get_submitted_course_ids(academic_year, semester_type)
            verified = selectors.get_verified_course_ids(academic_year, semester_type)
            auth_map = selectors.get_authentication_records(course_ids, working_year)

            grade_status_list = []
            for course in courses:
                inst = instructor_map.get(course.id)
                professor_name = (
                    user_map.get(inst.instructor_id_id, inst.instructor_id_id)
                    if inst
                    else "Not Assigned"
                )

                submitted_str = "Submitted" if course.id in submitted else "Not Submitted"
                verified_str = "Verified" if course.id in verified else "Not Verified"

                validated = "Not Validated"
                if course.id in verified:
                    auth_rec = auth_map.get(course.id)
                    if (
                        auth_rec
                        and auth_rec.authenticator_1
                        and auth_rec.authenticator_2
                        and auth_rec.authenticator_3
                    ):
                        validated = "Validated"

                grade_status_list.append({
                    "course_code": course.code,
                    "course_name": course.name,
                    "course_id": course.id,
                    "professor_name": professor_name,
                    "submitted": submitted_str,
                    "verified": verified_str,
                    "validated": validated,
                    "credits": course.credit,
                    "version": course.version,
                })

            return Response(
                {
                    "success": True,
                    "grade_status": grade_status_list,
                    "academic_year": academic_year,
                    "semester_type": semester_type,
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            logger.exception("GradeStatusAPI error")
            return Response(
                {"error": f"An error occurred: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class GradeSummaryAPI(APIView):
    """Get grade distribution per course (ORM-based, replaces raw SQL V39)."""

    permission_classes = [IsAuthenticated, IsAcadAdminOrDean]

    def post(self, request):
        academic_year = request.data.get("academic_year")
        semester_type = request.data.get("semester_type")

        if not academic_year or not semester_type:
            return Response(
                {"error": "Academic year and semester type are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            results = services.get_grade_summary(academic_year, semester_type)
            return Response(
                {
                    "success": True,
                    "grade_summary": results,
                    "academic_year": academic_year,
                    "semester_type": semester_type,
                    "total_courses": len(results),
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            logger.exception("GradeSummaryAPI error")
            return Response(
                {"error": f"An error occurred: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
