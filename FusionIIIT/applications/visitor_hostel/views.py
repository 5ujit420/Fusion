import datetime
import logging

import numpy as np
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET
from rest_framework.authentication import TokenAuthentication
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from applications.globals.models import ExtraInfo, HoldsDesignation
from notification.views import visitors_hostel_notif

from .models import Bill, BookingDetail, Inventory, InventoryBill, MealRecord, RoomDetail, VisitorDetail
from .selectors import (
    get_active_bookings_queryset,
    get_api_completed_bookings_queryset,
    get_available_rooms_between,
    get_available_rooms_queryset,
    get_booking_detail,
    get_booking_range_bills,
    get_booking_requests_queryset,
    get_completed_bookings_queryset,
    get_forwarded_booking_rooms_between,
    get_inactive_bookings_queryset,
    get_inventory_bill as get_inventory_bill_selector,
    get_inventory_bills_queryset,
    get_inventory_item as get_inventory_item_selector,
    get_inventory_queryset,
    get_overlapping_room_bookings,
    get_room_by_number,
    get_user_designation,
)
from .serializers import (
    BookingForwardSerializer,
    BookingRequestInputSerializer,
    BookingUpdateSerializer,
    CheckInSerializer,
    CheckOutSerializer,
    InventoryBillSerializer,
    InventoryCheckoutSerializer,
    InventoryMutationSerializer,
    InventorySerializer,
    RoomAvailabilitySerializer,
)
from .services import (
    add_checkout_inventory_items,
    add_inventory_item_and_bill,
    build_booking_bill_response,
    build_dashboard_context,
    check_in_booking,
    check_out_booking,
    confirm_booking as confirm_booking_service,
    create_booking_request,
    forward_booking as forward_booking_service,
    get_designation_user,
    record_meal_for_visitor,
    update_booking_details,
    update_expired_pending_bookings,
    update_inventory_item,
)


# main page showing dashboard of user

@login_required(login_url='/accounts/login/')
def visitorhostel(request):
    return render(request, "vhModule/visitorhostel.html", build_dashboard_context(request.user))

#### NEW
def update_expired_bookings():
    update_expired_pending_bookings(timezone.now().date())
    
@login_required
@require_GET
def get_intenders(request):
    intenders = User.objects.all().values('id', 'username')
    return JsonResponse(list(intenders), safe=False)

@login_required
def get_user_details(request):
    user = request.user
    user_details = {
        'id': user.id,
        'username': user.username,
        'role': 'student' if user.groups.filter(name='Students').exists() else 'other',
        'intender_id': user.id  # Assuming the intender_id is the same as the user ID
    }
    return JsonResponse(user_details)

# Get methods for bookings



@api_view(['GET'])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
def get_booking_requests(request):
    update_expired_bookings()
    bookings_list = [
        {
            'id': booking.id,
            'intender': booking.intender.first_name,
            'email': booking.intender.email,
            'bookingFrom': booking.booking_from.isoformat() if booking.booking_from else None,
            'bookingTo': booking.booking_to.isoformat() if booking.booking_to else None,
            'category': booking.visitor_category,
            'modifiedCategory': booking.modified_visitor_category,
            'status': booking.status,
            'remarks': booking.remark,
            'rooms': [room.room_number for room in booking.rooms.all()],
        }
        for booking in get_booking_requests_queryset(request.user)
    ]
    return JsonResponse({'pending_bookings': bookings_list})


#@login_required(login_url='/accounts/login/')
# def get_booking_requests(request):
#     print("works? in the original request")
#     if request.method == 'GET':
#         pending_bookings = BookingDetail.objects.select_related(
#             'intender', 'caretaker').filter(status="Pending")
#         print(pending_bookings)

#         return render(request, "vhModule/visitorhostel.html", {'pending_bookings': pending_bookings})
#     else:
#         return HttpResponseRedirect('/visitorhostel/')

# getting active bookings

@api_view(['GET'])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
def get_active_bookings(request):
    bookings_list = [
        {
            'id': booking.id,
            'intender': booking.intender.first_name,
            'email': booking.intender.email,
            'bookingFrom': booking.booking_from.isoformat() if booking.booking_from else None,
            'bookingTo': booking.booking_to.isoformat() if booking.booking_to else None,
            'category': booking.visitor_category,
            'modifiedVisitorCategory': booking.modified_visitor_category,
            'status': booking.status,
        }
        for booking in get_active_bookings_queryset(request.user)
    ]
    return JsonResponse({'active_bookings': bookings_list})



# @login_required(login_url='/accounts/login/')
# def get_active_bookings(request):
#     if request.method == 'POST':
#         active_bookings = BookingDetail.objects.select_related(
#             'intender', 'caretaker').filter(status="Confirmed")

