from django.contrib import admin
from .models import Quiz, Question


class QuestionInline(admin.TabularInline):
    model = Question
    extra = 0


@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = ("title", "subject", "score", "total_questions", "percentage", "completed", "created_at")
    list_filter = ("completed", "subject")
    search_fields = ("title", "subject", "source_pdf_name")
    inlines = [QuestionInline]


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ("quiz", "question_number", "question", "correct_answer", "user_answer")
    list_filter = ("correct_answer",)
