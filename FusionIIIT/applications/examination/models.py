from decimal import Decimal
from django.db import models
from applications.academic_procedures.models import course_registration
from applications.online_cms.models import Student_grades
from applications.academic_information.models import Course
from applications.programme_curriculum.models import (
    Course as Courses,
    CourseInstructor,
    Batch,
)


# ---------------------------------------------------------------------------
# TextChoices
# ---------------------------------------------------------------------------

class SemesterType(models.TextChoices):
    ODD = "Odd Semester", "Odd Semester"
    EVEN = "Even Semester", "Even Semester"
    SUMMER = "Summer Semester", "Summer Semester"


# ---------------------------------------------------------------------------
# Role constants
# ---------------------------------------------------------------------------

PROFESSOR_ROLES = frozenset({
    "Associate Professor",
    "Professor",
    "Assistant Professor",
})

ADMIN_ROLES = frozenset({"acadadmin"})

DEAN_ROLES = frozenset({"Dean Academic"})

ADMIN_OR_DEAN_ROLES = ADMIN_ROLES | DEAN_ROLES

ALL_STAFF_ROLES = PROFESSOR_ROLES | ADMIN_OR_DEAN_ROLES

# ---------------------------------------------------------------------------
# Programme constants
# ---------------------------------------------------------------------------

UG_PROGRAMMES = ("B.Tech", "B.Des")
PG_PROGRAMMES = ("M.Tech", "M.Des", "PhD")

# ---------------------------------------------------------------------------
# Grade constants
# ---------------------------------------------------------------------------

ALLOWED_GRADES = frozenset({
    "O", "A+", "A",
    "B+", "B",
    "C+", "C",
    "D+", "D", "F",
    "CD", "S", "X",
})

PBI_AND_BTP_ALLOWED_GRADES = frozenset(
    {f"{x:.1f}" for x in [i / 10 for i in range(20, 101)]}
)

PBI_BTP_COURSE_CODES = frozenset({"PR4001", "PR4002", "BTP4001"})

ALL_DISPLAY_GRADES = [
    "O", "A+", "A", "B+", "B", "C+", "C", "D+", "D", "F", "S", "X", "CD",
]

GRADE_CONVERSION = {
    "O": 1.0, "A+": 1.0, "A": 0.9, "B+": 0.8, "B": 0.7,
    "C+": 0.6, "C": 0.5, "D+": 0.4, "D": 0.3, "F": 0.2, "S": 0.0,
    **{f"A{i}": Decimal(str(0.9 + i * 0.01)) for i in range(1, 11)},
    **{f"B{i}": Decimal(str(0.8 + i * 0.01)) for i in range(1, 11)},
    **{
        f"{x / 10:.1f}": Decimal(f"{x / 100:.2f}")
        for x in range(20, 101)
    },
}


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class hidden_grades(models.Model):
    student_id = models.CharField(max_length=20)
    course_id = models.CharField(max_length=50)
    semester_id = models.CharField(max_length=10)
    grade = models.CharField(max_length=5)

    def __str__(self):
        return f"{self.student_id}, {self.course_id}"


class authentication(models.Model):
    authenticator_1 = models.BooleanField(default=False)
    authenticator_2 = models.BooleanField(default=False)
    authenticator_3 = models.BooleanField(default=False)
    year = models.DateField(auto_now_add=True)
    course_id = models.ForeignKey(Courses, on_delete=models.CASCADE, default=1)
    course_year = models.IntegerField(default=2024)

    @property
    def working_year(self):
        return self.year.year

    def __str__(self):
        return f"{self.course_id} , {self.course_year}"


class grade(models.Model):
    student = models.CharField(max_length=20)
    curriculum = models.CharField(max_length=50)
    semester_id = models.CharField(max_length=10, default='')
    grade = models.CharField(max_length=5, default="B")


class ResultAnnouncement(models.Model):
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE)
    semester = models.PositiveIntegerField()
    announced = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        status = "Announced" if self.announced else "Not Announced"
        return f"{self.batch.label} - Sem {self.semester} - {status}"
