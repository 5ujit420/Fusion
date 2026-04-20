from rest_framework import serializers

from .models import Bill, BookingDetail, Inventory, InventoryBill


class InventorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Inventory
        fields = "__all__"


class InventoryBillSerializer(serializers.ModelSerializer):
    class Meta:
        model = InventoryBill
        fields = "__all__"


class BillSerializer(serializers.ModelSerializer):
    total_bill = serializers.SerializerMethodField()

    class Meta:
        model = Bill
        fields = ["id", "booking", "meal_bill", "room_bill", "payment_status", "bill_date", "total_bill"]

    def get_total_bill(self, obj):
        return obj.meal_bill + obj.room_bill


class BookingDetailSerializer(serializers.ModelSerializer):
    intender_name = serializers.CharField(source="intender.username")
    bill = BillSerializer(required=False)

    class Meta:
        model = BookingDetail
        fields = ["intender_name", "booking_from", "booking_to", "bill"]


class BookingRequestInputSerializer(serializers.Serializer):
    booking_id = serializers.CharField(required=False, allow_blank=True)
    category = serializers.CharField()
    number_of_people = serializers.IntegerField(source="person_count")
    purpose_of_visit = serializers.CharField(source="purpose_of_visit")
    booking_from = serializers.DateField()
    booking_to = serializers.DateField()
    booking_from_time = serializers.CharField(required=False, allow_blank=True)
    booking_to_time = serializers.CharField(required=False, allow_blank=True)
    remarks_during_booking_request = serializers.CharField(required=False, allow_blank=True)
    bill_settlement = serializers.CharField(source="bill_to_be_settled_by")
    number_of_rooms = serializers.IntegerField()
    visitor_name = serializers.CharField()
    visitor_email = serializers.CharField(required=False, allow_blank=True)
    visitor_phone = serializers.CharField()
    visitor_organization = serializers.CharField(required=False, allow_blank=True)
    visitor_address = serializers.CharField(required=False, allow_blank=True)
    nationality = serializers.CharField(required=False, allow_blank=True)


class BookingForwardSerializer(serializers.Serializer):
    booking_id = serializers.IntegerField()
    modified_category = serializers.CharField()
    rooms = serializers.ListField(child=serializers.CharField(), required=False)
    remarks = serializers.CharField(required=False, allow_blank=True)
    action = serializers.CharField(required=False, allow_blank=True)


class BookingUpdateSerializer(serializers.Serializer):
    booking_id = serializers.IntegerField()
    modified_category = serializers.CharField()
    rooms = serializers.ListField(child=serializers.CharField(), required=False)
    remarks = serializers.CharField(required=False, allow_blank=True)
    visitorOrganization = serializers.CharField(source="visitor_organization")
    visitorPhone = serializers.CharField(source="visitor_phone")
    visitorEmail = serializers.CharField(source="visitor_email", required=False, allow_blank=True)
    visitorName = serializers.CharField(source="visitor_name")
    visitorAddress = serializers.CharField(source="visitor_address", required=False, allow_blank=True)
    billToBeSettledBy = serializers.CharField(source="bill_to_be_settled_by", required=False, allow_blank=True)
    purpose = serializers.CharField(required=False, allow_blank=True)
    numberOfRooms = serializers.IntegerField(source="number_of_rooms")
    personCount = serializers.IntegerField(source="person_count")


class RoomAvailabilitySerializer(serializers.Serializer):
    start_date = serializers.DateField()
    end_date = serializers.DateField()


class InventoryMutationSerializer(serializers.Serializer):
    item_name = serializers.CharField()
    bill_number = serializers.CharField()
    quantity = serializers.IntegerField()
    cost = serializers.IntegerField()
    consumable = serializers.BooleanField()


class InventoryCheckoutItemSerializer(serializers.Serializer):
    name = serializers.CharField()
    quantity = serializers.IntegerField(required=False, default=0)
    cost = serializers.IntegerField(required=False, default=0)


class InventoryCheckoutSerializer(serializers.Serializer):
    booking_id = serializers.IntegerField()
    inventory_items = InventoryCheckoutItemSerializer(many=True, required=False)
    meal_bill = serializers.IntegerField(required=False, default=0)
    room_bill = serializers.IntegerField(required=False, default=0)
    check_out_time = serializers.TimeField(input_formats=["%H:%M", "%H:%M:%S"], required=False)


class CheckInSerializer(serializers.Serializer):
    booking_id = serializers.IntegerField()
    name = serializers.CharField(source="visitor_name")
    phone = serializers.CharField(source="visitor_phone")
    email = serializers.CharField(source="visitor_email", required=False, allow_blank=True)
    address = serializers.CharField(source="visitor_address", required=False, allow_blank=True)
    check_in_time = serializers.TimeField(input_formats=["%H:%M", "%H:%M:%S"], required=False)


class CheckOutSerializer(serializers.Serializer):
    booking_id = serializers.IntegerField()
    meal_bill = serializers.IntegerField(required=False, default=0)
    room_bill = serializers.IntegerField(required=False, default=0)
    check_out_time = serializers.TimeField(input_formats=["%H:%M", "%H:%M:%S"], required=False)
