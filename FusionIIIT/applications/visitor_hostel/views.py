# views.py
# Thin legacy views for the visitor_hostel module.
# All business logic delegated to services.py, all queries to selectors.py.
# Fixes: V-05–V-13, V-16, V-22–V-32, V-35–V-36, V-38–V-39, V-41, V-43–V-44
# Refactoring: T-01b, T-03b, T-15b, T-27, T-28, T-30c

import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect
from django.shortcuts import render

from . import services
from . import selectors
from .exceptions import BookingError, InventoryError  # T-15b
from .forms import InventoryForm  # T-28
from .models import BookingDetail

logger = logging.getLogger(__name__)


@login_required(login_url='/accounts/login/')
def visitorhostel(request):
    """
    V-05: Dashboard view.
    T-03b: Role-based data assembly delegated to services.get_dashboard_data().
    T-01b: Replaced User.objects.all() with selectors.get_all_users().
    """
    user = request.user
    user_designation = services.get_user_designation(user)

    # T-03b: Single call replaces 20-line if/else block
    ctx = services.get_dashboard_data(user, user_designation)

    all_bookings = selectors.get_all_bookings()
    active_bookings = ctx['active_bookings']
    dashboard_bookings = ctx['dashboard_bookings']

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
        'complete_bookings': ctx['complete_bookings'],
        'pending_bookings': ctx['pending_bookings'],
        'active_bookings': active_bookings,
        'canceled_bookings': ctx['canceled_bookings'],
        'dashboard_bookings': dashboard_bookings,
        'bills': bills,
        'available_rooms': ctx['available_rooms'],
        'forwarded_rooms': ctx['forwarded_rooms'],
        'inventory': inventory,
        'inventory_bill': inventory_bill,
        'active_visitors': active_visitors,
        'intenders': selectors.get_all_users(),  # T-01b
        'user': user,
        'visitors': visitors,
        'rooms': rooms,
        'previous_visitors': previous_visitors,
        'completed_booking_bills': completed_booking_bills,
        'current_balance': current_balance,
        'rejected_bookings': ctx['rejected_bookings'],
        'cancel_booking_request': ctx['cancel_booking_request'],
        'cancel_booking_requested': ctx['cancel_booking_requested'],
        'user_designation': user_designation,
        'visitor_list': visitor_list,
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
        intenders = selectors.get_all_users()  # T-01b
        return render(request, "vhModule/visitorhostel.html", {'intenders': intenders})
    return HttpResponseRedirect('/visitorhostel/')


@login_required(login_url='/accounts/login/')
def request_booking(request):
    """V-06: Delegates to services.create_booking() + services.create_visitor().
    T-01b: User lookup moved to selectors.get_user_by_id().
    T-15b: Typed BookingError caught and surfaced to user.
    """
    if request.method == 'POST':
        try:
            intender_id = request.POST.get('intender')
            intender_user = selectors.get_user_by_id(intender_id)  # T-01b

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
        except BookingError as e:  # T-15b
            logger.error(f"Booking error in request_booking: {e}")
            messages.error(request, str(e))
        except Exception as e:
            logger.error(f"Unexpected error in request_booking: {e}")

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
        except BookingError as e:  # T-15b
            logger.error(f"Booking error in update_booking: {e}")
            messages.error(request, str(e))
        except Exception as e:
            logger.error(f"Unexpected error in update_booking: {e}")
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
        except BookingError as e:  # T-15b
            logger.error(f"Booking error in confirm_booking: {e}")
            messages.error(request, str(e))
        except Exception as e:
            logger.error(f"Unexpected error in confirm_booking: {e}")
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
        except BookingError as e:  # T-15b
            logger.error(f"Booking error in cancel_booking: {e}")
            messages.error(request, str(e))
        except Exception as e:
            logger.error(f"Unexpected error in cancel_booking: {e}")
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
        except BookingError as e:  # T-15b
            logger.error(f"Booking error in cancel_booking_request: {e}")
            messages.error(request, str(e))
        except Exception as e:
            logger.error(f"Unexpected error in cancel_booking_request: {e}")
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
        except BookingError as e:  # T-15b
            logger.error(f"Booking error in reject_booking: {e}")
            messages.error(request, str(e))
        except Exception as e:
            logger.error(f"Unexpected error in reject_booking: {e}")
    return HttpResponseRedirect('/visitorhostel/')


@login_required(login_url='/accounts/login/')
def check_in(request):
    """V-27: Delegates to services.check_in_visitor().
    T-30c: Replaced HttpResponse with HttpResponseRedirect.
    """
    if request.method == 'POST':
        try:
            services.check_in_visitor(
                booking_id=request.POST.get('booking-id'),
                visitor_name=request.POST.get('name'),
                visitor_phone=request.POST.get('phone'),
                visitor_email=request.POST.get('email', ''),
                visitor_address=request.POST.get('address', ''),
            )
        except BookingDetail.DoesNotExist:
            logger.error("Booking not found during check-in")
            return HttpResponseRedirect('/visitorhostel/')  # T-30c
        except BookingError as e:  # T-15b
            logger.error(f"Booking error in check_in: {e}")
            messages.error(request, str(e))
            return HttpResponseRedirect('/visitorhostel/')  # T-30c
        except Exception as e:
            logger.error(f"Unexpected error in check_in: {e}")
        return HttpResponseRedirect('/visitorhostel/')  # T-30c
    return HttpResponseRedirect('/visitorhostel/')  # T-30c


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
        except BookingError as e:  # T-15b
            logger.error(f"Booking error in check_out: {e}")
            messages.error(request, str(e))
        except Exception as e:
            logger.error(f"Unexpected error in check_out: {e}")
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
    """T-27: Removed list comprehension — pass queryset directly to template."""
    if request.method == 'POST':
        date_1 = request.POST.get('start_date')
        date_2 = request.POST.get('end_date')
        available_rooms = selectors.get_available_rooms(date_1, date_2)
        # T-27: Template iterates over available_rooms queryset directly
        return render(request, "vhModule/room-availability.html",
                      {'available_rooms': available_rooms})
    return HttpResponseRedirect('/visitorhostel/')


@login_required(login_url='/accounts/login/')
def add_to_inventory(request):
    """V-20, V-24: Delegates to services.add_inventory_item().
    T-28: Validates with InventoryForm before calling service.
    """
    if request.method == 'POST':
        form = InventoryForm(request.POST)  # T-28
        if form.is_valid():
            try:
                services.add_inventory_item(
                    item_name=form.cleaned_data['item_name'],
                    quantity=form.cleaned_data['quantity'],
                    cost=form.cleaned_data['cost'],
                    bill_number=form.cleaned_data['bill_number'],
                    consumable='true' if form.cleaned_data.get('consumable') else 'false',
                )
            except InventoryError as e:  # T-15b
                logger.error(f"Inventory error in add_to_inventory: {e}")
                messages.error(request, str(e))
            except Exception as e:
                logger.error(f"Unexpected error in add_to_inventory: {e}")
        else:
            logger.error(f"Invalid inventory form: {form.errors}")
            messages.error(request, "Invalid inventory input.")
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
        except InventoryError as e:  # T-15b
            logger.error(f"Inventory error in update_inventory: {e}")
            messages.error(request, str(e))
        except (ValueError, TypeError) as e:
            logger.error(f"Invalid inventory update input: {e}")
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
        except BookingError as e:  # T-15b
            logger.error(f"Booking error in forward_booking: {e}")
            messages.error(request, str(e))
        except Exception as e:
            logger.error(f"Unexpected error in forward_booking: {e}")
    return HttpResponseRedirect('/visitorhostel/')
