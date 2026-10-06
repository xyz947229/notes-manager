"""
Database models for the Notes application.
Demonstrates Django ORM relationships, validation, and model methods.
"""
from django.db import models
from django.utils.text import slugify


class Subject(models.Model):
    """Represents an academic subject (default or user-created)."""

    DEFAULT_SUBJECTS = [
        ("Python", "Core Python programming, OOP, functional tools, and scientific libraries"),
        ("DSA", "Data Structures and Algorithms, complexity analysis, trees, and graphs"),
        ("DBMS", "Database Management Systems, SQL, normalization, and ACID transactions"),
        ("Computer Organization", "Instruction sets, pipelining, memory hierarchy, and CPU design"),
        ("Java", "Object-oriented programming in Java, JVM architecture, and collections"),
        ("Mathematics", "Linear algebra, probability, statistics, and discrete structures"),
        ("Other", "General academic notes, seminars, and interdisciplinary topics"),
    ]

    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    description = models.TextField(blank=True, default="")
    is_custom = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name) or "subject"
            slug_candidate = base_slug
            counter = 1
            while Subject.objects.filter(slug=slug_candidate).exclude(pk=self.pk).exists():
                slug_candidate = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug_candidate
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name


class Note(models.Model):
    """
    Represents a student study note belonging to a Subject.
    Required fields per specification:
    - id, title, subject, content, covered, created_at, updated_at
    Plus topic and reading_progress for Knowledge Map and Continue Studying features.
    """

    title = models.CharField(max_length=200)
    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name="notes",
    )
    topic = models.CharField(
        max_length=120,
        default="Core Concepts",
        help_text="Sub-topic node used to build the NetworkX Knowledge Map.",
    )
    content = models.TextField()
    covered = models.BooleanField(default=False)
    reading_progress = models.PositiveSmallIntegerField(
        default=20,
        help_text="Reading progress percentage (0-100).",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at", "-created_at"]

    @property
    def subject_name(self) -> str:
        return self.subject.name if self.subject_id else "Other"

    @property
    def word_count(self) -> int:
        return len((self.content or "").split())

    def __str__(self) -> str:
        status = "Covered" if self.covered else "Pending"
        return f"[{self.subject_name}] {self.title} ({status})"