#         return render(request, "vhModule/visitorhostel.html", {'active_bookings': active_bookings})
#     else:
#         return HttpResponseRedirect('/visitorhostel/')


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
def get_inactive_bookings(request):
    bookings_list = [
        {
            'id': booking.id,
            'intender': booking.intender.first_name,
            'email': booking.intender.email,
            'bookingFrom': booking.booking_from.isoformat() if booking.booking_from else None,
            'bookingTo': booking.booking_to.isoformat() if booking.booking_to else None,
            'category': booking.visitor_category,
            'modifiedCategory': booking.modified_visitor_category,
            'status': booking.status,
        }
        for booking in get_inactive_bookings_queryset(request.user)
    ]
    return JsonResponse({'cancelled_bookings': bookings_list})


# @login_required(login_url='/accounts/login/')
# def get_inactive_bookings(request):
#     if request.method == 'POST':
#         inactive_bookings = BookingDetail.objects.select_related('intender', 'caretaker').filter(
#             Q(status="Cancelled") | Q(status="Rejected") | Q(status="Complete"))

#         return render(request, "vhModule/visitorhostel.html", {'inactive_bookings': inactive_bookings})
#     else:
#         return HttpResponseRedirect('/visitorhostel/')

# Method for making booking request

@api_view(['GET'])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
def get_completed_bookings(request):
    bookings_list = [
        {
            'id': booking.id,
            'intender': booking.intender.first_name,
            'email': booking.intender.email,
            'bookingFrom': booking.booking_from.isoformat() if booking.booking_from else None,
            'bookingTo': booking.booking_to.isoformat() if booking.booking_to else None,
            'checkOut': booking.check_out.isoformat() if booking.check_out else None,
            'category': booking.visitor_category,
        }
        for booking in get_completed_bookings_queryset(request.user)
    ]
    return JsonResponse({'completed_bookings': bookings_list})


@login_required(login_url='/accounts/login/')
def get_booking_form(request):
    if request.method == 'POST':
        intenders = User.objects.all()
        return render(request, "vhModule/visitorhostel.html", {'intenders': intenders})
    else:
        return HttpResponseRedirect('/visitorhostel/')

# request booking form action view starts here
# request booking form action view
@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
def request_booking(request):
    serializer = BookingRequestInputSerializer(
        data={
            'booking_id': request.data.get('booking_id'),
            'category': request.data.get('category'),
            'number_of_people': request.data.get('number-of-people'),
            'purpose_of_visit': request.data.get('purpose-of-visit'),
            'booking_from': request.data.get('booking_from'),
            'booking_to': request.data.get('booking_to'),
            'booking_from_time': request.data.get('booking_from_time'),
            'booking_to_time': request.data.get('booking_to_time'),
            'remarks_during_booking_request': request.data.get('remarks_during_booking_request'),
            'bill_settlement': request.data.get('bill_settlement'),
            'number_of_rooms': request.data.get('number-of-rooms'),
            'visitor_name': request.data.get('visitor_name'),
            'visitor_email': request.data.get('visitor_email'),
            'visitor_phone': request.data.get('visitor_phone'),
            'visitor_organization': request.data.get('visitor_organization'),
            'visitor_address': request.data.get('visitor_address'),
            'nationality': request.data.get('nationality'),
        }
    )
    if not serializer.is_valid():
        return JsonResponse({'error': serializer.errors}, status=400)
    try:
        booking = create_booking_request(serializer.validated_data, request.user)
        return JsonResponse({'success': 'Booking successfully created', 'booking_id': booking.id})
    except ValueError as exc:
        return JsonResponse({'error': str(exc)}, status=400)
    except Exception as exc:
        return JsonResponse({'error': str(exc)}, status=400)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
def expire_pending_bookings(request):
    if request.method == 'POST':
        current_date = timezone.now().date()
        
        # Fetch all bookings with status "Pending" and booking_to date less than the current date
        expired_bookings = BookingDetail.objects.filter(
            status='Pending',
            booking_to__lt=current_date
        )
        
        # Update the status of these bookings to "Expired"
        expired_bookings.update(status='Expired')
        
        return JsonResponse({'success': 'Pending bookings updated to Expired'}, status=200)
    else:
        return JsonResponse({'error': 'Invalid request method'}, status=400)
# request booking form action view starts here

# @login_required(login_url='/accounts/login/')
# def request_booking(request):

#     if request.method == 'POST':
#         print("Received Data:", request)
#         print("Request POST Data:", request.POST)
#         print("Request FILES Data:", request.FILES)
#         # print("Request Headers:", request.headers)
#         # print("Request Method:", request.method)
#         # print("Request User:", request.user)
#         flag = 0

#         # getting details from request form
#         intender = request.POST.get('intender')
#         user = User.objects.get(id=intender)
#         print("jiihuhhih")
#         print(user)
#         booking_id = request.POST.get('booking-id')
#         category = request.POST.get('category')
#         person_count = request.POST.get('number-of-people')
#         bookingObject = []
#         # if person_count and (int(person_count)<20):
#         #   person_count = person_count

#         # else:
#         #  flag = 1    # for error

