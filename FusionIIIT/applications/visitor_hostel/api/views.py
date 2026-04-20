from rest_framework import status
from rest_framework.authentication import TokenAuthentication
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from applications.visitor_hostel.selectors import get_inventory_queryset
from applications.visitor_hostel.services import add_inventory_item_and_bill

from .serializers import InventoryMutationSerializer, InventorySerializer


class AddToInventory(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = InventoryMutationSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        add_inventory_item_and_bill(serializer.validated_data)
        return Response({"message": "Item added successfully!"}, status=status.HTTP_201_CREATED)


class InventoryListView(ListAPIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = InventorySerializer

    def get_queryset(self):
        return get_inventory_queryset()
