# api/views.py
# DRF API views for the visitor_hostel module.
# All views are thin — logic delegated to services.py, queries to selectors.py.
# Fixes: V-01, V-17–V-22

import logging

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework.authentication import TokenAuthentication

from django.contrib.auth.models import User

from .. import services
from .. import selectors
from .serializers import (
    BookingDetailSerializer, RoomDetailSerializer, VisitorDetailSerializer,
    BillSerializer, InventorySerializer, MealRecordSerializer,
    BookingRequestInputSerializer, UpdateBookingInputSerializer,
    ConfirmBookingInputSerializer, CancelBookingInputSerializer,
    RejectBookingInputSerializer, CheckInInputSerializer,
    CheckOutInputSerializer, RecordMealInputSerializer,
    AddInventoryInputSerializer, UpdateInventoryInputSerializer,
    ForwardBookingInputSerializer, RoomAvailabilityInputSerializer,
    BillDateRangeInputSerializer,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Permission helpers  (V-17–V-22)
# ---------------------------------------------------------------------------

class IsVhCaretakerOrIncharge(permissions.BasePermission):
    """Only allow VhCaretaker or VhIncharge."""
    def has_permission(self, request, view):
        role = selectors.get_user_role(request.user)
        return role in ('VhCaretaker', 'VhIncharge')


class IsVhIncharge(permissions.BasePermission):
    """Only allow VhIncharge."""
    def has_permission(self, request, view):
        role = selectors.get_user_role(request.user)
        return role == 'VhIncharge'


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

class DashboardView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        role = services.get_user_designation(user)
        data = {'user_designation': role}

        if role == 'Intender':
            pending = selectors.get_pending_bookings_for_intender(user)
            active = selectors.get_active_bookings_for_intender(user)
            dashboard = selectors.get_dashboard_bookings_for_intender(user)
        else:
            pending = selectors.get_pending_bookings_all()
            active = selectors.get_active_bookings_all()
            dashboard = selectors.get_dashboard_bookings_all()

        data['pending_bookings'] = BookingDetailSerializer(pending, many=True).data
        data['active_bookings'] = BookingDetailSerializer(active, many=True).data
        data['dashboard_bookings'] = BookingDetailSerializer(dashboard, many=True).data
        data['bills'] = services.calculate_active_bills(active)
        return Response(data)


# ---------------------------------------------------------------------------
# Booking CRUD
# ---------------------------------------------------------------------------

class RequestBookingView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = BookingRequestInputSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        d = serializer.validated_data
        try:
            intender_user = User.objects.get(id=d['intender'])
            booking = services.create_booking(
                intender_user=intender_user, category=d['category'],
                person_count=d['number_of_people'], purpose=d['purpose_of_visit'],
                booking_from=d['booking_from'], booking_to=d['booking_to'],
                arrival_time=d.get('booking_from_time', ''),
                departure_time=d.get('booking_to_time', ''),
                number_of_rooms=d['number_of_rooms'],
                bill_to_be_settled_by=d['bill_settlement'],
            )
            visitor = services.create_visitor(
                visitor_name=d['name'], visitor_phone=d['phone'],
                visitor_email=d.get('email', ''), visitor_address=d.get('address', ''),
                visitor_organization=d.get('organization', ''),
                nationality=d.get('nationality', ''),
            )
            booking.visitor.add(visitor)
            booking.save()
            uploaded = request.FILES.get('files-during-booking-request')
            services.handle_booking_attachment(booking, uploaded)
            return Response({'booking_id': booking.id}, status=status.HTTP_201_CREATED)
        except Exception as e:
            logger.error(f"Error creating booking: {e}")
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class UpdateBookingView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = UpdateBookingInputSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        d = serializer.validated_data
        try:
            services.update_booking(
                d['booking_id'], d.get('number_of_people'),
                d.get('number_of_rooms'), d.get('booking_from'),
                d.get('booking_to'), d.get('purpose_of_visit', ''),
            )
            return Response({'success': True})
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ConfirmBookingView(APIView):
    """V-17: Requires VhIncharge role."""
    authentication_classes = [TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated, IsVhIncharge]

    def post(self, request):
        serializer = ConfirmBookingInputSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        d = serializer.validated_data
        try:
            services.confirm_booking(d['booking_id'], d['rooms'], d['category'], request.user)
            return Response({'success': True})
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class CancelBookingView(APIView):
    """V-18: Requires VhCaretaker or VhIncharge."""
    authentication_classes = [TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated, IsVhCaretakerOrIncharge]

    def post(self, request):
        serializer = CancelBookingInputSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        d = serializer.validated_data
        try:
            services.cancel_booking(d['booking_id'], d.get('remark', ''),
                                    d.get('charges'), request.user)
            return Response({'success': True})
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class CancelBookingRequestView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        booking_id = request.data.get('booking-id')
        remark = request.data.get('remark', '')
        try:
            services.request_cancel_booking(booking_id, remark, request.user)
            return Response({'success': True})
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class RejectBookingView(APIView):
    """V-19: Requires VhIncharge role."""
    authentication_classes = [TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated, IsVhIncharge]

    def post(self, request):
        serializer = RejectBookingInputSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        d = serializer.validated_data
        services.reject_booking(d['booking_id'], d.get('remark', ''))
        return Response({'success': True})


class CheckInView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated, IsVhCaretakerOrIncharge]

    def post(self, request):
        serializer = CheckInInputSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        d = serializer.validated_data
        try:
            services.check_in_visitor(
                d['booking_id'], d['name'], d['phone'],
                d.get('email', ''), d.get('address', ''),
            )
            return Response({'success': True})
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class CheckOutView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated, IsVhCaretakerOrIncharge]

    def post(self, request):
        serializer = CheckOutInputSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        d = serializer.validated_data
        try:
            services.check_out_booking(d['id'], d['mess_bill'], d['room_bill'], request.user)
            return Response({'success': True})
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class RecordMealView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated, IsVhCaretakerOrIncharge]

    def post(self, request):
        serializer = RecordMealInputSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        d = serializer.validated_data
        try:
            services.record_meal(
                d['booking'], d['pk'], d['m_tea'],
                d['breakfast'], d['lunch'], d['eve_tea'], d['dinner'],
            )
            return Response({'success': True})
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ForwardBookingView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated, IsVhCaretakerOrIncharge]

    def post(self, request):
        serializer = ForwardBookingInputSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        d = serializer.validated_data
        try:
            services.forward_booking(
                d['id'], d['modified_category'], d['rooms'],
                d.get('remark', ''), request.user,
            )
            return Response({'success': True})
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


