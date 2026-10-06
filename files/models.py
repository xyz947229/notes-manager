"""
Database model for Study Resources (Part 27: Resources page).
Stores metadata for uploaded and generated PDF, TXT, and CSV files.
"""
from django.db import models


class StudyResource(models.Model):
    """Represents a file in the Resources library (PDF, TXT, CSV, or study document)."""

    TYPE_PDF = "PDF"
    TYPE_TXT = "TXT"
    TYPE_CSV = "CSV"
    TYPE_OTHER = "OTHER"

    FILE_TYPE_CHOICES = [
        (TYPE_PDF, "PDF Document"),
        (TYPE_TXT, "Text File"),
        (TYPE_CSV, "CSV Spreadsheet"),
        (TYPE_OTHER, "Study Resource"),
    ]

    title = models.CharField(max_length=200)
    file = models.FileField(upload_to="resources/")
    filename = models.CharField(max_length=255)
    file_type = models.CharField(max_length=20, choices=FILE_TYPE_CHOICES, default=TYPE_PDF)
    file_size = models.PositiveIntegerField(default=0, help_text="File size in bytes")
    subject = models.CharField(max_length=100, default="Python")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-uploaded_at"]

    @property
    def formatted_size(self) -> str:
        size = float(self.file_size or 0)
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024.0 or unit == "GB":
                return f"{size:.1f} {unit}" if unit != "B" else f"{int(size)} B"
            size /= 1024.0
        return f"{int(self.file_size)} B"

    def __str__(self) -> str:
        return f"{self.filename} ({self.file_type}, {self.formatted_size})"
