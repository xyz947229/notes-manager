"""DRF Serializers for Notes and Subjects."""
from rest_framework import serializers
from .models import Note, Subject


class SubjectSerializer(serializers.ModelSerializer):
    total_notes = serializers.SerializerMethodField()
    covered_notes = serializers.SerializerMethodField()
    pending_notes = serializers.SerializerMethodField()

    class Meta:
        model = Subject
        fields = [
            "id",
            "name",
            "slug",
            "description",
            "is_custom",
            "total_notes",
            "covered_notes",
            "pending_notes",
            "created_at",
        ]

    def get_total_notes(self, obj: Subject) -> int:
        return obj.notes.count()

    def get_covered_notes(self, obj: Subject) -> int:
        return obj.notes.filter(covered=True).count()

    def get_pending_notes(self, obj: Subject) -> int:
        return obj.notes.filter(covered=False).count()


class NoteSerializer(serializers.ModelSerializer):
    subject_name = serializers.CharField(source="subject.name", read_only=True)
    word_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Note
        fields = [
            "id",
            "title",
            "subject",
            "subject_name",
            "topic",
            "content",
            "covered",
            "reading_progress",
            "word_count",
            "created_at",
            "updated_at",
        ]
        extra_kwargs = {
            "subject": {"required": False},
        }
