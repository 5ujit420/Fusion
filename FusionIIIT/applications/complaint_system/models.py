from django.db import models
from django.utils import timezone

from applications.globals.models import ExtraInfo


class AreaChoices(models.TextChoices):
    HALL_1 = 'hall-1', 'hall-1'
    HALL_3 = 'hall-3', 'hall-3'
    HALL_4 = 'hall-4', 'hall-4'
    LIBRARY = 'library', 'CC1'
    COMPUTER_CENTER = 'computer center', 'CC2'
    CORE_LAB = 'core_lab', 'core_lab'
    LHTC = 'LHTC', 'LHTC'
    NR2 = 'NR2', 'NR2'
    NR3 = 'NR3', 'NR3'
    ADMIN_BUILDING = 'Admin building', 'Admin building'
    REWA_RESIDENCY = 'Rewa_Residency', 'Rewa_Residency'
    MAA_SARASWATI_HOSTEL = 'Maa Saraswati Hostel', 'Maa Saraswati Hostel'
    NAGARJUN_HOSTEL = 'Nagarjun Hostel', 'Nagarjun Hostel'
    PANINI_HOSTEL = 'Panini Hostel', 'Panini Hostel'


class ComplaintTypeChoices(models.TextChoices):
    ELECTRICITY = 'Electricity', 'Electricity'
    CARPENTER = 'carpenter', 'carpenter'
    PLUMBER = 'plumber', 'plumber'
    GARBAGE = 'garbage', 'garbage'
    DUSTBIN = 'dustbin', 'dustbin'
    INTERNET = 'internet', 'internet'
    OTHER = 'other', 'other'


class ComplaintStatus(models.IntegerChoices):
    PENDING = 0, 'Pending'
    FORWARDED = 1, 'Forwarded'
    RESOLVED = 2, 'Resolved'
    DECLINED = 3, 'Declined'


# Backward compatibility alias for existing code referencing Constants
class Constants:
    AREA = AreaChoices.choices
    COMPLAINT_TYPE = ComplaintTypeChoices.choices


class Caretaker(models.Model):
    staff_id = models.ForeignKey(ExtraInfo, on_delete=models.CASCADE)
    area = models.CharField(choices=AreaChoices.choices, max_length=20, default='hall-3')
    rating = models.IntegerField(default=0)
    myfeedback = models.CharField(max_length=400, default='this is my feedback')

    def __str__(self):
        return str(self.id) + '-' + str(self.area)


class Warden(models.Model):
    staff_id = models.ForeignKey(ExtraInfo, on_delete=models.CASCADE)
    area = models.CharField(choices=AreaChoices.choices, max_length=20, default='hall-1')
    rating = models.IntegerField(default=0)
    myfeedback = models.CharField(max_length=400, default="No feedback yet")

    def __str__(self):
        return str(self.staff_id) + '-' + str(self.area)


class SectionIncharge(models.Model):
    staff_id = models.ForeignKey(ExtraInfo, on_delete=models.CASCADE)
    work_type = models.CharField(
        choices=ComplaintTypeChoices.choices, max_length=20, default='Electricity'
    )

    def __str__(self):
        return str(self.id) + '-' + self.work_type


class Workers(models.Model):
    secincharge_id = models.ForeignKey(SectionIncharge, on_delete=models.CASCADE, null=True)
    name = models.CharField(max_length=50)
    age = models.CharField(max_length=10)
    phone = models.BigIntegerField(blank=True)
    worker_type = models.CharField(
        choices=ComplaintTypeChoices.choices, max_length=20, default='internet'
    )

    def __str__(self):
        return str(self.id) + '-' + self.name


class StudentComplain(models.Model):
    complainer = models.ForeignKey(ExtraInfo, on_delete=models.CASCADE)
    complaint_date = models.DateTimeField(default=timezone.now)
    complaint_finish = models.DateField(blank=True, null=True)
    complaint_type = models.CharField(
        choices=ComplaintTypeChoices.choices, max_length=20, default='internet'
    )
    location = models.CharField(max_length=20, choices=AreaChoices.choices)
    specific_location = models.CharField(max_length=50, blank=True)
    details = models.CharField(max_length=100)
    status = models.IntegerField(default=ComplaintStatus.PENDING)
    remarks = models.CharField(max_length=300, default="Pending")
    flag = models.IntegerField(default=0)
    reason = models.CharField(max_length=100, blank=True, default="None")
    feedback = models.CharField(max_length=500, blank=True)
    worker_id = models.ForeignKey(Workers, blank=True, null=True, on_delete=models.CASCADE)
    upload_complaint = models.FileField(blank=True)
    comment = models.CharField(max_length=100, default="None")
    upload_resolved = models.FileField(upload_to='resolved_complaints/', blank=True, null=True)

    class Meta:
        db_table = "complaint_system_student_complain"

    def __str__(self):
        return str(self.complainer.user.username)


class ServiceProvider(models.Model):
    ser_pro_id = models.ForeignKey(
        ExtraInfo,
        on_delete=models.CASCADE,
        db_column="ser_pro_id_id"
    )
    type = models.CharField(
        choices=ComplaintTypeChoices.choices, max_length=30, default='Electricity'
    )

    class Meta:
        db_table = "complaint_system_service_provider"

    def __str__(self):
        return str(self.ser_pro_id) + '-' + str(self.type)


class Complaint_Admin(models.Model):
    sup_id = models.ForeignKey(ExtraInfo, on_delete=models.CASCADE)

    def __str__(self):
        return str(self.sup_id)


class ServiceAuthority(models.Model):
    ser_pro_id = models.ForeignKey(
        ExtraInfo,
        on_delete=models.CASCADE,
        db_column="ser_auth_id_id"
    )
    type = models.CharField(
        choices=ComplaintTypeChoices.choices, max_length=30, default='Electricity'
    )

    class Meta:
        db_table = "complaint_system_service_authority"

    def __str__(self):
        return str(self.ser_pro_id) + '-' + str(self.type)