#         #     person_count = 1
#         purpose_of_visit = request.POST.get('purpose-of-visit')
#         booking_from = request.POST.get('booking_from')
#         booking_to = request.POST.get('booking_to')
#         booking_from_time = request.POST.get('booking_from_time')
#         booking_to_time = request.POST.get('booking_to_time')
#         remarks_during_booking_request = request.POST.get(
#             'remarks_during_booking_request')
#         bill_to_be_settled_by = request.POST.get('bill_settlement')
#         number_of_rooms = request.POST.get('number-of-rooms')
#         caretaker = 'shailesh'

#      #   if (int(person_count)<int(number_of_rooms)):
#       #      flag=1

#       #  if flag ==0:
#         # print(sys.getsizeof(booking_from_time))
#         # print(sys.getsizeof(booking_from))
#         # print(sys.getsizeof(purpose_of_visit))
#         # print(sys.getsizeof(bill_to_be_settled_by))
#         # print("gfcfhcghv")
#         care_taker = HoldsDesignation.objects.select_related('user','working','designation').filter(designation__name = "VhCaretaker")
#         care_taker = care_taker[0]
#         # print(care_taker,"care_taker")
#         care_taker = care_taker.user
#         bookingObject = BookingDetail.objects.create(
#             caretaker=care_taker,
#             purpose=purpose_of_visit,
#             intender=user,
#             booking_from=booking_from,
#             booking_to=booking_to,
#             visitor_category=category,
#             person_count=person_count,
#             arrival_time=booking_from_time,
#             departure_time=booking_to_time,
#             # remark=remarks_during_booking_request,
#             number_of_rooms=number_of_rooms,
#             bill_to_be_settled_by=bill_to_be_settled_by)
#         # visitor_hostel_caretaker_notif(request.user,care_taker,"Submitted")
#         # print (bookingObject)
#         # print("Hello")
# #        {% if messages %}
# #   {% for message in messages %}
# #     <div class="alert alert-dismissible alert-success">
# #       <button type="button" class="close" data-dismiss="alert">
# #       ×
# #       </button>
# #       <strong>{{message}}<strong>
# #     </div>
# #  {% endfor %}
# # {% endif %}

# #         # in case of any attachment

# #         doc = request.FILES.get('files-during-booking-request')
# #         remark = remarks_during_booking_request,
# #         if doc:
# #             print("hello")
# #             filename, file_extenstion = os.path.splitext(
# #                 request.FILES.get('files-during-booking-request').booking_id)
# #             filename = booking_id
# #             full_path = settings.MEDIA_ROOT + "/VhImage/"
# #             url = settings.MEDIA_URL + filename + file_extenstion
# #             if not os.path.isdir(full_path):
# #                 cmd = "mkdir " + full_path
# #                 os.subprocess.call(cmd, shell=True)
# #             fs = FileSystemStorage(full_path, url)
# #             fs.save(filename + file_extenstion, doc)
# #             uploaded_file_url = "/media/online_cms/" + filename
# #             uploaded_file_url = uploaded_file_url + file_extenstion
# #             bookingObject.image = uploaded_file_url
# #             bookingObject.save()

# #         # visitor datails from place request form

#         visitor_name = request.POST.get('name')
#         visitor_phone = request.POST.get('phone')
#         visitor_email = request.POST.get('email')
#         visitor_address = request.POST.get('address')
#         visitor_organization = request.POST.get('organization')
#         visitor_nationality = request.POST.get('nationality')
#         # visitor_nationality="jk"
#         if visitor_organization == '':
#             visitor_organization = ' '

#         visitor = VisitorDetail.objects.create(
#             visitor_phone=visitor_phone, visitor_name=visitor_name, visitor_email=visitor_email, visitor_address=visitor_address, visitor_organization=visitor_organization, nationality=visitor_nationality
#         )

#         # try:
#         # bd = BookingDetail.objects.get(id=booking_id)

#         bookingObject.visitor.add(visitor)
#         bookingObject.save()

#         # except:
#         # print("exception occured")
#         # return HttpResponse('/visitorhostel/')

#         # for sending notification of booking request to caretaker

#         # caretaker_name = HoldsDesignation.objects.select_related('user','working','designation').get(designation__name = "VhCaretaker")
#         # visitors_hostel_notif(request.user, care_taker.user, 'booking_request')

#         return HttpResponseRedirect('/visitorhostel/')
#     else:
#         return HttpResponseRedirect('/visitorhostel/')

#get booking details as Caretaker

def get_booking_details(request, booking_id):
    try:
        booking = get_booking_detail(booking_id)
        first_visitor = booking.visitor.first()
        booking_data = {
            'intenderUsername': booking.intender.username,
            'intenderEmail': booking.intender.email,
            'bookingFrom': booking.booking_from,
            'bookingTo': booking.booking_to,
            'visitorCategory': booking.visitor_category,
            'modifiedVisitorCategory': booking.modified_visitor_category,
            'personCount': booking.person_count,
            'numberOfRooms': booking.number_of_rooms,
            'purpose': booking.purpose,
            'billToBeSettledBy': booking.bill_to_be_settled_by,
            'remarks': booking.remark,
            'visitorName': first_visitor.visitor_name if first_visitor else '',
            'visitorEmail': first_visitor.visitor_email if first_visitor else '',
            'visitorPhone': first_visitor.visitor_phone if first_visitor else '',
            'visitorOrganization': first_visitor.visitor_organization if first_visitor else '',
            'visitorAddress': first_visitor.visitor_address if first_visitor else '',
            'availableRooms': list(get_available_rooms_queryset().values('room_number'))
        }
        return JsonResponse(booking_data)
    except BookingDetail.DoesNotExist:
        return JsonResponse({'error': 'Booking not found'}, status=404)
    
