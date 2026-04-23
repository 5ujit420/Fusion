from rest_framework import serializers
from .models import Inventory, InventoryBill
from .models import BookingDetail, Bill, VisitorCategory, RoomType, BookingStatus


class InventorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Inventory
        fields = '__all__'


class InventoryBillSerializer(serializers.ModelSerializer):
    class Meta:
        model = InventoryBill
        fields = '__all__'


class BillSerializer(serializers.ModelSerializer):
    """
    Serializer for Bill model.
    Refactored to remove business logic (get_total_bill) - now uses model property.
    Resolves: Overloaded Serializer, Business Logic in Serializer
    """
    total_bill = serializers.IntegerField(source='calculate_total_bill', read_only=True)

    class Meta:
        model = Bill
        fields = ['id', 'booking', 'meal_bill', 'room_bill', 'payment_status', 'bill_date', 'total_bill']


class BookingInputSerializer(serializers.Serializer):
    """
    Input serializer for booking creation.
    Centralizes validation logic.
    Resolves: Scattered Validation, Fat View
    """
    arrival_date = serializers.DateField()
    departure_date = serializers.DateField()
    purpose = serializers.CharField(required=False, default="Hi!")
    visitor_category = serializers.ChoiceField(choices=VisitorCategory.choices, default='C')
    room_ids = serializers.ListField(child=serializers.IntegerField(), required=False)
    
    # Visitor data as list of dicts
    visitors = serializers.ListField(
        child=serializers.DictField(),
        required=False
    )

    def validate(self, data):
        """
        Centralized date validation.
        Resolves: Scattered Validation, Repeated Field-Level Checks
        """
        from django.utils import timezone
        
        arrival = data.get('arrival_date')
        departure = data.get('departure_date')
        
        if arrival and departure:
            if arrival >= departure:
                raise serializers.ValidationError("Arrival date must be before departure date")
            
            if arrival < timezone.now().date():
                raise serializers.ValidationError("Arrival date cannot be in the past")
            
            if (departure - arrival).days > 30:
                raise serializers.ValidationError("Maximum booking duration is 30 days")
        
        return data


class BookingOutputSerializer(serializers.ModelSerializer):
    """
    Output serializer for booking responses.
    Uses facade methods from model to avoid message chains.
    Resolves: Message Chains, Deep Dot-Access Chains
    """
    intender_name = serializers.CharField(source='intender.username')
    room_numbers = serializers.SerializerMethodField()
    visitor_emails = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = BookingDetail
        fields = [
            'id', 'intender_name', 'booking_from', 'booking_to', 
            'status', 'status_display', 'purpose', 'visitor_category',
            'room_numbers', 'visitor_emails', 'booking_date'
        ]
        read_only_fields = fields

    def get_room_numbers(self, obj):
        """Use model's facade method"""
        return obj.get_room_numbers()

    def get_visitor_emails(self, obj):
        """Use model's facade method"""
        return obj.get_visitor_emails()


class BookingDetailSerializer(serializers.ModelSerializer):
    """
    Legacy serializer - kept for backward compatibility.
    Uses model property instead of inline calculation.
    """
    intender_name = serializers.CharField(source='intender.username')
    
    class Meta:
        model = BookingDetail
        fields = ['id', 'intender_name', 'booking_from', 'booking_to', 'status', 'purpose']
