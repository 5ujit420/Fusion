"""
Services for visitor_hostel app.
Encapsulates all business logic.
Resolves: Fat View, Layer Violation, Feature Envy, Scattered Validation
"""
from django.utils import timezone
from django.db import transaction
from .models import BookingDetail, RoomDetail, VisitorDetail, MealRecord, Bill, Inventory


def calculate_room_bill(booking, visitor_category, days):
    """
    Calculate room bill based on visitor category and duration.
    Extracted from views.visitorhostel to resolve Feature Envy and Fat View.
    
    Rates (from original logic):
    - TA/Contingent: 100/day
    - UG Student: 400/day  
    - PG Student: 500/day
    - Scholar: 800/day
    - Project Staff: 1000/day
    - Faculty: 1400/day
    - Others: 1600/day
    """
    rates = {
        'TA/Contingent': 100,
        'UG Student': 400,
        'PG Student': 500,
        'Scholar': 800,
        'Project Staff': 1000,
        'Faculty': 1400,
        'Others': 1600,
    }
    
    rate = rates.get(visitor_category, 1600)
    return rate * days


def calculate_mess_bill(visitors):
    """
    Calculate mess bill based on meal records.
    Extracted from views.visitorhostel.
    """
    total = 0
    for visitor in visitors:
        meals = MealRecord.objects.filter(visitor=visitor)
        for meal in meals:
            # Assuming meal cost logic from original code
            if meal.breakfast:
                total += 50
            if meal.lunch:
                total += 80
            if meal.dinner:
                total += 70
    return total


def get_available_rooms():
    """
    Get list of available rooms.
    Business logic extracted from views.request_booking.
    """
    all_rooms = RoomDetail.objects.all()
    booked_room_ids = BookingDetail.objects.filter(
        booking_status='Active'
    ).values_list('rooms', flat=True)
    
    return [room for room in all_rooms if room.id not in booked_room_ids]


@transaction.atomic
def create_booking(intender, caretaker, visitor_data, room_ids, intended_arrival, intended_departure):
    """
    Create a new booking with validation.
    Consolidates logic from views.request_booking to resolve Layer Violation.
    """
    # Validate dates
    if intended_arrival >= intended_departure:
        raise ValueError("Arrival date must be before departure date")
    
    # Check room availability
    available_rooms = get_available_rooms()
    available_room_ids = [r.id for r in available_rooms]
    
    for room_id in room_ids:
        if room_id not in available_room_ids:
            raise ValueError(f"Room {room_id} is not available")
    
    # Create booking
    booking = BookingDetail.objects.create(
        intender=intender,
        caretaker=caretaker,
        intended_arrival_date=intended_arrival,
        intended_departure_date=intended_departure,
        booking_status='Pending',
    )
    
    # Add rooms
    booking.rooms.set(room_ids)
    
    # Create visitor records
    for vdata in visitor_data:
        VisitorDetail.objects.create(
            booking=booking,
            name=vdata.get('name'),
            email=vdata.get('email'),
            phone=vdata.get('phone'),
            address=vdata.get('address'),
            visitor_category=vdata.get('category', 'Others'),
        )
    
    return booking


@transaction.atomic
def confirm_booking(booking, actual_arrival=None):
    """
    Confirm a pending booking.
    Business logic extracted from views.confirm_booking.
    """
    if booking.booking_status != 'Pending':
        raise ValueError("Only pending bookings can be confirmed")
    
    booking.booking_status = 'Active'
    if actual_arrival:
        booking.actual_arrival_date = actual_arrival
    else:
        booking.actual_arrival_date = timezone.now().date()
    booking.save()
    
    return booking


@transaction.atomic
def cancel_booking(booking, reason=None):
    """
    Cancel a booking.
    Business logic extracted from views.cancel_booking.
    """
    if booking.booking_status == 'Completed':
        raise ValueError("Cannot cancel completed booking")
    
    booking.booking_status = 'Cancelled'
    booking.cancellation_reason = reason
    booking.save()
    
    return booking


@transaction.atomic
def check_in(booking, actual_arrival=None):
    """
    Process check-in for a booking.
    """
    if booking.booking_status != 'Active':
        raise ValueError("Can only check in active bookings")
    
    booking.check_in = actual_arrival or timezone.now()
    booking.save()
    return booking


@transaction.atomic
def check_out(booking, actual_departure=None):
    """
    Process check-out for a booking.
    """
    if booking.booking_status != 'Active':
        raise ValueError("Can only check out active bookings")
    
    booking.check_out = actual_departure or timezone.now()
    booking.booking_status = 'Completed'
    booking.actual_departure_date = actual_departure or timezone.now().date()
    booking.save()
    
    return booking


def validate_booking_dates(arrival_date, departure_date):
    """
    Validate booking date range.
    Centralized validation to resolve Scattered Validation.
    """
    today = timezone.now().date()
    
    if arrival_date < today:
        raise ValueError("Arrival date cannot be in the past")
    
    if departure_date <= arrival_date:
        raise ValueError("Departure date must be after arrival date")
    
    # Max booking duration (e.g., 30 days)
    if (departure_date - arrival_date).days > 30:
        raise ValueError("Maximum booking duration is 30 days")
    
    return True


def get_user_role(user):
    """
    Determine user's role in the system.
    Centralizes repeated designation checks (CS41).
    """
    if hasattr(user, 'holds_designations'):
        designations = user.holds_designations.all()
        for d in designations:
            if d.designation.name == 'Intender':
                return 'Intender'
            elif d.designation.name == 'Caretaker':
                return 'Caretaker'
            elif d.designation.name == 'Dean':
                return 'Dean'
    
    return 'Guest'
