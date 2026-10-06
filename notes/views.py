"""
Django Template Views for all 9 navigation sections of Notes Manager:
1. Home (Dashboard)
2. Notes (Subject tabs, Covered/Not Covered tabs, Search, Sort, Filter, CRUD)
3. Note Reading Experience (Previous/Next note, Progress, End-of-note Mark as Covered prompt)
4. Quiz (PDF Drag-and-Drop Upload, Interactive Question Stepper, Results & History)
5. Tasks (Today, Upcoming, Completed sections, '3 of 5 tasks completed' progress bar)
6. Progress (Notes/Quiz/Task Progress, Overall Formula, Consistency Heatmap & Streak, SMTP Report)
7. Analytics (NumPy arrays, SciPy linear regression & Z-scores, Matplotlib charts)
8. Knowledge Map (NetworkX Subject -> Topic -> Note interactive graph & hierarchy)
9. Resources & Settings (TXT/CSV exports, Resource library, FTP transfer, Socket & SMTP status)
"""
import json
from django.conf import settings
from django.shortcuts import get_object_or_404, render

from analytics.services import AnalyticsManager
from files.models import StudyResource
from files.services import FileManager
from networking.models import NetworkActivityLog
from networking.services import FTPResourceService, StudySocketService
from notes.models import Note, Subject
from notes.seed import ensure_initial_demo_data
from notes.services import NoteManager
from progress.services import ProgressTracker
from quizzes.models import Quiz
from quizzes.services import QuizManager
from tasks.services import TaskManager


def _base_context(active_page: str) -> dict:
    """Build shared navigation, progress, and socket status context for all templates."""
    ensure_initial_demo_data()
    progress = ProgressTracker.calculate_progress_metrics(update_today_log=False)
    socket_info = StudySocketService.check_status()
    return {
        "active_page": active_page,
        "global_progress": progress,
        "socket_info": socket_info,
        "subjects_nav": Subject.objects.all(),
    }


def dashboard_view(request):
    """Part 5 — Home Page / Dashboard."""
    ctx = _base_context("home")
    note_mgr = NoteManager()
    task_mgr = TaskManager()

    continue_note = note_mgr.get_continue_studying_note()
    task_data = task_mgr.get_categorized_tasks()
    recent_notes = Note.objects.select_related("subject").all()[:5]
    recent_quizzes = Quiz.objects.all()[:4]

    ctx.update(
        {
            "continue_note": continue_note,
            "task_data": task_data,
            "recent_notes": recent_notes,
            "recent_quizzes": recent_quizzes,
        }
    )
    return render(request, "dashboard.html", ctx)


def notes_list_view(request):
    """Part 6 — Notes Management (Subjects, Covered/Not Covered Tabs, Search, Sort, Filter)."""
    ctx = _base_context("notes")
    note_mgr = NoteManager(auto_seed=True)

    selected_subject = request.GET.get("subject", "all")
    selected_tab = request.GET.get("tab", "all")  # all | covered | uncovered
    search_query = request.GET.get("q", "").strip()
    sort_by = request.GET.get("sort", "updated_desc")

    covered_filter = None
    if selected_tab == "covered":
        covered_filter = "true"
    elif selected_tab in ("uncovered", "not_covered", "pending"):
        covered_filter = "false"

    filtered_notes = note_mgr.filter_and_sort_notes(
        subject=selected_subject,
        covered=covered_filter,
        search=search_query,
        sort_by=sort_by,
    )
    all_subject_notes = note_mgr.filter_and_sort_notes(
        subject=selected_subject,
        search=search_query,
        sort_by=sort_by,
    )
    covered_notes = [n for n in all_subject_notes if n.covered]
    uncovered_notes = [n for n in all_subject_notes if not n.covered]

    subjects_with_counts = []
    for s in Subject.objects.prefetch_related("notes").all():
        s_notes = list(s.notes.all())
        subjects_with_counts.append(
            {
                "id": s.id,
                "name": s.name,
                "slug": s.slug,
                "description": s.description,
                "is_custom": s.is_custom,
                "total": len(s_notes),
                "covered": sum(1 for n in s_notes if n.covered),
                "uncovered": sum(1 for n in s_notes if not n.covered),
            }
        )

    ctx.update(
        {
            "subjects": subjects_with_counts,
            "selected_subject": selected_subject,
            "selected_tab": selected_tab,
            "search_query": search_query,
            "sort_by": sort_by,
            "notes": filtered_notes,
            "covered_notes": covered_notes,
            "uncovered_notes": uncovered_notes,
            "total_filtered": len(all_subject_notes),
            "covered_count": len(covered_notes),
            "uncovered_count": len(uncovered_notes),
        }
    )
    return render(request, "notes.html", ctx)


