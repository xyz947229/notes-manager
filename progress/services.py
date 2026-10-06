"""
Object-Oriented service layer for Progress & Consistency Tracking.

Formula Documented (Part 13):
overall_progress = (notes_progress + quiz_progress + task_progress) / 3.0

Python Concepts Demonstrated:
- OOP (ProgressTracker class)
- NumPy (Vectorized calculation of average quiz scores, category array mean, and weekly stats)
- Generators / yield (Streaming progress logs for CSV export)
"""
from datetime import date, timedelta
from typing import Any, Dict, Generator, List, Set
import numpy as np
from django.utils import timezone
from notes.models import Note, Subject
from quizzes.models import Quiz
from tasks.models import Task
from .models import StudyLog


class ProgressTracker:
    """
    OOP Service class that computes Notes Progress, Quiz Progress, Task Progress,
    Overall Progress, and Study Consistency Streaks from live database records.
    """

    FORMULA_DESCRIPTION = "overall_progress = (notes_progress + quiz_progress + task_progress) / 3"

    @classmethod
    def record_study_activity(
        cls,
        activity_date: date = None,
        notes_delta: int = 0,
        quizzes_delta: int = 0,
        tasks_delta: int = 0,
        minutes_delta: int = 15,
    ) -> StudyLog:
        """Record or increment daily study activity in the database."""
        target_date = activity_date or timezone.localdate()
        log, created = StudyLog.objects.get_or_create(
            date=target_date,
            defaults={
                "notes_covered_count": max(0, notes_delta),
                "quizzes_completed_count": max(0, quizzes_delta),
                "tasks_completed_count": max(0, tasks_delta),
                "study_minutes": max(10, minutes_delta),
            },
        )
        if not created:
            log.notes_covered_count = max(0, log.notes_covered_count + notes_delta)
            log.quizzes_completed_count = max(0, log.quizzes_completed_count + quizzes_delta)
            log.tasks_completed_count = max(0, log.tasks_completed_count + tasks_delta)
            log.study_minutes = max(0, log.study_minutes + minutes_delta)

        metrics = cls.calculate_progress_metrics(update_today_log=False)
        log.overall_progress_snapshot = metrics["overall_progress"]
        log.save()
        return log

    @classmethod
    def calculate_progress_metrics(cls, update_today_log: bool = True) -> Dict[str, Any]:
        """
        Calculate the three major progress categories and Overall Progress using NumPy:
        1. Notes Progress = (covered_notes / total_notes) * 100
        2. Quiz Progress = Mean of completed quiz percentage array via NumPy
        3. Task Progress = (completed_tasks / total_tasks) * 100
        4. Overall Progress = (notes_progress + quiz_progress + task_progress) / 3
        """
        total_notes = Note.objects.count()
        covered_notes = Note.objects.filter(covered=True).count()
        pending_notes = max(0, total_notes - covered_notes)
        notes_progress = float(np.round((covered_notes / total_notes) * 100.0, 1)) if total_notes > 0 else 0.0

        completed_quizzes = list(Quiz.objects.filter(completed=True).values_list("percentage", flat=True))
        if completed_quizzes:
            quiz_scores_array = np.array(completed_quizzes, dtype=np.float64)
            quiz_progress = float(np.round(np.mean(quiz_scores_array), 1))
            highest_quiz_score = float(np.round(np.max(quiz_scores_array), 1))
            lowest_quiz_score = float(np.round(np.min(quiz_scores_array), 1))
        else:
            quiz_progress = 0.0
            highest_quiz_score = 0.0
            lowest_quiz_score = 0.0

        total_tasks = Task.objects.count()
        completed_tasks = Task.objects.filter(completed=True).count()
        pending_tasks = max(0, total_tasks - completed_tasks)
        task_progress = float(np.round((completed_tasks / total_tasks) * 100.0, 1)) if total_tasks > 0 else 0.0

        # Use NumPy vector for the 3-pillar overall progress formula
        category_vector = np.array([notes_progress, quiz_progress, task_progress], dtype=np.float64)
        overall_progress = float(np.round(np.mean(category_vector), 1))

        # Per-subject progress breakdown
        subject_breakdown: List[Dict[str, Any]] = []
        for subject in Subject.objects.all():
            s_total = subject.notes.count()
            s_cov = subject.notes.filter(covered=True).count()
            s_pct = round((s_cov / s_total) * 100.0, 1) if s_total > 0 else 0.0
            subject_breakdown.append(
                {
                    "subject": subject.name,
                    "total_notes": s_total,
                    "covered_notes": s_cov,
                    "pending_notes": s_total - s_cov,
                    "progress_percentage": s_pct,
                }
            )

        consistency = cls.calculate_consistency_metrics()

        if update_today_log and (total_notes > 0 or total_tasks > 0 or completed_quizzes):
            today = timezone.localdate()
            StudyLog.objects.filter(date=today).update(overall_progress_snapshot=overall_progress)

        return {
            "formula": cls.FORMULA_DESCRIPTION,
            "notes_progress": notes_progress,
            "quiz_progress": quiz_progress,
            "task_progress": task_progress,
            "overall_progress": overall_progress,
            "total_notes": total_notes,
            "covered_notes": covered_notes,
            "pending_notes": pending_notes,
            "total_quizzes": Quiz.objects.count(),
            "completed_quizzes": len(completed_quizzes),
            "average_quiz_score": quiz_progress,
            "highest_quiz_score": highest_quiz_score,
            "lowest_quiz_score": lowest_quiz_score,
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "pending_tasks": pending_tasks,
            "subject_breakdown": subject_breakdown,
            "consistency": consistency,
            "current_streak": consistency["current_streak"],
            "best_streak": consistency["best_streak"],
        }

    @classmethod
    def _collect_active_study_dates(cls) -> Set[date]:
        """Gather all dates with real study activity from StudyLog, Note, Quiz, and Task tables."""
        active_dates: Set[date] = set()

        for log in StudyLog.objects.all():
            if log.is_active_day:
                active_dates.add(log.date)

        for dt in Note.objects.values_list("updated_at", flat=True):
            if dt:
                active_dates.add(timezone.localtime(dt).date() if timezone.is_aware(dt) else dt.date())

        for dt in Quiz.objects.values_list("created_at", flat=True):
            if dt:
                active_dates.add(timezone.localtime(dt).date() if timezone.is_aware(dt) else dt.date())

        for dt in Task.objects.filter(completed=True).values_list("completed_at", flat=True):
            if dt:
                active_dates.add(timezone.localtime(dt).date() if timezone.is_aware(dt) else dt.date())

        return active_dates

    @classmethod
    def calculate_consistency_metrics(cls, num_days: int = 28) -> Dict[str, Any]:
        """
        Compute Current Streak, Best Streak, Study Days, Weekly Consistency,
        and a 28-day Calendar Heatmap from database records.
        """
        today = timezone.localdate()
        active_dates = cls._collect_active_study_dates()

        # Current streak calculation (counts backwards from today or yesterday)
        current_streak = 0
        cursor_date = today if today in active_dates else (today - timedelta(days=1))
        if cursor_date in active_dates:
            while cursor_date in active_dates:
                current_streak += 1
                cursor_date -= timedelta(days=1)

        # Best streak calculation across all sorted dates
        sorted_dates = sorted(active_dates)
        best_streak = 0
        running = 0
        prev_day = None
        for d in sorted_dates:
            if prev_day is not None and (d - prev_day).days == 1:
                running += 1
            else:
                running = 1
            best_streak = max(best_streak, running)
            prev_day = d

        # Weekly consistency (last 7 days)
        last_7_days = [today - timedelta(days=i) for i in range(6, -1, -1)]
        active_in_last_7 = sum(1 for d in last_7_days if d in active_dates)
        weekly_consistency = round((active_in_last_7 / 7.0) * 100.0, 1)

        # Build 28-day heatmap data
        logs_by_date = {
            log.date: log
            for log in StudyLog.objects.filter(date__gte=today - timedelta(days=num_days))
        }
        heatmap_days: List[Dict[str, Any]] = []
        weekly_minutes: List[int] = []

        for offset in range(num_days - 1, -1, -1):
            d = today - timedelta(days=offset)
            log = logs_by_date.get(d)
            actions = log.total_actions if log else (1 if d in active_dates else 0)
            minutes = log.study_minutes if log else (25 if d in active_dates else 0)

            if actions == 0 and d not in active_dates:
                level = 0
            elif actions <= 1:
                level = 1
            elif actions <= 3:
                level = 2
            elif actions <= 5:
                level = 3
            else:
                level = 4

            heatmap_days.append(
                {
                    "date": d.strftime("%Y-%m-%d"),
                    "label": d.strftime("%b %d"),
                    "weekday": d.strftime("%a"),
                    "actions": actions,
                    "study_minutes": minutes,
                    "level": level,
                    "active": d in active_dates,
                }
            )
            if offset < 7:
                weekly_minutes.append(minutes)

        return {
            "current_streak": current_streak,
            "best_streak": max(best_streak, current_streak),
            "total_study_days": len(active_dates),
            "tasks_completed": Task.objects.filter(completed=True).count(),
            "weekly_consistency": weekly_consistency,
            "active_days_this_week": active_in_last_7,
            "weekly_study_minutes": int(np.sum(np.array(weekly_minutes, dtype=np.int32))) if weekly_minutes else 0,
            "heatmap_days": heatmap_days,
        }

    @classmethod
    def stream_progress_for_export(cls) -> Generator[Dict[str, str], None, None]:
        """Generator using `yield` to stream daily study logs and overall summary for CSV export."""
        summary = cls.calculate_progress_metrics(update_today_log=False)
        for log in StudyLog.objects.all().order_by("-date").iterator():
            yield {
                "date": log.date.strftime("%Y-%m-%d"),
                "notes_covered_count": str(log.notes_covered_count),
                "quizzes_completed_count": str(log.quizzes_completed_count),
                "tasks_completed_count": str(log.tasks_completed_count),
                "study_minutes": str(log.study_minutes),
                "overall_progress": f"{log.overall_progress_snapshot:.1f}%",
                "current_streak": str(summary["current_streak"]),
            }
