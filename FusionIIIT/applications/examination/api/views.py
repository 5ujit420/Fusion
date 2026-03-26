"""
views.py — Thin API views for the examination module.

Views handle request parsing, serializer validation, delegation to services/selectors,
and response formatting only.  No business logic or direct DB queries live here.
"""

import json
import traceback

from django.http import HttpResponse, JsonResponse
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from applications.programme_curriculum.models import Course as Courses

from .. import selectors, services
from ..models import PROFESSOR_ROLES
from .serializers import (
    CheckCourseStudentsSerializer,
    CheckResultSerializer,
    CreateAnnouncementSerializer,
    DownloadExcelSerializer,
    DownloadGradesSerializer,
    DownloadTemplateSerializer,
    ExamViewSerializer,
    GeneratePDFSerializer,
    GenerateResultSerializer,
    GenerateStudentResultPDFSerializer,
    GenerateTranscriptFormGetSerializer,
    GenerateTranscriptFormPostSerializer,
    GenerateTranscriptSerializer,
    GradeStatusSerializer,
    GradeSummarySerializer,
    ModerateStudentGradesSerializer,
    PreviewGradesSerializer,
    ResultAnnouncementListSerializer,
    SubmitAPISerializer,
    SubmitGradesProfSerializer,
    SubmitGradesSerializer,
    UniqueRegistrationYearsSerializer,
    UpdateAnnouncementSerializer,
    UpdateEnterGradesDeanSerializer,
    UpdateEnterGradesSerializer,
    UpdateGradesSerializer,
    UploadGradesProfSerializer,
    UploadGradesSerializer,
    ValidateDeanSerializer,
    ValidateDeanSubmitSerializer,
    VerifyGradesDeanSerializer,
)


