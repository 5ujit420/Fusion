# api/views.py
# DRF API views for the visitor_hostel module.
# All views are thin — logic delegated to services.py, queries to selectors.py.
# Fixes: V-01, V-08, V-09, V-10, R-01, R-02

import logging

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework.authentication import TokenAuthentication

from django.contrib.auth.models import User

from .. import services
from .. import selectors
from ..models import BookingDetail, Inventory, RoomDetail, VisitorDetail
from .serializers import (
    BookingDetailSerializer, RoomDetailSerializer, VisitorDetailSerializer,
    BillSerializer, InventorySerializer, MealRecordSerializer,
    BookingRequestInputSerializer, UpdateBookingInputSerializer,
    ConfirmBookingInputSerializer, CancelBookingInputSerializer,
    CancelBookingRequestInputSerializer,
    RejectBookingInputSerializer, CheckInInputSerializer,
    CheckOutInputSerializer, RecordMealInputSerializer,
    AddInventoryInputSerializer, UpdateInventoryInputSerializer,
    ForwardBookingInputSerializer, RoomAvailabilityInputSerializer,
    BillDateRangeInputSerializer, EditRoomStatusInputSerializer,
)

logger = logging.getLogger(__name__)

_GENERIC_ERROR = 'Operation failed. Please try again.'


# ---------------------------------------------------------------------------
# Permission helpers
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
# Dashboard  (V-01, R-01)
# ---------------------------------------------------------------------------

