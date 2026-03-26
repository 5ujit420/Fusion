from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication
from rest_framework.response import Response
from rest_framework import status

from applications.complaint_system import selectors, services
from applications.complaint_system.models import (
    StudentComplain, Workers, Caretaker, ServiceProvider,
)
from applications.complaint_system.permissions import (
    IsCaretaker,
    IsServiceProvider,
    IsCaretakerOrServiceProvider,
    IsComplaintOwnerOrStaff,
    IsReportAuthorized,
    IsSuperUser,
)
from .serializers import (
    StudentComplainSerializer,
    WorkersSerializer,
    CaretakerSerializer,
    ServiceProviderSerializer,
    ExtraInfoSerializer,
    UserSerializer,
    FeedbackSerializer,
    ResolvePendingSerializer,
)


# ===================================================================
#  USER VIEWS
# ===================================================================

class CheckUser(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user_type, next_url = services.determine_user_type(request.user)
        if user_type is None:
            return Response({'error': 'wrong user credentials'}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'user_type': user_type, 'next_url': next_url})


class UserComplaintView(APIView):
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
    permission_classes = [IsAuthenticated, IsCaretaker]

    def get(self, request, feedcomp_id):
        try:
            complaint = selectors.get_complaint_by_id(feedcomp_id)
            serializer = StudentComplainSerializer(complaint)
            return Response(serializer.data)
        except StudentComplain.DoesNotExist:
            return Response({'error': 'Complaint not found'}, status=status.HTTP_404_NOT_FOUND)


class ResolvePendingView(APIView):
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
    permission_classes = [IsAuthenticated, IsCaretaker]

    def get(self, request):
        complaints = selectors.get_all_complaints()
        serializer = StudentComplainSerializer(complaints, many=True)
        return Response(serializer.data)


class SubmitFeedbackCaretakerView(APIView):
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
    permission_classes = [IsAuthenticated, IsReportAuthorized]

    def get(self, request):
        complaints, error = services.generate_report(request.user)
        if error:
            return Response({'detail': error}, status=status.HTTP_403_FORBIDDEN)
        serializer = StudentComplainSerializer(complaints, many=True)
        return Response(serializer.data)


# ===================================================================
#  TOKEN-AUTH API VIEWS (CRUD)
# ===================================================================

class ComplaintDetailAPIView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, detailcomp_id1):
        try:
            detail = services.get_complaint_detail_for_api(detailcomp_id1)
        except StudentComplain.DoesNotExist:
            return Response({'error': 'Complaint not found'}, status=status.HTTP_404_NOT_FOUND)

        response = {
            'complainer': UserSerializer(instance=detail['complainer_user']).data,
            'complainer_extra_info': ExtraInfoSerializer(instance=detail['complainer_extra_info']).data,
            'complaint_details': StudentComplainSerializer(instance=detail['complaint']).data,
            'worker_details': detail['worker_data'],
        }
        return Response(data=response, status=status.HTTP_200_OK)


class StudentComplainAPIView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        complaints = services.get_complaints_for_user(request.user)
        serialized = StudentComplainSerializer(complaints, many=True).data
        return Response(data={'student_complain': serialized}, status=status.HTTP_200_OK)


class CreateComplainAPIView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            complaint, data = services.create_complaint(request.data)
            return Response(data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class EditComplainAPIView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def delete(self, request, c_id):
        try:
            services.delete_complaint_by_id(c_id)
            return Response({'message': 'Complain deleted'}, status=status.HTTP_200_OK)
        except StudentComplain.DoesNotExist:
            return Response({'message': 'The Complain does not exist'}, status=status.HTTP_404_NOT_FOUND)

    def put(self, request, c_id):
        try:
            complaint, data = services.update_complaint(c_id, request.data)
            return Response(data, status=status.HTTP_200_OK)
        except StudentComplain.DoesNotExist:
            return Response({'message': 'The Complain does not exist'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class WorkerAPIView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        workers = selectors.get_all_workers()
        serialized = WorkersSerializer(workers, many=True).data
        return Response(data={'workers': serialized}, status=status.HTTP_200_OK)

    def post(self, request):
        extra = selectors.get_extrainfo_by_user(request.user)
        if not selectors.is_caretaker(extra.id):
            return Response(
                {'message': 'Logged in user does not have the permissions'},
                status=status.HTTP_403_FORBIDDEN,
            )
        try:
            worker, data = services.create_worker(request.data)
            return Response(data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class EditWorkerAPIView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated, IsCaretaker]

    def delete(self, request, w_id):
        try:
            services.delete_worker(w_id)
            return Response({'message': 'Worker deleted'}, status=status.HTTP_200_OK)
        except Workers.DoesNotExist:
            return Response({'message': 'The worker does not exist'}, status=status.HTTP_404_NOT_FOUND)

    def put(self, request, w_id):
        try:
            worker, data = services.update_worker(w_id, request.data)
            return Response(data, status=status.HTTP_200_OK)
        except Workers.DoesNotExist:
            return Response({'message': 'The worker does not exist'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class CaretakerAPIView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        caretakers = selectors.get_all_caretakers()
        serialized = CaretakerSerializer(caretakers, many=True).data
        return Response(data={'caretakers': serialized}, status=status.HTTP_200_OK)

    def post(self, request):
        extra = selectors.get_extrainfo_by_user(request.user)
        if not selectors.is_service_provider(extra.id):
            return Response(
                {'message': 'Logged in user does not have the permissions'},
                status=status.HTTP_403_FORBIDDEN,
            )
        try:
            caretaker, data = services.create_caretaker(request.data)
            return Response(data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class EditCaretakerAPIView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated, IsServiceProvider]

    def delete(self, request, c_id):
        try:
            services.delete_caretaker(c_id)
            return Response({'message': 'Caretaker deleted'}, status=status.HTTP_200_OK)
        except Caretaker.DoesNotExist:
            return Response({'message': 'The Caretaker does not exist'}, status=status.HTTP_404_NOT_FOUND)

    def put(self, request, c_id):
        try:
            caretaker, data = services.update_caretaker(c_id, request.data)
            return Response(data, status=status.HTTP_200_OK)
        except Caretaker.DoesNotExist:
            return Response({'message': 'The Caretaker does not exist'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ServiceProviderAPIView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        service_providers = selectors.get_all_service_providers()
        serialized = ServiceProviderSerializer(service_providers, many=True).data
        return Response(data={'service_providers': serialized}, status=status.HTTP_200_OK)

    def post(self, request):
        if not request.user.is_superuser:
            return Response(
                {'message': 'Logged in user does not have permission'},
                status=status.HTTP_403_FORBIDDEN,
            )
        try:
            sp, data = services.create_service_provider(request.data)
            return Response(data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class EditServiceProviderAPIView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated, IsSuperUser]

    def delete(self, request, s_id):
        try:
            services.delete_service_provider(s_id)
            return Response({'message': 'ServiceProvider deleted'}, status=status.HTTP_200_OK)
        except ServiceProvider.DoesNotExist:
            return Response({'message': 'The ServiceProvider does not exist'}, status=status.HTTP_404_NOT_FOUND)

    def put(self, request, s_id):
        try:
            sp, data = services.update_service_provider(s_id, request.data)
            return Response(data, status=status.HTTP_200_OK)
        except ServiceProvider.DoesNotExist:
            return Response({'message': 'The ServiceProvider does not exist'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
