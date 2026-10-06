"""
Object-Oriented service layer for Notes Management.

Python Syllabus Concepts Demonstrated:
1. OOP (Class NoteManager with encapsulated state, constructor, and domain methods)
2. Lambda Functions (Sorting notes by title, date, covered status, and word count)
3. Generators / yield (Streaming notes lazily for TXT/CSV export and batch processing)
4. Exception Handling (Custom NoteValidationError and database error handling)
"""
from typing import Dict, Generator, Iterable, List, Optional, Tuple
from django.db import DatabaseError, transaction
from django.db.models import Q
from .models import Note, Subject


class NoteValidationError(ValueError):
    """Raised when note or subject input fails validation rules."""


class NoteManager:
    """
    OOP Manager responsible for creating, querying, sorting, reading, and
    streaming study notes across subjects.
    """

    SORT_STRATEGIES = {
        # Meaningful Lambda Functions for dynamic in-memory sorting criteria
        "title_asc": lambda note: note.title.lower(),
        "title_desc": lambda note: note.title.lower(),
        "date_newest": lambda note: note.created_at.timestamp() if note.created_at else 0.0,
        "date_oldest": lambda note: note.created_at.timestamp() if note.created_at else 0.0,
        "updated_desc": lambda note: note.updated_at.timestamp() if note.updated_at else 0.0,
        "status": lambda note: (0 if not note.covered else 1, note.title.lower()),
        "length_desc": lambda note: len((note.content or "").split()),
    }

    def __init__(self, auto_seed: bool = False):
        self.auto_seed = auto_seed
        if self.auto_seed:
            self.ensure_default_subjects()

    def ensure_default_subjects(self) -> List[Subject]:
        """Ensure all default academic subjects exist in the database."""
        subjects = []
        try:
            for name, desc in Subject.DEFAULT_SUBJECTS:
                subject, _ = Subject.objects.get_or_create(
                    name=name,
                    defaults={"description": desc, "is_custom": False},
                )
                subjects.append(subject)
        except DatabaseError:
            return []
        return subjects

    def add_subject(self, name: str, description: str = "") -> Subject:
        """Create or retrieve a custom subject with validation."""
        cleaned_name = (name or "").strip()
        if not cleaned_name:
            raise NoteValidationError("Subject name cannot be empty.")
        if len(cleaned_name) > 100:
            raise NoteValidationError("Subject name must be 100 characters or fewer.")

        existing = Subject.objects.filter(name__iexact=cleaned_name).first()
        if existing:
            return existing

        return Subject.objects.create(
            name=cleaned_name,
            description=(description or f"Custom study notes for {cleaned_name}").strip(),
            is_custom=True,
        )

    def create_note(
        self,
        title: str,
        subject_name: str,
        content: str,
        topic: str = "Core Concepts",
        covered: bool = False,
        reading_progress: Optional[int] = None,
    ) -> Note:
        """Validate and create a new Note record."""
        cleaned_title = (title or "").strip()
        cleaned_content = (content or "").strip()
        cleaned_topic = (topic or "Core Concepts").strip() or "Core Concepts"

        if not cleaned_title:
            raise NoteValidationError("Note title cannot be empty.")
        if not cleaned_content:
            raise NoteValidationError("Note content cannot be empty.")

        subject = self.add_subject(subject_name or "Other")
        progress_val = (
            100
            if covered
            else (reading_progress if reading_progress is not None else 60)
        )
        progress_val = max(0, min(100, int(progress_val)))

        with transaction.atomic():
            note = Note.objects.create(
                title=cleaned_title,
                subject=subject,
                topic=cleaned_topic,
                content=cleaned_content,
                covered=bool(covered),
                reading_progress=progress_val,
            )
        return note

    def update_note(self, note_id: int, **data) -> Note:
        """Update an existing note with validation."""
        try:
            note = Note.objects.select_related("subject").get(pk=note_id)
        except Note.DoesNotExist as exc:
            raise NoteValidationError(f"Note with ID {note_id} was not found.") from exc

        if "title" in data:
            title = (data["title"] or "").strip()
            if not title:
                raise NoteValidationError("Note title cannot be empty.")
            note.title = title

        if "content" in data:
            content = (data["content"] or "").strip()
            if not content:
                raise NoteValidationError("Note content cannot be empty.")
            note.content = content

        if "topic" in data and data["topic"] is not None:
            note.topic = str(data["topic"]).strip() or "Core Concepts"

        if "subject" in data or "subject_name" in data:
            subj_input = data.get("subject_name") or data.get("subject")
            if isinstance(subj_input, Subject):
                note.subject = subj_input
            elif isinstance(subj_input, int) or (isinstance(subj_input, str) and subj_input.isdigit()):
                subj_obj = Subject.objects.filter(pk=int(subj_input)).first()
                if subj_obj:
                    note.subject = subj_obj
            elif isinstance(subj_input, str) and subj_input.strip():
                note.subject = self.add_subject(subj_input.strip())

        if "covered" in data and data["covered"] is not None:
            is_cov = str(data["covered"]).lower() in ("true", "1", "yes") if isinstance(data["covered"], str) else bool(data["covered"])
            note.covered = is_cov
            note.reading_progress = 100 if is_cov else max(20, min(90, note.reading_progress))

        if "reading_progress" in data and data["reading_progress"] is not None:
            note.reading_progress = max(0, min(100, int(data["reading_progress"])))

        note.save()
        return note

    def set_covered_status(self, note_id: int, covered: bool) -> Note:
        """Mark a note as covered or uncovered and update its reading progress."""
        return self.update_note(
            note_id,
            covered=covered,
            reading_progress=100 if covered else 60,
        )

    def delete_note(self, note_id: int) -> bool:
        """Delete a note by ID."""
        deleted_count, _ = Note.objects.filter(pk=note_id).delete()
        if not deleted_count:
            raise NoteValidationError(f"Note with ID {note_id} does not exist.")
        return True

    def filter_and_sort_notes(
        self,
        subject: Optional[str] = None,
        covered: Optional[str] = None,
        search: Optional[str] = None,
        sort_by: str = "updated_desc",
    ) -> List[Note]:
        """
        Query notes using Django ORM filters and sort them using Python lambda functions.
        """
        queryset = Note.objects.select_related("subject").all()

        if subject and subject.lower() not in ("all", ""):
            queryset = queryset.filter(
                Q(subject__name__iexact=subject) | Q(subject__slug__iexact=subject)
            )

        if covered is not None and str(covered).lower() not in ("all", ""):
            if str(covered).lower() in ("true", "1", "covered", "yes"):
                queryset = queryset.filter(covered=True)
            elif str(covered).lower() in ("false", "0", "uncovered", "pending", "not_covered", "no"):
                queryset = queryset.filter(covered=False)

        if search and search.strip():
            term = search.strip()
            queryset = queryset.filter(
                Q(title__icontains=term)
                | Q(content__icontains=term)
                | Q(topic__icontains=term)
                | Q(subject__name__icontains=term)
            )

        notes_list = list(queryset)
        sort_key = self.SORT_STRATEGIES.get(sort_by, self.SORT_STRATEGIES["updated_desc"])
        reverse_flag = sort_by in ("title_desc", "date_newest", "updated_desc", "length_desc")
        return sorted(notes_list, key=sort_key, reverse=reverse_flag)

    def get_adjacent_notes(self, current_note: Note) -> Tuple[Optional[Note], Optional[Note]]:
        """
        Return (previous_note, next_note) within the same subject (or across all notes)
        for seamless navigation on the Note Reading page.
        """
        subject_notes = list(
            Note.objects.select_related("subject")
            .filter(subject=current_note.subject)
            .order_by("created_at", "id")
        )
        if len(subject_notes) <= 1:
            subject_notes = list(
                Note.objects.select_related("subject").all().order_by("subject__name", "created_at", "id")
            )

        ids = [n.id for n in subject_notes]
        if current_note.id not in ids:
            return None, None

        idx = ids.index(current_note.id)
        prev_note = subject_notes[idx - 1] if idx > 0 else None
        next_note = subject_notes[idx + 1] if idx < len(subject_notes) - 1 else None
        return prev_note, next_note

    def get_continue_studying_note(self) -> Optional[Note]:
        """
        Select the best 'Continue Studying' note for the dashboard:
        prefers the most recently updated uncovered note, or falls back to the latest note.
        """
        uncovered_note = (
            Note.objects.select_related("subject")
            .filter(covered=False)
            .order_by("-updated_at")
            .first()
        )
        if uncovered_note:
            return uncovered_note
        return Note.objects.select_related("subject").order_by("-updated_at").first()

    @staticmethod
    def stream_notes_for_export(notes_iterable: Optional[Iterable[Note]] = None) -> Generator[Dict[str, str], None, None]:
        """
        Generator function using `yield` to lazily stream note dictionaries one at a time.
        Used by TXT and CSV export features to avoid loading large formatted strings into memory at once.
        """
        source = (
            notes_iterable
            if notes_iterable is not None
            else Note.objects.select_related("subject").all().iterator(chunk_size=50)
        )
        for note in source:
            yield {
                "id": str(note.id),
                "subject": note.subject.name if note.subject_id else "Other",
                "topic": note.topic,
                "title": note.title,
                "content": note.content,
                "status": "Covered" if note.covered else "Not Covered",
                "reading_progress": f"{note.reading_progress}%",
                "created_date": note.created_at.strftime("%Y-%m-%d %H:%M") if note.created_at else "",
                "updated_date": note.updated_at.strftime("%Y-%m-%d %H:%M") if note.updated_at else "",
            }
