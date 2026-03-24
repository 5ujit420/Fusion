from django.db import models
from django.utils import timezone
from applications.academic_information.models import Student


# ---------------------------------------------------------------------------
# Constants / TextChoices  (S43 — replaces old tuple-based Constants class)
# ---------------------------------------------------------------------------

class PlacementType(models.TextChoices):
    PLACEMENT = "PLACEMENT", "Placement"
    PBI = "PBI", "PBI"
    HIGHER_STUDIES = "HIGHER STUDIES", "Higher Studies"


class PlacedType(models.TextChoices):
    PLACED = "PLACED", "Placed"
    NOT_PLACED = "NOT PLACED", "Not Placed"


class DebarStatus(models.TextChoices):
    DEBAR = "DEBAR", "Debar"
    NOT_DEBAR = "NOT DEBAR", "Not Debar"


class InvitationStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    ACCEPTED = "ACCEPTED", "Accepted"
    REJECTED = "REJECTED", "Rejected"
    IGNORE = "IGNORE", "Ignore"


# Role name constants used for HoldsDesignation lookups (S43)
ROLE_PLACEMENT_CHAIRMAN = "placement chairman"
ROLE_PLACEMENT_OFFICER = "placement officer"
ROLE_STUDENT = "student"

# Department name constants (S43)
DEPT_CSE = "CSE"
DEPT_ECE = "ECE"
DEPT_ME = "ME"


# Keep legacy Constants class for backward compatibility with templates/forms
class Constants:
    # placement type for the record
    PLACEMENT_TYPE = (
        ('PLACEMENT', 'Placement'),
        ('PBI', 'PBI'),
        ('HIGHER STUDIES', 'Higher Studies'),
    )

    PLACED_TYPE = (
        ('PLACED', 'Placed'),
        ('NOT PLACED', 'Not Placed'),
    )

    DEBAR_TYPE = (
        ('DEBAR', 'Debar'),
        ('NOT DEBAR', 'Not Debar'),
    )

    INVITATION_TYPE = (
        ('PENDING', 'Pending'),
        ('ACCEPTED', 'Accepted'),
        ('REJECTED', 'Rejected'),
    )

    ACHIEVEMENT_TYPE = (
        ('MEDALS', 'Medals'),
        ('TROPHIES', 'Trophies'),
        ('CERTIFICATES', 'Certificates'),
        ('SCHOLARSHIPS', 'Scholarships'),
        ('PRIZES', 'Prizes'),
        ('OTHERS', 'Others'),
    )

    PROJECT_STATUS = (
        ('ONGOING', 'Ongoing'),
        ('COMPLETED', 'Completed'),
    )

    EXPERIENCE_TYPE = (
        ('JOB', 'Job'),
        ('INTERNSHIP', 'Internship'),
    )


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class Skill(models.Model):
    skill = models.CharField(max_length=30, unique=True)

    def __str__(self):
        return '{}'.format(self.skill)


class Has(models.Model):
    skill_id = models.ForeignKey(Skill, on_delete=models.CASCADE)
    unique_id = models.ForeignKey(Student, on_delete=models.CASCADE)
    skill_rating = models.IntegerField(default=0)

    def __str__(self):
        return '{} - {}'.format(self.unique_id.id, self.skill_id.skill)


class Education(models.Model):
    unique_id = models.ForeignKey(Student, on_delete=models.CASCADE)
    institute = models.CharField(max_length=200)
    degree = models.CharField(max_length=40)
    grade = models.CharField(max_length=10)
    stream = models.CharField(max_length=100)
    sdate = models.DateField()
    edate = models.DateField()

    # S42: Removed broken clean() method that used self.cleaned_data
    # (a Django Form API — not valid in a Model context).
    # Date validation belongs in forms/serializers layer.

    def __str__(self):
        return '{} - {}'.format(self.unique_id.id, self.degree)


