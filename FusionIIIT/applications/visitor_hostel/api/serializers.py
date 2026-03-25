# api/serializers.py
# Input/output validation for the visitor_hostel module.
# Fixes: V-09, V-10 — added missing input serializers.

from rest_framework import serializers
from ..models import (
    BookingDetail, VisitorDetail, RoomDetail, MealRecord,
    Bill, Inventory, InventoryBill,
    RoomStatus,
)


# ---------------------------------------------------------------------------
# Output serializers
# ---------------------------------------------------------------------------

class VisitorDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = VisitorDetail
        fields = ['id', 'visitor_name', 'visitor_phone', 'visitor_email',
                  'visitor_organization', 'visitor_address', 'nationality']


class RoomDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = RoomDetail
        fields = ['id', 'room_number', 'room_type', 'room_floor', 'room_status']


class BookingDetailSerializer(serializers.ModelSerializer):
    intender_username = serializers.CharField(source='intender.username', read_only=True)
    caretaker_username = serializers.CharField(source='caretaker.username', read_only=True)

    class Meta:
        model = BookingDetail
        fields = [
            'id', 'intender', 'intender_username', 'caretaker', 'caretaker_username',
            'visitor_category', 'modified_visitor_category', 'person_count', 'purpose',
            'booking_from', 'booking_to', 'arrival_time', 'departure_time',
            'status', 'remark', 'number_of_rooms', 'number_of_rooms_alloted',
            'booking_date', 'bill_to_be_settled_by', 'check_in', 'check_out',
        ]


class MealRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = MealRecord
        fields = ['id', 'booking', 'visitor', 'meal_date', 'morning_tea',
                  'eve_tea', 'breakfast', 'lunch', 'dinner', 'persons']


class BillSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bill
        fields = ['id', 'booking', 'caretaker', 'meal_bill', 'room_bill',
                  'payment_status', 'bill_date']


class InventorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Inventory
        fields = ['id', 'item_name', 'quantity', 'consumable', 'opening_stock',
                  'addition_stock', 'total_stock', 'serviceable', 'non_serviceable',
                  'inuse', 'total_usable', 'remark']


class InventoryBillSerializer(serializers.ModelSerializer):
    class Meta:
        model = InventoryBill
        fields = ['id', 'item_name', 'bill_number', 'cost']


# ---------------------------------------------------------------------------
# Input validation serializers
# ---------------------------------------------------------------------------

class BookingRequestInputSerializer(serializers.Serializer):
    intender = serializers.IntegerField(required=True)
    category = serializers.ChoiceField(choices=['A', 'B', 'C', 'D'], required=True)
    number_of_people = serializers.IntegerField(required=True, min_value=1)
    purpose_of_visit = serializers.CharField(required=True)
    booking_from = serializers.DateField(required=True)
    booking_to = serializers.DateField(required=True)
    booking_from_time = serializers.CharField(required=False, allow_blank=True, default='')
    booking_to_time = serializers.CharField(required=False, allow_blank=True, default='')
    number_of_rooms = serializers.IntegerField(required=True, min_value=1)
    bill_settlement = serializers.ChoiceField(
        choices=['Intender', 'Visitor', 'ProjectNo', 'Institute'], required=True
    )
    # Visitor details
    name = serializers.CharField(required=True, max_length=40)
    phone = serializers.CharField(required=True, max_length=15)
    email = serializers.CharField(required=False, allow_blank=True, max_length=40)
    address = serializers.CharField(required=False, allow_blank=True)
    organization = serializers.CharField(required=False, allow_blank=True, max_length=100)
    nationality = serializers.CharField(required=False, allow_blank=True, max_length=20)

    def validate(self, data):
        if data['booking_from'] > data['booking_to']:
            raise serializers.ValidationError("booking_from must be before booking_to")
        return data


class UpdateBookingInputSerializer(serializers.Serializer):
    booking_id = serializers.IntegerField(required=True)
    category = serializers.ChoiceField(choices=['A', 'B', 'C', 'D'], required=False)
    number_of_people = serializers.IntegerField(required=False, min_value=1)
    purpose_of_visit = serializers.CharField(required=False)
    booking_from = serializers.DateField(required=False)
    booking_to = serializers.DateField(required=False)
    number_of_rooms = serializers.IntegerField(required=False, min_value=1)


