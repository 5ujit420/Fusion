# views.py
# Legacy views for the visitor_hostel module.
# All business logic delegated to services.py, all queries to selectors.py.
# Fixes: V-01 to V-07, R-01, R-04, R-06 bug fix
# V-01: visitorhostel() now calls services.build_dashboard_context()
# V-02/V-03: User.objects.all() replaced with selectors.get_all_intenders()
# V-04: User.objects.get() replaced with selectors.get_user_by_id()
# V-05: All legacy POST views validate input via DRF serializers
# V-06: Role-based permission decorator applied to restricted views
# V-07: Django messages framework for error feedback
# R-04: Legacy action views marked deprecated with logging
# R-06: Fixed get_cancel_requested_for_intender → get_cancel_requested_bookings_for_intender

import logging
import warnings

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect, HttpResponse, HttpResponseForbidden
from django.shortcuts import render
from functools import wraps

from . import services
from . import selectors
from .api.serializers import (
    BookingRequestInputSerializer, UpdateBookingInputSerializer,
    ConfirmBookingInputSerializer, CancelBookingInputSerializer,
    CancelBookingRequestInputSerializer, RejectBookingInputSerializer,
    CheckInInputSerializer, CheckOutInputSerializer,
    RecordMealInputSerializer, AddInventoryInputSerializer,
    UpdateInventoryInputSerializer, EditRoomStatusInputSerializer,
    ForwardBookingInputSerializer, RoomAvailabilityInputSerializer,
    BillDateRangeInputSerializer,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# V-06: Role-based permission decorator
# ---------------------------------------------------------------------------

def role_required(allowed_roles):
    """V-06: Decorator to enforce role-based access on legacy views.
    allowed_roles: list of role strings, e.g. ['VhCaretaker', 'VhIncharge']
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            user_role = selectors.get_user_role(request.user)
            if user_role not in allowed_roles:
                messages.error(request, 'You do not have permission to perform this action.')
                return HttpResponseForbidden('Forbidden')
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


# ---------------------------------------------------------------------------
# R-04: Deprecation helper
# ---------------------------------------------------------------------------

def _deprecation_warning(view_name):
    """R-04: Log deprecation warning for legacy views."""
    warnings.warn(
        f"Legacy view '{view_name}' is deprecated. Use the corresponding API endpoint instead.",
        DeprecationWarning, stacklevel=3,
    )
    logger.info(f"Deprecated legacy view called: {view_name}")


# ---------------------------------------------------------------------------
# V-05: POST validation helper
# ---------------------------------------------------------------------------

def _validate_post(request, serializer_class, field_mapping=None, list_fields=None):
    """V-05: Validate request.POST data through a DRF serializer.
    field_mapping: dict mapping POST key names to serializer field names.
    list_fields: dict mapping POST list key names to serializer field names.
    Returns (validated_data, None) on success, (None, errors_dict) on failure.
    """
    data = {}
    for key, value in request.POST.items():
        mapped_key = field_mapping.get(key, key) if field_mapping else key
        data[mapped_key] = value
    if list_fields:
        for post_key, ser_key in list_fields.items():
            data[ser_key] = request.POST.getlist(post_key)
    serializer = serializer_class(data=data)
    if not serializer.is_valid():
        return None, serializer.errors
    return serializer.validated_data, None


# ---------------------------------------------------------------------------
# Dashboard  (V-01, R-01)
# ---------------------------------------------------------------------------

@login_required(login_url='/accounts/login/')
def visitorhostel(request):
    """V-01, R-01: Thin view — delegates entirely to services.build_dashboard_context()."""
    context = services.build_dashboard_context(request.user)
    return render(request, "vhModule/visitorhostel.html", context)


# ---------------------------------------------------------------------------
# Deprecated partial views (5B: dead endpoints, kept for backwards compat)
# ---------------------------------------------------------------------------

@login_required(login_url='/accounts/login/')
def get_booking_requests(request):
    _deprecation_warning('get_booking_requests')
    if request.method == 'POST':
        pending_bookings = selectors.get_booking_requests_pending()
        return render(request, "vhModule/visitorhostel.html", {'pending_bookings': pending_bookings})
    return HttpResponseRedirect('/visitorhostel/')


@login_required(login_url='/accounts/login/')
def get_active_bookings(request):
    _deprecation_warning('get_active_bookings')
    if request.method == 'POST':
        active_bookings = selectors.get_active_bookings_confirmed()
        return render(request, "vhModule/visitorhostel.html", {'active_bookings': active_bookings})
    return HttpResponseRedirect('/visitorhostel/')


@login_required(login_url='/accounts/login/')
def get_inactive_bookings(request):
    _deprecation_warning('get_inactive_bookings')
    if request.method == 'POST':
        inactive_bookings = selectors.get_inactive_bookings()
        return render(request, "vhModule/visitorhostel.html", {'inactive_bookings': inactive_bookings})
    return HttpResponseRedirect('/visitorhostel/')


@login_required(login_url='/accounts/login/')
def get_booking_form(request):
    """V-02: Uses selectors.get_all_intenders() instead of User.objects.all()."""
    _deprecation_warning('get_booking_form')
    if request.method == 'POST':
        intenders = selectors.get_all_intenders()
        return render(request, "vhModule/visitorhostel.html", {'intenders': intenders})
    return HttpResponseRedirect('/visitorhostel/')


# ---------------------------------------------------------------------------
# Booking CRUD  (V-05 validation, V-06 role checks, V-07 messages, R-04 deprecation)
# ---------------------------------------------------------------------------

@login_required(login_url='/accounts/login/')
def request_booking(request):
    """V-04/V-05: Validates via BookingRequestInputSerializer, uses selectors.get_user_by_id()."""
    _deprecation_warning('request_booking')
    if request.method == 'POST':
        validated, errors = _validate_post(request, BookingRequestInputSerializer, {
            'number-of-people': 'number_of_people',
            'purpose-of-visit': 'purpose_of_visit',
            'number-of-rooms': 'number_of_rooms',
        })
        if errors:
            messages.error(request, f'Invalid booking data: {errors}')
            return HttpResponseRedirect('/visitorhostel/')
        try:
            intender_user = selectors.get_user_by_id(validated['intender'])
            booking_params = dict(
                intender_user=intender_user, category=validated['category'],
                person_count=validated['number_of_people'],
                purpose=validated['purpose_of_visit'],
                booking_from=validated['booking_from'],
                booking_to=validated['booking_to'],
                arrival_time=validated.get('booking_from_time', ''),
                departure_time=validated.get('booking_to_time', ''),
                number_of_rooms=validated['number_of_rooms'],
                bill_to_be_settled_by=validated['bill_settlement'],
            )
            visitor_params = dict(
                visitor_name=validated['name'],
                visitor_phone=validated['phone'],
                visitor_email=validated.get('email', ''),
                visitor_address=validated.get('address', ''),
                visitor_organization=validated.get('organization', ''),
                nationality=validated.get('nationality', ''),
            )
            doc = request.FILES.get('files-during-booking-request')
            services.create_booking_with_visitor(booking_params, visitor_params, doc)
        except Exception as e:
            logger.error(f"Error in request_booking: {e}")
            messages.error(request, 'Failed to create booking. Please try again.')
        return HttpResponseRedirect('/visitorhostel/')
    return HttpResponseRedirect('/visitorhostel/')


@login_required(login_url='/accounts/login/')
def update_booking(request):
    """V-05: Validates via UpdateBookingInputSerializer."""
    _deprecation_warning('update_booking')
    if request.method == 'POST':
        validated, errors = _validate_post(request, UpdateBookingInputSerializer, {
            'booking-id': 'booking_id',
            'number-of-people': 'number_of_people',
            'purpose-of-visit': 'purpose_of_visit',
            'number-of-rooms': 'number_of_rooms',
        })
        if errors:
            messages.error(request, f'Invalid update data: {errors}')
            return HttpResponseRedirect('/visitorhostel/')
        try:
            services.update_booking(
                booking_id=validated['booking_id'],
                person_count=validated.get('number_of_people'),
                number_of_rooms=validated.get('number_of_rooms'),
                booking_from=validated.get('booking_from'),
                booking_to=validated.get('booking_to'),
                purpose=validated.get('purpose_of_visit', ''),
            )
        except Exception as e:
            logger.error(f"Error in update_booking: {e}")
            messages.error(request, 'Failed to update booking.')
        return HttpResponseRedirect('/visitorhostel/')
    return HttpResponseRedirect('/visitorhostel/')


@login_required(login_url='/accounts/login/')
@role_required(['VhIncharge'])
def confirm_booking(request):
    """V-05/V-06: Validated + role-restricted to VhIncharge."""
    _deprecation_warning('confirm_booking')
    if request.method == 'POST':
        validated, errors = _validate_post(
            request, ConfirmBookingInputSerializer,
            {'booking-id': 'booking_id'},
            list_fields={'rooms[]': 'rooms'},
        )
        if errors:
            messages.error(request, f'Invalid confirmation data: {errors}')
            return HttpResponseRedirect('/visitorhostel/')
        try:
            services.confirm_booking(
                booking_id=validated['booking_id'],
                rooms_list=validated['rooms'],
                category=validated['category'],
                requesting_user=request.user,
            )
        except Exception as e:
            logger.error(f"Error in confirm_booking: {e}")
            messages.error(request, 'Failed to confirm booking.')
        return HttpResponseRedirect('/visitorhostel/')
    return HttpResponseRedirect('/visitorhostel/')


@login_required(login_url='/accounts/login/')
@role_required(['VhCaretaker', 'VhIncharge'])
def cancel_booking(request):
    """V-05/V-06: Validated + role-restricted."""
    _deprecation_warning('cancel_booking')
    if request.method == 'POST':
        validated, errors = _validate_post(request, CancelBookingInputSerializer, {
            'booking-id': 'booking_id',
        })
        if errors:
            messages.error(request, f'Invalid cancellation data: {errors}')
            return HttpResponseRedirect('/visitorhostel/')
        try:
            services.cancel_booking(
                booking_id=validated['booking_id'],
                remark=validated.get('remark', ''),
                charges=validated.get('charges'),
                caretaker_user=request.user,
            )
        except Exception as e:
            logger.error(f"Error in cancel_booking: {e}")
            messages.error(request, 'Failed to cancel booking.')
        return HttpResponseRedirect('/visitorhostel/')
    return HttpResponseRedirect('/visitorhostel/')


@login_required(login_url='/accounts/login/')
def cancel_booking_request(request):
    """V-05: Validates via CancelBookingRequestInputSerializer."""
    _deprecation_warning('cancel_booking_request')
    if request.method == 'POST':
        validated, errors = _validate_post(request, CancelBookingRequestInputSerializer, {
            'booking-id': 'booking_id',
        })
        if errors:
            messages.error(request, f'Invalid cancellation request: {errors}')
            return HttpResponseRedirect('/visitorhostel/')
        try:
            services.request_cancel_booking(
                booking_id=validated['booking_id'],
                remark=validated.get('remark', ''),
                requesting_user=request.user,
            )
        except Exception as e:
            logger.error(f"Error in cancel_booking_request: {e}")
            messages.error(request, 'Failed to submit cancellation request.')
        return HttpResponseRedirect('/visitorhostel/')
    return HttpResponseRedirect('/visitorhostel/')


@login_required(login_url='/accounts/login/')
@role_required(['VhIncharge'])
def reject_booking(request):
    """V-05/V-06: Validated + role-restricted to VhIncharge."""
    _deprecation_warning('reject_booking')
    if request.method == 'POST':
        validated, errors = _validate_post(request, RejectBookingInputSerializer, {
            'booking-id': 'booking_id',
        })
        if errors:
            messages.error(request, f'Invalid rejection data: {errors}')
            return HttpResponseRedirect('/visitorhostel/')
        try:
            services.reject_booking(
                booking_id=validated['booking_id'],
                remark=validated.get('remark', ''),
            )
        except Exception as e:
            logger.error(f"Error in reject_booking: {e}")
            messages.error(request, 'Failed to reject booking.')
        return HttpResponseRedirect('/visitorhostel/')
    return HttpResponseRedirect('/visitorhostel/')


@login_required(login_url='/accounts/login/')
@role_required(['VhCaretaker', 'VhIncharge'])
def check_in(request):
    """V-05/V-06: Validated + role-restricted."""
    _deprecation_warning('check_in')
    if request.method == 'POST':
        validated, errors = _validate_post(request, CheckInInputSerializer, {
            'booking-id': 'booking_id',
        })
        if errors:
            messages.error(request, f'Invalid check-in data: {errors}')
            return HttpResponse('/visitorhostel/')
        try:
            services.check_in_visitor(
                booking_id=validated['booking_id'],
                visitor_name=validated['name'],
                visitor_phone=validated['phone'],
                visitor_email=validated.get('email', ''),
                visitor_address=validated.get('address', ''),
            )
        except Exception as e:
            logger.error(f"Error in check_in: {e}")
            messages.error(request, 'Failed to check in visitor.')
        return HttpResponse('/visitorhostel/')
    return HttpResponse('/visitorhostel/')


@login_required(login_url='/accounts/login/')
@role_required(['VhCaretaker', 'VhIncharge'])
def check_out(request):
    """V-05/V-06: Validated + role-restricted."""
    _deprecation_warning('check_out')
    if request.method == 'POST':
        validated, errors = _validate_post(request, CheckOutInputSerializer)
        if errors:
            messages.error(request, f'Invalid check-out data: {errors}')
            return HttpResponseRedirect('/visitorhostel/')
        try:
            services.check_out_booking(
                booking_id=validated['id'],
                meal_bill=validated['mess_bill'],
                room_bill=validated['room_bill'],
                caretaker_user=request.user,
            )
        except Exception as e:
            logger.error(f"Error in check_out: {e}")
            messages.error(request, 'Failed to check out.')
        return HttpResponseRedirect('/visitorhostel/')
    return HttpResponseRedirect('/visitorhostel/')


@login_required(login_url='/accounts/login/')
@role_required(['VhCaretaker', 'VhIncharge'])
def record_meal(request):
    """V-05/V-06: Validated + role-restricted."""
    _deprecation_warning('record_meal')
    if request.method == "POST":
        validated, errors = _validate_post(request, RecordMealInputSerializer)
        if errors:
            messages.error(request, f'Invalid meal data: {errors}')
            return HttpResponseRedirect('/visitorhostel/')
        try:
            services.record_meal(
                booking_id=validated['booking'],
                visitor_id=validated['pk'],
                m_tea=validated['m_tea'],
                breakfast=validated['breakfast'],
                lunch=validated['lunch'],
                eve_tea=validated['eve_tea'],
                dinner=validated['dinner'],
            )
        except Exception as e:
            logger.error(f"Error in record_meal: {e}")
            messages.error(request, 'Failed to record meal.')
        return HttpResponseRedirect('/visitorhostel/')
    return HttpResponseRedirect('/visitorhostel/')


@login_required(login_url='/accounts/login/')
def bill_between_dates(request):
    """V-05: Validates via BillDateRangeInputSerializer."""
    _deprecation_warning('bill_between_dates')
    if request.method == 'POST':
        validated, errors = _validate_post(request, BillDateRangeInputSerializer)
        if errors:
            messages.error(request, f'Invalid date range: {errors}')
            return HttpResponseRedirect('/visitorhostel/')
        bills, meal_total, room_total, total_bill, individual_total = (
            services.get_bill_report(validated['start_date'], validated['end_date'])
        )
        return render(request, "vhModule/booking_bw_dates.html", {
            'booking_bw_dates_length': bills,
            'meal_total': meal_total,
            'room_total': room_total,
            'total_bill': total_bill,
            'individual_total': individual_total,
            'booking_bw_dates': zip(bills, individual_total),
        })
    return HttpResponseRedirect('/visitorhostel/')


@login_required(login_url='/accounts/login/')
def room_availability(request):
    """V-05: Validates via RoomAvailabilityInputSerializer."""
    _deprecation_warning('room_availability')
    if request.method == 'POST':
        validated, errors = _validate_post(request, RoomAvailabilityInputSerializer)
        if errors:
            messages.error(request, f'Invalid date range: {errors}')
            return HttpResponseRedirect('/visitorhostel/')
        available_rooms = selectors.get_available_rooms(
            validated['start_date'], validated['end_date'])
        room_numbers = [room.room_number for room in available_rooms]
        return render(request, "vhModule/room-availability.html",
                      {'available_rooms': room_numbers})
    return HttpResponseRedirect('/visitorhostel/')


@login_required(login_url='/accounts/login/')
@role_required(['VhCaretaker', 'VhIncharge'])
def add_to_inventory(request):
    """V-05/V-06: Validated + role-restricted."""
    _deprecation_warning('add_to_inventory')
    if request.method == 'POST':
        validated, errors = _validate_post(request, AddInventoryInputSerializer)
        if errors:
            messages.error(request, f'Invalid inventory data: {errors}')
            return HttpResponseRedirect('/visitorhostel/')
        try:
            services.add_inventory_item(
                item_name=validated['item_name'],
                quantity=validated['quantity'],
                cost=validated['cost'],
                bill_number=validated['bill_number'],
                consumable=validated.get('consumable', 'false'),
            )
        except (ValueError, TypeError) as e:
            logger.error(f"Invalid inventory input: {e}")
            messages.error(request, 'Failed to add inventory item.')
        return HttpResponseRedirect('/visitorhostel/')
    return HttpResponseRedirect('/visitorhostel/')


@login_required(login_url='/accounts/login/')
@role_required(['VhCaretaker', 'VhIncharge'])
def update_inventory(request):
    """V-05/V-06: Validated + role-restricted."""
    _deprecation_warning('update_inventory')
    if request.method == 'POST':
        validated, errors = _validate_post(request, UpdateInventoryInputSerializer)
        if errors:
            messages.error(request, f'Invalid inventory data: {errors}')
            return HttpResponseRedirect('/visitorhostel/')
        try:
            services.update_inventory_item(
                item_id=validated['id'],
                quantity=validated['quantity'],
            )
        except (ValueError, TypeError) as e:
            logger.error(f"Invalid inventory update input: {e}")
            messages.error(request, 'Failed to update inventory.')
        return HttpResponseRedirect('/visitorhostel/')
    return HttpResponseRedirect('/visitorhostel/')


@login_required(login_url='/accounts/login/')
@role_required(['VhCaretaker', 'VhIncharge'])
def edit_room_status(request):
    """V-05/V-06: Validated + role-restricted."""
    _deprecation_warning('edit_room_status')
    if request.method == 'POST':
        validated, errors = _validate_post(request, EditRoomStatusInputSerializer)
        if errors:
            messages.error(request, f'Invalid room status data: {errors}')
            return HttpResponseRedirect('/visitorhostel/')
        try:
            services.edit_room_status(
                room_number=validated['room_number'],
                room_status=validated['room_status'],
            )
        except Exception as e:
            logger.error(f"Error editing room status: {e}")
            messages.error(request, 'Failed to update room status.')
        return HttpResponseRedirect('/visitorhostel/')
    return HttpResponseRedirect('/visitorhostel/')


@login_required(login_url='/accounts/login/')
@role_required(['VhCaretaker', 'VhIncharge'])
def forward_booking(request):
    """V-05/V-06: Validated + role-restricted."""
    _deprecation_warning('forward_booking')
    if request.method == 'POST':
        validated, errors = _validate_post(
            request, ForwardBookingInputSerializer,
            list_fields={'rooms[]': 'rooms'},
        )
        if errors:
            messages.error(request, f'Invalid forward data: {errors}')
            return HttpResponseRedirect('/visitorhostel/')
        try:
            services.forward_booking(
                booking_id=validated['id'],
                modified_category=validated['modified_category'],
                rooms_list=validated['rooms'],
                remark=validated.get('remark', ''),
                requesting_user=request.user,
            )
        except Exception as e:
            logger.error(f"Error in forward_booking: {e}")
            messages.error(request, 'Failed to forward booking.')
        return HttpResponseRedirect('/visitorhostel/')
    return HttpResponseRedirect('/visitorhostel/')
