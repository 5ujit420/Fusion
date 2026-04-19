from rest_framework import status as drf_status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from . import selectors, services
from .models import (
    StudentComplain,
    Workers,
)
from .serializers import (
    CaretakerSerializer,
    FeedbackSerializer,
    ResolvePendingSerializer,
    StudentComplainInputSerializer,
    StudentComplainOutputSerializer,
)


class CheckUser(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        extrainfo = selectors.get_current_extrainfo(request.user)
        response_payload = services.route_user(extrainfo)
        if response_payload is None:
            return Response({"error": "wrong user credentials"}, status=400)
        return Response(response_payload)


class BaseComplaintLodgeView(APIView):
    permission_classes = [IsAuthenticated]
    actor_scope = "user"
    notify_all = False

    def get_complainer(self, request):
        return selectors.get_current_extrainfo(request.user)

    def get(self, request):
        complaints = selectors.list_user_complaints(self.get_complainer(request))
        serializer = StudentComplainOutputSerializer(complaints, many=True)
        return Response(serializer.data)

    def post(self, request):
        complainer = self.get_complainer(request)
        data = services.prepare_complaint_payload(request.data, complainer.id, self.actor_scope)
        serializer = StudentComplainInputSerializer(data=data)
        if serializer.is_valid():
            complaint = serializer.save()
            services.notify_lodged_complaint(
                request.user,
                complaint,
                data.get("location", ""),
                notify_all=self.notify_all,
            )
            return Response(serializer.data, status=drf_status.HTTP_201_CREATED)
        return Response(serializer.errors, status=drf_status.HTTP_400_BAD_REQUEST)


class UserComplaintView(BaseComplaintLodgeView):
    actor_scope = "user"
    notify_all = True


class CaretakerFeedbackView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        feedback = request.data.get("feedback", "")
        rating = request.data.get("rating", "")
        caretaker_type = request.data.get("caretakertype", "")
        try:
            parsed_rating = int(rating)
        except ValueError:
            return Response({"error": "Invalid rating"}, status=400)
        services.update_caretaker_feedback(feedback, parsed_rating, caretaker_type)
        return Response({"success": "Feedback submitted"})


class SubmitFeedbackView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, complaint_id):
        feedback = request.data.get("feedback", "")
        rating = request.data.get("rating", "")
        try:
            parsed_rating = int(rating)
        except ValueError:
            return Response({"error": "Invalid rating"}, status=400)

        try:
            services.update_complaint_feedback_and_rating(
                complaint_id,
                feedback,
                parsed_rating,
                cast_rating_to_int=True,
            )
            return Response({"success": "Feedback submitted"})
        except (AttributeError, TypeError, StudentComplain.DoesNotExist, Workers.DoesNotExist):
            return Response({"error": "Internal server errror"}, status=500)


class ComplaintDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, detailcomp_id1):
        try:
            complaint = selectors.get_complaint(detailcomp_id1)
        except StudentComplain.DoesNotExist:
            return Response({"error": "Complaint not found"}, status=drf_status.HTTP_404_NOT_FOUND)
        serializer = StudentComplainOutputSerializer(complaint)
        return Response(serializer.data)


class CaretakerLodgeView(BaseComplaintLodgeView):
    actor_scope = "caretaker"
    notify_all = False


class CaretakerView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        extrainfo = selectors.get_current_extrainfo(request.user)
        try:
            caretaker = selectors.get_caretaker_for_user(extrainfo)
        except selectors.Caretaker.DoesNotExist:
            return Response({"error": "Caretaker does not exist"}, status=drf_status.HTTP_404_NOT_FOUND)
        complaints = selectors.list_complaints_for_location(caretaker.area)
        serializer = StudentComplainOutputSerializer(complaints, many=True)
        return Response(serializer.data)


class FeedbackCareView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, feedcomp_id):
        try:
            detail = selectors.get_complaint(feedcomp_id, selectors.COMPLAINT_RELATED_FIELDS)
        except StudentComplain.DoesNotExist:
            return Response({"error": "Complaint not found"}, status=drf_status.HTTP_404_NOT_FOUND)
        serializer = StudentComplainOutputSerializer(detail)
        return Response(serializer.data)


