from django.contrib import admin
from .models import hidden_grades, authentication, grade, ResultAnnouncement


@admin.register(hidden_grades)
class HiddenGradesAdmin(admin.ModelAdmin):
    list_display = ('student_id', 'course_id', 'semester_id', 'grade')
    search_fields = ('student_id', 'course_id')


@admin.register(authentication)
class AuthenticationAdmin(admin.ModelAdmin):
    list_display = ('course_id', 'course_year', 'authenticator_1', 'authenticator_2', 'authenticator_3')
    list_filter = ('course_year',)


@admin.register(grade)
class GradeAdmin(admin.ModelAdmin):
    list_display = ('student', 'curriculum', 'semester_id', 'grade')
    search_fields = ('student',)


@admin.register(ResultAnnouncement)
class ResultAnnouncementAdmin(admin.ModelAdmin):
    list_display = ('batch', 'semester', 'announced', 'created_at')
    list_filter = ('announced', 'semester')
