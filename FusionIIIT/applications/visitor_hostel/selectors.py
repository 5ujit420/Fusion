"""
Selectors for visitor_hostel app.
Encapsulates all read-side database queries.
Resolves: N+1 Query Problem, Query Logic Duplication, Fat View (ORM Logic)
"""
from django.utils import timezone
from datetime import timedelta
from .models import BookingDetail, RoomDetail, VisitorDetail, MealRecord, Bill


def get_bookings_by_status(status, user=None, user_designation=None):
    """
    Generic selector for bookings filtered by status.
    Handles role-based filtering logic.
    """
    queryset = BookingDetail.objects.filter(booking_status=status)
    
    # Role-based filtering logic extracted from views
    if user_designation == 'Intender':
        queryset = queryset.filter(intender=user)
    elif user_designation == 'Caretaker':
        # Caretakers see all, or specific logic if required
        pass
    elif user_designation == 'Dean':
        queryset = queryset.filter(caretaker=user)
    
    return queryset.select_related('intender', 'caretaker').prefetch_related('rooms', 'visitor')


def get_pending_bookings(user=None, user_designation=None):
    """Get pending bookings with optimized joins."""
    return get_bookings_by_status('Pending', user, user_designation)


def get_active_bookings(user=None, user_designation=None):
    """Get active bookings with optimized joins."""
    return get_bookings_by_status('Active', user, user_designation)


def get_dashboard_context_data(user, user_designation):
    """
    Consolidated selector for dashboard data.
    Resolves N+1 by prefetching related objects upfront.
    """
    today = timezone.now().date()
    
    # Pending
    pending_qs = BookingDetail.objects.filter(booking_status='Pending')
    if user_designation == 'Intender':
        pending_qs = pending_qs.filter(intender=user)
    elif user_designation == 'Caretaker':
        pass 
    elif user_designation == 'Dean':
        pending_qs = pending_qs.filter(caretaker=user)
        
    pending_bookings = pending_qs.select_related('intender', 'caretaker').prefetch_related('rooms')

    # Active
    active_qs = BookingDetail.objects.filter(booking_status='Active')
    if user_designation == 'Intender':
        active_qs = active_qs.filter(intender=user)
    elif user_designation == 'Dean':
        active_qs = active_qs.filter(caretaker=user)
        
    # Critical Fix: Prefetch rooms and visitors to avoid N+1 in template loops
    active_bookings = active_qs.select_related('intender', 'caretaker').prefetch_related('rooms', 'visitor')

    # Completed (recent)
    completed_qs = BookingDetail.objects.filter(
        booking_status='Completed',
        actual_departure_date__gte=today - timedelta(days=30)
    )
    if user_designation == 'Intender':
        completed_qs = completed_qs.filter(intender=user)
    elif user_designation == 'Dean':
        completed_qs = completed_qs.filter(caretaker=user)
        
    completed_bookings = completed_qs.select_related('intender', 'caretaker').prefetch_related('rooms')

    return {
        'pending_bookings': pending_bookings,
        'active_bookings': active_bookings,
        'completed_bookings': completed_bookings,
    }


def get_available_rooms_map():
    """
    Returns a dict of room_number -> room_id for available rooms.
    Logic extracted from views.visitorhostel.
    """
    all_rooms = RoomDetail.objects.all()
    booked_room_ids = BookingDetail.objects.filter(
        booking_status='Active'
    ).values_list('rooms', flat=True)
    
    available_rooms = {}
    for room in all_rooms:
        if room.id not in booked_room_ids:
            available_rooms[room.room_number] = room.id
            
    return available_rooms


def get_visitor_meal_records(booking_id):
    """Prefetch meal records for a booking to avoid N+1."""
    booking = BookingDetail.objects.prefetch_related('visitor__mealrecord_set').get(id=booking_id)
    return booking.visitor.mealrecord_set.all()


def update_expired_bookings():
    """
    Utility to mark bookings as completed if departure date has passed.
    Consolidates duplicate logic from multiple views.
    """
    today = timezone.now().date()
    expired = BookingDetail.objects.filter(
        booking_status='Active',
        intended_departure_date__lt=today
    )
    return expired.update(booking_status='Completed')
