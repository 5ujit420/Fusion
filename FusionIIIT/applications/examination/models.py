from django.db import models
from applications.academic_procedures.models import (course_registration)
from applications.online_cms.models import (Student_grades)
from applications.academic_information.models import Course
from applications.programme_curriculum.models import Course as Courses, CourseInstructor, Batch


class HiddenGrade(models.Model):
    """Stores grades before they are published (V35: PascalCase rename)."""
    student_id = models.CharField(max_length=20)
    course_id = models.CharField(max_length=50)
    semester_id = models.CharField(max_length=10)
    grade = models.CharField(max_length=5)

    class Meta:
        db_table = 'examination_hidden_grades'

    def __str__(self):
        return f"{self.student_id}, {self.course_id}"


class Authentication(models.Model):
    """Tracks three-way authenticator sign-off on course grades (V35)."""
    authenticator_1 = models.BooleanField(default=False)
    authenticator_2 = models.BooleanField(default=False)
    authenticator_3 = models.BooleanField(default=False)
    year = models.DateField(auto_now_add=True)
    course_id = models.ForeignKey(Courses, on_delete=models.CASCADE, default=1)
    course_year = models.IntegerField(default=2024)

    class Meta:
        db_table = 'examination_authentication'

    @property
    def working_year(self):
        return self.year.year

    def __str__(self):
        return f"{self.course_id} , {self.course_year}"


class Grade(models.Model):
    """Legacy grade model — kept for backward compatibility (V35)."""
    student = models.CharField(max_length=20)
    curriculum = models.CharField(max_length=50)
    semester_id = models.CharField(max_length=10, default='')
    grade = models.CharField(max_length=5, default="B")

    class Meta:
        db_table = 'examination_grade'

    def __str__(self):
        return f"{self.student} - {self.curriculum}: {self.grade}"


class ResultAnnouncement(models.Model):
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE)
    semester = models.PositiveIntegerField()
    announced = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        status = "Announced" if self.announced else "Not Announced"
        return f"{self.batch} - Sem {self.semester} - {status}"


# ---------------------------------------------------------------------------
# Backward-compatible aliases so existing imports don't break
# ---------------------------------------------------------------------------
hidden_grades = HiddenGrade
authentication = Authentication
grade = Grade
