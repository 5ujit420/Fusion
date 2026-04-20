# api/views.py
# T-14 / CS-29: Fixed N+1 in complaint_details_api — select_related on initial query.
# T-19 / CS-38: Replaced HTTP_203_NON_AUTHORITATIVE_INFORMATION with HTTP_403_FORBIDDEN.
# T-12 / CS-31: Updated imports to use renamed serializer classes (*Serializer singular).

from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from applications.globals.models import User, ExtraInfo
from applications.complaint_system.models import Caretaker, StudentComplain, ServiceProvider, Workers
from . import serializers


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
def complaint_details_api(request, detailcomp_id1):
    """T-14 / CS-29: Fixed N+1 — single query with select_related instead of 3 separate queries."""
    try:
        complaint_detail = StudentComplain.objects.select_related(
            'complainer__user', 'complainer__department', 'worker_id'
        ).get(id=detailcomp_id1)
    except StudentComplain.DoesNotExist:
        return Response({'error': 'Complaint not found'}, status=status.HTTP_404_NOT_FOUND)

    complaint_detail_serialized = serializers.StudentComplainSerializer(
        instance=complaint_detail
    ).data

    if complaint_detail.worker_id is None:
        worker_detail_serialized = {}
    else:
        worker_detail_serialized = serializers.WorkersSerializer(
            instance=complaint_detail.worker_id
        ).data

    # complainer data already prefetched via select_related
    complainer_serialized = serializers.UserSerializer(
        instance=complaint_detail.complainer.user
    ).data
    complainer_extra_info_serialized = serializers.ExtraInfoSerializer(
        instance=complaint_detail.complainer
    ).data

    return Response(data={
        'complainer': complainer_serialized,
        'complainer_extra_info': complainer_extra_info_serialized,
        'complaint_details': complaint_detail_serialized,
        'worker_details': worker_detail_serialized,
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
def student_complain_api(request):
    user = get_object_or_404(User, username=request.user.username)
    extra_info = ExtraInfo.objects.filter(user=user).first()
    if extra_info.user_type == 'student':
        complain = StudentComplain.objects.filter(complainer=extra_info)
    elif extra_info.user_type == 'staff':
        caretaker = Caretaker.objects.get(staff_id=extra_info)
        complain = StudentComplain.objects.filter(location=caretaker.area)
    elif extra_info.user_type == 'faculty':
        sp = ServiceProvider.objects.get(ser_pro_id=extra_info)
        complain = StudentComplain.objects.filter(complaint_type=sp.type)
    else:
        complain = StudentComplain.objects.none()
    return Response(data={
        'student_complain': serializers.StudentComplainSerializer(complain, many=True).data
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
def create_complain_api(request):
    ser = serializers.StudentComplainSerializer(data=request.data)
    if ser.is_valid():
        ser.save()
        return Response(ser.data, status=status.HTTP_201_CREATED)
    return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE', 'PUT'])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
def edit_complain_api(request, c_id):
    try:
        complain = StudentComplain.objects.get(id=c_id)
    except StudentComplain.DoesNotExist:
        return Response({'error': 'The complaint does not exist'}, status=status.HTTP_404_NOT_FOUND)
    if request.method == 'DELETE':
        complain.delete()
        return Response({'message': 'Complaint deleted'}, status=status.HTTP_204_NO_CONTENT)
    ser = serializers.StudentComplainSerializer(complain, data=request.data)
    if ser.is_valid():
        ser.save()
        return Response(ser.data, status=status.HTTP_200_OK)
    return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
def worker_api(request):
    if request.method == 'GET':
        workers = serializers.WorkersSerializer(Workers.objects.all(), many=True).data
        return Response({'workers': workers}, status=status.HTTP_200_OK)

    # POST — only caretakers may add workers
    user = get_object_or_404(User, username=request.user.username)
    extra_info = ExtraInfo.objects.filter(user=user).first()
    try:
        Caretaker.objects.get(staff_id=extra_info)
    except Caretaker.DoesNotExist:
        return Response(
            {'error': 'Logged in user does not have the permissions'},
            status=status.HTTP_403_FORBIDDEN,   # T-19: was 203
        )
    ser = serializers.WorkersSerializer(data=request.data)
    if ser.is_valid():
        ser.save()
        return Response(ser.data, status=status.HTTP_201_CREATED)
    return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE', 'PUT'])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
def edit_worker_api(request, w_id):
    user = get_object_or_404(User, username=request.user.username)
    extra_info = ExtraInfo.objects.filter(user=user).first()
    try:
        Caretaker.objects.get(staff_id=extra_info)
    except Caretaker.DoesNotExist:
        return Response(
            {'error': 'Logged in user does not have the permissions'},
            status=status.HTTP_403_FORBIDDEN,   # T-19: was 203
        )
    try:
        worker = Workers.objects.get(id=w_id)
    except Workers.DoesNotExist:
        return Response({'error': 'The worker does not exist'}, status=status.HTTP_404_NOT_FOUND)
    if request.method == 'DELETE':
        worker.delete()
        return Response({'message': 'Worker deleted'}, status=status.HTTP_204_NO_CONTENT)
    ser = serializers.WorkersSerializer(worker, data=request.data)
    if ser.is_valid():
        ser.save()
        return Response(ser.data, status=status.HTTP_200_OK)
    return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
def caretaker_api(request):
    if request.method == 'GET':
        return Response(
            {'caretakers': serializers.CaretakerSerializer(Caretaker.objects.all(), many=True).data},
            status=status.HTTP_200_OK,
        )
    user = get_object_or_404(User, username=request.user.username)
    extra_info = ExtraInfo.objects.filter(user=user).first()
    try:
        ServiceProvider.objects.get(ser_pro_id=extra_info)
    except ServiceProvider.DoesNotExist:
        return Response(
            {'error': 'Logged in user does not have the permissions'},
            status=status.HTTP_403_FORBIDDEN,   # T-19: was 203
        )
    ser = serializers.CaretakerSerializer(data=request.data)
    if ser.is_valid():
        ser.save()
        return Response(ser.data, status=status.HTTP_201_CREATED)
    return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE', 'PUT'])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
def edit_caretaker_api(request, c_id):
    user = get_object_or_404(User, username=request.user.username)
    extra_info = ExtraInfo.objects.filter(user=user).first()
    try:
        ServiceProvider.objects.get(ser_pro_id=extra_info)
    except ServiceProvider.DoesNotExist:
        return Response(
            {'error': 'Logged in user does not have the permissions'},
            status=status.HTTP_403_FORBIDDEN,
        )
    try:
        caretaker = Caretaker.objects.get(id=c_id)
    except Caretaker.DoesNotExist:
        return Response({'error': 'The caretaker does not exist'}, status=status.HTTP_404_NOT_FOUND)
    if request.method == 'DELETE':
        caretaker.delete()
        return Response({'message': 'Caretaker deleted'}, status=status.HTTP_204_NO_CONTENT)
    ser = serializers.CaretakerSerializer(caretaker, data=request.data)
    if ser.is_valid():
        ser.save()
        return Response(ser.data, status=status.HTTP_200_OK)
    return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
def service_provider_api(request):
    if request.method == 'GET':
        return Response(
            {'service_providers': serializers.ServiceProviderSerializer(
                ServiceProvider.objects.all(), many=True
            ).data},
            status=status.HTTP_200_OK,
        )
    user = get_object_or_404(User, username=request.user.username)
    if not user.is_superuser:
        return Response(
            {'error': 'Logged in user does not have permission'},
            status=status.HTTP_403_FORBIDDEN,
        )
    ser = serializers.ServiceProviderSerializer(data=request.data)
    if ser.is_valid():
        ser.save()
        return Response(ser.data, status=status.HTTP_201_CREATED)
    return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE', 'PUT'])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
def edit_service_provider_api(request, s_id):
    user = get_object_or_404(User, username=request.user.username)
    if not user.is_superuser:
        return Response(
            {'error': 'Logged in user does not have permission'},
            status=status.HTTP_403_FORBIDDEN,
        )
    try:
        sp = ServiceProvider.objects.get(id=s_id)
    except ServiceProvider.DoesNotExist:
        return Response({'error': 'The service provider does not exist'}, status=status.HTTP_404_NOT_FOUND)
    if request.method == 'DELETE':
        sp.delete()
        return Response({'message': 'Service provider deleted'}, status=status.HTTP_204_NO_CONTENT)
    ser = serializers.ServiceProviderSerializer(sp, data=request.data)
    if ser.is_valid():
        ser.save()
        return Response(ser.data, status=status.HTTP_200_OK)
    return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)
