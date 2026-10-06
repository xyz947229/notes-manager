"""DRF Serializer for StudyLog."""
from rest_framework import serializers
from .models import StudyLog


class StudyLogSerializer(serializers.ModelSerializer):
    total_actions = serializers.IntegerField(read_only=True)

    class Meta:
        model = StudyLog
        fields = [
            "id",
            "date",
            "notes_covered_count",
            "quizzes_completed_count",
            "tasks_completed_count",
            "study_minutes",
            "overall_progress_snapshot",
            "total_actions",
            "updated_at",
        ]