# ---------------------------------------------------------------------------
# Room availability
# ---------------------------------------------------------------------------

class RoomAvailabilityView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = RoomAvailabilityInputSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        d = serializer.validated_data
        rooms = selectors.get_available_rooms(d['start_date'], d['end_date'])
        return Response(RoomDetailSerializer(rooms, many=True).data)


# ---------------------------------------------------------------------------
# Inventory  (V-20, V-21)
# ---------------------------------------------------------------------------

class AddInventoryView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated, IsVhCaretakerOrIncharge]

    def post(self, request):
        serializer = AddInventoryInputSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        d = serializer.validated_data
        try:
            services.add_inventory_item(
                d['item_name'], d['quantity'], d['cost'],
                d['bill_number'], d.get('consumable', 'false'),
            )
            return Response({'success': True}, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class UpdateInventoryView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated, IsVhCaretakerOrIncharge]

    def post(self, request):
        serializer = UpdateInventoryInputSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        d = serializer.validated_data
        services.update_inventory_item(d['id'], d['quantity'])
        return Response({'success': True})


# ---------------------------------------------------------------------------
# Bill report
# ---------------------------------------------------------------------------

class BillBetweenDatesView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated, IsVhCaretakerOrIncharge]

    def post(self, request):
        serializer = BillDateRangeInputSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        d = serializer.validated_data
        bills, meal_total, room_total, total_bill, individual_total = (
            services.get_bill_report(d['start_date'], d['end_date'])
        )
        return Response({
            'bills': BillSerializer(bills, many=True).data,
            'meal_total': meal_total,
            'room_total': room_total,
            'total_bill': total_bill,
        })


# ---------------------------------------------------------------------------
# Room status  (V-22)
# ---------------------------------------------------------------------------

class EditRoomStatusView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated, IsVhCaretakerOrIncharge]

    def post(self, request):
        room_number = request.data.get('room_number')
        room_status = request.data.get('room_status')
        if not room_number or not room_status:
            return Response({'error': 'room_number and room_status required'},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            services.edit_room_status(room_number, room_status)
            return Response({'success': True})
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