# updating a booking request

@login_required(login_url='/accounts/login/')
def update_booking(request):
    if request.method == 'POST':
        user = request.user
        print(request.POST)

        booking_id = request.POST.get('booking-id')

        category = request.POST.get('category')
        person_count = request.POST.get('number-of-people')
        bookingObject = []
        if person_count:
            person_count = person_count
        else:
            person_count = 1
        purpose_of_visit = request.POST.get('purpose-of-visit')
        booking_from = request.POST.get('booking_from')
        booking_to = request.POST.get('booking_to')
        number_of_rooms = request.POST.get('number-of-rooms')

        # remark = request.POST.get('remark')
        booking = get_booking_detail(booking_id)
        booking.person_count = person_count
        booking.number_of_rooms = number_of_rooms
        booking.booking_from = booking_from
        booking.booking_to = booking_to
        booking.purpose = purpose_of_visit
        booking.save()
        forwarded_rooms = {}
        # BookingDetail.objects.filter(id=booking_id).update(person_count=person_count,
        #                                                     purpose=purpose_of_visit,
        #                                                     booking_from=booking_from,
        #                                                     booking_to=booking_to,
        #                                                     number_of_rooms=number_of_rooms)
        booking = get_booking_detail(booking_id)
        c_bookings = BookingDetail.objects.select_related('intender', 'caretaker').prefetch_related('rooms').filter(
            Q(status="Forward"),  booking_to__gte=datetime.datetime.today()).order_by('booking_from')
        for booking in c_bookings:
            booking_from = booking.booking_from
            booking_to = booking.booking_to
            temp2 = get_forwarded_booking_rooms_between(booking_from, booking_to)
            forwarded_rooms[booking.id] = temp2
        return render(request, "visitorhostel/",
                      {
                          'forwarded_rooms': forwarded_rooms})

    else:
        return HttpResponseRedirect('/visitorhostel/')

# new confirm booking byVhIncharge

@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
@login_required(login_url='/accounts/login/')
def confirm_booking_new(request):
    serializer = BookingForwardSerializer(data=request.data)
    if not serializer.is_valid():
        return JsonResponse({'error': serializer.errors}, status=400)
    try:
        confirm_booking_service(request_user=request.user, **serializer.validated_data)
        return JsonResponse({'success': f"Booking successfully {serializer.validated_data.get('action')}ed"})
    except BookingDetail.DoesNotExist:
        return JsonResponse({'error': 'Booking not found'}, status=404)
    except RoomDetail.DoesNotExist:
        return JsonResponse({'error': 'One or more rooms not found'}, status=404)
    except Exception as exc:
        return JsonResponse({'error': str(exc)}, status=400)


# confirm booking by VhIncharge

@login_required(login_url='/accounts/login/')
def confirm_booking(request):
    if request.method == 'POST':
        booking_id = request.POST.get('booking-id')
        intender = request.POST.get('intender'),
        category = request.POST.get('category')
        purpose = request.POST.get('purpose-of-visit')
        booking_from = request.POST.get('booking_from')
        booking_to = request.POST.get('booking_to')
        person_count = request.POST.get('number-of-people')

        # rooms list
        rooms = request.POST.getlist('rooms[]')
        # print(rooms)
        booking = BookingDetail.objects.select_related(
            'intender', 'caretaker').get(id=booking_id)
        bd = BookingDetail.objects.select_related(
            'intender', 'caretaker').get(id=booking_id)
        bd.status = 'Confirmed'
        bd.category = category

        for room in rooms:
            room_object = RoomDetail.objects.get(room_number=room)
            bd.rooms.add(room_object)
        bd.save()

        # notification of booking confirmation
        visitors_hostel_notif(request.user, bd.intender,
                              'booking_confirmation')
        return HttpResponseRedirect('/visitorhostel/')
    else:
        return HttpResponseRedirect('/visitorhostel/')


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
def cancel_booking(request):
    if request.method == 'POST':
        user = request.user
        print(request.POST)
        booking_id = request.POST.get('booking-id')
        remark = request.POST.get('remark')
        charges = request.POST.get('charges')
        BookingDetail.objects.select_related('intender', 'caretaker').filter(id=booking_id).update(
            status='Canceled', remark=remark)
        booking = BookingDetail.objects.select_related(
            'intender', 'caretaker').get(id=booking_id)

        # if no applicable charges then set charges to zero
        x = 0
        if charges:
            Bill.objects.create(booking=booking, meal_bill=x, room_bill=int(
                charges), caretaker=user, payment_status=True)
        else:
            Bill.objects.create(booking=booking, meal_bill=x,
                                room_bill=x, caretaker=user, payment_status=True)

        complete_bookings = BookingDetail.objects.filter(Q(status="Canceled") | Q(
            status="Complete"), booking_to__lt=datetime.datetime.today()).select_related('intender', 'caretaker').order_by('booking_from')

        # to notify the intender that his cancellation request has been confirmed

        visitors_hostel_notif(request.user, booking.intender,
                              'booking_cancellation_request_accepted')
        return HttpResponseRedirect('/visitorhostel/')
    else:
        return HttpResponseRedirect('/visitorhostel/')

