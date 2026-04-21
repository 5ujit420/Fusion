import datetime

from django import forms

from applications.visitor_hostel.models import VISITOR_CATEGORY


# T-26: Removed unused ModelForm import, deleted Room_booking class,
#        deleted commented-out booking_request and InventoryForm.

CHOICES = tuple(VISITOR_CATEGORY)


class RoomAvailability(forms.Form):
    date_from = forms.DateField(initial=datetime.date.today)
    date_to = forms.DateField(initial=datetime.date.today)


class InventoryForm(forms.Form):
    """T-28b: Restored InventoryForm for pre-service validation in add_to_inventory view."""
    item_name = forms.CharField(max_length=20)
    quantity = forms.IntegerField(min_value=1)
    cost = forms.IntegerField(min_value=0)
    bill_number = forms.CharField(max_length=40)
    consumable = forms.BooleanField(required=False, initial=False)
