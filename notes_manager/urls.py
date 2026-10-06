"""
URL Configuration for notes_manager project.
Maps both HTML page routes and REST API endpoints (/api/...).
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path
from notes import api_views, views

urlpatterns = [
    path("admin/", admin.site.urls),

    # --- Frontend Page Routes (Part 28) ---
    path("", views.dashboard_view, name="home"),
    path("notes/", views.notes_list_view, name="notes"),
    path("notes/<int:pk>/", views.note_reading_view, name="note_detail"),
    path("quiz/", views.quiz_view, name="quiz"),
    path("tasks/", views.tasks_view, name="tasks"),
    path("progress/", views.progress_view, name="progress"),
    path("analytics/", views.analytics_view, name="analytics"),
    path("knowledge-map/", views.knowledge_map_view, name="knowledge_map"),
    path("resources/", views.resources_view, name="resources"),
    path("settings/", views.settings_view, name="settings"),

    # --- File Export & Download Routes (Part 18, 19, 27) ---
    path("files/export/notes.txt", api_views.export_notes_txt_view, name="export_notes_txt"),
    path("files/export/<str:export_type>.csv", api_views.export_csv_view, name="export_csv"),
    path("files/download/<int:pk>/", api_views.download_resource_view, name="download_resource"),

    # --- REST API Endpoints (Part 30) ---
    path("api/subjects/", api_views.api_subjects_list_create, name="api_subjects"),
    path("api/notes/", api_views.api_notes_list_create, name="api_notes"),
    path("api/notes/<int:pk>/", api_views.api_note_detail, name="api_note_detail"),
    path("api/tasks/", api_views.api_tasks_list_create, name="api_tasks"),
    path("api/tasks/<int:pk>/", api_views.api_task_detail, name="api_task_detail"),
    path("api/quizzes/", api_views.api_quizzes_list, name="api_quizzes"),
    path("api/quizzes/<int:pk>/", api_views.api_quiz_detail, name="api_quiz_detail"),
    path("api/quiz/generate/", api_views.api_quiz_generate, name="api_quiz_generate"),
    path("api/quiz/submit/", api_views.api_quiz_submit, name="api_quiz_submit"),
    path("api/progress/", api_views.api_progress_summary, name="api_progress"),
    path("api/analytics/", api_views.api_analytics_summary, name="api_analytics"),
    path("api/knowledge-map/", api_views.api_knowledge_map, name="api_knowledge_map"),
    path("api/email/report/", api_views.api_send_email_report, name="api_email_report"),
    path("api/socket/status/", api_views.api_socket_status, name="api_socket_status"),
    path("api/ftp/files/", api_views.api_ftp_files, name="api_ftp_files"),
    path("api/ftp/download/<str:filename>/", api_views.api_ftp_download, name="api_ftp_download"),
    path("api/resources/", api_views.api_resources_list_upload, name="api_resources"),
    path("api/resources/<int:pk>/", api_views.api_resource_delete, name="api_resource_delete"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