# cancel confirmed booing by intender


@login_required(login_url='/accounts/login/')
def cancel_booking_request(request):
    if request.method == 'POST':
        intender = request.user.holds_designations.filter(
            designation__name='VhIncharge')
        booking_id = request.POST.get('booking-id')
        remark = request.POST.get('remark')
        BookingDetail.objects.select_related('intender', 'caretaker').filter(
            id=booking_id).update(status='CancelRequested', remark=remark)

        incharge_name = HoldsDesignation.objects.select_related(
            'user', 'working', 'designation').filter(designation__name="VhIncharge")[1]

        # to notify the VhIncharge about a new cancelltaion request

        visitors_hostel_notif(
            request.user, incharge_name.user, 'cancellation_request_placed')
        return HttpResponseRedirect('/visitorhostel/')
    else:
        return HttpResponseRedirect('/visitorhostel/')


# rehject a booking request
@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
def reject_booking(request):
    if request.method == 'POST':
        booking_id = request.POST.get('booking-id')
        remark = request.POST.get('remark')
        BookingDetail.objects.select_related('intender', 'caretaker').filter(id=booking_id).update(
            status="Rejected", remark=remark)

        # to notify the intender that his request has been rejected

        # visitors_hostel_notif(request.user, booking.intender, 'booking_rejected')
        return HttpResponseRedirect('/visitorhostel/')
    else:
        return HttpResponseRedirect('/visitorhostel/')

# Guest check in view


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
def check_in(request):
    serializer = CheckInSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({'error': serializer.errors}, status=400)
    try:
        check_in_booking(serializer.validated_data['booking_id'], serializer.validated_data)
        return Response({'status': 'visitor checked in'})
    except BookingDetail.DoesNotExist:
        return Response({'error': 'Booking not found'}, status=404)
    except Exception as exc:
        return Response({'error': str(exc)}, status=400)

# @login_required(login_url='/accounts/login/')
# def check_in(request):
#     if request.method == 'POST':
#         booking_id = request.POST.get('booking-id')
#         visitor_name = request.POST.get('name')
#         visitor_phone = request.POST.get('phone')
#         visitor_email = request.POST.get('email')
#         visitor_address = request.POST.get('address')
#         check_in_date = datetime.date.today()

#         # save visitors details
#         visitor = VisitorDetail.objects.create(
#             visitor_phone=visitor_phone, visitor_name=visitor_name, visitor_email=visitor_email, visitor_address=visitor_address)
#         try:
#             bd = BookingDetail.objects.select_related(
#                 'intender', 'caretaker').get(id=booking_id)
#             bd.status = "CheckedIn"
#             bd.check_in = check_in_date
#             bd.visitor.add(visitor)
#             bd.save()

#         except:
#             return HttpResponse('/visitorhostel/')
#         return HttpResponse('/visitorhostel/')
#     else:
#         return HttpResponse('/visitorhostel/')

# guest check out view

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
def check_out(request):
    serializer = CheckOutSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({'error': serializer.errors}, status=400)
    try:
        check_out_booking(serializer.validated_data['booking_id'], serializer.validated_data.get('check_out_time'))
        return Response({'status': 'visitor checked out', 'check_out_time': serializer.validated_data.get('check_out_time')})
    except BookingDetail.DoesNotExist:
        return Response({'error': 'Booking not found'}, status=404)
    except Exception as exc:
        return Response({'error': str(exc)}, status=400)
    
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
def check_out_with_inventory(request):
    serializer = InventoryCheckoutSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({'error': serializer.errors}, status=400)
    try:
        booking_id = serializer.validated_data['booking_id']
        check_out_time = serializer.validated_data.get('check_out_time')
        check_out_booking(booking_id, check_out_time)
        add_checkout_inventory_items(booking_id, serializer.validated_data.get('inventory_items', []))
        return Response({'status': 'visitor checked out and inventory updated', 'check_out_time': check_out_time})
    except BookingDetail.DoesNotExist:
        return Response({'error': 'Booking not found'}, status=404)
    except Exception as exc:
        return Response({'error': str(exc)}, status=400)
# @login_required(login_url='/accounts/login/')
# def check_out(request):
#     user = get_object_or_404(User, username=request.user.username)
#     c = ExtraInfo.objects.select_related('department').all().filter(user=user)

