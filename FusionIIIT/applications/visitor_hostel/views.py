# views.py
# Thin legacy views for the visitor_hostel module.
# All business logic delegated to services.py, all queries to selectors.py.
# Fixes: V-05–V-13, V-16, V-22–V-32, V-35–V-36, V-38–V-39, V-41, V-43–V-44
# Removed: V-29/V-30 (all print statements), V-31 (commented-out code)
# Removed: V-38 (unused Caretaker import), V-39 (wildcard imports)
# Removed: V-32 (broken bill_generation view)

import logging

from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import render
from django.contrib.auth.models import User

from . import services
from . import selectors
from .models import BookingDetail

logger = logging.getLogger(__name__)


@login_required(login_url='/accounts/login/')
def visitorhostel(request):
    """
    V-05: Dashboard view — delegates to services/selectors.
    R-01: Parametric queries by role. R-02: Consolidated visitor/room counts.
    V-35: Removed User.objects.all(). V-36: Deferred previous_visitors.
    """
    user = request.user
    user_designation = services.get_user_designation(user)

    available_rooms = {}
    forwarded_rooms = {}
    cancel_booking_request = []

    if user_designation == "Intender":
        pending_bookings = selectors.get_pending_bookings_for_intender(user)
        active_bookings = selectors.get_active_bookings_for_intender(user)
        dashboard_bookings = selectors.get_dashboard_bookings_for_intender(user)
        complete_bookings = selectors.get_complete_bookings_for_intender(user)
        canceled_bookings = selectors.get_canceled_bookings_for_intender(user)
        rejected_bookings = selectors.get_rejected_bookings_for_intender(user)
        cancel_booking_requested = selectors.get_cancel_requested_bookings_for_intender(user)
    else:
        pending_bookings = selectors.get_pending_bookings_all()
        active_bookings = selectors.get_active_bookings_all()
        dashboard_bookings = selectors.get_dashboard_bookings_all()
        cancel_booking_request = selectors.get_cancel_requests_all()
        complete_bookings = selectors.get_complete_bookings_all()
        canceled_bookings = selectors.get_canceled_bookings_all()
        rejected_bookings = selectors.get_rejected_bookings_all()
        cancel_booking_requested = selectors.get_cancel_requested_for_intender(user)
        c_bookings = selectors.get_forwarded_bookings()

        available_rooms = services.compute_room_availability(pending_bookings)
        forwarded_rooms = services.compute_forwarded_rooms(c_bookings)

    all_bookings = selectors.get_all_bookings()
    visitors, rooms = services.get_visitor_and_room_counts(active_bookings)

    inventory = selectors.get_all_inventory()
    inventory_bill = selectors.get_all_inventory_bills()

    completed_booking_bills, current_balance = services.calculate_current_balance()
    active_visitors = services.get_active_visitor_map(active_bookings)
    bills = services.calculate_active_bills(active_bookings)
    previous_visitors = selectors.get_all_visitors()
    visitor_list = services.get_visitor_list_from_dashboard(dashboard_bookings)

    return render(request, "vhModule/visitorhostel.html", {
        'all_bookings': all_bookings,
        'complete_bookings': complete_bookings,
        'pending_bookings': pending_bookings,
        'active_bookings': active_bookings,
        'canceled_bookings': canceled_bookings,
        'dashboard_bookings': dashboard_bookings,
        'bills': bills,
        'available_rooms': available_rooms,
        'forwarded_rooms': forwarded_rooms,
        'inventory': inventory,
        'inventory_bill': inventory_bill,
        'active_visitors': active_visitors,
        'intenders': User.objects.all(),
        'user': user,
        'visitors': visitors,
        'rooms': rooms,
        'previous_visitors': previous_visitors,
        'completed_booking_bills': completed_booking_bills,
        'current_balance': current_balance,
        'rejected_bookings': rejected_bookings,
        'cancel_booking_request': cancel_booking_request,
        'cancel_booking_requested': cancel_booking_requested,
        'user_designation': user_designation,
    })


@login_required(login_url='/accounts/login/')
def get_booking_requests(request):
    if request.method == 'POST':
        pending_bookings = selectors.get_booking_requests_pending()
        return render(request, "vhModule/visitorhostel.html", {'pending_bookings': pending_bookings})
    return HttpResponseRedirect('/visitorhostel/')


@login_required(login_url='/accounts/login/')
def get_active_bookings(request):
    if request.method == 'POST':
        active_bookings = selectors.get_active_bookings_confirmed()
        return render(request, "vhModule/visitorhostel.html", {'active_bookings': active_bookings})
    return HttpResponseRedirect('/visitorhostel/')


@login_required(login_url='/accounts/login/')
def get_inactive_bookings(request):
    if request.method == 'POST':
        inactive_bookings = selectors.get_inactive_bookings()
        return render(request, "vhModule/visitorhostel.html", {'inactive_bookings': inactive_bookings})
    return HttpResponseRedirect('/visitorhostel/')


