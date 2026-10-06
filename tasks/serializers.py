"""DRF Serializer for Task model."""
from rest_framework import serializers
from .models import Task


class TaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = [
            "id",
            "title",
            "description",
            "subject",
            "due_date",
            "priority",
            "completed",
            "completed_at",
            "created_at",
        ]
