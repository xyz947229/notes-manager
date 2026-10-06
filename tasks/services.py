"""
Object-Oriented service layer for Daily Tasks management.

Demonstrates:
- OOP (TaskManager class)
- Lambda Functions (Sorting tasks by priority rank and due date)
- Generators / yield (Streaming tasks for CSV export)
- Exception Handling (TaskValidationError)
"""
from datetime import date, datetime
from typing import Any, Dict, Generator, Iterable, List, Optional
from django.utils import timezone
from .models import Task


class TaskValidationError(ValueError):
    """Raised when task data fails validation."""


class TaskManager:
    """OOP service class managing student daily tasks and completion statistics."""

    PRIORITY_WEIGHTS = {
        Task.PRIORITY_HIGH: 3,
        Task.PRIORITY_MEDIUM: 2,
        Task.PRIORITY_LOW: 1,
    }

    @staticmethod
    def _parse_due_date(raw_date: Any) -> date:
        if isinstance(raw_date, datetime):
            return raw_date.date()
        if isinstance(raw_date, date):
            return raw_date
        if isinstance(raw_date, str) and raw_date.strip():
            try:
                return datetime.strptime(raw_date.strip()[:10], "%Y-%m-%d").date()
            except ValueError as exc:
                raise TaskValidationError(
                    f"Invalid due_date format '{raw_date}'. Expected YYYY-MM-DD."
                ) from exc
        return timezone.localdate()

    def create_task(
        self,
        title: str,
        description: str = "",
        subject: str = "Python",
        priority: str = Task.PRIORITY_MEDIUM,
        due_date: Any = None,
        completed: bool = False,
    ) -> Task:
        cleaned_title = (title or "").strip()
        if not cleaned_title:
            raise TaskValidationError("Task title cannot be empty.")

        cleaned_priority = (priority or Task.PRIORITY_MEDIUM).strip().capitalize()
        if cleaned_priority not in self.PRIORITY_WEIGHTS:
            cleaned_priority = Task.PRIORITY_MEDIUM

        parsed_due = self._parse_due_date(due_date)
        is_done = bool(completed)

        return Task.objects.create(
            title=cleaned_title,
            description=(description or "").strip(),
            subject=(subject or "Python").strip() or "Python",
            priority=cleaned_priority,
            due_date=parsed_due,
            completed=is_done,
            completed_at=timezone.now() if is_done else None,
        )

    def update_task(self, task_id: int, **data) -> Task:
        try:
            task = Task.objects.get(pk=task_id)
        except Task.DoesNotExist as exc:
            raise TaskValidationError(f"Task with ID {task_id} was not found.") from exc

        if "title" in data:
            title = (data["title"] or "").strip()
            if not title:
                raise TaskValidationError("Task title cannot be empty.")
            task.title = title

        if "description" in data and data["description"] is not None:
            task.description = str(data["description"]).strip()

        if "subject" in data and data["subject"]:
            task.subject = str(data["subject"]).strip()

        if "priority" in data and data["priority"]:
            prio = str(data["priority"]).strip().capitalize()
            if prio in self.PRIORITY_WEIGHTS:
                task.priority = prio

        if "due_date" in data and data["due_date"]:
            task.due_date = self._parse_due_date(data["due_date"])

        if "completed" in data and data["completed"] is not None:
            raw_comp = data["completed"]
            is_comp = (
                raw_comp.lower() in ("true", "1", "yes")
                if isinstance(raw_comp, str)
                else bool(raw_comp)
            )
            task.completed = is_comp
            task.completed_at = timezone.now() if is_comp else None

        task.save()
        return task

    def set_completion(self, task_id: int, completed: bool) -> Task:
        return self.update_task(task_id, completed=completed)

    def delete_task(self, task_id: int) -> bool:
        deleted, _ = Task.objects.filter(pk=task_id).delete()
        if not deleted:
            raise TaskValidationError(f"Task with ID {task_id} does not exist.")
        return True

    def sort_tasks_by_priority(self, tasks: Iterable[Task]) -> List[Task]:
        """
        Sort tasks using a Python lambda function:
        1. Incomplete tasks before completed tasks
        2. Higher priority weight first (High=3, Medium=2, Low=1)
        3. Earlier due date first
        """
        return sorted(
            list(tasks),
            key=lambda t: (
                1 if t.completed else 0,
                -self.PRIORITY_WEIGHTS.get(t.priority, 1),
                t.due_date or date.max,
                t.title.lower(),
            ),
        )

    def get_categorized_tasks(self) -> Dict[str, Any]:
        """
        Organize tasks into 'Today', 'Upcoming', and 'Completed' sections
        and compute completion summary metrics.
        """
        today = timezone.localdate()
        all_tasks = self.sort_tasks_by_priority(Task.objects.all())

        today_tasks = [t for t in all_tasks if not t.completed and t.due_date <= today]
        upcoming_tasks = [t for t in all_tasks if not t.completed and t.due_date > today]
        completed_tasks = sorted(
            [t for t in all_tasks if t.completed],
            key=lambda t: (
                -(t.completed_at.timestamp() if t.completed_at else 0.0),
                -self.PRIORITY_WEIGHTS.get(t.priority, 1),
            ),
        )

        total_count = len(all_tasks)
        completed_count = len(completed_tasks)
        progress_pct = round((completed_count / total_count) * 100, 1) if total_count > 0 else 0.0

        # Today's active + completed today
        due_today_or_done_today = [
            t for t in all_tasks if t.due_date <= today
        ]

        return {
            "today_tasks": today_tasks,
            "upcoming_tasks": upcoming_tasks,
            "completed_tasks": completed_tasks,
            "all_tasks": all_tasks,
            "total_count": total_count,
            "completed_count": completed_count,
            "pending_count": total_count - completed_count,
            "progress_percentage": progress_pct,
            "summary_text": f"{completed_count} of {total_count} tasks completed",
            "today_schedule": due_today_or_done_today[:6],
        }

    @staticmethod
    def stream_tasks_for_export(tasks_iterable: Optional[Iterable[Task]] = None) -> Generator[Dict[str, str], None, None]:
        """Generator using `yield` to stream task rows for CSV export."""
        source = tasks_iterable if tasks_iterable is not None else Task.objects.all().iterator()
        for task in source:
            yield {
                "id": str(task.id),
                "title": task.title,
                "description": task.description,
                "subject": task.subject,
                "priority": task.priority,
                "due_date": task.due_date.strftime("%Y-%m-%d") if task.due_date else "",
                "status": "Completed" if task.completed else "Pending",
                "created_at": task.created_at.strftime("%Y-%m-%d %H:%M") if task.created_at else "",
            }