class Experience(models.Model):
    unique_id = models.ForeignKey(Student, on_delete=models.CASCADE)
    title = models.CharField(max_length=100)
    status = models.CharField(max_length=100, choices=Constants.EXPERIENCE_TYPE)
    company = models.CharField(max_length=200)
    location = models.CharField(max_length=200)
    description = models.TextField(max_length=500, null=True, blank=True)
    sdate = models.DateField()
    edate = models.DateField()

    def __str__(self):
        return '{} - {}'.format(self.unique_id.id, self.title)


class Achievement(models.Model):
    unique_id = models.ForeignKey(Student, on_delete=models.CASCADE)
    achievement = models.CharField(max_length=200)
    achievement_type = models.CharField(max_length=200, choices=Constants.ACHIEVEMENT_TYPE)
    description = models.TextField(max_length=500, null=True, blank=True)
    issuer = models.CharField(max_length=200)
    date_earned = models.DateField()

    def __str__(self):
        return '{} - {}'.format(self.unique_id.id, self.achievement)


class Publication(models.Model):
    unique_id = models.ForeignKey(Student, on_delete=models.CASCADE)
    publication_title = models.CharField(max_length=200)
    description = models.TextField(max_length=500, null=True, blank=True)
    publisher = models.CharField(max_length=250)
    publication_date = models.DateField()

    def __str__(self):
        return '{} - {}'.format(self.unique_id.id, self.publication_title)


class Patent(models.Model):
    unique_id = models.ForeignKey(Student, on_delete=models.CASCADE)
    patent_name = models.CharField(max_length=200)
    description = models.TextField(max_length=500, null=True, blank=True)
    patent_office = models.CharField(max_length=250)
    patent_date = models.DateField()

    def __str__(self):
        return '{} - {}'.format(self.unique_id.id, self.patent_name)


class Course(models.Model):
    unique_id = models.ForeignKey(Student, on_delete=models.CASCADE)
    course_name = models.CharField(max_length=200)
    description = models.TextField(max_length=500, null=True, blank=True)
    license_no = models.CharField(max_length=250, null=True, blank=True)
    sdate = models.DateField()
    edate = models.DateField()

    def __str__(self):
        return '{} - {}'.format(self.unique_id.id, self.course_name)


class Project(models.Model):
    unique_id = models.ForeignKey(Student, on_delete=models.CASCADE)
    project_name = models.CharField(max_length=200)
    project_status = models.CharField(max_length=200, choices=Constants.PROJECT_STATUS)
    summary = models.TextField(max_length=500, null=True, blank=True)
    project_link = models.CharField(max_length=200, null=True, blank=True)
    sdate = models.DateField()
    edate = models.DateField()

    def __str__(self):
        return '{} - {}'.format(self.unique_id.id, self.project_name)


class Extracurricular(models.Model):
    unique_id = models.ForeignKey(Student, on_delete=models.CASCADE)
    event_name = models.CharField(max_length=200, default='')
    body = models.CharField(max_length=200, default='')
    description = models.TextField(max_length=500, null=True, blank=True)
    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)

    def __str__(self):
        return '{} - {}'.format(self.unique_id.id, self.event_name)


class Conference(models.Model):
    unique_id = models.ForeignKey(Student, on_delete=models.CASCADE)
    conference_name = models.CharField(max_length=200, default='')
    description = models.TextField(max_length=500, null=True, blank=True)
    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)

    def __str__(self):
        return '{} - {}'.format(self.unique_id.id, self.conference_name)


class CompanyDetails(models.Model):
    company_name = models.CharField(max_length=100, default='')
    description = models.TextField(max_length=500, null=True, blank=True)
    address = models.TextField(max_length=500, null=True, blank=True)
    contact = models.CharField(max_length=20, null=True, blank=True)

    def __str__(self):
        return '{}'.format(self.company_name)


