from django.contrib import admin
from .models import HiddenGrade, Authentication, Grade, ResultAnnouncement

admin.site.register(HiddenGrade)
admin.site.register(Authentication)
admin.site.register(Grade)
admin.site.register(ResultAnnouncement)