# api/urls.py
# DRF URL routing for the visitor_hostel module.

from django.urls import path
from .views import (
    DashboardView, RequestBookingView, UpdateBookingView,
    ConfirmBookingView, CancelBookingView, CancelBookingRequestView,
    RejectBookingView, CheckInView, CheckOutView,
    RecordMealView, ForwardBookingView, RoomAvailabilityView,
    AddInventoryView, UpdateInventoryView, BillBetweenDatesView,
    EditRoomStatusView,
)

urlpatterns = [
    path('dashboard/', DashboardView.as_view(), name='api_dashboard'),
    path('request-booking/', RequestBookingView.as_view(), name='api_request_booking'),
    path('update-booking/', UpdateBookingView.as_view(), name='api_update_booking'),
    path('confirm-booking/', ConfirmBookingView.as_view(), name='api_confirm_booking'),
    path('cancel-booking/', CancelBookingView.as_view(), name='api_cancel_booking'),
    path('cancel-booking-request/', CancelBookingRequestView.as_view(), name='api_cancel_booking_request'),
    path('reject-booking/', RejectBookingView.as_view(), name='api_reject_booking'),
    path('check-in/', CheckInView.as_view(), name='api_check_in'),
    path('check-out/', CheckOutView.as_view(), name='api_check_out'),
    path('record-meal/', RecordMealView.as_view(), name='api_record_meal'),
    path('forward-booking/', ForwardBookingView.as_view(), name='api_forward_booking'),
    path('room-availability/', RoomAvailabilityView.as_view(), name='api_room_availability'),
    path('add-to-inventory/', AddInventoryView.as_view(), name='api_add_inventory'),
    path('update-inventory/', UpdateInventoryView.as_view(), name='api_update_inventory'),
    path('bill-between-dates/', BillBetweenDatesView.as_view(), name='api_bill_between_dates'),
    path('edit-room-status/', EditRoomStatusView.as_view(), name='api_edit_room_status'),
]