class ResolvePendingView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, cid):
        serializer = ResolvePendingSerializer(data=request.data)
        if serializer.is_valid():
            try:
                services.resolve_pending_complaint(
                    request.user,
                    cid,
                    serializer,
                    request.FILES,
                    notify_on_decline=True,
                )
                return Response({"success": "Complaint status updated"})
            except StudentComplain.DoesNotExist:
                return Response({"error": "Complaint not found"}, status=drf_status.HTTP_404_NOT_FOUND)
        return Response(serializer.errors, status=drf_status.HTTP_400_BAD_REQUEST)

    def get(self, request, cid):
        try:
            complaint = selectors.get_complaint(cid, selectors.COMPLAINT_RELATED_FIELDS)
        except StudentComplain.DoesNotExist:
            return Response({"error": "Complaint not found"}, status=drf_status.HTTP_404_NOT_FOUND)
        serializer = StudentComplainOutputSerializer(complaint)
        return Response(serializer.data)


class SearchComplaintView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        complaints = selectors.list_all_complaints()
        serializer = StudentComplainOutputSerializer(complaints, many=True)
        return Response(serializer.data)


class SubmitFeedbackCaretakerView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, complaint_id):
        serializer = FeedbackSerializer(data=request.data)
        if serializer.is_valid():
            feedback = serializer.validated_data["feedback"]
            rating = serializer.validated_data["rating"]
            services.update_complaint_feedback_and_rating(
                complaint_id,
                feedback,
                int(rating),
                cast_rating_to_int=True,
            )
            return Response({"success": "Feedback submitted"})
        return Response(serializer.errors, status=drf_status.HTTP_400_BAD_REQUEST)

    def get(self, request, complaint_id):
        try:
            complaint = selectors.get_complaint(complaint_id, selectors.COMPLAINT_RELATED_FIELDS)
        except StudentComplain.DoesNotExist:
            return Response({"error": "Complaint not found"}, status=drf_status.HTTP_404_NOT_FOUND)
        serializer = StudentComplainOutputSerializer(complaint)
        return Response(serializer.data)


class ServiceProviderLodgeView(BaseComplaintLodgeView):
    actor_scope = "service_provider"
    notify_all = False


class ServiceProviderView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        extrainfo = selectors.get_current_extrainfo(request.user)
        try:
            service_provider = selectors.get_service_provider_for_user(extrainfo)
        except selectors.ServiceProvider.DoesNotExist:
            return Response({"error": "ServiceProvider does not exist"}, status=drf_status.HTTP_404_NOT_FOUND)
        complaints = selectors.list_complaints_for_type(service_provider.type, status_value=1)
        serializer = StudentComplainOutputSerializer(complaints, many=True)
        return Response(serializer.data)


class FeedbackSuperView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, feedcomp_id):
        try:
            complaint = selectors.get_complaint(feedcomp_id, selectors.COMPLAINT_RELATED_FIELDS)
        except StudentComplain.DoesNotExist:
            return Response({"error": "Complaint not found"}, status=drf_status.HTTP_404_NOT_FOUND)
        caretaker = selectors.get_caretaker_by_area(complaint.location)
        complaint_data = StudentComplainOutputSerializer(complaint).data
        caretaker_data = CaretakerSerializer(caretaker).data if caretaker else None
        return Response({"complaint": complaint_data, "caretaker": caretaker_data})


class CaretakerIdKnowMoreView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, caretaker_id):
        try:
            caretaker = selectors.get_caretaker_by_id(caretaker_id)
        except selectors.Caretaker.DoesNotExist:
            return Response({"error": "Caretaker not found"}, status=drf_status.HTTP_404_NOT_FOUND)
        pending_complaints = selectors.list_pending_complaints_by_area(caretaker.area)
        caretaker_data = CaretakerSerializer(caretaker).data
        complaints_data = StudentComplainOutputSerializer(pending_complaints, many=True).data
        return Response({"caretaker": caretaker_data, "pending_complaints": complaints_data})


class ServiceProviderComplaintDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, detailcomp_id1):
        try:
            complaint = selectors.get_complaint(detailcomp_id1, selectors.COMPLAINT_RELATED_FIELDS)
        except StudentComplain.DoesNotExist:
            return Response({"error": "Complaint not found"}, status=drf_status.HTTP_404_NOT_FOUND)
        caretaker = selectors.get_caretaker_by_area(complaint.location)
        complaint_data = StudentComplainOutputSerializer(complaint).data
        caretaker_data = CaretakerSerializer(caretaker).data if caretaker else None
        return Response({"complaint": complaint_data, "caretaker": caretaker_data})


