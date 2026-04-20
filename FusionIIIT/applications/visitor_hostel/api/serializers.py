from applications.visitor_hostel.serializers import (
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


class InventoryItemSerializer(InventorySerializer):
    class Meta(InventorySerializer.Meta):
        fields = ["item_name", "quantity"]
