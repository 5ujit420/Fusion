#views.py
from django.shortcuts import get_object_or_404, render
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from applications.globals.models import User, ExtraInfo
from notifications.models import Notification
from .models import Caretaker, Warden, SectionIncharge, Workers, StudentComplain, ServiceProvider, ServiceAuthority, Complaint_Admin
from notification.views import complaint_system_notif

from applications.filetracking.sdk.methods import *
from applications.filetracking.models import *

from .serializers import (
    StudentComplainSerializer,
    CaretakerSerializer,
    Complaint_AdminSerializer,
    WardenSerializer,
    FeedbackSerializer,
    ResolvePendingSerializer,
    WorkersSerializer
)
from .services import (
    get_user_type,
    calculate_complaint_deadline,
    lodge_complaint,
    resolve_complaint,
    submit_feedback,
    send_lodge_notification,
    generate_report_for_user,
    update_complaint_status,
    forward_complaint_file,
    validate_rating,
    LOCATION_DESIGNATION_MAP,
    DEADLINE_DAYS_MAP
)
from .selectors import (
    get_user_extra_info,
    get_user_type_info,
    get_caretaker_complaints,
    get_warden_complaints,
    get_service_provider_complaints,
    get_user_complaints,
    get_complaint_detail,
    get_all_caretakers,
    get_all_wardens,
    get_all_service_providers,
    get_all_complaint_admins,
    get_all_workers,
    get_complaint_statistics,
    get_active_complaints,
    get_pending_complaints,
    get_resolved_complaints
)

