from django.contrib import admin
from .models import Subject, Note


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_custom", "created_at")
    search_fields = ("name", "description")


@admin.register(Note)
class NoteAdmin(admin.ModelAdmin):
    list_display = ("title", "subject", "topic", "covered", "reading_progress", "updated_at")
    list_filter = ("covered", "subject")
    search_fields = ("title", "topic", "content")
