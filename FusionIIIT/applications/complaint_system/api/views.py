# api/views.py
# Class-based API views for the complaint_system module.
# All DB queries delegated to selectors, business logic to services.
# Addresses: RR-19 (deprecated url/FBV), RR-20 (worker_detail bug)

from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication
from rest_framework.response import Response
from rest_framework import status

from applications.complaint_system import selectors, services
from applications.complaint_system.models import (
    StudentComplain, Workers, Caretaker, ServiceProvider,
)
from .serializers import (
    StudentComplainSerializer,
    WorkersSerializer,
    CaretakerSerializer,
    ServiceProviderSerializer,
    ExtraInfoSerializer,
    UserSerializer,
)


class ComplaintDetailAPIView(APIView):
    """
    RR-20 fix: Uses Workers model (not 'worker_detail' variable).
    Delegates detail assembly to services.get_complaint_detail_for_api().
    """
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
    """List complaints for the logged-in user based on their role."""
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        complaints = services.get_complaints_for_user(request.user)
        serialized = StudentComplainSerializer(complaints, many=True).data
        return Response(data={'student_complain': serialized}, status=status.HTTP_200_OK)


class CreateComplainAPIView(APIView):
    """Create a new complaint."""
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = StudentComplainSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class EditComplainAPIView(APIView):
    """Edit or delete a complaint by ID."""
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def delete(self, request, c_id):
        try:
            complaint = selectors.get_complaint_by_id_basic(c_id)
        except StudentComplain.DoesNotExist:
            return Response({'message': 'The Complain does not exist'}, status=status.HTTP_404_NOT_FOUND)
        complaint.delete()
        return Response({'message': 'Complain deleted'}, status=status.HTTP_200_OK)

    def put(self, request, c_id):
        try:
            complaint = selectors.get_complaint_by_id_basic(c_id)
        except StudentComplain.DoesNotExist:
            return Response({'message': 'The Complain does not exist'}, status=status.HTTP_404_NOT_FOUND)
        serializer = StudentComplainSerializer(complaint, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class WorkerAPIView(APIView):
    """List all workers (GET) or create a new worker (POST)."""
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
        serializer = WorkersSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class EditWorkerAPIView(APIView):
    """Edit or delete a worker by ID."""
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def _check_caretaker(self, request):
        extra = selectors.get_extrainfo_by_user(request.user)
        if not selectors.is_caretaker(extra.id):
            return Response(
                {'message': 'Logged in user does not have the permissions'},
                status=status.HTTP_403_FORBIDDEN,
            )
        return None

    def delete(self, request, w_id):
        error_resp = self._check_caretaker(request)
        if error_resp:
            return error_resp
        try:
            worker = selectors.get_worker_by_id(w_id)
        except Workers.DoesNotExist:
            return Response({'message': 'The worker does not exist'}, status=status.HTTP_404_NOT_FOUND)
        worker.delete()
        return Response({'message': 'Worker deleted'}, status=status.HTTP_200_OK)

    def put(self, request, w_id):
        error_resp = self._check_caretaker(request)
        if error_resp:
            return error_resp
        try:
            worker = selectors.get_worker_by_id(w_id)
        except Workers.DoesNotExist:
            return Response({'message': 'The worker does not exist'}, status=status.HTTP_404_NOT_FOUND)
        serializer = WorkersSerializer(worker, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CaretakerAPIView(APIView):
    """List all caretakers (GET) or create a new caretaker (POST)."""
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
        serializer = CaretakerSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class EditCaretakerAPIView(APIView):
    """Edit or delete a caretaker by ID."""
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def _check_service_provider(self, request):
        extra = selectors.get_extrainfo_by_user(request.user)
        if not selectors.is_service_provider(extra.id):
            return Response(
                {'message': 'Logged in user does not have the permissions'},
                status=status.HTTP_403_FORBIDDEN,
            )
        return None

    def delete(self, request, c_id):
        error_resp = self._check_service_provider(request)
        if error_resp:
            return error_resp
        try:
            caretaker = selectors.get_caretaker_by_pk(c_id)
        except Caretaker.DoesNotExist:
            return Response({'message': 'The Caretaker does not exist'}, status=status.HTTP_404_NOT_FOUND)
        caretaker.delete()
        return Response({'message': 'Caretaker deleted'}, status=status.HTTP_200_OK)

    def put(self, request, c_id):
        error_resp = self._check_service_provider(request)
        if error_resp:
            return error_resp
        try:
            caretaker = selectors.get_caretaker_by_pk(c_id)
        except Caretaker.DoesNotExist:
            return Response({'message': 'The Caretaker does not exist'}, status=status.HTTP_404_NOT_FOUND)
        serializer = CaretakerSerializer(caretaker, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ServiceProviderAPIView(APIView):
    """List all service providers (GET) or create one (POST, superuser only)."""
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
        serializer = ServiceProviderSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class EditServiceProviderAPIView(APIView):
    """Edit or delete a service provider by ID (superuser only)."""
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def delete(self, request, s_id):
        if not request.user.is_superuser:
            return Response(
                {'message': 'Logged in user does not have permission'},
                status=status.HTTP_403_FORBIDDEN,
            )
        try:
            sp = selectors.get_service_provider_by_pk(s_id)
        except ServiceProvider.DoesNotExist:
            return Response({'message': 'The ServiceProvider does not exist'}, status=status.HTTP_404_NOT_FOUND)
        sp.delete()
        return Response({'message': 'ServiceProvider deleted'}, status=status.HTTP_200_OK)

    def put(self, request, s_id):
        if not request.user.is_superuser:
            return Response(
                {'message': 'Logged in user does not have permission'},
                status=status.HTTP_403_FORBIDDEN,
            )
        try:
            sp = selectors.get_service_provider_by_pk(s_id)
        except ServiceProvider.DoesNotExist:
            return Response({'message': 'The ServiceProvider does not exist'}, status=status.HTTP_404_NOT_FOUND)
        serializer = ServiceProviderSerializer(sp, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
