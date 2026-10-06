"""
Object-Oriented File Management Service (TXT export, CSV export, Resource validation).

Python Concepts Demonstrated:
- OOP (FileManager class with encapsulation and custom FileHandlingError)
- File Handling (`os`, `pathlib`, file streams, Django ContentFile)
- TXT & CSV Functionality (`csv` standard library module)
- Generators / yield (`stream_notes_txt`, `stream_csv_rows` for memory-efficient streaming)
- Security & Exception Handling (Strict extension allowlist, size limits, safe filenames)
"""
import csv
import io
from pathlib import Path
from typing import Any, Dict, Generator, Iterable, List, Optional
from django.conf import settings
from django.core.files.base import ContentFile
from django.utils import timezone
from notes.services import NoteManager
from progress.services import ProgressTracker
from quizzes.services import QuizManager
from tasks.services import TaskManager
from .models import StudyResource


class FileHandlingError(ValueError):
    """Raised when file upload, validation, or export fails."""


class EchoBuffer:
    """Pseudo-buffer that returns the value written to it, used with csv.writer and generators."""

    def write(self, value: str) -> str:
        return value


class FileManager:
    """
    OOP Service class managing TXT exports, CSV exports, and StudyResource uploads.
    """

    ALLOWED_EXTENSIONS = {".pdf", ".txt", ".csv", ".md", ".json"}
    BLOCKED_EXTENSIONS = {".exe", ".bat", ".cmd", ".sh", ".ps1", ".php", ".dll", ".msi", ".js"}
    MAX_UPLOAD_BYTES = 20 * 1024 * 1024  # 20 MB

    @classmethod
    def validate_uploaded_file(cls, uploaded_file: Any) -> str:
        """
        Validate uploaded resource file type and size (Part 31 Security).
        Returns the detected file_type category ('PDF', 'TXT', 'CSV', 'OTHER').
        """
        if uploaded_file is None:
            raise FileHandlingError("No file was selected for upload.")

        raw_name = Path(getattr(uploaded_file, "name", "")).name
        if not raw_name:
            raise FileHandlingError("Uploaded file must have a valid filename.")

        ext = Path(raw_name).suffix.lower()
        if ext in cls.BLOCKED_EXTENSIONS or ext not in cls.ALLOWED_EXTENSIONS:
            allowed_str = ", ".join(sorted(cls.ALLOWED_EXTENSIONS))
            raise FileHandlingError(
                f"File type '{ext or 'unknown'}' is not permitted. Allowed file types: {allowed_str}."
            )

        size = getattr(uploaded_file, "size", 0)
        if size <= 0:
            raise FileHandlingError("Uploaded file cannot be empty (0 bytes).")
        if size > cls.MAX_UPLOAD_BYTES:
            raise FileHandlingError("Uploaded file exceeds the 20 MB maximum size limit.")

        if ext == ".pdf":
            return StudyResource.TYPE_PDF
        if ext == ".txt":
            return StudyResource.TYPE_TXT
        if ext == ".csv":
            return StudyResource.TYPE_CSV
        return StudyResource.TYPE_OTHER

    @classmethod
    def save_uploaded_resource(
        cls,
        uploaded_file: Any,
        title: str = "",
        subject: str = "Python",
    ) -> StudyResource:
        """Validate and save an uploaded study resource into Django media storage."""
        file_type = cls.validate_uploaded_file(uploaded_file)
        clean_filename = Path(uploaded_file.name).name
        clean_title = (title or "").strip() or Path(clean_filename).stem.replace("_", " ").title()

        resource = StudyResource.objects.create(
            title=clean_title,
            file=uploaded_file,
            filename=clean_filename,
            file_type=file_type,
            file_size=int(getattr(uploaded_file, "size", 0)),
            subject=(subject or "Python").strip() or "Python",
        )
        return resource

    @classmethod
    def delete_resource(cls, resource_id: int) -> bool:
        """Delete a StudyResource record and safely unlink its physical file."""
        try:
            resource = StudyResource.objects.get(pk=resource_id)
        except StudyResource.DoesNotExist as exc:
            raise FileHandlingError(f"Resource with ID {resource_id} was not found.") from exc

        try:
            if resource.file and resource.file.name:
                file_path = Path(settings.MEDIA_ROOT) / resource.file.name
                if file_path.exists() and file_path.is_file():
                    file_path.unlink()
        except OSError:
            pass

        resource.delete()
        return True

    # ==========================================================
    # PART 18: TEXT FILE (.txt) EXPORT WITH GENERATOR (yield)
    # ==========================================================
    @classmethod
    def stream_notes_txt(cls, subject: Optional[str] = None) -> Generator[str, None, None]:
        """
        Generator using `yield` that produces formatted sections for `notes.txt`.
        Includes Subject, Note title, Content, Status, and Date for every note.
        """
        note_mgr = NoteManager()
        notes = note_mgr.filter_and_sort_notes(subject=subject, sort_by="title_asc")

        header = (
            "======================================================================\n"
            "NOTES MANAGER — ACADEMIC STUDY NOTES EXPORT (notes.txt)\n"
            f"Generated At: {timezone.localtime().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"Total Notes Exported: {len(notes)}\n"
            "======================================================================\n\n"
        )
        yield header

        if not notes:
            yield "No study notes available to export.\n"
            return

        for idx, note_dict in enumerate(NoteManager.stream_notes_for_export(notes), start=1):
            block = (
                f"Note #{idx}\n"
                f"Subject : {note_dict['subject']} ({note_dict['topic']})\n"
                f"Title   : {note_dict['title']}\n"
                f"Status  : {note_dict['status']} ({note_dict['reading_progress']})\n"
                f"Date    : {note_dict['updated_date']}\n"
                f"----------------------------------------------------------------------\n"
                f"{note_dict['content']}\n"
                f"======================================================================\n\n"
            )
            yield block

    @classmethod
    def generate_notes_txt_content(cls, subject: Optional[str] = None, save_to_resources: bool = False) -> str:
        """Assemble full `notes.txt` content and optionally archive a copy in StudyResource."""
        content = "".join(cls.stream_notes_txt(subject=subject))
        if save_to_resources:
            cls._save_generated_file_to_resources(
                filename="notes.txt",
                title="Exported Study Notes (TXT)",
                content_bytes=content.encode("utf-8"),
                file_type=StudyResource.TYPE_TXT,
            )
        return content

    # ==========================================================
    # PART 19: CSV EXPORT USING PYTHON'S `csv` MODULE & `yield`
    # ==========================================================
    @classmethod
    def stream_csv_rows(
        cls,
        headers: List[str],
        dict_generator: Iterable[Dict[str, Any]],
    ) -> Generator[str, None, None]:
        """
        Generator using `yield` and Python's `csv` module to stream CSV lines one by one.
        """
        pseudo_buffer = EchoBuffer()
        writer = csv.DictWriter(pseudo_buffer, fieldnames=headers, extrasaction="ignore")
        yield writer.writerow(dict(zip(headers, headers)))
        for row_dict in dict_generator:
            yield writer.writerow(row_dict)

    @classmethod
    def get_csv_export_stream(cls, export_type: str) -> Generator[str, None, None]:
        """Return a CSV streaming generator for notes, quiz_results, tasks, or progress."""
        normalized = (export_type or "notes").strip().lower()

        if normalized in ("notes", "notes.csv"):
            headers = [
                "id",
                "subject",
                "topic",
                "title",
                "status",
                "reading_progress",
                "created_date",
                "updated_date",
                "content",
            ]
            return cls.stream_csv_rows(headers, NoteManager.stream_notes_for_export())

        if normalized in ("quiz_results", "quizzes", "quiz_results.csv"):
            headers = [
                "id",
                "title",
                "subject",
                "score",
                "total_questions",
                "percentage",
                "time_taken_seconds",
                "completed",
                "created_at",
            ]
            return cls.stream_csv_rows(headers, QuizManager.stream_quiz_results_for_export())

        if normalized in ("tasks", "tasks.csv"):
            headers = [
                "id",
                "title",
                "subject",
                "priority",
                "due_date",
                "status",
                "description",
                "created_at",
            ]
            return cls.stream_csv_rows(headers, TaskManager.stream_tasks_for_export())

        if normalized in ("progress", "progress.csv"):
            headers = [
                "date",
                "notes_covered_count",
                "quizzes_completed_count",
                "tasks_completed_count",
                "study_minutes",
                "overall_progress",
                "current_streak",
            ]
            return cls.stream_csv_rows(headers, ProgressTracker.stream_progress_for_export())

        raise FileHandlingError(
            f"Unsupported CSV export type '{export_type}'. Choose from: notes, quiz_results, tasks, progress."
        )

    @classmethod
    def generate_csv_content(cls, export_type: str, save_to_resources: bool = False) -> str:
        """Build complete CSV content string for testing or archiving in StudyResource."""
        output = io.StringIO()
        for line in cls.get_csv_export_stream(export_type):
            output.write(line)
        csv_text = output.getvalue()

        if save_to_resources:
            filename_map = {
                "notes": ("notes.csv", "Exported Study Notes (CSV)"),
                "quiz_results": ("quiz_results.csv", "Exported Quiz Results (CSV)"),
                "tasks": ("tasks.csv", "Exported Daily Tasks (CSV)"),
                "progress": ("progress.csv", "Exported Study Progress (CSV)"),
            }
            fname, title = filename_map.get(export_type, ("export.csv", "Exported Data (CSV)"))
            cls._save_generated_file_to_resources(
                filename=fname,
                title=title,
                content_bytes=csv_text.encode("utf-8"),
                file_type=StudyResource.TYPE_CSV,
            )
        return csv_text

    @classmethod
    def _save_generated_file_to_resources(
        cls,
        filename: str,
        title: str,
        content_bytes: bytes,
        file_type: str,
        subject: str = "All Subjects",
    ) -> StudyResource:
        existing = StudyResource.objects.filter(filename=filename).first()
        if existing:
            cls.delete_resource(existing.id)

        django_file = ContentFile(content_bytes, name=filename)
        return StudyResource.objects.create(
            title=title,
            file=django_file,
            filename=filename,
            file_type=file_type,
            file_size=len(content_bytes),
            subject=subject,
        )
