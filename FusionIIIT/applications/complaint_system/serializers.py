# serializers.py
# T-09: validate_rating centralised in FeedbackSerializer (CS-17, RD-08).
# T-13: Distinct ComplaintCreateSerializer (input) and StudentComplainSerializer (output) (CS-27).
# T-18: Root serializers.py is now the single canonical source; api/serializers.py duplicates removed.

from rest_framework import serializers
from .models import StudentComplain, Caretaker, Warden, Complaint_Admin, Workers


# ---------------------------------------------------------------------------
# Output serializer  (read-only, used for all GET responses)
# ---------------------------------------------------------------------------
class StudentComplainSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentComplain
        fields = '__all__'


# ---------------------------------------------------------------------------
# Input serializer  (write-only fields; used in POST / PUT complaint creation)
# T-13: Separates input from output to avoid raw field exposure on writes.
# ---------------------------------------------------------------------------
class ComplaintCreateSerializer(serializers.ModelSerializer):
    """Validates and creates a new StudentComplain. Side effects (notifications)
    remain in services.py — serializer has no side effects (CS-27)."""

    class Meta:
        model = StudentComplain
        fields = [
            'complainer', 'complaint_type', 'location', 'specific_location',
            'details', 'status', 'complaint_finish', 'upload_complaint',
        ]


# ---------------------------------------------------------------------------
# Caretaker / Warden / Admin serializers
# ---------------------------------------------------------------------------
class CaretakerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Caretaker
        fields = '__all__'


class WardenSerializer(serializers.ModelSerializer):
    class Meta:
        model = Warden
        fields = '__all__'


class Complaint_AdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = Complaint_Admin
        fields = '__all__'


class WorkersSerializer(serializers.ModelSerializer):
    class Meta:
        model = Workers
        fields = '__all__'


# ---------------------------------------------------------------------------
# Feedback serializer  (T-09 — validate_rating replaces 3 view-level try/except)
# ---------------------------------------------------------------------------
class FeedbackSerializer(serializers.Serializer):
    feedback = serializers.CharField()
    rating   = serializers.IntegerField()

    def validate_rating(self, value):
        if value < 1 or value > 5:
            raise serializers.ValidationError('Rating must be between 1 and 5.')
        return value


# ---------------------------------------------------------------------------
# Resolve-pending serializer
# ---------------------------------------------------------------------------
class ResolvePendingSerializer(serializers.Serializer):
    yesorno         = serializers.ChoiceField(choices=[('Yes', 'Yes'), ('No', 'No')])
    comment         = serializers.CharField(required=False, allow_blank=True)
    upload_resolved = serializers.ImageField(required=False, allow_null=True)