class DashboardView(APIView):
    """R-01: Uses services.build_dashboard_context() — single source of truth."""
    authentication_classes = [TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        ctx = services.build_dashboard_context(request.user)
        data = {'user_designation': ctx['user_designation']}
        data['pending_bookings'] = BookingDetailSerializer(ctx['pending_bookings'], many=True).data
        data['active_bookings'] = BookingDetailSerializer(ctx['active_bookings'], many=True).data
        data['dashboard_bookings'] = BookingDetailSerializer(ctx['dashboard_bookings'], many=True).data
        data['bills'] = ctx['bills']
        return Response(data)


# ---------------------------------------------------------------------------
# Booking CRUD
# ---------------------------------------------------------------------------

class RequestBookingView(APIView):
    """R-02: Uses services.create_booking_with_visitor() — consolidated creation."""
    authentication_classes = [TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = BookingRequestInputSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        d = serializer.validated_data
        try:
            intender_user = selectors.get_user_by_id(d['intender'])
            booking_params = dict(
                intender_user=intender_user, category=d['category'],
                person_count=d['number_of_people'], purpose=d['purpose_of_visit'],
                booking_from=d['booking_from'], booking_to=d['booking_to'],
                arrival_time=d.get('booking_from_time', ''),
                departure_time=d.get('booking_to_time', ''),
                number_of_rooms=d['number_of_rooms'],
                bill_to_be_settled_by=d['bill_settlement'],
            )
            visitor_params = dict(
                visitor_name=d['name'], visitor_phone=d['phone'],
                visitor_email=d.get('email', ''), visitor_address=d.get('address', ''),
                visitor_organization=d.get('organization', ''),
                nationality=d.get('nationality', ''),
            )
            uploaded = request.FILES.get('files-during-booking-request')
            booking, visitor = services.create_booking_with_visitor(
                booking_params, visitor_params, uploaded)
            return Response({'booking_id': booking.id}, status=status.HTTP_201_CREATED)
        except User.DoesNotExist:
            return Response({'error': 'Intender user not found'}, status=status.HTTP_400_BAD_REQUEST)
        except ValueError as e:
            logger.error(f"Error creating booking: {e}")
            return Response({'error': _GENERIC_ERROR}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error creating booking: {e}")
            return Response({'error': _GENERIC_ERROR}, status=status.HTTP_400_BAD_REQUEST)


class UpdateBookingView(APIView):
    """SA-1: Added ownership check — only the intender who created the booking can update it."""
    authentication_classes = [TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = UpdateBookingInputSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        d = serializer.validated_data
        try:
            booking = selectors.get_booking_by_id(d['booking_id'])
            if booking.intender != request.user:
                return Response(
                    {'error': 'You can only update your own bookings.'},
                    status=status.HTTP_403_FORBIDDEN,
                )
            services.update_booking(
                d['booking_id'], d.get('number_of_people'),
                d.get('number_of_rooms'), d.get('booking_from'),
                d.get('booking_to'), d.get('purpose_of_visit', ''),
            )
            return Response({'success': True})
        except BookingDetail.DoesNotExist:
            return Response({'error': 'Booking not found'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error updating booking: {e}")
            return Response({'error': _GENERIC_ERROR}, status=status.HTTP_400_BAD_REQUEST)


class ConfirmBookingView(APIView):
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
        except BookingDetail.DoesNotExist:
            return Response({'error': 'Booking not found'}, status=status.HTTP_400_BAD_REQUEST)
        except RoomDetail.DoesNotExist:
            return Response({'error': 'Room not found'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error confirming booking: {e}")
            return Response({'error': _GENERIC_ERROR}, status=status.HTTP_400_BAD_REQUEST)


class CancelBookingView(APIView):
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
        except BookingDetail.DoesNotExist:
            return Response({'error': 'Booking not found'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error canceling booking: {e}")
            return Response({'error': _GENERIC_ERROR}, status=status.HTTP_400_BAD_REQUEST)


class CancelBookingRequestView(APIView):
    """V-09: Now uses CancelBookingRequestInputSerializer instead of raw request.data.get()."""
    authentication_classes = [TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = CancelBookingRequestInputSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        d = serializer.validated_data
        try:
            services.request_cancel_booking(d['booking_id'], d.get('remark', ''), request.user)
            return Response({'success': True})
        except BookingDetail.DoesNotExist:
            return Response({'error': 'Booking not found'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error requesting cancellation: {e}")
            return Response({'error': _GENERIC_ERROR}, status=status.HTTP_400_BAD_REQUEST)


class RejectBookingView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated, IsVhIncharge]

    def post(self, request):
        serializer = RejectBookingInputSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        d = serializer.validated_data
        try:
            services.reject_booking(d['booking_id'], d.get('remark', ''))
            return Response({'success': True})
        except BookingDetail.DoesNotExist:
            return Response({'error': 'Booking not found'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error rejecting booking: {e}")
            return Response({'error': _GENERIC_ERROR}, status=status.HTTP_400_BAD_REQUEST)


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
        except BookingDetail.DoesNotExist:
            return Response({'error': 'Booking not found'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error during check-in: {e}")
            return Response({'error': _GENERIC_ERROR}, status=status.HTTP_400_BAD_REQUEST)


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
        except BookingDetail.DoesNotExist:
            return Response({'error': 'Booking not found'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error during check-out: {e}")
            return Response({'error': _GENERIC_ERROR}, status=status.HTTP_400_BAD_REQUEST)


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
        except (BookingDetail.DoesNotExist, VisitorDetail.DoesNotExist):
            return Response({'error': 'Booking or visitor not found'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error recording meal: {e}")
            return Response({'error': _GENERIC_ERROR}, status=status.HTTP_400_BAD_REQUEST)


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
        except BookingDetail.DoesNotExist:
            return Response({'error': 'Booking not found'}, status=status.HTTP_400_BAD_REQUEST)
        except RoomDetail.DoesNotExist:
            return Response({'error': 'Room not found'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error forwarding booking: {e}")
            return Response({'error': _GENERIC_ERROR}, status=status.HTTP_400_BAD_REQUEST)


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
# Inventory
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
        except (ValueError, TypeError) as e:
            logger.error(f"Error adding inventory: {e}")
            return Response({'error': _GENERIC_ERROR}, status=status.HTTP_400_BAD_REQUEST)


class UpdateInventoryView(APIView):
    """SA-3: Added error handling for consistency with other API views."""
    authentication_classes = [TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated, IsVhCaretakerOrIncharge]

    def post(self, request):
        serializer = UpdateInventoryInputSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        d = serializer.validated_data
        try:
            services.update_inventory_item(d['id'], d['quantity'])
            return Response({'success': True})
        except Inventory.DoesNotExist:
            return Response({'error': 'Inventory item not found'}, status=status.HTTP_400_BAD_REQUEST)
        except (ValueError, TypeError) as e:
            logger.error(f"Error updating inventory: {e}")
            return Response({'error': _GENERIC_ERROR}, status=status.HTTP_400_BAD_REQUEST)


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
# Room status  (V-10)
# ---------------------------------------------------------------------------

class EditRoomStatusView(APIView):
    """V-10: Now uses EditRoomStatusInputSerializer with choice validation."""
    authentication_classes = [TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated, IsVhCaretakerOrIncharge]

    def post(self, request):
        serializer = EditRoomStatusInputSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        d = serializer.validated_data
        try:
            services.edit_room_status(d['room_number'], d['room_status'])
            return Response({'success': True})
        except RoomDetail.DoesNotExist:
            return Response({'error': 'Room not found'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error editing room status: {e}")
            return Response({'error': _GENERIC_ERROR}, status=status.HTTP_400_BAD_REQUEST)
