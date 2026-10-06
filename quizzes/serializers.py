"""DRF Serializers for Quiz and Question models."""
from rest_framework import serializers
from .models import Question, Quiz


class QuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Question
        fields = [
            "id",
            "question_number",
            "question",
            "option_a",
            "option_b",
            "option_c",
            "option_d",
            "correct_answer",
            "user_answer",
            "explanation",
        ]


class QuizSerializer(serializers.ModelSerializer):
    questions = QuestionSerializer(many=True, read_only=True)

    class Meta:
        model = Quiz
        fields = [
            "id",
            "title",
            "subject",
            "source_pdf_name",
            "score",
            "total_questions",
            "correct_answers",
            "incorrect_answers",
            "percentage",
            "time_taken_seconds",
            "completed",
            "created_at",
            "questions",
        ]