def note_reading_view(request, pk: int):
    """Part 7 — Note Reading Experience with Previous/Next navigation and Mark as Covered prompt."""
    ctx = _base_context("notes")
    note_mgr = NoteManager()
    note = get_object_or_404(Note.objects.select_related("subject"), pk=pk)
    prev_note, next_note = note_mgr.get_adjacent_notes(note)

    subject_notes = list(
        Note.objects.filter(subject=note.subject).order_by("created_at", "id")
    )
    subject_total = len(subject_notes)
    subject_covered = sum(1 for n in subject_notes if n.covered)
    subject_progress = round((subject_covered / subject_total) * 100, 1) if subject_total > 0 else 0.0

    paragraphs = [p.strip() for p in (note.content or "").split("\n\n") if p.strip()]

    ctx.update(
        {
            "note": note,
            "paragraphs": paragraphs,
            "previous_note": prev_note,
            "next_note": next_note,
            "subject_notes": subject_notes,
            "subject_progress": subject_progress,
        }
    )
    return render(request, "note_detail.html", ctx)


def quiz_view(request):
    """Part 9 — Quiz System (PDF Drag-and-Drop Upload, Interactive Quiz Runner, Quiz History)."""
    ctx = _base_context("quiz")
    sort_by = request.GET.get("sort", "date_desc")
    quizzes = QuizManager.get_sorted_quizzes(sort_by=sort_by)

    active_quiz_id = request.GET.get("take")
    active_quiz = None
    if active_quiz_id and str(active_quiz_id).isdigit():
        active_quiz = Quiz.objects.prefetch_related("questions").filter(pk=int(active_quiz_id)).first()
    if active_quiz is None and quizzes:
        active_quiz = Quiz.objects.prefetch_related("questions").filter(pk=quizzes[0].id).first()

    active_questions_json = "[]"
    if active_quiz:
        q_list = [
            {
                "id": q.id,
                "question_number": q.question_number,
                "question": q.question,
                "option_a": q.option_a,
                "option_b": q.option_b,
                "option_c": q.option_c,
                "option_d": q.option_d,
                "correct_answer": q.correct_answer,
                "user_answer": q.user_answer,
                "explanation": q.explanation,
            }
            for q in active_quiz.questions.all()
        ]
        active_questions_json = json.dumps(q_list)

    ctx.update(
        {
            "quizzes": quizzes,
            "sort_by": sort_by,
            "active_quiz": active_quiz,
            "active_questions_json": active_questions_json,
            "api_configured": bool(getattr(settings, "QUIZ_API_KEY", "")),
        }
    )
    return render(request, "quiz.html", ctx)


def tasks_view(request):
    """Part 11 — Daily Tasks (Today, Upcoming, Completed sections & progress bar)."""
    ctx = _base_context("tasks")
    task_mgr = TaskManager()
    categorized = task_mgr.get_categorized_tasks()
    ctx.update({"task_data": categorized})
    return render(request, "tasks.html", ctx)


def progress_view(request):
    """Part 12 & Part 13 — Consistency Tracker, Three-Pillar Progress Tracker, & SMTP Report."""
    ctx = _base_context("progress")
    progress_metrics = ProgressTracker.calculate_progress_metrics()
    ctx.update(
        {
            "progress": progress_metrics,
            "consistency": progress_metrics["consistency"],
        }
    )
    return render(request, "progress.html", ctx)