class ConfirmBookingInputSerializer(serializers.Serializer):
    booking_id = serializers.IntegerField(required=True)
    category = serializers.ChoiceField(choices=['A', 'B', 'C', 'D'], required=True)
    rooms = serializers.ListField(child=serializers.CharField(), required=True)


class CancelBookingInputSerializer(serializers.Serializer):
    booking_id = serializers.IntegerField(required=True)
    remark = serializers.CharField(required=False, allow_blank=True, default='')
    charges = serializers.IntegerField(required=False, default=0)


class CancelBookingRequestInputSerializer(serializers.Serializer):
    """V-09: New — was missing, CancelBookingRequestView used raw request.data.get()."""
    booking_id = serializers.IntegerField(required=True)
    remark = serializers.CharField(required=False, allow_blank=True, default='')


class RejectBookingInputSerializer(serializers.Serializer):
    booking_id = serializers.IntegerField(required=True)
    remark = serializers.CharField(required=False, allow_blank=True, default='')


class CheckInInputSerializer(serializers.Serializer):
    booking_id = serializers.IntegerField(required=True)
    name = serializers.CharField(required=True, max_length=40)
    phone = serializers.CharField(required=True, max_length=15)
    email = serializers.CharField(required=False, allow_blank=True, max_length=40)
    address = serializers.CharField(required=False, allow_blank=True)


class CheckOutInputSerializer(serializers.Serializer):
    id = serializers.IntegerField(required=True)
    mess_bill = serializers.IntegerField(required=True, min_value=0)
    room_bill = serializers.IntegerField(required=True, min_value=0)


class RecordMealInputSerializer(serializers.Serializer):
    pk = serializers.IntegerField(required=True)
    booking = serializers.IntegerField(required=True)
    m_tea = serializers.IntegerField(required=True, min_value=0)
    breakfast = serializers.IntegerField(required=True, min_value=0)
    lunch = serializers.IntegerField(required=True, min_value=0)
    eve_tea = serializers.IntegerField(required=True, min_value=0)
    dinner = serializers.IntegerField(required=True, min_value=0)


class AddInventoryInputSerializer(serializers.Serializer):
    item_name = serializers.CharField(required=True, max_length=20)
    bill_number = serializers.CharField(required=True, max_length=40)
    quantity = serializers.IntegerField(required=True, min_value=0)
    cost = serializers.IntegerField(required=True, min_value=0)
    consumable = serializers.CharField(required=False, default='false')


class UpdateInventoryInputSerializer(serializers.Serializer):
    id = serializers.IntegerField(required=True)
    quantity = serializers.IntegerField(required=True)


class ForwardBookingInputSerializer(serializers.Serializer):
    id = serializers.IntegerField(required=True)
    previous_category = serializers.ChoiceField(choices=['A', 'B', 'C', 'D'], required=False)
    modified_category = serializers.ChoiceField(choices=['A', 'B', 'C', 'D'], required=True)
    rooms = serializers.ListField(child=serializers.CharField(), required=True)
    remark = serializers.CharField(required=False, allow_blank=True, default='')


class EditRoomStatusInputSerializer(serializers.Serializer):
    """V-10: New — was missing, EditRoomStatusView used raw request.data.get()."""
    room_number = serializers.CharField(required=True, max_length=4)
    room_status = serializers.ChoiceField(
        choices=[s.value for s in RoomStatus], required=True
    )


class RoomAvailabilityInputSerializer(serializers.Serializer):
    start_date = serializers.DateField(required=True)
    end_date = serializers.DateField(required=True)

    def validate(self, data):
        if data['start_date'] > data['end_date']:
            raise serializers.ValidationError("start_date must be before or equal to end_date")
        return data


class BillDateRangeInputSerializer(serializers.Serializer):
    start_date = serializers.DateField(required=True)
    end_date = serializers.DateField(required=True)

    def validate(self, data):
        if data['start_date'] > data['end_date']:
            raise serializers.ValidationError("start_date must be before or equal to end_date")
        return data
