from django.contrib import admin
from .models import StudyLog


@admin.register(StudyLog)
class StudyLogAdmin(admin.ModelAdmin):
    list_display = (
        "date",
        "notes_covered_count",
        "quizzes_completed_count",
        "tasks_completed_count",
        "study_minutes",
        "overall_progress_snapshot",
    )
    list_filter = ("date",)