#     if user:
#         if request.method == 'POST':
#             id = request.POST.get('id')
#             meal_bill = request.POST.get('mess_bill')
#             room_bill = request.POST.get('room_bill')
#             checkout_date = datetime.date.today()
#             total_bill = int(meal_bill)+int(room_bill)
#             BookingDetail.objects.select_related('intender', 'caretaker').filter(id=id).update(
#                 check_out=datetime.datetime.today(), status="Complete")
#             booking = BookingDetail.objects.select_related(
#                 'intender', 'caretaker').get(id=id)
#             Bill.objects.create(booking=booking, meal_bill=int(meal_bill), room_bill=int(
#                 room_bill), caretaker=user, payment_status=True, bill_date=checkout_date)

#             # for visitors in visitor_info:

#             # meal=Meal.objects.all().filter(visitor=v_id).distinct()
#             # print(meal)
#             # for m in meal:
#             # mess_bill1=0
#             # if m.morning_tea==True:
#             #     mess_bill1=mess_bill1+ m.persons*10
#             #     print(mess_bill1)
#             # if m.eve_tea==True:
#             #     mess_bill1=mess_bill1+m.persons*10
#             # if m.breakfast==True:
#             #     mess_bill1=mess_bill1+m.persons*50
#             # if m.lunch==True:
#             #     mess_bill1=mess_bill1+m.persons*100
#             # if m.dinner==True:
#             #     mess_bill1=mess_bill1+m.persons*100
#             #
#             # if mess_bill1==m.persons*270:
#             #     mess_bill=mess_bill+225*m.persons
#             # else:
#             #         mess_bill=mess_bill + mess_bill1

#             # RoomStatus.objects.filter(book_room=book_room[0]).update(status="Available",book_room='')

#             return HttpResponseRedirect('/visitorhostel/')
#         else:
#             return HttpResponseRedirect('/visitorhostel/')


@login_required(login_url='/accounts/login/')
def record_meal(request):
    user = get_object_or_404(User, username=request.user.username)
    c = ExtraInfo.objects.select_related('department').all().filter(user=user)

    if user:
        if request.method == "POST":

            id = request.POST.get('pk')
            booking_id = request.POST.get('booking')
            record_meal_for_visitor(
                booking_id=booking_id,
                visitor_id=id,
                meal_payload={
                    "m_tea": request.POST.get("m_tea"),
                    "breakfast": request.POST.get("breakfast"),
                    "lunch": request.POST.get("lunch"),
                    "eve_tea": request.POST.get("eve_tea"),
                    "dinner": request.POST.get("dinner"),
                },
            )
            return HttpResponseRedirect('/visitorhostel/')
        else:
            return HttpResponseRedirect('/visitorhostel/')

# generate bill records between date range


@login_required(login_url='/accounts/login/')
def bill_generation(request):
    user = get_object_or_404(User, username=request.user.username)
    c = ExtraInfo.objects.all().filter(user=user)

    if user:
        if request.method == 'POST':
            v_id = request.POST.getlist('visitor')[0]

            meal_bill = request.POST.getlist('mess_bill')[0]
            room_bill = request.POST.getlist('room_bill')[0]
            status = request.POST.getlist('status')[0]
            if status == "True":
                st = True
            else:
                st = False

            user = get_object_or_404(User, username=request.user.username)
            c = ExtraInfo.objects.select_related(
                'department').filter(user=user)
            visitor = Visitor.objects.filter(visitor_phone=v_id)
            visitor = visitor[0]
            visitor_bill = Visitor_bill.objects.create(
                visitor=visitor, caretaker=user, meal_bill=meal_bill, room_bill=room_bill, payment_status=st)
            messages.success(request, 'guest check out successfully')
            return HttpResponseRedirect('/visitorhostel/')

        else:
            return HttpResponseRedirect('/visitorhostel/')
        
# get available rooms list between date range

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
def room_availabity_new(request):
    serializer = RoomAvailabilitySerializer(data=request.data)
    if not serializer.is_valid():
        return JsonResponse({'error': serializer.errors}, status=400)
    available_rooms_list = [
        room.room_number
        for room in get_available_rooms_between(
            serializer.validated_data['start_date'],
            serializer.validated_data['end_date'],
        )
    ]
    available_rooms_array = np.asarray(available_rooms_list)
    return JsonResponse({'available_rooms': available_rooms_array.tolist()})

# get available rooms list between date range


@login_required(login_url='/accounts/login/')
def room_availabity(request):
    if request.method == 'POST':
        date_1 = request.POST.get('start_date')
        date_2 = request.POST.get('end_date')
        available_rooms_list = []
        available_rooms_bw_dates = get_available_rooms_between(date_1, date_2)
        # print("Available rooms are ")
        for room in available_rooms_bw_dates:
            available_rooms_list.append(room.room_number)

        available_rooms_array = np.asarray(available_rooms_list)
        print(available_rooms_array)
        return render(request, "vhModule/room-availability.html", {'available_rooms': available_rooms_array})
    else:
        return HttpResponseRedirect('/visitorhostel/')




