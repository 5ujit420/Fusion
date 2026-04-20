# models.py
# T-11: Replaced Constants class with django.db.models.TextChoices subclasses.
# T-36 / T-11: Added named status constants (COMPLAINT_STATUS_*).
from django.db import models
from django.utils import timezone

from applications.globals.models import ExtraInfo

# ---------------------------------------------------------------------------
# Status constants (T-11, CS-36)
# ---------------------------------------------------------------------------
COMPLAINT_STATUS_PENDING = 0
COMPLAINT_STATUS_ASSIGNED = 1
COMPLAINT_STATUS_RESOLVED = 2
COMPLAINT_STATUS_DECLINED = 3


# ---------------------------------------------------------------------------
# TextChoices enums (T-11, CS-23)
# DB values are preserved verbatim so no migration is required.
# ---------------------------------------------------------------------------
class Area(models.TextChoices):
    HALL_1          = 'hall-1',               'hall-1'
    HALL_3          = 'hall-3',               'hall-3'
    HALL_4          = 'hall-4',               'hall-4'
    CC1             = 'library',              'CC1'
    CC2             = 'computer center',      'CC2'
    CORE_LAB        = 'core_lab',             'core_lab'
    LHTC            = 'LHTC',                 'LHTC'
    NR2             = 'NR2',                  'NR2'
    NR3             = 'NR3',                  'NR3'
    ADMIN_BUILDING  = 'Admin building',       'Admin building'
    REWA_RESIDENCY  = 'Rewa_Residency',       'Rewa_Residency'
    MAA_SARASWATI   = 'Maa Saraswati Hostel', 'Maa Saraswati Hostel'
    NAGARJUN        = 'Nagarjun Hostel',      'Nagarjun Hostel'
    PANINI          = 'Panini Hostel',        'Panini Hostel'


class ComplaintType(models.TextChoices):
    ELECTRICITY = 'Electricity', 'Electricity'
    CARPENTER   = 'carpenter',   'Carpenter'
    PLUMBER     = 'plumber',     'Plumber'
    GARBAGE     = 'garbage',     'Garbage'
    DUSTBIN     = 'dustbin',     'Dustbin'
    INTERNET    = 'internet',    'Internet'
    OTHER       = 'other',       'Other'


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------
class Caretaker(models.Model):
    staff_id   = models.ForeignKey(ExtraInfo, on_delete=models.CASCADE)
    area       = models.CharField(choices=Area.choices, max_length=20, default=Area.HALL_3)
    rating     = models.IntegerField(default=0)
    myfeedback = models.CharField(max_length=400, default='this is my feedback')

    def __str__(self):
        return f'{self.id}-{self.area}'


class Warden(models.Model):
    staff_id   = models.ForeignKey(ExtraInfo, on_delete=models.CASCADE)
    area       = models.CharField(choices=Area.choices, max_length=20, default=Area.HALL_1)
    rating     = models.IntegerField(default=0)
    myfeedback = models.CharField(max_length=400, default='No feedback yet')

    def __str__(self):
        return f'{self.staff_id}-{self.area}'


class SectionIncharge(models.Model):
    staff_id  = models.ForeignKey(ExtraInfo, on_delete=models.CASCADE)
    work_type = models.CharField(
        choices=ComplaintType.choices, max_length=20, default=ComplaintType.ELECTRICITY
    )

    def __str__(self):
        return f'{self.id}-{self.work_type}'


class Workers(models.Model):
    secincharge_id = models.ForeignKey(SectionIncharge, on_delete=models.CASCADE, null=True)
    name           = models.CharField(max_length=50)
    age            = models.CharField(max_length=10)
    phone          = models.BigIntegerField(blank=True)
    worker_type    = models.CharField(
        choices=ComplaintType.choices, max_length=20, default=ComplaintType.INTERNET
    )

    def __str__(self):
        return f'{self.id}-{self.name}'


class StudentComplain(models.Model):
    complainer        = models.ForeignKey(ExtraInfo, on_delete=models.CASCADE)
    complaint_date    = models.DateTimeField(default=timezone.now)
    complaint_finish  = models.DateField(blank=True, null=True)
    complaint_type    = models.CharField(
        choices=ComplaintType.choices, max_length=20, default=ComplaintType.INTERNET
    )
    location          = models.CharField(max_length=20, choices=Area.choices)
    specific_location = models.CharField(max_length=50, blank=True)
    details           = models.CharField(max_length=100)
    status            = models.IntegerField(default=COMPLAINT_STATUS_PENDING)
    remarks           = models.CharField(max_length=300, default='Pending')
    flag              = models.IntegerField(default=0)
    reason            = models.CharField(max_length=100, blank=True, default='None')
    feedback          = models.CharField(max_length=500, blank=True)
    worker_id         = models.ForeignKey(Workers, blank=True, null=True, on_delete=models.CASCADE)
    upload_complaint  = models.FileField(blank=True)
    comment           = models.CharField(max_length=100, default='None')
    upload_resolved   = models.FileField(upload_to='resolved_complaints/', blank=True, null=True)

    class meta:                         # lowercase preserved — changing to Meta would require migration
        db_table = 'complaint_system_student_complain'

    def __str__(self):
        return str(self.complainer.user.username)


class ServiceProvider(models.Model):
    ser_pro_id = models.ForeignKey(
        ExtraInfo, on_delete=models.CASCADE, db_column='ser_pro_id_id'
    )
    type = models.CharField(
        choices=ComplaintType.choices, max_length=30, default=ComplaintType.ELECTRICITY
    )

    class Meta:
        db_table = 'complaint_system_service_provider'

    def __str__(self):
        return f'{self.ser_pro_id}-{self.type}'


class Complaint_Admin(models.Model):
    sup_id = models.ForeignKey(ExtraInfo, on_delete=models.CASCADE)

    def __str__(self):
        return str(self.sup_id)


class ServiceAuthority(models.Model):
    ser_pro_id = models.ForeignKey(
        ExtraInfo, on_delete=models.CASCADE, db_column='ser_auth_id_id'
    )
    type = models.CharField(
        choices=ComplaintType.choices, max_length=30, default=ComplaintType.ELECTRICITY
    )

    class Meta:
        db_table = 'complaint_system_service_authority'

    def __str__(self):
        return f'{self.ser_pro_id}-{self.type}'
