from django.contrib import admin
from .models import StudyResource


@admin.register(StudyResource)
class StudyResourceAdmin(admin.ModelAdmin):
    list_display = ("filename", "title", "file_type", "formatted_size", "subject", "uploaded_at")
    list_filter = ("file_type", "subject")
    search_fields = ("filename", "title", "subject")