@api_view(['POST'])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
def check_partial_booking(request):
    """
    API to check room availability with partial booking support.
    """
    if request.method == 'POST':
        date_1 = request.data.get('start_date')
        date_2 = request.data.get('end_date')
        
        if not (date_1 and date_2):
            return JsonResponse({'error': 'Start date and end date are required.'}, status=400)
        
        # Convert input dates to datetime objects
        start_date = datetime.datetime.strptime(date_1, "%Y-%m-%d").date()
        end_date = datetime.datetime.strptime(date_2, "%Y-%m-%d").date()

        rooms = RoomDetail.objects.all()
        response_data = []

        for room in rooms:
            room_id = room.id
            room_number = room.room_number
            room_type = room.room_type

            # Check for existing bookings for the given room
            overlapping_bookings = get_overlapping_room_bookings(room_id, start_date, end_date)

            # Initialize response data
            partial_available = False
            available_ranges = []

            # If there are overlapping bookings, find the partial availability
            if overlapping_bookings.exists():
                partial_available = True
                current_start = start_date

                for booking in overlapping_bookings:
                    if booking.booking_from > current_start:
                        available_ranges.append({
                            'from': current_start,
                            'to': booking.booking_from
                        })
                    current_start = booking.booking_to

                if current_start < end_date:
                    available_ranges.append({
                        'from': current_start,
                        'to': end_date
                    })

            # Append room data to response
            response_data.append({
                'room_id': room_id,
                'room_number': room_number,
                'room_type': room_type, 
                'requested_from': date_1,
                'requested_to': date_2,
                'is_fully_available': not overlapping_bookings.exists(),
                'is_partial_available': partial_available,
                'available_ranges': available_ranges if partial_available else None,
            })

        return JsonResponse(response_data, safe=False)
    
    else:
        return JsonResponse({'error': 'Invalid request method'}, status=400)
@login_required(login_url='/accounts/login/')
def add_to_inventory(request):
    if request.method == 'POST':
        serializer = InventoryMutationSerializer(
            data={
                'item_name': request.POST.get('item_name'),
                'bill_number': request.POST.get('bill_number'),
                'quantity': request.POST.get('quantity'),
                'cost': request.POST.get('cost'),
                'consumable': request.POST.get('consumable') != 'false',
            }
        )
        if serializer.is_valid():
            add_inventory_item_and_bill(serializer.validated_data)
        return HttpResponseRedirect('/visitorhostel/')
    else:
        return HttpResponseRedirect('/visitorhostel/')


@login_required(login_url='/accounts/login/')
def update_inventory(request):
    if request.method == 'POST':
        id = request.POST.get('id')
        quantity = int(request.POST.get('quantity'))
        update_inventory_item(id, quantity)
        return HttpResponseRedirect('/visitorhostel/')
    else:
        return HttpResponseRedirect('/visitorhostel/')


@login_required(login_url='/accounts/login/')
def edit_room_status(request):
    if request.method == 'POST':
        room_number = request.POST.get('room_number')
        room_status = request.POST.get('room_status')
        room = get_room_by_number(room_number)
        RoomDetail.objects.filter(id=room.id).update(room_status=room_status)
        return HttpResponseRedirect('/visitorhostel/')
    else:
        return HttpResponseRedirect('/visitorhostel/')


@login_required(login_url='/accounts/login/')
def bill_between_dates(request):
    if request.method == 'POST':
        date_1 = request.POST.get('start_date')
        date_2 = request.POST.get('end_date')
        bill_range_bw_dates = bill_range(date_1, date_2)
        meal_total = 0
        room_total = 0
        individual_total = []

        # calculating room and mess bill booking wise
        for i in bill_range_bw_dates:
            meal_total = meal_total + i.meal_bill
            room_total = room_total + i.room_bill
            individual_total.append(i.meal_bill + i.room_bill)
        total_bill = meal_total + room_total
        # zip(bill_range_bw_dates, individual_total)
        return render(request, "vhModule/booking_bw_dates.html", {
            # 'booking_bw_dates': bill_range_bw_dates,
            'booking_bw_dates_length': bill_range_bw_dates,
            'meal_total': meal_total,
            'room_total': room_total,
            'total_bill': total_bill,
            'individual_total': individual_total,
            'booking_bw_dates': zip(bill_range_bw_dates, individual_total)
        })
    else:
        return HttpResponseRedirect('/visitorhostel/')


def bill_range(date1, date2):
    return get_booking_range_bills(date1, date2)


def booking_details(date1, date2):
    return get_available_rooms_between(date1, date2)

# function for finding forwarded booking rooms


def forwarded_booking_details(date1, date2):
    return get_forwarded_booking_rooms_between(date1, date2)


# View for forwarding booking - from VhCaretaker to VhIncharge

