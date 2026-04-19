from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.authentication import TokenAuthentication
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from applications.globals.models import User

from applications.complaint_system import selectors, services
from applications.complaint_system.models import ServiceProvider, StudentComplain, Workers
from applications.complaint_system.serializers import (
    CaretakerSerializer,
    ExtraInfoSerializer,
    ServiceProviderSerializer,
    StudentComplainInputSerializer,
    StudentComplainOutputSerializer,
    UserSerializer,
    WorkersSerializer,
)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
def complaint_details_api(request, detailcomp_id1):
    complaint_detail = selectors.get_complaint(detailcomp_id1, selectors.COMPLAINT_RELATED_FIELDS)
    complaint_detail_serialized = StudentComplainOutputSerializer(instance=complaint_detail).data
    if complaint_detail.worker_id is None:
        worker_detail_serialized = {}
    else:
        worker_detail = selectors.get_worker_by_id(complaint_detail.worker_id_id)
        worker_detail_serialized = WorkersSerializer(instance=worker_detail).data
    complainer = complaint_detail.complainer.user
    complainer_serialized = UserSerializer(instance=complainer).data
    complainer_extra_info_serialized = ExtraInfoSerializer(instance=complaint_detail.complainer).data
    response = {
        "complainer": complainer_serialized,
        "complainer_extra_info": complainer_extra_info_serialized,
        "complaint_details": complaint_detail_serialized,
        "worker_details": worker_detail_serialized,
    }
    return Response(data=response, status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
def student_complain_api(request):
    user = get_object_or_404(User, username=request.user.username)
    extrainfo = selectors.get_current_extrainfo(user)
    if extrainfo.user_type == "student":
        complain = selectors.list_user_complaints(extrainfo)
    elif extrainfo.user_type == "staff":
        staff = selectors.get_caretaker_for_user(extrainfo)
        complain = selectors.list_complaints_for_location(staff.area)
    elif extrainfo.user_type == "faculty":
        faculty = selectors.get_service_provider_for_user(extrainfo)
        complain = selectors.list_complaints_for_type(faculty.type)
    else:
        complain = StudentComplain.objects.none()
    complains = StudentComplainOutputSerializer(complain, many=True).data
    return Response(data={"student_complain": complains}, status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
def create_complain_api(request):
    serializer = StudentComplainInputSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["DELETE", "PUT"])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
def edit_complain_api(request, c_id):
    try:
        complain = selectors.get_complaint(c_id)
    except StudentComplain.DoesNotExist:
        return Response({"message": "The Complain does not exist"}, status=status.HTTP_404_NOT_FOUND)
    if request.method == "DELETE":
        complain.delete()
        return Response({"message": "Complain deleted"}, status=status.HTTP_404_NOT_FOUND)
    serializer = StudentComplainInputSerializer(complain, data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
def worker_api(request):
    if request.method == "GET":
        worker = Workers.objects.all()
        workers = WorkersSerializer(worker, many=True).data
        return Response(data={"workers": workers}, status=status.HTTP_200_OK)

    user = get_object_or_404(User, username=request.user.username)
    extrainfo = selectors.get_current_extrainfo(user)
    try:
        selectors.get_caretaker_for_user(extrainfo)
    except selectors.Caretaker.DoesNotExist:
        return Response({"message": "Logged in user does not have the permissions"}, status=status.HTTP_203_NON_AUTHORITATIVE_INFORMATION)
    serializer = WorkersSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["DELETE", "PUT"])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
def edit_worker_api(request, w_id):
    user = get_object_or_404(User, username=request.user.username)
    extrainfo = selectors.get_current_extrainfo(user)
    try:
        selectors.get_caretaker_for_user(extrainfo)
    except selectors.Caretaker.DoesNotExist:
        return Response({"message": "Logged in user does not have the permissions"}, status=status.HTTP_203_NON_AUTHORITATIVE_INFORMATION)
    try:
        worker = selectors.get_worker_by_id(w_id)
    except Workers.DoesNotExist:
        return Response({"message": "The worker does not exist"}, status=status.HTTP_404_NOT_FOUND)
    if request.method == "DELETE":
        worker.delete()
        return Response({"message": "Worker deleted"}, status=status.HTTP_404_NOT_FOUND)
    serializer = WorkersSerializer(worker, data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
def caretaker_api(request):
    if request.method == "GET":
        caretakers = CaretakerSerializer(selectors.Caretaker.objects.all(), many=True).data
        return Response(data={"caretakers": caretakers}, status=status.HTTP_200_OK)

    user = get_object_or_404(User, username=request.user.username)
    extrainfo = selectors.get_current_extrainfo(user)
    try:
        ServiceProvider.objects.get(ser_pro_id=extrainfo)
    except ServiceProvider.DoesNotExist:
        return Response({"message": "Logged in user does not have the permissions"}, status=status.HTTP_203_NON_AUTHORITATIVE_INFORMATION)
    serializer = CaretakerSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["DELETE", "PUT"])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
def edit_caretaker_api(request, c_id):
    user = get_object_or_404(User, username=request.user.username)
    extrainfo = selectors.get_current_extrainfo(user)
    try:
        ServiceProvider.objects.get(ser_pro_id=extrainfo)
    except ServiceProvider.DoesNotExist:
        return Response({"message": "Logged in user does not have the permissions"}, status=status.HTTP_203_NON_AUTHORITATIVE_INFORMATION)
    try:
        caretaker = selectors.get_caretaker_by_id(c_id)
    except selectors.Caretaker.DoesNotExist:
        return Response({"message": "The Caretaker does not exist"}, status=status.HTTP_404_NOT_FOUND)
    if request.method == "DELETE":
        caretaker.delete()
        return Response({"message": "Caretaker deleted"}, status=status.HTTP_404_NOT_FOUND)
    serializer = CaretakerSerializer(caretaker, data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
def service_provider_api(request):
    if request.method == "GET":
        service_providers = ServiceProviderSerializer(ServiceProvider.objects.all(), many=True).data
        return Response(data={"service_providers": service_providers}, status=status.HTTP_200_OK)

    user = get_object_or_404(User, username=request.user.username)
    if user.is_superuser is False:
        return Response({"message": "Logged in user does not have permission"}, status=status.HTTP_203_NON_AUTHORITATIVE_INFORMATION)
    serializer = ServiceProviderSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["DELETE", "PUT"])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
def edit_service_provider_api(request, s_id):
    user = get_object_or_404(User, username=request.user.username)
    if user.is_superuser is False:
        return Response({"message": "Logged in user does not have permission"}, status=status.HTTP_203_NON_AUTHORITATIVE_INFORMATION)
    try:
        service_provider = ServiceProvider.objects.get(id=s_id)
    except ServiceProvider.DoesNotExist:
        return Response({"message": "The Caretaker does not exist"}, status=status.HTTP_404_NOT_FOUND)
    if request.method == "DELETE":
        service_provider.delete()
        return Response({"message": "Caretaker deleted"}, status=status.HTTP_404_NOT_FOUND)
    serializer = ServiceProviderSerializer(service_provider, data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
