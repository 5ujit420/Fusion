from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

from applications.placement_cell.api.serializers import (
    PlacementScheduleSerializer, PlacementRecordSerializer, ChairmanVisitSerializer,
    PlacementStatusSerializer, ScheduleInputSerializer, RecordInputSerializer,
    VisitInputSerializer, SkillSerializer, EducationSerializer
)
from applications.placement_cell.services import (
    save_placement_schedule, save_placement_record, save_chairman_visit,
    update_invitation_status, delete_invitation_status, delete_placement_record,
    calculate_placement_statistics, get_placement_schedule_list, create_has_skill
)
from applications.placement_cell.selectors import (
    get_placement_records, get_chairman_visits, get_student_records, get_company_details
)

class PlacementStatisticsView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        stats = calculate_placement_statistics()
        return Response({"statistics": list(stats)}, status=status.HTTP_200_OK)

class GetReferenceListView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        return Response({"message": "Reference lists"}, status=status.HTTP_200_OK)

class CheckingRolesView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        return Response({"role": request.GET.get('role', '')}, status=status.HTTP_200_OK)

class CompanyNameDropdownView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        name = request.GET.get('company_name', '')
        details = get_company_details(name)
        data = [{"id": d.id, "name": d.company_name} for d in details]
        return Response(data, status=status.HTTP_200_OK)

class InvitationStatusView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        pk = request.data.get('status_id')
        action = request.data.get('action')
        update_invitation_status(pk, action)
        return Response({"message": "Status updated successfully"}, status=status.HTTP_200_OK)

class DeleteInvitationStatusView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        pk = request.data.get('status_id')
        delete_invitation_status(pk)
        return Response({"message": "Status deleted successfully"}, status=status.HTTP_200_OK)

class StudentRecordsView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user_info = get_student_records(request.user)
        return Response({"user": user_info.id if user_info else None}, status=status.HTTP_200_OK)
        
    def post(self, request):
        form_type = request.data.get('form_type')
        if form_type == 'skill':
            create_has_skill(request.user, request.data.get('skill'), request.data.get('skill_rating'))
            return Response({"message": "Skill added"}, status=status.HTTP_201_CREATED)
        return Response({"message": "Unhandled form type"}, status=status.HTTP_400_BAD_REQUEST)

class ManageRecordsView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        records = get_placement_records()
        serializer = PlacementRecordSerializer(records, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

class DeletePlacementStatisticsView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        pk = request.data.get('record_id')
        delete_placement_record(pk)
        return Response({"message": "Deleted successfully"}, status=status.HTTP_200_OK)

class CVView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, username):
        return Response({"cv": f"CV data for {username}"}, status=status.HTTP_200_OK)

class AddPlacementScheduleView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        schedules = get_placement_schedule_list()
        serializer = PlacementScheduleSerializer(schedules, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

class PlacementScheduleSaveView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        serializer = ScheduleInputSerializer(data=request.data)
        if serializer.is_valid():
            schedule = save_placement_schedule(serializer.validated_data)
            return Response({"message": "Schedule saved", "id": schedule.id}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class DeletePlacementRecordView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        record_id = request.data.get('record_id')
        delete_placement_record(record_id)
        return Response({"message": "Record deleted"}, status=status.HTTP_200_OK)

class AddPlacementRecordView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        records = get_placement_records()
        serializer = PlacementRecordSerializer(records, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

class PlacementRecordSaveView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        serializer = RecordInputSerializer(data=request.data)
        if serializer.is_valid():
            record = save_placement_record(serializer.validated_data)
            return Response({"message": "Record saved", "id": record.id}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class AddPlacementVisitView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        visits = get_chairman_visits()
        serializer = ChairmanVisitSerializer(visits, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

class PlacementVisitSaveView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        serializer = VisitInputSerializer(data=request.data)
        if serializer.is_valid():
            visit = save_chairman_visit(serializer.validated_data)
            return Response({"message": "Visit saved", "id": visit.id}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