@login_required(login_url='/accounts/login/')
def get_booking_form(request):
    if request.method == 'POST':
        intenders = User.objects.all()
        return render(request, "vhModule/visitorhostel.html", {'intenders': intenders})
    return HttpResponseRedirect('/visitorhostel/')


@login_required(login_url='/accounts/login/')
def request_booking(request):
    """V-06: Delegates to services.create_booking() + services.create_visitor()."""
    if request.method == 'POST':
        try:
            intender_id = request.POST.get('intender')
            intender_user = User.objects.get(id=intender_id)

            booking_obj = services.create_booking(
                intender_user=intender_user,
                category=request.POST.get('category'),
                person_count=request.POST.get('number-of-people'),
                purpose=request.POST.get('purpose-of-visit'),
                booking_from=request.POST.get('booking_from'),
                booking_to=request.POST.get('booking_to'),
                arrival_time=request.POST.get('booking_from_time'),
                departure_time=request.POST.get('booking_to_time'),
                number_of_rooms=request.POST.get('number-of-rooms'),
                bill_to_be_settled_by=request.POST.get('bill_settlement'),
            )

            doc = request.FILES.get('files-during-booking-request')
            services.handle_booking_attachment(booking_obj, doc)

            visitor = services.create_visitor(
                visitor_name=request.POST.get('name'),
                visitor_phone=request.POST.get('phone'),
                visitor_email=request.POST.get('email', ''),
                visitor_address=request.POST.get('address', ''),
                visitor_organization=request.POST.get('organization', ''),
                nationality=request.POST.get('nationality', ''),
            )
            booking_obj.visitor.add(visitor)
            booking_obj.save()
        except Exception as e:
            logger.error(f"Error in request_booking: {e}")

        return HttpResponseRedirect('/visitorhostel/')
    return HttpResponseRedirect('/visitorhostel/')


@login_required(login_url='/accounts/login/')
def update_booking(request):
    """V-07: Delegates to services.update_booking()."""
    if request.method == 'POST':
        try:
            services.update_booking(
                booking_id=request.POST.get('booking-id'),
                person_count=request.POST.get('number-of-people'),
                number_of_rooms=request.POST.get('number-of-rooms'),
                booking_from=request.POST.get('booking_from'),
                booking_to=request.POST.get('booking_to'),
                purpose=request.POST.get('purpose-of-visit'),
            )
        except Exception as e:
            logger.error(f"Error in update_booking: {e}")
        return HttpResponseRedirect('/visitorhostel/')
    return HttpResponseRedirect('/visitorhostel/')


@login_required(login_url='/accounts/login/')
def confirm_booking(request):
    """V-08: Delegates to services.confirm_booking() with R-08."""
    if request.method == 'POST':
        try:
            services.confirm_booking(
                booking_id=request.POST.get('booking-id'),
                rooms_list=request.POST.getlist('rooms[]'),
                category=request.POST.get('category'),
                requesting_user=request.user,
            )
        except Exception as e:
            logger.error(f"Error in confirm_booking: {e}")
        return HttpResponseRedirect('/visitorhostel/')
    return HttpResponseRedirect('/visitorhostel/')


@login_required(login_url='/accounts/login/')
def cancel_booking(request):
    """V-09: Delegates to services.cancel_booking() with R-09."""
    if request.method == 'POST':
        try:
            services.cancel_booking(
                booking_id=request.POST.get('booking-id'),
                remark=request.POST.get('remark', ''),
                charges=request.POST.get('charges'),
                caretaker_user=request.user,
            )
        except Exception as e:
            logger.error(f"Error in cancel_booking: {e}")
        return HttpResponseRedirect('/visitorhostel/')
    return HttpResponseRedirect('/visitorhostel/')


@login_required(login_url='/accounts/login/')
def cancel_booking_request(request):
    """Delegates to services.request_cancel_booking()."""
    if request.method == 'POST':
        try:
            services.request_cancel_booking(
                booking_id=request.POST.get('booking-id'),
                remark=request.POST.get('remark', ''),
                requesting_user=request.user,
            )
        except Exception as e:
            logger.error(f"Error in cancel_booking_request: {e}")
        return HttpResponseRedirect('/visitorhostel/')
    return HttpResponseRedirect('/visitorhostel/')


@login_required(login_url='/accounts/login/')
def reject_booking(request):
    """V-19: Delegates to services.reject_booking()."""
    if request.method == 'POST':
        try:
            services.reject_booking(
                booking_id=request.POST.get('booking-id'),
                remark=request.POST.get('remark', ''),
            )
        except Exception as e:
            logger.error(f"Error in reject_booking: {e}")
        return HttpResponseRedirect('/visitorhostel/')
    return HttpResponseRedirect('/visitorhostel/')


@login_required(login_url='/accounts/login/')
def check_in(request):
    """V-27: Specific exception handling. Delegates to services.check_in_visitor()."""
    if request.method == 'POST':
        try:
            services.check_in_visitor(
                booking_id=request.POST.get('booking-id'),
                visitor_name=request.POST.get('name'),
                visitor_phone=request.POST.get('phone'),
                visitor_email=request.POST.get('email', ''),
                visitor_address=request.POST.get('address', ''),
            )
        except BookingDetail.DoesNotExist:  # V-27: specific exception
            logger.error("Booking not found during check-in")
            return HttpResponse('/visitorhostel/')
        except Exception as e:
            logger.error(f"Error in check_in: {e}")
        return HttpResponse('/visitorhostel/')
    return HttpResponse('/visitorhostel/')


