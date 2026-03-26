# views.py
# Thin API views for the complaint_system module.
# All business logic delegated to services.py, all queries to selectors.py.
# Addresses: RR-01 through RR-17

from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from .serializers import (
    StudentComplainSerializer,
    CaretakerSerializer,
    FeedbackSerializer,
    ResolvePendingSerializer,
    WorkersSerializer,
    ServiceProviderSerializer,
    ExtraInfoSerializer,
    UserSerializer,
)
from .permissions import (
    IsCaretaker,
    IsServiceProvider,
    IsCaretakerOrServiceProvider,
    IsComplaintOwnerOrStaff,
    IsReportAuthorized,
)
from .models import (
    StudentComplain, Caretaker, ServiceProvider, Workers,
)
from . import services
from . import selectors


# ===================================================================
#  USER VIEWS
# ===================================================================

class CheckUser(APIView):
    """RR-24: Thin view — delegates to services.determine_user_type()"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user_type, next_url = services.determine_user_type(request.user)
        if user_type is None:
            return Response({'error': 'wrong user credentials'}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'user_type': user_type, 'next_url': next_url})


class UserComplaintView(APIView):
    """RR-03, RR-04: Thin view — delegates to services.lodge_complaint()"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        extra = selectors.get_extrainfo_by_user(request.user)
        complaints = selectors.get_complaints_by_complainer(extra)
        serializer = StudentComplainSerializer(complaints, many=True)
        return Response(serializer.data)

    def post(self, request):
        data = request.data.copy()
        try:
            complaint, serialized = services.lodge_complaint(
                user=request.user,
                validated_data=data,
                notify_single=False,
            )
            return Response(serialized, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class CaretakerFeedbackView(APIView):
    """Uses FeedbackSerializer for input validation."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = FeedbackSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        caretaker_type = request.data.get('caretakertype', '')
        services.submit_caretaker_area_feedback(
            caretaker_type,
            serializer.validated_data['feedback'],
            serializer.validated_data['rating'],
        )
        return Response({'success': 'Feedback submitted'})


class SubmitFeedbackView(APIView):
    """RR-05, RR-16: Uses FeedbackSerializer; specific exception handling."""
    permission_classes = [IsAuthenticated]

    def post(self, request, complaint_id):
        serializer = FeedbackSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        try:
            services.submit_complaint_feedback(
                complaint_id,
                serializer.validated_data['feedback'],
                serializer.validated_data['rating'],
            )
            return Response({'success': 'Feedback submitted'})
        except StudentComplain.DoesNotExist:
            return Response({'error': 'Complaint not found'}, status=status.HTTP_404_NOT_FOUND)
        except Caretaker.DoesNotExist:
            return Response({'error': 'Caretaker not found'}, status=status.HTTP_404_NOT_FOUND)


class ComplaintDetailView(APIView):
    """RR-09: Single definition (removed duplicate)."""
    permission_classes = [IsAuthenticated]

    def get(self, request, detailcomp_id1):
        try:
            complaint = selectors.get_complaint_by_id(detailcomp_id1)
            serializer = StudentComplainSerializer(complaint)
            return Response(serializer.data)
        except StudentComplain.DoesNotExist:
            return Response({'error': 'Complaint not found'}, status=status.HTTP_404_NOT_FOUND)


# ===================================================================
#  CARETAKER VIEWS
# ===================================================================

class CaretakerLodgeView(APIView):
    """RR-03: Delegates to services.lodge_complaint()"""
    permission_classes = [IsAuthenticated, IsCaretaker]

    def post(self, request):
        data = request.data.copy()
        try:
            complaint, serialized = services.lodge_complaint(
                user=request.user,
                validated_data=data,
                notify_single=True,
            )
            return Response(serialized, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def get(self, request):
        extra = selectors.get_extrainfo_by_user(request.user)
        complaints = selectors.get_complaints_by_complainer(extra)
        serializer = StudentComplainSerializer(complaints, many=True)
        return Response(serializer.data)


class CaretakerView(APIView):
    """Caretaker dashboard: complaints in their area."""
    permission_classes = [IsAuthenticated, IsCaretaker]

    def get(self, request):
        extra = selectors.get_extrainfo_by_user(request.user)
        try:
            caretaker = selectors.get_caretaker_by_staff_id(extra.id)
            complaints = selectors.get_complaints_by_location(caretaker.area)
            serializer = StudentComplainSerializer(complaints, many=True)
            return Response(serializer.data)
        except Caretaker.DoesNotExist:
            return Response({'error': 'Caretaker does not exist'}, status=status.HTTP_404_NOT_FOUND)


class FeedbackCareView(APIView):
    """Feedback detail for a complaint (caretaker view)."""
    permission_classes = [IsAuthenticated, IsCaretaker]

    def get(self, request, feedcomp_id):
        try:
            complaint = selectors.get_complaint_by_id(feedcomp_id)
            serializer = StudentComplainSerializer(complaint)
            return Response(serializer.data)
        except StudentComplain.DoesNotExist:
            return Response({'error': 'Complaint not found'}, status=status.HTTP_404_NOT_FOUND)


class ResolvePendingView(APIView):
    """RR-08: Delegates to services.resolve_complaint()"""
    permission_classes = [IsAuthenticated, IsCaretaker]

    def post(self, request, cid):
        serializer = ResolvePendingSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        try:
            result = services.resolve_complaint(
                cid=cid,
                yesorno=serializer.validated_data['yesorno'],
                comment=serializer.validated_data.get('comment', ''),
                upload_file=request.FILES.get('upload_resolved'),
                requesting_user=request.user,
            )
            return Response(result)
        except StudentComplain.DoesNotExist:
            return Response({'error': 'Complaint not found'}, status=status.HTTP_404_NOT_FOUND)

    def get(self, request, cid):
        try:
            complaint = selectors.get_complaint_by_id(cid)
            serializer = StudentComplainSerializer(complaint)
            return Response(serializer.data)
        except StudentComplain.DoesNotExist:
            return Response({'error': 'Complaint not found'}, status=status.HTTP_404_NOT_FOUND)


class SearchComplaintView(APIView):
    """Placeholder search — returns all complaints."""
    permission_classes = [IsAuthenticated, IsCaretaker]

    def get(self, request):
        complaints = selectors.get_all_complaints()
        serializer = StudentComplainSerializer(complaints, many=True)
        return Response(serializer.data)


class SubmitFeedbackCaretakerView(APIView):
    """RR-05: Delegates to services.submit_complaint_feedback()"""
    permission_classes = [IsAuthenticated, IsCaretaker]

    def post(self, request, complaint_id):
        serializer = FeedbackSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        try:
            services.submit_complaint_feedback(
                complaint_id,
                serializer.validated_data['feedback'],
                serializer.validated_data['rating'],
            )
            return Response({'success': 'Feedback submitted'})
        except StudentComplain.DoesNotExist:
            return Response({'error': 'Complaint not found'}, status=status.HTTP_404_NOT_FOUND)
        except Caretaker.DoesNotExist:
            return Response({'error': 'Caretaker not found'}, status=status.HTTP_404_NOT_FOUND)

    def get(self, request, complaint_id):
        try:
            complaint = selectors.get_complaint_by_id(complaint_id)
            serializer = StudentComplainSerializer(complaint)
            return Response(serializer.data)
        except StudentComplain.DoesNotExist:
            return Response({'error': 'Complaint not found'}, status=status.HTTP_404_NOT_FOUND)


class RemoveWorkerView(APIView):
    """Worker removal — delegates to services.remove_worker()"""
    permission_classes = [IsAuthenticated, IsCaretaker]

    def post(self, request, work_id):
        try:
            success, message = services.remove_worker(work_id)
            if success:
                return Response({'success': message}, status=status.HTTP_200_OK)
            return Response({'error': message}, status=status.HTTP_400_BAD_REQUEST)
        except Workers.DoesNotExist:
            return Response({'error': 'Worker not found'}, status=status.HTTP_404_NOT_FOUND)

    def delete(self, request, work_id):
        return self.post(request, work_id)


class ForwardComplaintView(APIView):
    """RR-14: Delegates to services.forward_complaint_to_service_provider()"""
    permission_classes = [IsAuthenticated, IsCaretaker]

    def post(self, request, comp_id1):
        try:
            result, status_code = services.forward_complaint_to_service_provider(
                comp_id1, request.user
            )
            return Response(result, status=status_code)
        except StudentComplain.DoesNotExist:
            return Response({'error': 'Complaint not found'}, status=status.HTTP_404_NOT_FOUND)

    def get(self, request, comp_id1):
        try:
            complaint = selectors.get_complaint_by_id_basic(comp_id1)
            serializer = StudentComplainSerializer(complaint)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except StudentComplain.DoesNotExist:
            return Response({'error': 'Not a valid complaint'}, status=status.HTTP_404_NOT_FOUND)


class DeleteComplaintView(APIView):
    """RR-13: Ownership/role check via services.delete_complaint()"""
    permission_classes = [IsAuthenticated, IsComplaintOwnerOrStaff]

    def post(self, request, comp_id1):
        try:
            success, message = services.delete_complaint(comp_id1, request.user)
            if success:
                return Response({'success': message}, status=status.HTTP_200_OK)
            return Response({'error': message}, status=status.HTTP_403_FORBIDDEN)
        except StudentComplain.DoesNotExist:
            return Response({'error': 'Complaint not found'}, status=status.HTTP_404_NOT_FOUND)

    def delete(self, request, comp_id1):
        return self.post(request, comp_id1)


class ChangeStatusView(APIView):
    """RR-06: Single view for both caretaker and SP status changes."""
    permission_classes = [IsAuthenticated, IsCaretakerOrServiceProvider]

    def post(self, request, complaint_id, status_value):
        try:
            services.change_complaint_status(complaint_id, status_value)
            return Response({'success': 'Complaint status updated'}, status=status.HTTP_200_OK)
        except StudentComplain.DoesNotExist:
            return Response({'error': 'Complaint not found'}, status=status.HTTP_404_NOT_FOUND)


# ===================================================================
#  SERVICE PROVIDER VIEWS
# ===================================================================

class ServiceProviderLodgeView(APIView):
    """RR-03: Delegates to services.lodge_complaint()"""
    permission_classes = [IsAuthenticated, IsServiceProvider]

    def post(self, request):
        data = request.data.copy()
        try:
            complaint, serialized = services.lodge_complaint(
                user=request.user,
                validated_data=data,
                notify_single=True,
            )
            return Response(serialized, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def get(self, request):
        extra = selectors.get_extrainfo_by_user(request.user)
        complaints = selectors.get_complaints_by_complainer(extra)
        serializer = StudentComplainSerializer(complaints, many=True)
        return Response(serializer.data)


class ServiceProviderView(APIView):
    """Service provider dashboard: complaints of their type with status=1."""
    permission_classes = [IsAuthenticated, IsServiceProvider]

    def get(self, request):
        extra = selectors.get_extrainfo_by_user(request.user)
        try:
            sp = selectors.get_service_provider_by_extrainfo(extra)
            complaints = selectors.get_complaints_by_type_and_status(sp.type, 1)
            serializer = StudentComplainSerializer(complaints, many=True)
            return Response(serializer.data)
        except ServiceProvider.DoesNotExist:
            return Response({'error': 'ServiceProvider does not exist'}, status=status.HTTP_404_NOT_FOUND)


class FeedbackSuperView(APIView):
    """Feedback detail for a complaint (service provider view)."""
    permission_classes = [IsAuthenticated, IsServiceProvider]

    def get(self, request, feedcomp_id):
        try:
            complaint = selectors.get_complaint_by_id(feedcomp_id)
            caretaker = selectors.get_caretaker_by_area(complaint.location)
            complaint_data = StudentComplainSerializer(complaint).data
            caretaker_data = CaretakerSerializer(caretaker).data if caretaker else None
            return Response({'complaint': complaint_data, 'caretaker': caretaker_data})
        except StudentComplain.DoesNotExist:
            return Response({'error': 'Complaint not found'}, status=status.HTTP_404_NOT_FOUND)


class CaretakerIdKnowMoreView(APIView):
    """Caretaker details + pending complaints in their area."""
    permission_classes = [IsAuthenticated, IsServiceProvider]

    def get(self, request, caretaker_id):
        try:
            caretaker = selectors.get_caretaker_by_id(caretaker_id)
            pending = selectors.get_pending_complaints_by_location(caretaker.area)
            caretaker_data = CaretakerSerializer(caretaker).data
            complaints_data = StudentComplainSerializer(pending, many=True).data
            return Response({'caretaker': caretaker_data, 'pending_complaints': complaints_data})
        except Caretaker.DoesNotExist:
            return Response({'error': 'Caretaker not found'}, status=status.HTTP_404_NOT_FOUND)


class ServiceProviderComplaintDetailView(APIView):
    """Complaint detail with caretaker info for service providers."""
    permission_classes = [IsAuthenticated, IsServiceProvider]

    def get(self, request, detailcomp_id1):
        try:
            complaint = selectors.get_complaint_by_id(detailcomp_id1)
            caretaker = selectors.get_caretaker_by_area(complaint.location)
            complaint_data = StudentComplainSerializer(complaint).data
            caretaker_data = CaretakerSerializer(caretaker).data if caretaker else None
            return Response({'complaint': complaint_data, 'caretaker': caretaker_data})
        except StudentComplain.DoesNotExist:
            return Response({'error': 'Complaint not found'}, status=status.HTTP_404_NOT_FOUND)


class ServiceProviderResolvePendingView(APIView):
    """RR-08: Delegates to services.resolve_complaint()"""
    permission_classes = [IsAuthenticated, IsServiceProvider]

    def post(self, request, cid):
        serializer = ResolvePendingSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        try:
            result = services.resolve_complaint(
                cid=cid,
                yesorno=serializer.validated_data['yesorno'],
                comment=serializer.validated_data.get('comment', ''),
                upload_file=request.FILES.get('upload_resolved'),
                requesting_user=request.user,
            )
            return Response(result)
        except StudentComplain.DoesNotExist:
            return Response({'error': 'Complaint not found'}, status=status.HTTP_404_NOT_FOUND)

    def get(self, request, cid):
        try:
            complaint = selectors.get_complaint_by_id(cid)
            serializer = StudentComplainSerializer(complaint)
            return Response(serializer.data)
        except StudentComplain.DoesNotExist:
            return Response({'error': 'Complaint not found'}, status=status.HTTP_404_NOT_FOUND)


class ServiceProviderSubmitFeedbackView(APIView):
    """RR-05: Delegates to services.submit_complaint_feedback()"""
    permission_classes = [IsAuthenticated, IsServiceProvider]

    def post(self, request, complaint_id):
        serializer = FeedbackSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        try:
            services.submit_complaint_feedback(
                complaint_id,
                serializer.validated_data['feedback'],
                serializer.validated_data['rating'],
            )
            return Response({'success': 'Feedback submitted'})
        except StudentComplain.DoesNotExist:
            return Response({'error': 'Complaint not found'}, status=status.HTTP_404_NOT_FOUND)
        except Caretaker.DoesNotExist:
            return Response({'error': 'Caretaker not found'}, status=status.HTTP_404_NOT_FOUND)

    def get(self, request, complaint_id):
        try:
            complaint = selectors.get_complaint_by_id(complaint_id)
            serializer = StudentComplainSerializer(complaint)
            return Response(serializer.data)
        except StudentComplain.DoesNotExist:
            return Response({'error': 'Complaint not found'}, status=status.HTTP_404_NOT_FOUND)


# ===================================================================
#  REPORT VIEW
# ===================================================================

class GenerateReportView(APIView):
    """RR-15: Delegates to services.generate_report()"""
    permission_classes = [IsAuthenticated, IsReportAuthorized]

    def get(self, request):
        complaints, error = services.generate_report(request.user)
        if error:
            return Response({'detail': error}, status=status.HTTP_403_FORBIDDEN)
        serializer = StudentComplainSerializer(complaints, many=True)
        return Response(serializer.data)
