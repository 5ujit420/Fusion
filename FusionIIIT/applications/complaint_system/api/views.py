from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404

from applications.complaint_system.models import StudentComplain
from applications.complaint_system import selectors
from applications.complaint_system import services
from . import serializers

class CheckUserRoleView(APIView):
    """
    Returns the roles of the current user. Replaces the legacy Checkout User view.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        extrainfo = selectors.get_extrainfo_by_user(request.user)
        roles = selectors.check_user_roles(extrainfo)
        return Response(roles, status=status.HTTP_200_OK)


class ComplaintListView(APIView):
    """
    Handles Listing complaints for the current user and Lodging a new one.
    Replaces UserComplaintView / CaretakerLodgeView / ServiceProviderLodgeView.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        extrainfo = selectors.get_extrainfo_by_user(request.user)
        complaints = selectors.get_complaints_by_complainer(extrainfo)
        serializer = serializers.StudentComplainSerializer(complaints, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        extrainfo = selectors.get_extrainfo_by_user(request.user)
        serializer = serializers.StudentComplainSerializer(data=request.data)
        
        if serializer.is_valid():
            try:
                complaint = services.lodge_complaint(
                    user=request.user,
                    complainer_extra_info=extrainfo,
                    data=serializer.validated_data
                )
                output = serializers.StudentComplainSerializer(complaint)
                return Response(output.data, status=status.HTTP_201_CREATED)
            except Exception as e:
                return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ComplaintDetailView(APIView):
    """
    Retrieves, updates, or deletes a specific complaint.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            complaint = selectors.get_complaint_detail_by_id(pk)
            serializer = serializers.StudentComplainSerializer(complaint)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except StudentComplain.DoesNotExist:
            return Response({'error': 'Complaint not found'}, status=status.HTTP_404_NOT_FOUND)

    def delete(self, request, pk):
        try:
            complaint = selectors.get_complaint_by_id(pk)
            complaint.delete()
            return Response({'message': 'Complaint deleted'}, status=status.HTTP_204_NO_CONTENT)
        except StudentComplain.DoesNotExist:
            return Response({'error': 'Complaint not found'}, status=status.HTTP_404_NOT_FOUND)

    def put(self, request, pk):
        try:
            complaint = selectors.get_complaint_by_id(pk)
            serializer = serializers.StudentComplainSerializer(complaint, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except StudentComplain.DoesNotExist:
            return Response({'error': 'Complaint not found'}, status=status.HTTP_404_NOT_FOUND)


class ResolvePendingView(APIView):
    """
    Resolves a complaint (accept/decline) with optional image upload.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            complaint = selectors.get_complaint_by_id(pk)
        except StudentComplain.DoesNotExist:
            return Response({'error': 'Complaint not found'}, status=status.HTTP_404_NOT_FOUND)

        serializer = serializers.ResolvePendingSerializer(data=request.data)
        if serializer.is_valid():
            try:
                complaint = services.resolve_complaint(
                    user=request.user,
                    complaint=complaint,
                    status_yes_no=serializer.validated_data['yesorno'],
                    comment=serializer.validated_data.get('comment', ''),
                    upload_resolved=serializer.validated_data.get('upload_resolved')
                )
                output = serializers.StudentComplainSerializer(complaint)
                return Response(output.data, status=status.HTTP_200_OK)
            except Exception as e:
                return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class SubmitFeedbackView(APIView):
    """
    Submits specific feedback/rating for a complaint and recalculates caretaker ratings.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            complaint = selectors.get_complaint_by_id(pk)
        except StudentComplain.DoesNotExist:
            return Response({'error': 'Complaint not found'}, status=status.HTTP_404_NOT_FOUND)

        serializer = serializers.FeedbackSerializer(data=request.data)
        if serializer.is_valid():
            services.submit_complaint_feedback(
                complaint=complaint,
                rating=serializer.validated_data['rating'],
                feedback=serializer.validated_data.get('feedback', '')
            )
            return Response({'message': 'Feedback submitted successfully'}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ForwardComplaintView(APIView):
    """
    Assigns the complaint to a service provider worker.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            complaint = selectors.get_complaint_by_id(pk)
            complaint = services.assign_worker_to_complaint(request.user, complaint)
            return Response({'message': 'Complaint forwarded successfully'}, status=status.HTTP_200_OK)
        except StudentComplain.DoesNotExist:
            return Response({'error': 'Complaint not found'}, status=status.HTTP_404_NOT_FOUND)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ChangeComplaintStatusView(APIView):
    """
    Allows arbitrary change of status.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk, status_str):
        try:
            complaint = selectors.get_complaint_by_id(pk)
            services.change_complaint_status(complaint, status_str)
            return Response({'message': 'Status updated successfully'}, status=status.HTTP_200_OK)
        except StudentComplain.DoesNotExist:
            return Response({'error': 'Complaint not found'}, status=status.HTTP_404_NOT_FOUND)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class GenerateReportView(APIView):
    """
    Returns complaints mapped specifically to the requesting user's roles.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        extrainfo = selectors.get_extrainfo_by_user(request.user)
        complaints = selectors.get_report_complaints_for_user(request.user, extrainfo)
        
        if complaints.exists():
            serializer = serializers.StudentComplainSerializer(complaints, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response({"detail": "Not authorized to generate report or no complaints found."}, status=status.HTTP_403_FORBIDDEN)


class WorkerListView(APIView):
    """
    List or add workers.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        workers = selectors.get_all_workers()
        serializer = serializers.WorkersSerializer(workers, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        extrainfo = selectors.get_extrainfo_by_user(request.user)
        if not selectors.check_user_roles(extrainfo)['is_caretaker']:
            return Response({'message': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)
            
        serializer = serializers.WorkersSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class WorkerDetailView(APIView):
    """
    Update or delete a worker.
    """
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        extrainfo = selectors.get_extrainfo_by_user(request.user)
        if not selectors.check_user_roles(extrainfo)['is_caretaker']:
            return Response({'message': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)
            
        try:
            worker = selectors.get_worker_by_id(pk)
            removed = services.remove_worker(worker)
            if removed:
                return Response({'message': 'Worker deleted'}, status=status.HTTP_204_NO_CONTENT)
            return Response({'error': 'Worker is assigned to some complaints'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            return Response({'error': 'Worker not found'}, status=status.HTTP_404_NOT_FOUND)

    def put(self, request, pk):
        extrainfo = selectors.get_extrainfo_by_user(request.user)
        if not selectors.check_user_roles(extrainfo)['is_caretaker']:
            return Response({'message': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)
            
        try:
            worker = selectors.get_worker_by_id(pk)
            serializer = serializers.WorkersSerializer(worker, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception:
             return Response({'error': 'Worker not found'}, status=status.HTTP_404_NOT_FOUND)


class CaretakerListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        caretakers = selectors.get_all_caretakers()
        serializer = serializers.CaretakerSerializer(caretakers, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        extrainfo = selectors.get_extrainfo_by_user(request.user)
        if not selectors.check_user_roles(extrainfo)['is_service_provider']:
            return Response({'message': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)
            
        serializer = serializers.CaretakerSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CaretakerDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        extrainfo = selectors.get_extrainfo_by_user(request.user)
        if not selectors.check_user_roles(extrainfo)['is_service_provider']:
            return Response({'message': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)
        
        try:
            caretaker = selectors.get_caretaker_by_id(pk)
            caretaker.delete()
            return Response({'message': 'Deleted'}, status=status.HTTP_204_NO_CONTENT)
        except Exception:
            return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)

    def put(self, request, pk):
        extrainfo = selectors.get_extrainfo_by_user(request.user)
        if not selectors.check_user_roles(extrainfo)['is_service_provider']:
            return Response({'message': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)
            
        try:
            caretaker = selectors.get_caretaker_by_id(pk)
            serializer = serializers.CaretakerSerializer(caretaker, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)


class ServiceProviderListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        providers = selectors.get_all_service_providers()
        serializer = serializers.ServiceProviderSerializer(providers, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        if not request.user.is_superuser:
            return Response({'message': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)
        serializer = serializers.ServiceProviderSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ServiceProviderDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        if not request.user.is_superuser:
            return Response({'message': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)
        try:
            sp = selectors.get_all_service_providers().get(id=pk)
            sp.delete()
            return Response({'message': 'Deleted'}, status=status.HTTP_204_NO_CONTENT)
        except Exception:
            return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)

    def put(self, request, pk):
        if not request.user.is_superuser:
            return Response({'message': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)
        try:
            sp = selectors.get_all_service_providers().get(id=pk)
            serializer = serializers.ServiceProviderSerializer(sp, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)