@login_required(login_url='/accounts/login/')
def forward_booking(request):
    if request.method == 'POST':
        user = request.user
        booking_id = request.POST.get('id')
        previous_category = request.POST.get('previous_category')
        modified_category = request.POST.get('modified_category')
        rooms = request.POST.getlist('rooms[]')
        remark = request.POST.get('remark')
        print(rooms)
        forward_booking_service(
            booking_id=booking_id,
            modified_category=modified_category,
            rooms=rooms,
            remarks=remark,
            request_user=request.user,
            notify_index=1,
        )

        dashboard_bookings = BookingDetail.objects.select_related('intender', 'caretaker').filter(Q(status="Pending") | Q(status="Forward") | Q(
            status="Confirmed") | Q(status='Rejected'), booking_to__gte=datetime.datetime.today(), intender=user).order_by('booking_from')

        # return render(request, "vhModule/visitorhostel.html",
        #           {'dashboard_bookings' : dashboard_bookings})
        return HttpResponseRedirect('/visitorhostel/')
    else:
        return HttpResponseRedirect('/visitorhostel/')

logger = logging.getLogger(__name__)
@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
def forward_booking_new(request):
    serializer = BookingForwardSerializer(data=request.data)
    if not serializer.is_valid():
        return JsonResponse({'error': serializer.errors}, status=400)
    try:
        forward_booking_service(request_user=request.user, **serializer.validated_data)
        return JsonResponse({'success': 'Booking successfully forwarded'})
    except BookingDetail.DoesNotExist:
        return JsonResponse({'error': 'Booking not found'}, status=404)
    except RoomDetail.DoesNotExist:
        return JsonResponse({'error': 'One or more rooms not found'}, status=404)
    except Exception as exc:
        return JsonResponse({'error': str(exc)}, status=400)
    
@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
def update_booking_new(request):
    serializer = BookingUpdateSerializer(data=request.data)
    if not serializer.is_valid():
        return JsonResponse({'error': serializer.errors}, status=400)
    try:
        update_booking_details(serializer.validated_data['booking_id'], serializer.validated_data, request.user)
        return JsonResponse({'success': 'Booking successfully forwarded'})
    except BookingDetail.DoesNotExist:
        return JsonResponse({'error': 'Booking not found'}, status=404)
    except RoomDetail.DoesNotExist:
        return JsonResponse({'error': 'One or more rooms not found'}, status=404)
    except Exception as exc:
        logger.error(f"Error: {str(exc)}")
        return JsonResponse({'error': str(exc)}, status=400)



#account statements

# Fetch all inventory items
@api_view(['GET'])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
def get_inventory_items(request):
    inventories = get_inventory_queryset()
    serializer = InventorySerializer(inventories, many=True)
    return Response(serializer.data)

# Fetch a specific inventory item by ID
@api_view(['GET'])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
def get_inventory_item(request, pk):
    try:
        inventory = get_inventory_item_selector(pk)
        serializer = InventorySerializer(inventory)
        return Response(serializer.data)
    except Inventory.DoesNotExist:
        return Response({"error": "Inventory item not found"}, status=404)

# Fetch all bills
@api_view(['GET'])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
def get_inventory_bills(request):
    bills = get_inventory_bills_queryset()
    serializer = InventoryBillSerializer(bills, many=True)
    return Response(serializer.data)

# Fetch a specific bill by ID
@api_view(['GET'])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
def get_inventory_bill(request, pk):
    try:
        bill = get_inventory_bill_selector(pk)
        serializer = InventoryBillSerializer(bill)
        return Response(serializer.data)
    except InventoryBill.DoesNotExist:
        return Response({"error": "Bill not found"}, status=404)


#income
# account statements

# Fetch all booking details
@api_view(['GET'])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
def get_all_bills(request):
    bookings = BookingDetail.objects.select_related('intender', 'caretaker').filter(Q(status="Confirmed") | Q(status="Active"))
    return Response([build_booking_bill_response(booking) for booking in bookings])

@api_view(['GET'])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
def get_bills_id(request, pk):
    try:
        booking = BookingDetail.objects.select_related('intender', 'caretaker').get(id=pk, status="Confirmed")
        return Response(build_booking_bill_response(booking))

    except BookingDetail.DoesNotExist:
        return Response({"error": "Booking detail not found"}, status=404)

    
@api_view(['GET'])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
def completed_bookings(request):
    bookings_list = [
        {
            'intender': booking.intender.first_name,
            'bookingDate': booking.booking_date.isoformat() if booking.booking_date else None,
            'checkIn': booking.check_in.isoformat() if booking.check_in else None,
            'checkInTime': booking.check_in_time if booking.check_in_time else None,
            'checkOutTime': booking.check_out_time if booking.check_out_time else None,
            'checkOut': booking.check_out.isoformat() if booking.check_out else None,
            'category': booking.visitor_category,
            'modifiedVisitorCategory': booking.modified_visitor_category,
        }
        for booking in get_api_completed_bookings_queryset(request.user)
    ]
    return JsonResponse({'completed_bookings': bookings_list})