class ServiceProviderResolvePendingView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, cid):
        serializer = ResolvePendingSerializer(data=request.data)
        if serializer.is_valid():
            try:
                services.resolve_pending_complaint(
                    request.user,
                    cid,
                    serializer,
                    request.FILES,
                    notify_on_decline=False,
                )
                return Response({"success": "Complaint status updated"})
            except StudentComplain.DoesNotExist:
                return Response({"error": "Complaint not found"}, status=drf_status.HTTP_404_NOT_FOUND)
        return Response(serializer.errors, status=drf_status.HTTP_400_BAD_REQUEST)

    def get(self, request, cid):
        try:
            complaint = selectors.get_complaint(cid, ("complainer", "complainer__user"))
        except StudentComplain.DoesNotExist:
            return Response({"error": "Complaint not found"}, status=drf_status.HTTP_404_NOT_FOUND)
        serializer = StudentComplainOutputSerializer(complaint)
        return Response(serializer.data)


class ServiceProviderSubmitFeedbackView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, complaint_id):
        serializer = FeedbackSerializer(data=request.data)
        if serializer.is_valid():
            feedback = serializer.validated_data["feedback"]
            rating = serializer.validated_data["rating"]
            services.update_complaint_feedback_and_rating(
                complaint_id,
                feedback,
                int(rating),
                cast_rating_to_int=True,
            )
            return Response({"success": "Feedback submitted"})
        return Response(serializer.errors, status=drf_status.HTTP_400_BAD_REQUEST)

    def get(self, request, complaint_id):
        try:
            complaint = selectors.get_complaint(complaint_id, selectors.COMPLAINT_RELATED_FIELDS)
        except StudentComplain.DoesNotExist:
            return Response({"error": "Complaint not found"}, status=drf_status.HTTP_404_NOT_FOUND)
        serializer = StudentComplainOutputSerializer(complaint)
        return Response(serializer.data)


class RemoveWorkerView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, work_id):
        try:
            worker = selectors.get_worker_by_id(work_id)
        except selectors.Workers.DoesNotExist:
            return Response({"error": "Worker not found"}, status=drf_status.HTTP_404_NOT_FOUND)

        assigned_complaints = selectors.count_worker_complaints(worker)
        if assigned_complaints == 0:
            worker.delete()
            return Response({"success": "Worker removed successfully"}, status=drf_status.HTTP_200_OK)
        return Response({"error": "Worker is assigned to some complaints"}, status=drf_status.HTTP_400_BAD_REQUEST)

    def delete(self, request, work_id):
        return self.post(request, work_id)


class ForwardCompaintView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, comp_id1):
        try:
            complaint = selectors.get_complaint(comp_id1)
        except StudentComplain.DoesNotExist:
            return Response({"error": "Complaint not found"}, status=drf_status.HTTP_404_NOT_FOUND)

        response_data, _service_provider, response_status = services.forward_complaint(request.user, complaint)
        return Response(response_data, status=response_status)

    def get(self, request, comp_id1):
        try:
            complaint = selectors.get_complaint(comp_id1)
        except StudentComplain.DoesNotExist:
            return Response({"error": "Not a valid complaint"}, status=drf_status.HTTP_404_NOT_FOUND)
        serializer = StudentComplainOutputSerializer(complaint)
        return Response(serializer.data, status=drf_status.HTTP_200_OK)


class DeleteComplaintView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, comp_id1):
        try:
            complaint = selectors.get_complaint(comp_id1)
        except StudentComplain.DoesNotExist:
            return Response({"error": "Complaint not found"}, status=drf_status.HTTP_404_NOT_FOUND)
        complaint.delete()
        return Response({"success": "Complaint deleted successfully"}, status=drf_status.HTTP_200_OK)

    def delete(self, request, comp_id1):
        return self.post(request, comp_id1)


class ChangeStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, complaint_id, status):
        try:
            complaint = selectors.get_complaint(complaint_id)
        except StudentComplain.DoesNotExist:
            return Response({"error": "Complaint not found"}, status=drf_status.HTTP_404_NOT_FOUND)
        services.change_complaint_status(complaint, status)
        return Response({"success": "Complaint status updated"}, status=drf_status.HTTP_200_OK)


class ChangeStatusSuperView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, complaint_id, status):
        try:
            complaint = selectors.get_complaint(complaint_id)
        except StudentComplain.DoesNotExist:
            return Response({"error": "Complaint not found"}, status=drf_status.HTTP_404_NOT_FOUND)
        services.change_complaint_status(complaint, status)
        return Response({"success": "Complaint status updated"}, status=drf_status.HTTP_200_OK)


class GenerateReportView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        complaints = services.get_report_queryset(request.user)
        if complaints is None:
            return Response({"detail": "Not authorized to generate report."}, status=403)
        serializer = StudentComplainOutputSerializer(complaints, many=True)
        return Response(serializer.data)
