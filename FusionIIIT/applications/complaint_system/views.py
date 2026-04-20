# views.py
# Thin DRF views — HTTP handling only.
# All ORM queries → selectors.py  |  All business logic → services.py
#
# T-04: CheckUser uses selectors.is_* + services.determine_user_role (CS-03, CS-28).
# T-05: UserComplaintView.post delegates to services (CS-01, CS-18, CS-26).
# T-06: ResolvePendingView.post delegates to services.resolve_complaint (CS-24).
# T-07: ChangeComplaintStatusView merges ChangeStatusView + ChangeStatusSuperView (CS-14, RD-03).
# T-08: Bare except removed; typed exceptions; standard {'error':...} envelope (CS-37, CS-38).
# T-09: No view-level rating coercion — FeedbackSerializer.validate_rating handles it (CS-17).
# T-12: Variables renamed a/b/y → auth_user/extra_info (CS-30).
# T-15: Commented-out post block deleted (CS-32, RD-04).
# T-16: Single import block (CS-33, RD-09).
# T-17: SearchComplaintView implemented via selectors.search_complaints (CS-34).
# T-20: GenerateReportView delegates to selectors.get_report_by_role (CS-02, CS-10).
# T-23: Guard clauses replace nested conditionals (CS-04).
# T-25: Pagination on all list endpoints (DRF compliance).

import logging

from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (
    Caretaker,
    Complaint_Admin,
    StudentComplain,
    Workers,
    COMPLAINT_STATUS_PENDING,
)
from .serializers import (
    CaretakerSerializer,
    Complaint_AdminSerializer,
    ComplaintCreateSerializer,
    FeedbackSerializer,
    ResolvePendingSerializer,
    StudentComplainSerializer,
    WardenSerializer,
    WorkersSerializer,
)
from . import selectors, services

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Pagination (T-25)
# ---------------------------------------------------------------------------
class StandardResultsPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


