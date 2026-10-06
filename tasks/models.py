"""
Database models for the Daily Tasks application.
Fields per specification:
- id, title, description, subject, due_date, priority, completed, created_at
"""
from django.db import models
from django.utils import timezone


class Task(models.Model):
    """Represents a daily or upcoming academic study task."""

    PRIORITY_HIGH = "High"
    PRIORITY_MEDIUM = "Medium"
    PRIORITY_LOW = "Low"

    PRIORITY_CHOICES = [
        (PRIORITY_HIGH, "High"),
        (PRIORITY_MEDIUM, "Medium"),
        (PRIORITY_LOW, "Low"),
    ]

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, default="")
    subject = models.CharField(max_length=100, default="Python")
    due_date = models.DateField(default=timezone.localdate)
    priority = models.CharField(
        max_length=20,
        choices=PRIORITY_CHOICES,
        default=PRIORITY_MEDIUM,
    )
    completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["completed", "due_date", "-created_at"]

    def __str__(self) -> str:
        state = "Done" if self.completed else "Pending"
        return f"[{self.priority}] {self.title} ({state})"