# Converted to DRF APIView
class CheckUser(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        The function is used to check the type of user.
        There are three types of users: student, staff, or faculty.
        Returns the user type and the appropriate endpoint.
        """
        # Use service layer for user type detection - fixes N+1 query and loop-based checking
        result = get_user_type(request.user)
        return Response(result)

# Converted to DRF APIView
class UserComplaintView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Returns the list of complaints made by the user.
        """
        # Use selector layer for optimized query
        complaints = get_user_complaints(request.user)
        serializer = StudentComplainSerializer(complaints, many=True)
        return Response(serializer.data)

    def post(self, request):
        """
        Allows the user to register a new complaint.
        """
        # Use service layer - extracts business logic from view
        data = request.data
        
        success, complaint, error = lodge_complaint(request.user, data)
        
        if success:
            serializer = StudentComplainSerializer(complaint)
            return Response(serializer.data, status=201)
        else:
            return Response({"error": error}, status=400)

# Converted to DRF APIView
class CaretakerFeedbackView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        Allows the user to submit feedback for a particular type of caretaker.
        """
        feedback = request.data.get("feedback", "")
        rating = request.data.get("rating", "")
        caretaker_type = request.data.get("caretakertype", "")
        
        # Use service layer validation
        valid, error = validate_rating(rating)
        if not valid:
            return Response({"error": error}, status=400)
        
        # Use service layer for feedback submission
        success, complaint, error = submit_feedback(
            request.user, 
            complaint_id=None,  # Not used for caretaker feedback
            feedback_text=feedback,
            rating=int(rating)
        )
        
        # Update all caretakers in the area (legacy behavior preserved)
        from .models import Caretaker
        all_caretaker = Caretaker.objects.filter(area=caretaker_type).order_by("-id")
        for x in all_caretaker:
            rate = x.rating
            if rate == 0:
                newrate = int(rating)
            else:
                newrate = (rate + int(rating)) / 2
            x.myfeedback = feedback
            x.rating = newrate
            x.save()
            
        return Response({"success": "Feedback submitted"})

# Converted to DRF APIView
class SubmitFeedbackView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, complaint_id):
        """
        Allows the user to submit feedback for a complaint.
        """
        feedback = request.data.get("feedback", "")
        rating = request.data.get("rating", "")

        try:
            rating = int(rating)
        except ValueError:
            return Response({"error": "Invalid rating"}, status=400)
        
        try:
            StudentComplain.objects.filter(id=complaint_id).update(feedback=feedback, flag=rating)
            a = StudentComplain.objects.filter(id=complaint_id).first()
            care = Caretaker.objects.filter(area=a.location).first()
            rate = care.rating
            if rate == 0:
                newrate = rating
            else:
                newrate = int((rating + rate) / 2)
            care.rating = newrate
            care.save()
            return Response({"success": "Feedback submitted"})
        except:
            return Response({"error": "Internal server errror"}, status=500)

# Converted to DRF APIView
class ComplaintDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, detailcomp_id1):
        """
        Returns the details of a complaint.
        """
        try:
            complaint = StudentComplain.objects.select_related(
                "complainer", "complainer_user", "complainer_department"
            ).get(id=detailcomp_id1)
        except StudentComplain.DoesNotExist:
            return Response({"error": "Complaint not found"}, status=404)
        serializer = StudentComplainSerializer(complaint)
        return Response(serializer.data)
    # Import DRF classes
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

# Import necessary models and serializers
from .serializers import (
    StudentComplainSerializer,
    CaretakerSerializer,
    FeedbackSerializer,
    ResolvePendingSerializer,
)
# Other imports remain the same
import datetime
from datetime import datetime, timedelta
from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.shortcuts import get_object_or_404, render
from applications.globals.models import User, ExtraInfo, HoldsDesignation
from notifications.models import Notification
from .models import Caretaker, StudentComplain, ServiceProvider
from notification.views import complaint_system_notif
from applications.filetracking.sdk.methods import *
from applications.filetracking.models import *
from operator import attrgetter

# Converted to DRF APIView
class CaretakerLodgeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        Allows the caretaker to lodge a new complaint.
        """
        # Get the current user
        a = request.user
        y = ExtraInfo.objects.select_related('user', 'department').filter(user=a).first()

        data = request.data.copy()
        data['complainer'] = y.id
        data['status'] = 0
        comp_type = data.get('complaint_type', '')
        # Finish time is according to complaint type
        complaint_finish = datetime.now() + timedelta(days=2)
        if comp_type == 'Electricity':
            complaint_finish = datetime.now() + timedelta(days=2)
        elif comp_type == 'carpenter':
            complaint_finish = datetime.now() + timedelta(days=2)
        elif comp_type == 'plumber':
            complaint_finish = datetime.now() + timedelta(days=2)
        elif comp_type == 'garbage':
            complaint_finish = datetime.now() + timedelta(days=1)
        elif comp_type == 'dustbin':
            complaint_finish = datetime.now() + timedelta(days=1)
        elif comp_type == 'internet':
            complaint_finish = datetime.now() + timedelta(days=4)
        elif comp_type == 'other':
            complaint_finish = datetime.now() + timedelta(days=3)
        data['complaint_finish'] = complaint_finish.date()

        serializer = StudentComplainSerializer(data=data)
        if serializer.is_valid():
            complaint = serializer.save()

            # Notification logic (if any)
            location = data.get('location', '')
            if location == "hall-1":
                dsgn = "hall1caretaker"
            elif location == "hall-3":
                dsgn = "hall3caretaker"
            elif location == "hall-4":
                dsgn = "hall4caretaker"
            elif location == "CC1":
                dsgn = "cc1convener"
            elif location == "CC2":
                dsgn = "CC2 convener"
            elif location == "core_lab":
                dsgn = "corelabcaretaker"
            elif location == "LHTC":
                dsgn = "lhtccaretaker"
            elif location == "NR2":
                dsgn = "nr2caretaker"
            elif location == "Maa Saraswati Hostel":
                dsgn = "mshcaretaker"
            elif location == "Nagarjun Hostel":
                dsgn = "nhcaretaker"
            elif location == "Panini Hostel":
                dsgn = "phcaretaker"
            else:
                dsgn = "rewacaretaker"
            caretaker_name = HoldsDesignation.objects.select_related('user', 'working', 'designation').get(designation__name=dsgn)

            # Send notification
            student = 1
            message = "A New Complaint has been lodged"
            complaint_system_notif(request.user, caretaker_name.user, 'lodge_comp_alert', complaint.id, student, message)

            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def get(self, request):
        """
        Returns the list of complaints lodged by the caretaker.
        """
        a = request.user
        y = ExtraInfo.objects.select_related('user', 'department').filter(user=a).first()
        complaints = StudentComplain.objects.filter(complainer=y).order_by('-id')
        serializer = StudentComplainSerializer(complaints, many=True)
        return Response(serializer.data)

# Converted to DRF APIView
class CaretakerView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Returns the list of complaints assigned to the caretaker.
        """
        current_user = request.user
        y = ExtraInfo.objects.select_related('user', 'department').filter(user=current_user).first()
        try:
            a = Caretaker.objects.select_related('staff_id').get(staff_id=y.id)
            b = a.area
            complaints = StudentComplain.objects.filter(location=b).order_by('-id')
            serializer = StudentComplainSerializer(complaints, many=True)
            return Response(serializer.data)
        except Caretaker.DoesNotExist:
            return Response({'error': 'Caretaker does not exist'}, status=status.HTTP_404_NOT_FOUND)

# Converted to DRF APIView
class FeedbackCareView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, feedcomp_id):
        """
        Returns the feedback details for a specific complaint.
        """
        try:
            detail = StudentComplain.objects.select_related('complainer', 'complainer_user', 'complainer_department').get(id=feedcomp_id)
            serializer = StudentComplainSerializer(detail)
            return Response(serializer.data)
        except StudentComplain.DoesNotExist:
            return Response({'error': 'Complaint not found'}, status=status.HTTP_404_NOT_FOUND)

# Converted to DRF APIView
class ResolvePendingView(APIView):
    permission_classes = [IsAuthenticated]

    # def post(self, request, cid):
    #     """
    #     Allows the caretaker to resolve a pending complaint.
    #     """
    #     serializer = ResolvePendingSerializer(data=request.data)
    #     print("Incoming data:", request.data)
    #     if serializer.is_valid():
    #         newstatus = serializer.validated_data['yesorno']
    #         comment = serializer.validated_data.get('comment', '')
    #         intstatus = 2 if newstatus == 'Yes' else 3
    #         StudentComplain.objects.filter(id=cid).update(status=intstatus, comment=comment)

    #         # Send notification to the complainer
    #         try:
    #             complainer_details = StudentComplain.objects.select_related('complainer').get(id=cid)
    #             student = 0
    #             if newstatus == 'Yes':
    #                 message = "Congrats! Your complaint has been resolved"
    #                 notification_type = 'comp_resolved_alert'
    #             else:
    #                 message = "Your complaint has been declined"
    #                 notification_type = 'comp_declined_alert'

    #             complaint_system_notif(request.user, complainer_details.complainer.user, notification_type, complainer_details.id, student, message)
    #             return Response({'success': 'Complaint status updated'})
    #         except StudentComplain.DoesNotExist:
    #             return Response({'error': 'Complaint not found'}, status=status.HTTP_404_NOT_FOUND)
    #     else:
    #         return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    def post(self, request, cid):
        """
        Allows the caretaker to resolve a pending complaint.
        """
        serializer = ResolvePendingSerializer(data=request.data)
        print("Incoming data:", request.data)
        print("Incoming files:", request.FILES)  # ✅ Debugging log

        if serializer.is_valid():
            newstatus = serializer.validated_data['yesorno']
            comment = serializer.validated_data.get('comment', '')
            intstatus = 2 if newstatus == 'Yes' else 3
            StudentComplain.objects.filter(id=cid).update(status=intstatus, comment=comment)

            # Send notification to the complainer
            # ✅ Get the complaint record
            try:
                complaint = StudentComplain.objects.get(id=cid)
                complaint.status = intstatus
                complaint.comment = comment

                # ✅ Save the uploaded image if it exists
                if 'upload_resolved' in request.FILES:
                    complaint.upload_resolved = request.FILES['upload_resolved']
                    print("✅ Image Saved:", complaint.upload_resolved)

                complaint.save()

                # ✅ Send notification
                complainer_details = StudentComplain.objects.select_related('complainer').get(id=cid)
                student = 0
                if newstatus == 'Yes':
                    message = "Congrats! Your complaint has been resolved"
                    notification_type = 'comp_resolved_alert'
                else:
                    message = "Your complaint has been declined"
                    notification_type = 'comp_declined_alert'

                complaint_system_notif(request.user, complainer_details.complainer.user, notification_type,
                                       complainer_details.id, student, message)

                return Response({'success': 'Complaint status updated'})
            except StudentComplain.DoesNotExist:
                return Response({'error': 'Complaint not found'}, status=status.HTTP_404_NOT_FOUND)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def get(self, request, cid):
        """
        Returns the details of the complaint to be resolved.
        """
        try:
            complaint = StudentComplain.objects.select_related('complainer', 'complainer_user',
                                                               'complainer_department').get(id=cid)
            serializer = StudentComplainSerializer(complaint)
            return Response(serializer.data)
        except StudentComplain.DoesNotExist:
            return Response({'error': 'Complaint not found'}, status=status.HTTP_404_NOT_FOUND)


# Converted to DRF APIView
class ComplaintDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, detailcomp_id1):
        """
        Returns the details of a complaint for the caretaker.
        """
        try:
            complaint = StudentComplain.objects.select_related().get(id=detailcomp_id1)
            serializer = StudentComplainSerializer(complaint)
            print(serializer.data)
            return Response(serializer.data)
        except StudentComplain.DoesNotExist:
            return Response({'error': 'Complaint not found'}, status=status.HTTP_404_NOT_FOUND)