class NotifyStudent(models.Model):
    placement_type = models.CharField(max_length=20, choices=Constants.PLACEMENT_TYPE, default='PLACEMENT')
    company_name = models.CharField(max_length=100, default='')
    description = models.TextField(max_length=1000, null=True, blank=True)
    ctc = models.DecimalField(decimal_places=2, max_digits=5, default=0)
    timestamp = models.DateTimeField(auto_now_add=True, null=True)

    def __str__(self):
        return '{} - {}'.format(self.company_name, self.placement_type)


class PlacementStatus(models.Model):
    notify_id = models.ForeignKey(NotifyStudent, on_delete=models.CASCADE)
    unique_id = models.ForeignKey(Student, on_delete=models.CASCADE)
    invitation = models.CharField(max_length=20, choices=Constants.INVITATION_TYPE, default='PENDING')
    timestamp = models.DateTimeField(default=timezone.now)
    no_of_days = models.IntegerField(default=10)

    def __str__(self):
        return '{} - {}'.format(self.unique_id.id, self.notify_id)


class StudentPlacement(models.Model):
    unique_id = models.OneToOneField(Student, on_delete=models.CASCADE, related_name='studentplacement')
    debar = models.CharField(max_length=20, choices=Constants.DEBAR_TYPE, default='NOT DEBAR')
    placed_type = models.CharField(max_length=20, choices=Constants.PLACED_TYPE, default='NOT PLACED')
    placement_date = models.DateField(null=True, blank=True)

    def __str__(self):
        return '{} placement'.format(self.unique_id.id)


class StudentRecord(models.Model):
    unique_id = models.ForeignKey(Student, on_delete=models.CASCADE)
    record_id = models.ForeignKey('PlacementRecord', on_delete=models.CASCADE)

    def __str__(self):
        return '{}'.format(self.unique_id.id.id)


class PlacementRecord(models.Model):
    placement_type = models.CharField(max_length=20, choices=Constants.PLACEMENT_TYPE, default='PLACEMENT')
    name = models.CharField(max_length=100, default='')
    ctc = models.DecimalField(decimal_places=2, max_digits=5, default=0)
    year = models.IntegerField(default=0)
    test_type = models.CharField(max_length=100, null=True, blank=True)
    test_score = models.IntegerField(null=True, blank=True, default=0)

    def __str__(self):
        return '{} - {}'.format(self.name, self.placement_type)


class Role(models.Model):
    role = models.CharField(max_length=100, default='')

    def __str__(self):
        return '{}'.format(self.role)


class Reference(models.Model):
    unique_id = models.ForeignKey(Student, on_delete=models.CASCADE)
    reference_name = models.CharField(max_length=100, default='')
    reference_designation = models.CharField(max_length=100, default='')
    reference_institute = models.CharField(max_length=100, default='')
    reference_email = models.CharField(max_length=100, default='')
    reference_mobile = models.CharField(max_length=100, default='')

    def __str__(self):
        return '{} - {}'.format(self.unique_id.id, self.reference_name)


class ChairmanVisit(models.Model):
    company_name = models.CharField(max_length=100, default='')
    location = models.CharField(max_length=100, default='')
    description = models.TextField(max_length=1000, null=True, blank=True)
    visiting_date = models.DateField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True, null=True)

    def __str__(self):
        return '{}'.format(self.company_name)


class PlacementSchedule(models.Model):
    notify_id = models.ForeignKey(NotifyStudent, on_delete=models.CASCADE)
    title = models.CharField(max_length=100, default='')
    description = models.TextField(max_length=500, null=True, blank=True)
    placement_date = models.DateField(null=True, blank=True)
    attached_file = models.FileField(upload_to='placement_cell/', blank=True, null=True)
    role = models.ForeignKey(Role, on_delete=models.CASCADE, null=True)
    location = models.CharField(max_length=200, null=True, blank=True)
    time = models.TimeField(null=True, blank=True)

    def get_role(self):
        # S48: Fixed bare except → specific exception types
        try:
            return self.role.role
        except (AttributeError, Role.DoesNotExist):
            return ''

    def __str__(self):
        return '{}'.format(self.title)