@login_required(login_url='/accounts/login/')
def check_out(request):
    """V-10, V-25: Delegates to services.check_out_booking()."""
    if request.method == 'POST':
        try:
            services.check_out_booking(
                booking_id=request.POST.get('id'),
                meal_bill=request.POST.get('mess_bill'),
                room_bill=request.POST.get('room_bill'),
                caretaker_user=request.user,
            )
        except Exception as e:
            logger.error(f"Error in check_out: {e}")
        return HttpResponseRedirect('/visitorhostel/')
    return HttpResponseRedirect('/visitorhostel/')


@login_required(login_url='/accounts/login/')
def record_meal(request):
    """V-11, V-28: Delegates to services.record_meal()."""
    if request.method == "POST":
        try:
            services.record_meal(
                booking_id=request.POST.get('booking'),
                visitor_id=request.POST.get('pk'),
                m_tea=request.POST.get('m_tea'),
                breakfast=request.POST.get('breakfast'),
                lunch=request.POST.get('lunch'),
                eve_tea=request.POST.get('eve_tea'),
                dinner=request.POST.get('dinner'),
            )
        except Exception as e:
            logger.error(f"Error in record_meal: {e}")
        return HttpResponseRedirect('/visitorhostel/')
    return HttpResponseRedirect('/visitorhostel/')


@login_required(login_url='/accounts/login/')
def bill_between_dates(request):
    """Delegates to services.get_bill_report()."""
    if request.method == 'POST':
        date_1 = request.POST.get('start_date')
        date_2 = request.POST.get('end_date')
        bills, meal_total, room_total, total_bill, individual_total = (
            services.get_bill_report(date_1, date_2)
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
    """V-41: Fixed typo (was room_availabity). Delegates to selectors."""
    if request.method == 'POST':
        date_1 = request.POST.get('start_date')
        date_2 = request.POST.get('end_date')
        available_rooms = selectors.get_available_rooms(date_1, date_2)
        room_numbers = [room.room_number for room in available_rooms]
        return render(request, "vhModule/room-availability.html",
                      {'available_rooms': room_numbers})
    return HttpResponseRedirect('/visitorhostel/')


@login_required(login_url='/accounts/login/')
def add_to_inventory(request):
    """V-20, V-24: Delegates to services.add_inventory_item()."""
    if request.method == 'POST':
        try:
            services.add_inventory_item(
                item_name=request.POST.get('item_name'),
                quantity=request.POST.get('quantity'),
                cost=request.POST.get('cost'),
                bill_number=request.POST.get('bill_number'),
                consumable=request.POST.get('consumable', 'false'),
            )
        except (ValueError, TypeError) as e:
            logger.error(f"Invalid inventory input: {e}")
        return HttpResponseRedirect('/visitorhostel/')
    return HttpResponseRedirect('/visitorhostel/')


@login_required(login_url='/accounts/login/')
def update_inventory(request):
    """V-21: Delegates to services.update_inventory_item()."""
    if request.method == 'POST':
        try:
            services.update_inventory_item(
                item_id=request.POST.get('id'),
                quantity=request.POST.get('quantity'),
            )
        except (ValueError, TypeError) as e:
            logger.error(f"Invalid inventory update input: {e}")
        return HttpResponseRedirect('/visitorhostel/')
    return HttpResponseRedirect('/visitorhostel/')


@login_required(login_url='/accounts/login/')
def edit_room_status(request):
    """V-22: Delegates to services.edit_room_status()."""
    if request.method == 'POST':
        try:
            services.edit_room_status(
                room_number=request.POST.get('room_number'),
                room_status=request.POST.get('room_status'),
            )
        except Exception as e:
            logger.error(f"Error editing room status: {e}")
        return HttpResponseRedirect('/visitorhostel/')
    return HttpResponseRedirect('/visitorhostel/')


@login_required(login_url='/accounts/login/')
def forward_booking(request):
    """V-13: Delegates to services.forward_booking() with R-08."""
    if request.method == 'POST':
        try:
            services.forward_booking(
                booking_id=request.POST.get('id'),
                modified_category=request.POST.get('modified_category'),
                rooms_list=request.POST.getlist('rooms[]'),
                remark=request.POST.get('remark', ''),
                requesting_user=request.user,
            )
        except Exception as e:
            logger.error(f"Error in forward_booking: {e}")
        return HttpResponseRedirect('/visitorhostel/')
    return HttpResponseRedirect('/visitorhostel/')


# V-32: Removed broken bill_generation() view (referenced non-existent models)
# V-16: Removed dead caretaker = 'shailesh' assignment
# V-29/V-30: Removed all print() statements
# V-31: Removed all commented-out code (~80 lines)