def analytics_view(request):
    """Part 14, 15, 16 — NumPy, SciPy & Matplotlib Study Analytics."""
    ctx = _base_context("analytics")
    analytics_payload = AnalyticsManager.get_full_analytics_payload(include_charts=True)
    ctx.update(analytics_payload)
    return render(request, "analytics.html", ctx)


def knowledge_map_view(request):
    """Part 17 — NetworkX Knowledge Map Visualization (Subjects -> Topics -> Notes)."""
    ctx = _base_context("knowledge_map")
    km_data = AnalyticsManager.get_knowledge_map_data()
    km_chart = AnalyticsManager.generate_networkx_chart()
    ctx.update(
        {
            "knowledge_map": km_data,
            "knowledge_map_json": json.dumps(km_data),
            "knowledge_map_chart": km_chart,
        }
    )
    return render(request, "knowledge_map.html", ctx)


def resources_view(request):
    """Part 18, 19, 25, 27 — TXT/CSV Export, Resources Library, and FTP Resource Transfer."""
    ctx = _base_context("resources")
    # Ensure initial exported TXT and CSV files exist in StudyResource library for immediate demo
    if not StudyResource.objects.filter(filename="notes.txt").exists():
        FileManager.generate_notes_txt_content(save_to_resources=True)
    if not StudyResource.objects.filter(filename="notes.csv").exists():
        FileManager.generate_csv_content("notes", save_to_resources=True)
    if not StudyResource.objects.filter(filename="quiz_results.csv").exists():
        FileManager.generate_csv_content("quiz_results", save_to_resources=True)
    if not StudyResource.objects.filter(filename="tasks.csv").exists():
        FileManager.generate_csv_content("tasks", save_to_resources=True)

    filter_type = request.GET.get("type", "ALL").upper()
    resources_qs = StudyResource.objects.all()
    if filter_type in ("PDF", "TXT", "CSV", "OTHER"):
        resources_qs = resources_qs.filter(file_type=filter_type)

    ftp_service = FTPResourceService()
    try:
        ftp_info = ftp_service.list_files()
    except Exception as exc:
        ftp_info = {"connected": False, "mode": "Error", "error": str(exc), "files": []}

    transfer_logs = NetworkActivityLog.objects.filter(
        protocol=NetworkActivityLog.PROTOCOL_FTP
    )[:8]

    ctx.update(
        {
            "resources": resources_qs,
            "filter_type": filter_type,
            "ftp_info": ftp_info,
            "transfer_logs": transfer_logs,
        }
    )
    return render(request, "resources.html", ctx)


def settings_view(request):
    """Part 23, 24, 25, 28 — Settings, Networking Telemetry (Socket, SMTP, FTP) & Viva Reference."""
    ctx = _base_context("settings")
    ftp_service = FTPResourceService()
    try:
        ftp_info = ftp_service.list_files()
    except Exception as exc:
        ftp_info = {"connected": False, "mode": "Offline", "error": str(exc), "files": []}

    recent_network_logs = NetworkActivityLog.objects.all()[:10]

    ctx.update(
        {
            "ftp_info": ftp_info,
            "network_logs": recent_network_logs,
            "config_summary": {
                "api_url": getattr(settings, "QUIZ_API_URL", ""),
                "api_key_configured": bool(getattr(settings, "QUIZ_API_KEY", "")),
                "smtp_host": f"{getattr(settings, 'EMAIL_HOST', '')}:{getattr(settings, 'EMAIL_PORT', 587)}",
                "smtp_credentials_configured": bool(
                    getattr(settings, "EMAIL_HOST_USER", "") and getattr(settings, "EMAIL_HOST_PASSWORD", "")
                ),
                "ftp_endpoint": f"{getattr(settings, 'FTP_HOST', '127.0.0.1')}:{getattr(settings, 'FTP_PORT', 2121)}",
                "ftp_mock_mode": getattr(settings, "FTP_MOCK_MODE", True),
            },
        }
    )
    return render(request, "settings.html", ctx)