# Converted to DRF APIView
class SearchComplaintView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Searches for complaints based on query parameters.
        """
        # Implement search logic based on query parameters
        # For now, return all complaints
        complaints = StudentComplain.objects.all()
        serializer = StudentComplainSerializer(complaints, many=True)
        return Response(serializer.data)

# Converted to DRF APIView
class SubmitFeedbackCaretakerView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, complaint_id):
        """
        Allows the caretaker to submit feedback for a complaint.
        """
        serializer = FeedbackSerializer(data=request.data)
        if serializer.is_valid():
            feedback = serializer.validated_data['feedback']
            rating = serializer.validated_data['rating']
            try:
                rating = int(rating)
            except ValueError:
                return Response({'error': 'Invalid rating'}, status=status.HTTP_400_BAD_REQUEST)
            StudentComplain.objects.filter(id=complaint_id).update(feedback=feedback, flag=rating)

            a = StudentComplain.objects.select_related('complainer', 'complainer_user', 'complainer_department').filter(id=complaint_id).first()
            care = Caretaker.objects.filter(area=a.location).first()
            rate = care.rating
            newrate = int((rating + rate) / 2) if rate != 0 else rating
            care.rating = newrate
            care.save()
            return Response({'success': 'Feedback submitted'})
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def get(self, request, complaint_id):
        """
        Returns the complaint details for which feedback is to be submitted.
        """
        try:
            complaint = StudentComplain.objects.select_related('complainer', 'complainer_user', 'complainer_department').get(id=complaint_id)
            serializer = StudentComplainSerializer(complaint)
            return Response(serializer.data)
        except StudentComplain.DoesNotExist:
            return Response({'error': 'Complaint not found'}, status=status.HTTP_404_NOT_FOUND)
# views.py

# Import DRF classes
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

# Import necessary models and serializers
from .serializers import (
    StudentComplainSerializer,
    CaretakerSerializer,
    FeedbackSerializer,
    ResolvePendingSerializer,
)
# Other imports remain the same
import datetime
from datetime import datetime, timedelta
from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.shortcuts import get_object_or_404, render
from applications.globals.models import User, ExtraInfo, HoldsDesignation
from notifications.models import Notification
from .models import Caretaker, StudentComplain, ServiceProvider
from notification.views import complaint_system_notif
from applications.filetracking.sdk.methods import *
from applications.filetracking.models import *
from operator import attrgetter

# Converted to DRF APIView
class ServiceProviderLodgeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        Allows the service_provider to lodge a new complaint.
        """
        # Get the current user
        a = request.user
        y = ExtraInfo.objects.select_related('user', 'department').filter(user=a).first()

        data = request.data.copy()
        data['complainer'] = y.id
        data['status'] = 0

        comp_type = data.get('complaint_type', '')
        # Finish time is according to complaint type
        complaint_finish = datetime.now() + timedelta(days=2)
        if comp_type == 'Electricity':
            complaint_finish = datetime.now() + timedelta(days=2)
        elif comp_type == 'carpenter':
            complaint_finish = datetime.now() + timedelta(days=2)
        elif comp_type == 'plumber':
            complaint_finish = datetime.now() + timedelta(days=2)
        elif comp_type == 'garbage':
            complaint_finish = datetime.now() + timedelta(days=1)
        elif comp_type == 'dustbin':
            complaint_finish = datetime.now() + timedelta(days=1)
        elif comp_type == 'internet':
            complaint_finish = datetime.now() + timedelta(days=4)
        elif comp_type == 'other':
            complaint_finish = datetime.now() + timedelta(days=3)
        data['complaint_finish'] = complaint_finish.date()

        serializer = StudentComplainSerializer(data=data)
        if serializer.is_valid():
            complaint = serializer.save()

            # Notification logic (if any)
            location = data.get('location', '')
            if location == "hall-1":
                dsgn = "hall1caretaker"
            elif location == "hall-3":
                dsgn = "hall3caretaker"
            elif location == "hall-4":
                dsgn = "hall4caretaker"
            elif location == "CC1":
                dsgn = "cc1convener"
            elif location == "CC2":
                dsgn = "CC2 convener"
            elif location == "core_lab":
                dsgn = "corelabcaretaker"
            elif location == "LHTC":
                dsgn = "lhtccaretaker"
            elif location == "NR2":
                dsgn = "nr2caretaker"
            elif location == "Maa Saraswati Hostel":
                dsgn = "mshcaretaker"
            elif location == "Nagarjun Hostel":
                dsgn = "nhcaretaker"
            elif location == "Panini Hostel":
                dsgn = "phcaretaker"
            else:
                dsgn = "rewacaretaker"
            caretaker_name = HoldsDesignation.objects.select_related('user', 'working', 'designation').get(designation__name=dsgn)

            # Send notification
            student = 1
            message = "A New Complaint has been lodged"
            complaint_system_notif(request.user, caretaker_name.user, 'lodge_comp_alert', complaint.id, student, message)

            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def get(self, request):
        """
        Returns the history of complaints lodged by the service_provider.
        """
        a = request.user
        y = ExtraInfo.objects.select_related('user', 'department').filter(user=a).first()
        complaints = StudentComplain.objects.filter(complainer=y).order_by('-id')
        serializer = StudentComplainSerializer(complaints, many=True)
        return Response(serializer.data)

