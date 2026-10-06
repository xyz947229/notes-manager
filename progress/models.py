"""
Database models for Progress and Study Consistency tracking.
Stores daily study logs for streak calculations, heatmaps, and historical progress snapshots.
"""
from django.db import models
from django.utils import timezone


class StudyLog(models.Model):
    """
    Stores daily study activity used by the Consistency Tracker heatmap and streak calculator.
    """

    date = models.DateField(default=timezone.localdate, unique=True)
    notes_covered_count = models.PositiveIntegerField(default=0)
    quizzes_completed_count = models.PositiveIntegerField(default=0)
    tasks_completed_count = models.PositiveIntegerField(default=0)
    study_minutes = models.PositiveIntegerField(default=25)
    overall_progress_snapshot = models.FloatField(default=0.0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date"]

    @property
    def total_actions(self) -> int:
        return (
            self.notes_covered_count
            + self.quizzes_completed_count
            + self.tasks_completed_count
        )

    @property
    def is_active_day(self) -> bool:
        return self.total_actions > 0 or self.study_minutes > 0

    def __str__(self) -> str:
        return (
            f"{self.date}: {self.total_actions} actions "
            f"({self.study_minutes} mins, {self.overall_progress_snapshot:.1f}%)"
        )
