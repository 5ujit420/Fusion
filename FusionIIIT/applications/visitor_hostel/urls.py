# urls.py
# Root URL routing — migrated from deprecated url() to path().
# V-42: Uses path() instead of url(r'^...')
# V-41: Fixed room_availabity → room_availability
# V-32: Removed broken bill/ route

from django.urls import path, include

from . import views
from .api import urls as api_urls

app_name = 'visitorhostel'

urlpatterns = [
    path('', views.visitorhostel, name='visitorhostel'),
    path('get-booking-requests/', views.get_booking_requests, name='get_booking_requests'),
    path('get-active-bookings/', views.get_active_bookings, name='get_active_bookings'),
    path('get-booking-form/', views.get_booking_form, name='get_booking_form'),
    path('request-booking/', views.request_booking, name='request_booking'),
    path('confirm-booking/', views.confirm_booking, name='confirm_booking'),
    path('cancel-booking/', views.cancel_booking, name='cancel_booking'),
    path('cancel-booking-request/', views.cancel_booking_request, name='cancel_booking_request'),
    path('reject-booking/', views.reject_booking, name='reject_booking'),
    path('check-in/', views.check_in, name='check_in'),
    path('check-out/', views.check_out, name='check_out'),
    path('record-meal/', views.record_meal, name='record_meal'),
    path('update-booking/', views.update_booking, name='update_booking'),
    path('bill_between_date_range/', views.bill_between_dates, name='generate_records'),
    path('room-availability/', views.room_availability, name='room_availability'),
    path('add-to-inventory/', views.add_to_inventory, name='add_to_inventory'),
    path('update-inventory/', views.update_inventory, name='update_inventory'),
    path('edit-room-status/', views.edit_room_status, name='edit_room_status'),
    path('forward-booking/', views.forward_booking, name='forward_booking'),

    # REST API urls
    path('api/', include(api_urls)),
]
