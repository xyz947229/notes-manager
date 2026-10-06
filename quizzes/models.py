"""
Database models for the Quizzes application.
Includes QUIZ and QUESTION models per Part 8 specification.
"""
from django.db import models


class Quiz(models.Model):
    """
    Represents a generated quiz from an uploaded PDF or study note.
    Required fields per specification:
    - id, title, subject, score, total_questions, created_at
    Plus percentage, correct/incorrect counts, source_pdf_name, time_taken_seconds, completed.
    """

    title = models.CharField(max_length=220)
    subject = models.CharField(max_length=100, default="Python")
    source_pdf_name = models.CharField(max_length=255, blank=True, default="")
    score = models.IntegerField(default=0)
    total_questions = models.PositiveIntegerField(default=5)
    correct_answers = models.PositiveIntegerField(default=0)
    incorrect_answers = models.PositiveIntegerField(default=0)
    percentage = models.FloatField(default=0.0)
    time_taken_seconds = models.PositiveIntegerField(default=0)
    completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name_plural = "Quizzes"

    def __str__(self) -> str:
        return f"{self.title} ({self.subject}) - {self.score}/{self.total_questions} ({self.percentage:.1f}%)"


class Question(models.Model):
    """
    Represents a multiple-choice question belonging to a Quiz.
    Required fields per specification:
    - id, quiz, question, option_a, option_b, option_c, option_d, correct_answer
    """

    ANSWER_CHOICES = [
        ("A", "Option A"),
        ("B", "Option B"),
        ("C", "Option C"),
        ("D", "Option D"),
    ]

    quiz = models.ForeignKey(
        Quiz,
        on_delete=models.CASCADE,
        related_name="questions",
    )
    question_number = models.PositiveIntegerField(default=1)
    question = models.TextField()
    option_a = models.CharField(max_length=350)
    option_b = models.CharField(max_length=350)
    option_c = models.CharField(max_length=350)
    option_d = models.CharField(max_length=350)
    correct_answer = models.CharField(max_length=1, choices=ANSWER_CHOICES, default="A")
    user_answer = models.CharField(max_length=1, blank=True, default="")
    explanation = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["question_number", "id"]

    def __str__(self) -> str:
        return f"Q{self.question_number}: {self.question[:60]}"