# ---------------------------------------------------------------------------
# Exam view (role redirect)
# ---------------------------------------------------------------------------

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def exam_view(request):
    serializer = ExamViewSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    role = serializer.validated_data["Role"]
    if not role:
        return Response(
            {"error": "Role parameter is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    redirect_url = services.get_redirect_url_for_role(role)
    return Response({"redirect_url": redirect_url})


# ---------------------------------------------------------------------------
# Unique years
# ---------------------------------------------------------------------------

class UniqueStudentGradeYearsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        years = selectors.get_unique_student_grade_years()
        return Response({"academic_years": list(years)}, status=200)


class UniqueRegistrationYearsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UniqueRegistrationYearsSerializer(data=request.GET)
        serializer.is_valid(raise_exception=True)
        programme_type = serializer.validated_data.get("programme_type")
        years = selectors.get_unique_registration_years(programme_type)
        return Response({"academic_years": list(years)}, status=200)


# ---------------------------------------------------------------------------
# Download template
# ---------------------------------------------------------------------------

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def download_template(request):
    serializer = DownloadTemplateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data
    try:
        response, error = services.generate_download_template(
            data["course"], data["year"], data["semester_type"], data.get("programme_type"),
        )
        if error:
            return Response({"error": error}, status=status.HTTP_404_NOT_FOUND)
        return response
    except Exception as e:
        return Response(
            {"error": f"An unexpected error occurred: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


# ---------------------------------------------------------------------------
# Check course students
# ---------------------------------------------------------------------------

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def check_course_students(request):
    serializer = CheckCourseStudentsSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data
    try:
        has_students, student_count = services.check_course_students(
            data["course"], data["year"], data["semester_type"], data.get("programme_type"),
        )
        return Response(
            {
                "has_students": has_students,
                "student_count": student_count,
                "course_id": data["course"],
                "programme_type": data.get("programme_type"),
            },
            status=status.HTTP_200_OK,
        )
    except Exception as e:
        return Response(
            {"error": f"An unexpected error occurred: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


# ---------------------------------------------------------------------------
# Submit grades (acadadmin — course list)
# ---------------------------------------------------------------------------

class SubmitGradesView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = SubmitGradesSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        academic_year = data.get("academic_year")
        semester_type = data.get("semester_type")

        if academic_year and semester_type:
            courses = selectors.get_courses_for_session(academic_year, semester_type)
            return Response(
                {"courses": list(courses.values())}, status=status.HTTP_200_OK
            )

        sessions = selectors.get_available_sessions()
        return Response({"sessions": list(sessions)}, status=status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# Upload grades (acadadmin)
# ---------------------------------------------------------------------------

class UploadGradesAPI(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        serializer = UploadGradesSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

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

        try:
            msg, error = services.upload_grades_admin(
                data["course_id"], data["academic_year"], data["semester_type"], csv_file,
            )
            if error:
                return Response({"error": error}, status=status.HTTP_400_BAD_REQUEST)
            return Response({"message": msg}, status=status.HTTP_200_OK)
        except Courses.DoesNotExist:
            return Response(
                {"error": "Invalid course ID."}, status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {"error": f"An error occurred: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )


# ---------------------------------------------------------------------------
# Update grades (acadadmin — unverified courses)
# ---------------------------------------------------------------------------

class UpdateGradesAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = UpdateGradesSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        courses_info = selectors.get_unverified_course_ids(
            data["academic_year"], data["semester_type"]
        )
        unique_year_ids = selectors.get_unique_year_ids_for_grades(
            data["academic_year"], data["semester_type"]
        )
        return Response(
            {
                "courses_info": list(courses_info.values()),
                "unique_year_ids": list(unique_year_ids),
            },
            status=200,
        )


# ---------------------------------------------------------------------------
# Update enter grades (acadadmin — single course)
# ---------------------------------------------------------------------------

class UpdateEnterGradesAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = UpdateEnterGradesSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        course_present = selectors.get_student_grades(
            data["course"], data["year"], data.get("semester_type")
        )
        if not course_present.exists():
            return Response(
                {"message": "This course is not submitted by the instructor."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if course_present.first().verified:
            return Response(
                {"message": "This course is already verified."},
                status=status.HTTP_200_OK,
            )

        return Response(
            {"registrations": list(course_present.values())},
            status=status.HTTP_200_OK,
        )


# ---------------------------------------------------------------------------
# Moderate student grades
# ---------------------------------------------------------------------------

class ModerateStudentGradesAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ModerateStudentGradesSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            response = services.moderate_student_grades(
                data["student_ids"],
                data["semester_ids"],
                data["course_ids"],
                data["grades"],
                data["remarks"],
                data["allow_resubmission"],
            )
            return response
        except Exception as e:
            return Response(
                {"error": f"An error occurred: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


# ---------------------------------------------------------------------------
# Generate transcript
# ---------------------------------------------------------------------------

class GenerateTranscript(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = GenerateTranscriptSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            result = services.generate_transcript_data(
                data["student"], data["semester"]
            )
            return Response(result, status=status.HTTP_200_OK)
        except Exception:
            return Response(
                {"error": "Student ID does not exist."},
                status=status.HTTP_400_BAD_REQUEST,
            )


# ---------------------------------------------------------------------------
# Generate transcript form
# ---------------------------------------------------------------------------

class GenerateTranscriptForm(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = GenerateTranscriptFormGetSerializer(data=request.GET)
        serializer.is_valid(raise_exception=True)

        result = services.get_transcript_form_data()
        return Response(result, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = GenerateTranscriptFormPostSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        result = services.get_students_for_transcript(
            data["batch"], data.get("specialization"), data["semester"]
        )
        return Response(result, status=status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# Generate result (Excel)
# ---------------------------------------------------------------------------

class GenerateResultAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = GenerateResultSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            response, error = services.generate_result_excel(
                data["semester"],
                data["batch"],
                data.get("semester_type"),
                data.get("specialization"),
            )
            if error:
                return Response({"error": error}, status=404)
            return response
        except Exception as e:
            traceback.print_exc()
            return Response({"error": str(e)}, status=500)


# ---------------------------------------------------------------------------
# Submit API (unique courses)
# ---------------------------------------------------------------------------

class SubmitAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = SubmitAPISerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        courses_info = selectors.get_unique_courses_from_registrations()
        return Response(
            {"courses_info": list(courses_info.values())},
            status=status.HTTP_200_OK,
        )


# ---------------------------------------------------------------------------
# Download excel CSV
# ---------------------------------------------------------------------------

class DownloadExcelAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = DownloadExcelSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        return services.generate_download_excel_csv(
            data["student_ids"],
            data["semester_ids"],
            data["course_ids"],
            data["grades"],
        )


# ---------------------------------------------------------------------------
# Submit grades prof (course list for professor)
# ---------------------------------------------------------------------------

class SubmitGradesProfAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = SubmitGradesProfSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        courses_data = services.get_prof_courses_data(
            request.user.username,
            data["academic_year"],
            data["semester_type"],
            data.get("programme_type"),
        )
        return Response(
            {"courses_info": courses_data}, status=status.HTTP_200_OK
        )


# ---------------------------------------------------------------------------
# Upload grades prof
# ---------------------------------------------------------------------------

class UploadGradesProfAPI(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        serializer = UploadGradesProfSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        csv_file = request.FILES.get("csv_file")
        if not csv_file:
            return Response(
                {"error": "No file provided. Please upload a CSV file."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not csv_file.name.lower().endswith(".csv"):
            return Response(
                {"error": "Invalid file format. Please upload a CSV file."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            msg, error = services.upload_grades_prof(
                request.user.username,
                data["course_id"],
                data["academic_year"],
                data["semester_type"],
                csv_file,
                data.get("programme_type"),
            )
            if error:
                if error.startswith("ACCESS_DENIED:"):
                    return Response(
                        {"error": f"Access denied: {error.split(':', 1)[1]}"},
                        status=status.HTTP_403_FORBIDDEN,
                    )
                # Check if error is a JSON string (mixed UG/PG case)
                try:
                    error_data = json.loads(error)
                    return Response(error_data, status=status.HTTP_400_BAD_REQUEST)
                except (json.JSONDecodeError, TypeError):
                    pass
                return Response({"error": error}, status=status.HTTP_400_BAD_REQUEST)
            return Response({"message": msg}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


# ---------------------------------------------------------------------------
# Generate PDF (faculty grade sheet or student result)
# ---------------------------------------------------------------------------

class GeneratePDFAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            role = request.data.get("Role")

            # If no role or student role or student_info present → student result PDF
            if not role or role.lower() == "student" or "student_info" in request.data:
                return self._generate_student_result_pdf(request)

            # Faculty role check
            if role not in PROFESSOR_ROLES:
                return Response(
                    {"error": "Access denied."}, status=status.HTTP_403_FORBIDDEN
                )

            course_id = request.data.get("course_id")
            academic_year = request.data.get("academic_year")
            semester_type = request.data.get("semester_type")
            programme_type = request.data.get("programme_type")

            response, error = services.generate_course_grade_pdf(
                course_id, academic_year, semester_type, request.user, programme_type
            )
            if error:
                return Response(
                    {"success": False, "error": error}, status=404
                )
            return response

        except Exception as e:
            traceback.print_exc()
            return Response({"error": str(e)}, status=500)

    def _generate_student_result_pdf(self, request):
        data = request.data
        student_info = data.get("student_info", {})
        courses = data.get("courses", [])
        spi = float(data.get("spi", 0))
        cpi = float(data.get("cpi", 0))
        su = int(data.get("su", 0))
        tu = int(data.get("tu", 0))
        semester_no = data.get("semester_no", 1)
        semester_type = data.get("semester_type", "")
        semester_label = data.get("semester_label", "")
        is_transcript = (
            data.get("is_transcript", False)
            or data.get("document_type") == "transcript"
        )

        return services.generate_student_result_pdf(
            student_info, courses, spi, cpi, su, tu,
            semester_no, semester_type, semester_label, is_transcript,
        )


# ---------------------------------------------------------------------------
# Download grades (professor)
# ---------------------------------------------------------------------------

class DownloadGradesAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = DownloadGradesSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            courses = services.get_download_grades_data(
                request.user.username,
                data["academic_year"],
                data["semester_type"],
                data.get("programme_type"),
            )
            return Response({"courses": courses}, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            return Response(
                {"error": "Internal server error."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


# ---------------------------------------------------------------------------
# Verify grades dean
# ---------------------------------------------------------------------------

class VerifyGradesDeanView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = VerifyGradesDeanSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        courses = selectors.get_verified_courses_dean(
            data["academic_year"], data["semester_type"]
        )
        courses_info = list(courses.values("id", "code", "name"))
        return Response({"courses_info": courses_info}, status=status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# Update enter grades dean
# ---------------------------------------------------------------------------

class UpdateEnterGradesDeanView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = UpdateEnterGradesDeanSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        qs = selectors.get_dean_student_grades(
            data.get("course"), data.get("year"), data.get("semester_type")
        )
        if not qs.exists():
            return Response(
                {"message": "THIS COURSE IS NOT SUBMITTED BY THE INSTRUCTOR"}
            )
        return Response(
            {"registrations": list(qs.values())}, status=status.HTTP_200_OK
        )


# ---------------------------------------------------------------------------
# Validate dean (verified courses list)
# ---------------------------------------------------------------------------

class ValidateDeanView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ValidateDeanSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        courses_info = selectors.get_verified_courses_for_validation()
        working_years = selectors.get_working_years()

        return Response(
            {
                "courses_info": list(courses_info.values()),
                "working_years": list(working_years),
            },
            status=status.HTTP_200_OK,
        )


# ---------------------------------------------------------------------------
# Validate dean submit (CSV comparison)
# ---------------------------------------------------------------------------

class ValidateDeanSubmitView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ValidateDeanSubmitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

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

        year = data["year"]
        if not year.isdigit():
            return Response(
                {"error": "Academic Year must be a number."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            mismatches, error = services.validate_dean_csv(
                data["course"], year, csv_file
            )
            if error:
                return Response({"error": error}, status=status.HTTP_400_BAD_REQUEST)
            if not mismatches:
                return Response(
                    {"message": "There are no mismatches."},
                    status=status.HTTP_200_OK,
                )
            return Response(
                {"mismatches": mismatches}, status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {"error": f"An error occurred while processing the file: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


# ---------------------------------------------------------------------------
# Check result (student)
# ---------------------------------------------------------------------------

class CheckResultView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = CheckResultSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        result, error = services.get_student_result_data(
            request.user.username, data["semester_no"], data["semester_type"]
        )
        if error:
            http_status = 404 if "not found" in error.get("message", "").lower() else 200
            return JsonResponse(error, status=http_status)
        return JsonResponse(result)


# ---------------------------------------------------------------------------
# Preview grades
# ---------------------------------------------------------------------------

class PreviewGradesAPI(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        serializer = PreviewGradesSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

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

        preview, error = services.preview_grades_csv(
            data["course_id"],
            data["academic_year"],
            data["semester_type"],
            csv_file,
            data.get("programme_type"),
        )
        if error:
            return Response({"error": error}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"preview": preview}, status=status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# Result announcements
# ---------------------------------------------------------------------------

class ResultAnnouncementListAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = ResultAnnouncementListSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        result = services.get_announcements_data(serializer.validated_data["role"])
        return Response(result, status=status.HTTP_200_OK)


class UpdateAnnouncementAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = UpdateAnnouncementSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            services.update_announcement(data["id"], data["announced"])
            return Response({"success": True}, status=status.HTTP_200_OK)
        except Exception as e:
            traceback.print_exc()
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CreateAnnouncementAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = CreateAnnouncementSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            result, created = services.create_announcement(
                data["batch"], data["semester"]
            )
            if result is None:
                return Response(
                    {"error": created}, status=status.HTTP_404_NOT_FOUND
                )
            http_status = status.HTTP_201_CREATED if created else status.HTTP_200_OK
            return Response(result, status=http_status)
        except Exception as e:
            traceback.print_exc()
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# ---------------------------------------------------------------------------
# Student semester list
# ---------------------------------------------------------------------------

class StudentSemesterListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        semesters = services.get_student_semester_list(request.user.username)
        return JsonResponse({"success": True, "semesters": semesters})


# ---------------------------------------------------------------------------
# Grade status
# ---------------------------------------------------------------------------

class GradeStatusAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = GradeStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            grade_status_list = services.get_grade_status(
                data["academic_year"], data["semester_type"]
            )
            return Response(
                {
                    "success": True,
                    "grade_status": grade_status_list,
                    "academic_year": data["academic_year"],
                    "semester_type": data["semester_type"],
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response(
                {"error": f"An error occurred: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


# ---------------------------------------------------------------------------
# Grade summary
# ---------------------------------------------------------------------------

class GradeSummaryAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = GradeSummarySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            results = services.get_grade_summary(
                data["academic_year"], data["semester_type"]
            )
            return Response(
                {
                    "success": True,
                    "grade_summary": results,
                    "academic_year": data["academic_year"],
                    "semester_type": data["semester_type"],
                    "total_courses": len(results),
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response(
                {"error": f"An error occurred: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


# ---------------------------------------------------------------------------
# Generate student result PDF
# ---------------------------------------------------------------------------

class GenerateStudentResultPDFAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            data = request.data
            student_info = data.get("student_info", {})
            courses = data.get("courses", [])

            # If student_info or courses not provided, fetch from DB
            if not student_info or not courses:
                semester_no = data.get("semester_no")
                semester_type = data.get("semester_type")

                if semester_no is None or semester_type is None:
                    return JsonResponse(
                        {"success": False, "message": "semester_no and semester_type are required."},
                        status=400,
                    )

                response, error = services.generate_student_result_pdf_from_db(
                    request.user.username, semester_no, semester_type, data
                )
                if error:
                    http_status = 404 if "not found" in error.get("message", "").lower() else 200
                    return JsonResponse(error, status=http_status)
                return response
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
                    semester_no, semester_type, semester_label, is_transcript,
                )

        except Exception as e:
            return JsonResponse(
                {"error": f"PDF generation failed: {str(e)}"}, status=500
            )
