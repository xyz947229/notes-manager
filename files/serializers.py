"""DRF Serializer for StudyResource."""
from rest_framework import serializers
from .models import StudyResource


class StudyResourceSerializer(serializers.ModelSerializer):
    formatted_size = serializers.CharField(read_only=True)
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = StudyResource
        fields = [
            "id",
            "title",
            "filename",
            "file_type",
            "file_size",
            "formatted_size",
            "subject",
            "file_url",
            "uploaded_at",
        ]

    def get_file_url(self, obj: StudyResource) -> str:
        try:
            return obj.file.url if obj.file else ""
        except ValueError:
            return ""