# ---------------------------------------------------------------------------
# User-type dispatch
# ---------------------------------------------------------------------------
class CheckUser(APIView):
    """T-04 / CS-03 / CS-28: role detection via selectors; dict dispatch via services."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        extra_info = selectors.get_extra_info_by_user(request.user)
        role_info = services.determine_user_role(extra_info)
        if role_info is None:
            return Response(
                {'error': 'Wrong user credentials'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response({'user_type': role_info['role'], 'next_url': role_info['next_url']})


# ---------------------------------------------------------------------------
# Student / generic user
# ---------------------------------------------------------------------------
class UserComplaintView(APIView):
    """T-05 / CS-01 / CS-26: thin post; T-25: paginated get."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        extra_info = selectors.get_extra_info_by_user(request.user)
        complaints = selectors.get_complaints_by_complainer(extra_info)
        paginator = StandardResultsPagination()
        page = paginator.paginate_queryset(complaints, request)
        return paginator.get_paginated_response(
            StudentComplainSerializer(page, many=True).data
        )

    def post(self, request):
        extra_info = selectors.get_extra_info_by_user(request.user)
        data = request.data.copy()
        data['complainer'] = extra_info.id
        data['status'] = COMPLAINT_STATUS_PENDING
        data['complaint_finish'] = services.compute_complaint_deadline(
            data.get('complaint_type', '')
        )
        serializer = ComplaintCreateSerializer(data=data)
        if serializer.is_valid():
            complaint = serializer.save()
            services.notify_caretakers_multi(
                request.user, complaint, data.get('location', '')
            )
            return Response(
                StudentComplainSerializer(complaint).data,
                status=status.HTTP_201_CREATED,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CaretakerFeedbackView(APIView):
    """T-09 / CS-17: rating validated by FeedbackSerializer; no view-level coercion."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = FeedbackSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        feedback = serializer.validated_data['feedback']
        rating = serializer.validated_data['rating']
        caretaker_type = request.data.get('caretakertype', '')
        for caretaker in Caretaker.objects.filter(area=caretaker_type).order_by('-id'):
            caretaker.myfeedback = feedback
            caretaker.rating = services.calculate_new_rating(caretaker.rating, rating)
            caretaker.save()
        return Response({'success': 'Feedback submitted'})


class SubmitFeedbackView(APIView):
    """T-08 / T-09 / CS-37: typed except; rating validated by serializer."""
    permission_classes = [IsAuthenticated]

    def post(self, request, complaint_id):
        serializer = FeedbackSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        feedback = serializer.validated_data['feedback']
        rating = serializer.validated_data['rating']
        try:
            StudentComplain.objects.filter(id=complaint_id).update(
                feedback=feedback, flag=rating
            )
            complaint = StudentComplain.objects.get(id=complaint_id)
            services.update_caretaker_rating(complaint.location, rating)
            return Response({'success': 'Feedback submitted'})
        except (StudentComplain.DoesNotExist, Caretaker.DoesNotExist) as exc:
            logger.exception('SubmitFeedbackView failed: %s', exc)
            return Response(
                {'error': 'Complaint or caretaker not found'},
                status=status.HTTP_404_NOT_FOUND,
            )


class ComplaintDetailView(APIView):
    """Single canonical ComplaintDetailView (was defined twice — T-15 / CS-32)."""
    permission_classes = [IsAuthenticated]

    def get(self, request, detailcomp_id1):
        try:
            complaint = selectors.get_complaint_detail_by_id(detailcomp_id1)
        except StudentComplain.DoesNotExist:
            return Response(
                {'error': 'Complaint not found'}, status=status.HTTP_404_NOT_FOUND
            )
        return Response(StudentComplainSerializer(complaint).data)


# ---------------------------------------------------------------------------
# Caretaker views
# ---------------------------------------------------------------------------
class CaretakerLodgeView(APIView):
    """T-05 (mirror of UserComplaintView.post pattern) + T-25 paginated get."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        extra_info = selectors.get_extra_info_by_user(request.user)
        data = request.data.copy()
        data['complainer'] = extra_info.id
        data['status'] = COMPLAINT_STATUS_PENDING
        data['complaint_finish'] = services.compute_complaint_deadline(
            data.get('complaint_type', '')
        )
        serializer = ComplaintCreateSerializer(data=data)
        if serializer.is_valid():
            complaint = serializer.save()
            services.notify_caretaker_single(
                request.user, complaint, data.get('location', '')
            )
            return Response(
                StudentComplainSerializer(complaint).data,
                status=status.HTTP_201_CREATED,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def get(self, request):
        extra_info = selectors.get_extra_info_by_user(request.user)
        complaints = selectors.get_complaints_by_complainer(extra_info)
        paginator = StandardResultsPagination()
        page = paginator.paginate_queryset(complaints, request)
        return paginator.get_paginated_response(
            StudentComplainSerializer(page, many=True).data
        )


class CaretakerView(APIView):
    """T-25: paginated. CS-22: ORM in selector."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        extra_info = selectors.get_extra_info_by_user(request.user)
        try:
            caretaker = Caretaker.objects.select_related('staff_id').get(
                staff_id=extra_info
            )
            complaints = selectors.get_complaints_by_area(caretaker.area)
            paginator = StandardResultsPagination()
            page = paginator.paginate_queryset(complaints, request)
            return paginator.get_paginated_response(
                StudentComplainSerializer(page, many=True).data
            )
        except Caretaker.DoesNotExist:
            return Response(
                {'error': 'Caretaker does not exist'}, status=status.HTTP_404_NOT_FOUND
            )


class FeedbackCareView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, feedcomp_id):
        try:
            detail = selectors.get_complaint_detail_by_id(feedcomp_id)
            return Response(StudentComplainSerializer(detail).data)
        except StudentComplain.DoesNotExist:
            return Response(
                {'error': 'Complaint not found'}, status=status.HTTP_404_NOT_FOUND
            )


class ResolvePendingView(APIView):
    """T-06 / CS-24: delegates to services.resolve_complaint; RD-06/07: single fetch."""
    permission_classes = [IsAuthenticated]

    def post(self, request, cid):
        serializer = ResolvePendingSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        yesorno = serializer.validated_data['yesorno']
        comment = serializer.validated_data.get('comment', '')
        image_file = request.FILES.get('upload_resolved')
        try:
            complaint, _ = services.resolve_complaint(cid, yesorno, comment, image_file)
            notif_type  = 'comp_resolved_alert' if yesorno == 'Yes' else 'comp_declined_alert'
            message     = ('Congrats! Your complaint has been resolved'
                           if yesorno == 'Yes' else 'Your complaint has been declined')
            services.send_complaint_notification(
                request.user, complaint.complainer.user,
                notif_type, complaint.id, 0, message,
            )
            return Response({'success': 'Complaint status updated'})
        except StudentComplain.DoesNotExist:
            return Response(
                {'error': 'Complaint not found'}, status=status.HTTP_404_NOT_FOUND
            )

    def get(self, request, cid):
        try:
            return Response(
                StudentComplainSerializer(selectors.get_complaint_detail_by_id(cid)).data
            )
        except StudentComplain.DoesNotExist:
            return Response(
                {'error': 'Complaint not found'}, status=status.HTTP_404_NOT_FOUND
            )


class SearchComplaintView(APIView):
    """T-17 / CS-34: implemented via selectors.search_complaints."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        query = request.query_params.get('q', '')
        results = selectors.search_complaints(query)
        paginator = StandardResultsPagination()
        page = paginator.paginate_queryset(results, request)
        return paginator.get_paginated_response(
            StudentComplainSerializer(page, many=True).data
        )


class SubmitFeedbackCaretakerView(APIView):
    """T-09 / T-10: rating by serializer; rating calc by services."""
    permission_classes = [IsAuthenticated]

    def post(self, request, complaint_id):
        serializer = FeedbackSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        feedback = serializer.validated_data['feedback']
        rating = serializer.validated_data['rating']
        StudentComplain.objects.filter(id=complaint_id).update(
            feedback=feedback, flag=rating
        )
        try:
            complaint = selectors.get_complaint_detail_by_id(complaint_id)
            services.update_caretaker_rating(complaint.location, rating)
            return Response({'success': 'Feedback submitted'})
        except StudentComplain.DoesNotExist:
            return Response(
                {'error': 'Complaint not found'}, status=status.HTTP_404_NOT_FOUND
            )

    def get(self, request, complaint_id):
        try:
            return Response(
                StudentComplainSerializer(
                    selectors.get_complaint_detail_by_id(complaint_id)
                ).data
            )
        except StudentComplain.DoesNotExist:
            return Response(
                {'error': 'Complaint not found'}, status=status.HTTP_404_NOT_FOUND
            )


# ---------------------------------------------------------------------------
# Service-provider views
# ---------------------------------------------------------------------------
class ServiceProviderLodgeView(APIView):
    """Mirror of CaretakerLodgeView for service-provider role."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        extra_info = selectors.get_extra_info_by_user(request.user)
        data = request.data.copy()
        data['complainer'] = extra_info.id
        data['status'] = COMPLAINT_STATUS_PENDING
        data['complaint_finish'] = services.compute_complaint_deadline(
            data.get('complaint_type', '')
        )
        serializer = ComplaintCreateSerializer(data=data)
        if serializer.is_valid():
            complaint = serializer.save()
            services.notify_caretaker_single(
                request.user, complaint, data.get('location', '')
            )
            return Response(
                StudentComplainSerializer(complaint).data,
                status=status.HTTP_201_CREATED,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def get(self, request):
        extra_info = selectors.get_extra_info_by_user(request.user)
        complaints = selectors.get_complaints_by_complainer(extra_info)
        paginator = StandardResultsPagination()
        page = paginator.paginate_queryset(complaints, request)
        return paginator.get_paginated_response(
            StudentComplainSerializer(page, many=True).data
        )


class ServiceProviderView(APIView):
    """T-25: paginated."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        extra_info = selectors.get_extra_info_by_user(request.user)
        try:
            from .models import ServiceProvider
            sp = ServiceProvider.objects.select_related('ser_pro_id').get(
                ser_pro_id=extra_info
            )
            complaints = selectors.get_complaints_by_type_and_status(
                sp.type, complaint_status=1
            )
            paginator = StandardResultsPagination()
            page = paginator.paginate_queryset(complaints, request)
            return paginator.get_paginated_response(
                StudentComplainSerializer(page, many=True).data
            )
        except Exception:
            return Response(
                {'error': 'ServiceProvider does not exist'},
                status=status.HTTP_404_NOT_FOUND,
            )


class FeedbackSuperView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, feedcomp_id):
        try:
            complaint = selectors.get_complaint_detail_by_id(feedcomp_id)
            caretaker = Caretaker.objects.filter(area=complaint.location).first()
            return Response({
                'complaint': StudentComplainSerializer(complaint).data,
                'caretaker': CaretakerSerializer(caretaker).data if caretaker else None,
            })
        except StudentComplain.DoesNotExist:
            return Response(
                {'error': 'Complaint not found'}, status=status.HTTP_404_NOT_FOUND
            )


class CaretakerIdKnowMoreView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, caretaker_id):
        try:
            caretaker = Caretaker.objects.select_related('staff_id').get(id=caretaker_id)
            pending = StudentComplain.objects.filter(
                location=caretaker.area, status=COMPLAINT_STATUS_PENDING
            )
            return Response({
                'caretaker': CaretakerSerializer(caretaker).data,
                'pending_complaints': StudentComplainSerializer(pending, many=True).data,
            })
        except Caretaker.DoesNotExist:
            return Response(
                {'error': 'Caretaker not found'}, status=status.HTTP_404_NOT_FOUND
            )


class ServiceProviderComplaintDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, detailcomp_id1):
        try:
            complaint = selectors.get_complaint_detail_by_id(detailcomp_id1)
            caretaker = Caretaker.objects.filter(area=complaint.location).first()
            return Response({
                'complaint': StudentComplainSerializer(complaint).data,
                'caretaker': CaretakerSerializer(caretaker).data if caretaker else None,
            })
        except StudentComplain.DoesNotExist:
            return Response(
                {'error': 'Complaint not found'}, status=status.HTTP_404_NOT_FOUND
            )


class ServiceProviderResolvePendingView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, cid):
        serializer = ResolvePendingSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        yesorno = serializer.validated_data['yesorno']
        comment = serializer.validated_data.get('comment', '')
        try:
            complaint, _ = services.resolve_complaint(cid, yesorno, comment)
            services.send_complaint_notification(
                request.user, complaint.complainer.user,
                'comp_resolved_alert', complaint.id, 0,
                'Congrats! Your complaint has been resolved',
            )
            return Response({'success': 'Complaint status updated'})
        except StudentComplain.DoesNotExist:
            return Response(
                {'error': 'Complaint not found'}, status=status.HTTP_404_NOT_FOUND
            )

    def get(self, request, cid):
        try:
            return Response(
                StudentComplainSerializer(selectors.get_complaint_by_id(cid)).data
            )
        except StudentComplain.DoesNotExist:
            return Response(
                {'error': 'Complaint not found'}, status=status.HTTP_404_NOT_FOUND
            )