# Converted to DRF APIView
class ServiceProviderView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Returns the list of complaints assigned to the service_provider's area.
        """
        current_user = request.user
        y = ExtraInfo.objects.select_related('user', 'department').filter(user=current_user).first()
        try:
            service_provider = ServiceProvider.objects.select_related('ser_pro_id').get(ser_pro_id=y)
            type = service_provider.type
            complaints = StudentComplain.objects.filter(complaint_type=type, status=1).order_by('-id')
            serializer = StudentComplainSerializer(complaints, many=True)
            return Response(serializer.data)
        except ServiceProvider.DoesNotExist:
            return Response({'error': 'ServiceProvider does not exist'}, status=status.HTTP_404_NOT_FOUND)

# Converted to DRF APIView
class FeedbackSuperView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, feedcomp_id):
        """
        Returns the feedback details for a specific complaint for the service_provider.
        """
        try:
            complaint = StudentComplain.objects.select_related('complainer', 'complainer_user', 'complainer_department').get(id=feedcomp_id)
            caretaker = Caretaker.objects.select_related('staff_id', 'staff_id_user', 'staff_id_department').filter(area=complaint.location).first()
            complaint_data = StudentComplainSerializer(complaint).data
            caretaker_data = CaretakerSerializer(caretaker).data if caretaker else None
            return Response({'complaint': complaint_data, 'caretaker': caretaker_data})
        except StudentComplain.DoesNotExist:
            return Response({'error': 'Complaint not found'}, status=status.HTTP_404_NOT_FOUND)

# Converted to DRF APIView
class CaretakerIdKnowMoreView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, caretaker_id):
        """
        Returns the details of a caretaker and the list of pending complaints in their area.
        """
        try:
            caretaker = Caretaker.objects.select_related('staff_id', 'staff_id_user', 'staff_id_department').get(id=caretaker_id)
            area = caretaker.area
            pending_complaints = StudentComplain.objects.filter(location=area, status=0)
            caretaker_data = CaretakerSerializer(caretaker).data
            complaints_data = StudentComplainSerializer(pending_complaints, many=True).data
            return Response({'caretaker': caretaker_data, 'pending_complaints': complaints_data})
        except Caretaker.DoesNotExist:
            return Response({'error': 'Caretaker not found'}, status=status.HTTP_404_NOT_FOUND)

# Converted to DRF APIView
class ServiceProviderComplaintDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, detailcomp_id1):
        """
        Returns the details of a complaint for the service_provider, including caretaker info.
        """
        try:
            complaint = StudentComplain.objects.select_related('complainer', 'complainer_user', 'complainer_department').get(id=detailcomp_id1)
            caretaker = Caretaker.objects.select_related('staff_id', 'staff_id_user', 'staff_id_department').filter(area=complaint.location).first()
            complaint_data = StudentComplainSerializer(complaint).data
            caretaker_data = CaretakerSerializer(caretaker).data if caretaker else None
            return Response({'complaint': complaint_data, 'caretaker': caretaker_data})
        except StudentComplain.DoesNotExist:
            return Response({'error': 'Complaint not found'}, status=status.HTTP_404_NOT_FOUND)

# Converted to DRF APIView
class ServiceProviderResolvePendingView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, cid):
        """
        Allows the service_provider to resolve a pending complaint.
        """
        serializer = ResolvePendingSerializer(data=request.data)
        if serializer.is_valid():
            newstatus = serializer.validated_data['yesorno']
            comment = serializer.validated_data.get('comment', '')
            intstatus = 2 if newstatus == 'Yes' else 3
            StudentComplain.objects.filter(id=cid).update(status=intstatus, comment=comment)

            # Send notification to the complainer
            try:
                complainer_details = StudentComplain.objects.select_related('complainer').get(id=cid)
                student = 0
                message = "Congrats! Your complaint has been resolved"
                complaint_system_notif(request.user, complainer_details.complainer.user, 'comp_resolved_alert', complainer_details.id, student, message)
                return Response({'success': 'Complaint status updated'})
            except StudentComplain.DoesNotExist:
                return Response({'error': 'Complaint not found'}, status=status.HTTP_404_NOT_FOUND)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def get(self, request, cid):
        """
        Returns the details of the complaint to be resolved.
        """
        try:
            complaint = StudentComplain.objects.select_related('complainer').get(id=cid)
            serializer = StudentComplainSerializer(complaint)
            return Response(serializer.data)
        except StudentComplain.DoesNotExist:
            return Response({'error': 'Complaint not found'}, status=status.HTTP_404_NOT_FOUND)

# Converted to DRF APIView
class ServiceProviderSubmitFeedbackView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, complaint_id):
        """
        Allows the service_provider to submit feedback for a complaint.
        """
        serializer = FeedbackSerializer(data=request.data)
        if serializer.is_valid():
            feedback = serializer.validated_data['feedback']
            rating = serializer.validated_data['rating']
            try:
                rating = int(rating)
            except ValueError:
                return Response({'error': 'Invalid rating'}, status=status.HTTP_400_BAD_REQUEST)
            StudentComplain.objects.filter(id=complaint_id).update(feedback=feedback, flag=rating)

            # Update caretaker's rating
            try:
                complaint = StudentComplain.objects.select_related('complainer', 'complainer_user', 'complainer_department').get(id=complaint_id)
                care = Caretaker.objects.filter(area=complaint.location).first()
                rate = care.rating
                newrate = int((rating + rate) / 2) if rate != 0 else rating
                care.rating = newrate
                care.save()
                return Response({'success': 'Feedback submitted'})
            except Caretaker.DoesNotExist:
                return Response({'error': 'Caretaker not found'}, status=status.HTTP_404_NOT_FOUND)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def get(self, request, complaint_id):
        """
        Returns the complaint details for which feedback is to be submitted.
        """
        try:
            complaint = StudentComplain.objects.select_related('complainer', 'complainer_user', 'complainer_department').get(id=complaint_id)
            serializer = StudentComplainSerializer(complaint)
            return Response(serializer.data)
        except StudentComplain.DoesNotExist:
            return Response({'error': 'Complaint not found'}, status=status.HTTP_404_NOT_FOUND)
# views.py

# Import DRF classes
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

# Import necessary models and serializers
from .models import Caretaker, StudentComplain, ServiceProvider, Workers, SectionIncharge
from .serializers import StudentComplainSerializer, WorkersSerializer  # Added WorkersSerializer
from applications.globals.models import User, ExtraInfo, HoldsDesignation

# Converted 'removew' function to DRF APIView 'RemoveWorkerView'
class RemoveWorkerView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, work_id):
        """
        Allows the caretaker to remove a worker if not assigned to any complaints.
        """
        try:
            worker = Workers.objects.get(id=work_id)
            assigned_complaints = StudentComplain.objects.filter(worker_id=worker).count()
            if assigned_complaints == 0:
                worker.delete()
                return Response({'success': 'Worker removed successfully'}, status=status.HTTP_200_OK)
            else:
                return Response({'error': 'Worker is assigned to some complaints'}, status=status.HTTP_400_BAD_REQUEST)
        except Workers.DoesNotExist:
            return Response({'error': 'Worker not found'}, status=status.HTTP_404_NOT_FOUND)

    # Optionally, accept DELETE method
    def delete(self, request, work_id):
        return self.post(request, work_id)

# Converted 'assign_worker' function to DRF APIView 'AssignWorkerView'
class ForwardCompaintView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, comp_id1):
        """
        Assigns a complaint to a service_provider.
        """
        current_user = request.user
        y = ExtraInfo.objects.filter(user=current_user).first()
        complaint_id = comp_id1

        try:
            complaint = StudentComplain.objects.get(id=complaint_id)
        except StudentComplain.DoesNotExist:
            return Response({'error': 'Complaint not found'}, status=status.HTTP_404_NOT_FOUND)

        complaint_type = complaint.complaint_type

        service_providers = ServiceProvider.objects.filter(type=complaint_type)
        if not service_providers.exists():
            return Response({'error': 'ServiceProvider does not exist for this complaint type'}, status=status.HTTP_404_NOT_FOUND)

        service_provider = service_providers.first()
        service_provider_details = ExtraInfo.objects.get(id=service_provider.ser_pro_id.id)

        # Update complaint status
        complaint.status = 1
        complaint.save()

        # Forward file to service_provider
        sup_designations = HoldsDesignation.objects.filter(user=service_provider_details.user_id).distinct('user_id')
        
        #send notification to all the service providers
        for sup in sup_designations:
            print(sup.user_id)
            complaint_system_notif(request.user, User.objects.get(id=sup.user_id), 'comp_assigned_alert', complaint_id, 0, "A new complaint has been assigned to you")
        

        files = File.objects.filter(src_object_id=complaint_id)

        if not files.exists():
            return Response({'error': 'No files associated with this complaint'}, status=status.HTTP_206_PARTIAL_CONTENT)

        service_provider_username = User.objects.get(id=service_provider_details.user_id).username

        file = forward_file(
            file_id=files.first().id,
            receiver=service_provider_username,
            receiver_designation=sup_designations.first().designation,
            file_extra_JSON={},
            remarks="",
            file_attachment=None
        )

        return Response({'success': 'Complaint assigned to service_provider'}, status=status.HTTP_200_OK)

    def get(self, request, comp_id1):
        """
        Retrieves complaint details.
        """
        try:
            complaint = StudentComplain.objects.get(id=comp_id1)
            serializer = StudentComplainSerializer(complaint)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except StudentComplain.DoesNotExist:
            return Response({'error': 'Not a valid complaint'}, status=status.HTTP_404_NOT_FOUND)

# Converted 'deletecomplaint' function to DRF APIView 'DeleteComplaintView'
class DeleteComplaintView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, comp_id1):
        """
        Deletes a complaint.
        """
        try:
            complaint = StudentComplain.objects.get(id=comp_id1)
            complaint.delete()
            return Response({'success': 'Complaint deleted successfully'}, status=status.HTTP_200_OK)
        except StudentComplain.DoesNotExist:
            return Response({'error': 'Complaint not found'}, status=status.HTTP_404_NOT_FOUND)

    def delete(self, request, comp_id1):
        return self.post(request, comp_id1)

# Converted 'changestatus' function to DRF APIView 'ChangeStatusView'
class ChangeStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, complaint_id, status):
        """
        Allows the caretaker to change the status of a complaint.
        """
        try:
            complaint = StudentComplain.objects.get(id=complaint_id)
            if status == '3' or status == '2':
                complaint.status = status
                complaint.worker_id = None
            else:
                complaint.status = status
            complaint.save()
            return Response({'success': 'Complaint status updated'}, status=status.HTTP_200_OK)
        except StudentComplain.DoesNotExist:
            return Response({'error': 'Complaint not found'}, status=status.HTTP_404_NOT_FOUND)

# Converted 'changestatussuper' function to DRF APIView 'ChangeStatusSuperView'
class ChangeStatusSuperView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, complaint_id, status):
        """
        Allows the service_provider to change the status of a complaint.
        """
        try:
            complaint = StudentComplain.objects.get(id=complaint_id)
            if status == '3' or status == '2':
                complaint.status = status
                complaint.worker_id = None
            else:
                complaint.status = status
            complaint.save()
            return Response({'success': 'Complaint status updated'}, status=status.HTTP_200_OK)
        except StudentComplain.DoesNotExist:
            return Response({'error': 'Complaint not found'}, status=status.HTTP_404_NOT_FOUND)
        
class GenerateReportView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Generates a report of complaints for the caretaker's area, warden's area, or service_provider's type.
        """
        user = request.user
        try:
            complaint_admin_user = Complaint_Admin.objects.get(sup_id=user.extrainfo)
            complaints = StudentComplain.objects.all()
        except Complaint_Admin.DoesNotExist:
            complaint_admin_user = None

        if not complaint_admin_user:
            is_caretaker = hasattr(user, 'caretaker')
            is_service_provider = False
            is_complaint_admin = hasattr(user, 'complaint_admin')  # Check if the user has the 'complaintadmin' attribute

            # Check if user is a service_provider
            try:
                service_provider = ServiceProvider.objects.get(ser_pro_id=user.extrainfo)
                is_service_provider = True
            except ServiceProvider.DoesNotExist:
                is_service_provider = False

            try:
                is_service_authority = ServiceAuthority.objects.get(ser_pro_id=user.extrainfo)
                is_service_authority = True
            except ServiceAuthority.DoesNotExist:
                is_service_authority = False

            try:
                warden = Warden.objects.get(staff_id=user.extrainfo)
                is_warden = True
            except Warden.DoesNotExist:
                is_warden = False

            if not is_caretaker and not is_service_provider and not is_complaint_admin and not is_service_provider and not is_service_provider and not is_service_authority and not is_warden:
                return Response({"detail": "Not authorized to generate report."}, status=403)

            complaints = None

            # Generate report for service_provider
            if is_service_provider:
                print(f"Generating report for ServiceProvider {service_provider}")
                complaints = StudentComplain.objects.filter(complaint_type=service_provider.type, status__in=[1, 2, 3])  # Include resolved complaints

            # Generate report for caretaker
            if is_caretaker and not is_service_provider and not is_warden:
                caretaker = get_object_or_404(Caretaker, staff_id=user.extrainfo)
                complaints = StudentComplain.objects.filter(location=caretaker.area)

            if is_warden:
                warden = get_object_or_404(Warden, staff_id=user.extrainfo)
                complaints = StudentComplain.objects.filter(location=warden.area)

            # Generate report for complaint admin
            if is_complaint_admin:
                complaints = StudentComplain.objects.all()  # Complaint admin can see all complaints
    
        serializer = StudentComplainSerializer(complaints, many=True)
        return Response(serializer.data)