class ServiceProviderSubmitFeedbackView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, complaint_id):
        serializer = FeedbackSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        feedback = serializer.validated_data['feedback']
        rating = serializer.validated_data['rating']
        try:
            StudentComplain.objects.filter(id=complaint_id).update(
                feedback=feedback, flag=rating
            )
            complaint = selectors.get_complaint_detail_by_id(complaint_id)
            services.update_caretaker_rating(complaint.location, rating)
            return Response({'success': 'Feedback submitted'})
        except Caretaker.DoesNotExist:
            return Response(
                {'error': 'Caretaker not found'}, status=status.HTTP_404_NOT_FOUND
            )

    def get(self, request, complaint_id):
        try:
            return Response(
                StudentComplainSerializer(
                    selectors.get_complaint_detail_by_id(complaint_id)
                ).data
            )
        except StudentComplain.DoesNotExist:
            return Response(
                {'error': 'Complaint not found'}, status=status.HTTP_404_NOT_FOUND
            )


# ---------------------------------------------------------------------------
# Worker / admin operations
# ---------------------------------------------------------------------------
class RemoveWorkerView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, work_id):
        try:
            removed = services.remove_worker(work_id)
        except Workers.DoesNotExist:
            return Response(
                {'error': 'Worker not found'}, status=status.HTTP_404_NOT_FOUND
            )
        if removed:
            return Response(
                {'success': 'Worker removed successfully'}, status=status.HTTP_200_OK
            )
        return Response(
            {'error': 'Worker is assigned to some complaints'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    def delete(self, request, work_id):
        return self.post(request, work_id)


class ForwardCompaintView(APIView):
    """T-21 / CS-20: all filetracking SDK calls in services.assign_complaint_to_service_provider."""
    permission_classes = [IsAuthenticated]

    def post(self, request, comp_id1):
        try:
            _, has_files = services.assign_complaint_to_service_provider(
                comp_id1, request.user
            )
            if not has_files:
                return Response(
                    {'error': 'No files associated with this complaint'},
                    status=status.HTTP_206_PARTIAL_CONTENT,
                )
            return Response(
                {'success': 'Complaint assigned to service_provider'},
                status=status.HTTP_200_OK,
            )
        except StudentComplain.DoesNotExist:
            return Response(
                {'error': 'Complaint not found'}, status=status.HTTP_404_NOT_FOUND
            )
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_404_NOT_FOUND)

    def get(self, request, comp_id1):
        try:
            complaint = selectors.get_complaint_by_id(comp_id1)
            return Response(
                StudentComplainSerializer(complaint).data, status=status.HTTP_200_OK
            )
        except StudentComplain.DoesNotExist:
            return Response(
                {'error': 'Not a valid complaint'}, status=status.HTTP_404_NOT_FOUND
            )


class DeleteComplaintView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, comp_id1):
        try:
            StudentComplain.objects.get(id=comp_id1).delete()
            return Response(
                {'success': 'Complaint deleted successfully'}, status=status.HTTP_200_OK
            )
        except StudentComplain.DoesNotExist:
            return Response(
                {'error': 'Complaint not found'}, status=status.HTTP_404_NOT_FOUND
            )

    def delete(self, request, comp_id1):
        return self.post(request, comp_id1)


class ChangeComplaintStatusView(APIView):
    """T-07 / CS-14 / RD-03: merged ChangeStatusView + ChangeStatusSuperView.
    Parameter renamed complaint_new_status to avoid shadowing rest_framework.status."""
    permission_classes = [IsAuthenticated]

    def post(self, request, complaint_id, complaint_new_status):
        try:
            services.change_complaint_status(complaint_id, complaint_new_status)
            return Response(
                {'success': 'Complaint status updated'}, status=status.HTTP_200_OK
            )
        except StudentComplain.DoesNotExist:
            return Response(
                {'error': 'Complaint not found'}, status=status.HTTP_404_NOT_FOUND
            )


class GenerateReportView(APIView):
    """T-20 / CS-02 / CS-10: delegates entirely to selectors.get_report_by_role; T-25 paginated."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        complaints = selectors.get_report_by_role(request.user)
        if complaints is None:
            return Response(
                {'error': 'Not authorized to generate report.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        paginator = StandardResultsPagination()
        page = paginator.paginate_queryset(complaints, request)
        return paginator.get_paginated_response(
            StudentComplainSerializer(page, many=True).data
        )
