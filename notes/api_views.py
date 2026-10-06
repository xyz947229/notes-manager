"""
REST API Views using Django REST Framework (Part 30).
Provides clean JSON endpoints with full exception handling and friendly error messages.
"""
from pathlib import Path
from django.http import FileResponse, HttpResponse, StreamingHttpResponse
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from analytics.services import AnalyticsManager
from files.models import StudyResource
from files.serializers import StudyResourceSerializer
from files.services import FileHandlingError, FileManager
from networking.services import (
    EmailReportError,
    FTPResourceService,
    FTPTransferError,
    SMTPReportService,
    StudySocketService,
)
from notes.models import Note, Subject
from notes.seed import build_minimal_searchable_pdf
from notes.serializers import NoteSerializer, SubjectSerializer
from notes.services import NoteManager, NoteValidationError
from progress.services import ProgressTracker
from quizzes.models import Quiz
from quizzes.serializers import QuizSerializer
from quizzes.services import (
    ExternalAPIError,
    PDFExtractionError,
    QuizManager,
    QuizValidationError,
)
from tasks.models import Task
from tasks.serializers import TaskSerializer
from tasks.services import TaskManager, TaskValidationError


# ==========================================================
# NOTES & SUBJECTS API (/api/notes/, /api/subjects/)
# ==========================================================
@api_view(["GET", "POST"])
def api_subjects_list_create(request):
    note_mgr = NoteManager(auto_seed=True)
    if request.method == "GET":
        subjects = Subject.objects.all()
        serializer = SubjectSerializer(subjects, many=True)
        return Response({"status": "success", "subjects": serializer.data})

    try:
        subject = note_mgr.add_subject(
            name=request.data.get("name", ""),
            description=request.data.get("description", ""),
        )
        return Response(
            {"status": "success", "subject": SubjectSerializer(subject).data},
            status=status.HTTP_201_CREATED,
        )
    except NoteValidationError as exc:
        return Response({"status": "error", "message": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET", "POST"])
def api_notes_list_create(request):
    note_mgr = NoteManager(auto_seed=True)
    if request.method == "GET":
        subject = request.query_params.get("subject")
        covered = request.query_params.get("covered")
        search = request.query_params.get("search")
        sort_by = request.query_params.get("sort", "updated_desc")

        notes = note_mgr.filter_and_sort_notes(
            subject=subject,
            covered=covered,
            search=search,
            sort_by=sort_by,
        )
        return Response(
            {
                "status": "success",
                "count": len(notes),
                "notes": NoteSerializer(notes, many=True).data,
            }
        )

    try:
        subj_input = (
            request.data.get("subject_name")
            or request.data.get("subject")
            or "Python"
        )
        if isinstance(subj_input, int) or (isinstance(subj_input, str) and subj_input.isdigit()):
            subj_obj = Subject.objects.filter(pk=int(subj_input)).first()
            subj_name = subj_obj.name if subj_obj else "Python"
        else:
            subj_name = str(subj_input)

        raw_cov = request.data.get("covered", False)
        covered_bool = (
            raw_cov.lower() in ("true", "1", "yes")
            if isinstance(raw_cov, str)
            else bool(raw_cov)
        )

        note = note_mgr.create_note(
            title=request.data.get("title", ""),
            subject_name=subj_name,
            topic=request.data.get("topic", "Core Concepts"),
            content=request.data.get("content", ""),
            covered=covered_bool,
            reading_progress=request.data.get("reading_progress"),
        )
        ProgressTracker.record_study_activity(
            notes_delta=1 if note.covered else 0,
            minutes_delta=15,
        )
        return Response(
            {
                "status": "success",
                "message": "Note created successfully.",
                "note": NoteSerializer(note).data,
            },
            status=status.HTTP_201_CREATED,
        )
    except NoteValidationError as exc:
        return Response({"status": "error", "message": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET", "PUT", "PATCH", "DELETE"])
def api_note_detail(request, pk: int):
    note_mgr = NoteManager()
    if request.method == "GET":
        try:
            note = Note.objects.select_related("subject").get(pk=pk)
            prev_note, next_note = note_mgr.get_adjacent_notes(note)
            data = NoteSerializer(note).data
            data["previous_note_id"] = prev_note.id if prev_note else None
            data["next_note_id"] = next_note.id if next_note else None
            return Response({"status": "success", "note": data})
        except Note.DoesNotExist:
            return Response(
                {"status": "error", "message": f"Note with ID {pk} not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

    if request.method in ("PUT", "PATCH"):
        try:
            was_covered = Note.objects.filter(pk=pk, covered=True).exists()
            note = note_mgr.update_note(pk, **request.data)
            if note.covered and not was_covered:
                ProgressTracker.record_study_activity(notes_delta=1, minutes_delta=20)
            progress = ProgressTracker.calculate_progress_metrics()
            return Response(
                {
                    "status": "success",
                    "message": "Note updated successfully.",
                    "note": NoteSerializer(note).data,
                    "notes_progress": progress["notes_progress"],
                    "overall_progress": progress["overall_progress"],
                }
            )
        except NoteValidationError as exc:
            code = status.HTTP_404_NOT_FOUND if "not found" in str(exc).lower() else status.HTTP_400_BAD_REQUEST
            return Response({"status": "error", "message": str(exc)}, status=code)

    # DELETE
    try:
        note_mgr.delete_note(pk)
        return Response({"status": "success", "message": "Note deleted successfully."})
    except NoteValidationError as exc:
        return Response({"status": "error", "message": str(exc)}, status=status.HTTP_404_NOT_FOUND)


# ==========================================================
# DAILY TASKS API (/api/tasks/, /api/tasks/<id>/)
# ==========================================================
@api_view(["GET", "POST"])
def api_tasks_list_create(request):
    task_mgr = TaskManager()
    if request.method == "GET":
        categorized = task_mgr.get_categorized_tasks()
        return Response(
            {
                "status": "success",
                "summary_text": categorized["summary_text"],
                "progress_percentage": categorized["progress_percentage"],
                "total_count": categorized["total_count"],
                "completed_count": categorized["completed_count"],
                "pending_count": categorized["pending_count"],
                "today_tasks": TaskSerializer(categorized["today_tasks"], many=True).data,
                "upcoming_tasks": TaskSerializer(categorized["upcoming_tasks"], many=True).data,
                "completed_tasks": TaskSerializer(categorized["completed_tasks"], many=True).data,
                "tasks": TaskSerializer(categorized["all_tasks"], many=True).data,
            }
        )

    try:
        task = task_mgr.create_task(
            title=request.data.get("title", ""),
            description=request.data.get("description", ""),
            subject=request.data.get("subject", "Python"),
            priority=request.data.get("priority", Task.PRIORITY_MEDIUM),
            due_date=request.data.get("due_date"),
            completed=request.data.get("completed", False),
        )
        categorized = task_mgr.get_categorized_tasks()
        return Response(
            {
                "status": "success",
                "message": "Task created successfully.",
                "task": TaskSerializer(task).data,
                "summary_text": categorized["summary_text"],
                "progress_percentage": categorized["progress_percentage"],
            },
            status=status.HTTP_201_CREATED,
        )
    except TaskValidationError as exc:
        return Response({"status": "error", "message": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET", "PUT", "PATCH", "DELETE"])
def api_task_detail(request, pk: int):
    task_mgr = TaskManager()
    if request.method == "GET":
        try:
            task = Task.objects.get(pk=pk)
            return Response({"status": "success", "task": TaskSerializer(task).data})
        except Task.DoesNotExist:
            return Response(
                {"status": "error", "message": f"Task with ID {pk} not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

    if request.method in ("PUT", "PATCH"):
        try:
            was_done = Task.objects.filter(pk=pk, completed=True).exists()
            task = task_mgr.update_task(pk, **request.data)
            if task.completed and not was_done:
                ProgressTracker.record_study_activity(tasks_delta=1, minutes_delta=15)
            categorized = task_mgr.get_categorized_tasks()
            progress = ProgressTracker.calculate_progress_metrics()
            return Response(
                {
                    "status": "success",
                    "message": "Task updated successfully.",
                    "task": TaskSerializer(task).data,
                    "summary_text": categorized["summary_text"],
                    "progress_percentage": categorized["progress_percentage"],
                    "overall_progress": progress["overall_progress"],
                }
            )
        except TaskValidationError as exc:
            code = status.HTTP_404_NOT_FOUND if "not found" in str(exc).lower() else status.HTTP_400_BAD_REQUEST
            return Response({"status": "error", "message": str(exc)}, status=code)

    try:
        task_mgr.delete_task(pk)
        categorized = task_mgr.get_categorized_tasks()
        return Response(
            {
                "status": "success",
                "message": "Task deleted successfully.",
                "summary_text": categorized["summary_text"],
                "progress_percentage": categorized["progress_percentage"],
            }
        )
    except TaskValidationError as exc:
        return Response({"status": "error", "message": str(exc)}, status=status.HTTP_404_NOT_FOUND)


# ==========================================================
# QUIZZES API (/api/quizzes/, /api/quiz/generate/, /api/quiz/submit/)
# ==========================================================
@api_view(["GET"])
def api_quizzes_list(request):
    sort_by = request.query_params.get("sort", "date_desc")
    quizzes = QuizManager.get_sorted_quizzes(sort_by=sort_by)
    return Response(
        {
            "status": "success",
            "count": len(quizzes),
            "quizzes": QuizSerializer(quizzes, many=True).data,
        }
    )


@api_view(["GET"])
def api_quiz_detail(request, pk: int):
    try:
        quiz = Quiz.objects.prefetch_related("questions").get(pk=pk)
        return Response({"status": "success", "quiz": QuizSerializer(quiz).data})
    except Quiz.DoesNotExist:
        return Response(
            {"status": "error", "message": f"Quiz with ID {pk} not found."},
            status=status.HTTP_404_NOT_FOUND,
        )


@api_view(["POST"])
def api_quiz_generate(request):
    """
    Generate a new quiz from an uploaded PDF file (or sample PDF / study note text).
    Follows: PDF -> Django View -> PDFExtractor -> APIService -> Validation -> Database -> Frontend.
    """
    quiz_mgr = QuizManager()
    pdf_file = request.FILES.get("pdf_file") or request.FILES.get("file")
    subject = request.data.get("subject", "Python")
    title = request.data.get("title", "")
    try:
        num_questions = max(1, min(15, int(request.data.get("num_questions", 5))))
    except (TypeError, ValueError):
        num_questions = 5

    try:
        if pdf_file is not None:
            # Also archive uploaded PDF into StudyResource library for the Resources page
            try:
                FileManager.save_uploaded_resource(pdf_file, title=title, subject=subject)
                pdf_file.seek(0)
            except Exception:
                pdf_file.seek(0)

            quiz = quiz_mgr.create_quiz_from_pdf(
                pdf_file=pdf_file,
                title=title,
                subject=subject,
                num_questions=num_questions,
            )
        elif str(request.data.get("use_sample_pdf", "")).lower() in ("true", "1", "yes"):
            import io
            sample_bytes = build_minimal_searchable_pdf(
                [
                    f"{subject} College Study Guide and Viva Reference",
                    "Object-Oriented Programming encapsulates state and behavior inside reusable classes.",
                    "Lambda functions define concise anonymous single-expression functions for sorting.",
                    "Generators use the yield keyword to stream large datasets one item at a time.",
                    "NumPy and SciPy enable vectorized numerical arrays and linear regression statistics.",
                    "NetworkX constructs directed graphs linking Subjects, Topics, and Study Notes.",
                ]
            )
            fake_pdf = io.BytesIO(sample_bytes)
            fake_pdf.name = f"sample_{subject.lower().replace(' ', '_')}_notes.pdf"
            fake_pdf.size = len(sample_bytes)
            quiz = quiz_mgr.create_quiz_from_pdf(
                pdf_file=fake_pdf,
                title=title or f"{subject} Sample PDF Quiz",
                subject=subject,
                num_questions=num_questions,
            )
        else:
            raise PDFExtractionError("Please upload a valid .pdf file to generate a quiz.")

        return Response(
            {
                "status": "success",
                "message": f"Generated {quiz.total_questions} questions from PDF.",
                "quiz": QuizSerializer(quiz).data,
            },
            status=status.HTTP_201_CREATED,
        )
    except (PDFExtractionError, QuizValidationError, ExternalAPIError) as exc:
        return Response({"status": "error", "message": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
def api_quiz_submit(request):
    """Submit answers for a quiz, calculate score & percentage, and update database."""
    quiz_mgr = QuizManager()
    quiz_id = request.data.get("quiz_id")
    answers = request.data.get("answers", {})
    time_taken = request.data.get("time_taken_seconds", 0)

    if not quiz_id:
        return Response(
            {"status": "error", "message": "quiz_id is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        result = quiz_mgr.submit_quiz(
            quiz_id=int(quiz_id),
            user_answers=answers,
            time_taken_seconds=int(time_taken or 0),
        )
        ProgressTracker.record_study_activity(quizzes_delta=1, minutes_delta=20)
        progress = ProgressTracker.calculate_progress_metrics()
        return Response(
            {
                "status": "success",
                "message": f"Quiz submitted! You scored {result['score']}/{result['total_questions']} ({result['percentage']}%).",
                "result": result,
                "quiz_progress": progress["quiz_progress"],
                "overall_progress": progress["overall_progress"],
            }
        )
    except (QuizValidationError, ValueError) as exc:
        return Response({"status": "error", "message": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


# ==========================================================
# PROGRESS, ANALYTICS & KNOWLEDGE MAP API
# ==========================================================
@api_view(["GET"])
def api_progress_summary(request):
    metrics = ProgressTracker.calculate_progress_metrics()
    return Response({"status": "success", "progress": metrics})


@api_view(["GET"])
def api_analytics_summary(request):
    include_charts = request.query_params.get("charts", "true").lower() not in ("false", "0", "no")
    payload = AnalyticsManager.get_full_analytics_payload(include_charts=include_charts)
    return Response({"status": "success", **payload})


@api_view(["GET"])
def api_knowledge_map(request):
    km_data = AnalyticsManager.get_knowledge_map_data()
    return Response({"status": "success", "knowledge_map": km_data})


# ==========================================================
# NETWORKING API: SMTP EMAIL, SOCKET, FTP
# ==========================================================
@api_view(["POST"])
def api_send_email_report(request):
    email = request.data.get("email", "")
    strict_mode = str(request.data.get("strict_smtp", "false")).lower() in ("true", "1", "yes")
    smtp_service = SMTPReportService()
    try:
        result = smtp_service.send_progress_report(recipient_email=email, strict_smtp=strict_mode)
        return Response({"status": "success", **result})
    except EmailReportError as exc:
        return Response({"status": "error", "message": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET", "POST"])
def api_socket_status(request):
    msg = request.data.get("message", "STUDY_SESSION_PING") if request.method == "POST" else "STATUS_CHECK"
    status_data = StudySocketService.check_status(message=msg)
    return Response({"status": "success", "socket": status_data})


@api_view(["GET", "POST"])
def api_ftp_files(request):
    ftp_service = FTPResourceService()
    if request.method == "GET":
        try:
            data = ftp_service.list_files()
            return Response({"status": "success", "ftp": data})
        except FTPTransferError as exc:
            return Response({"status": "error", "message": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    uploaded = request.FILES.get("file")
    try:
        result = ftp_service.upload_file(uploaded)
        return Response(
            {
                "status": "success",
                "message": f"Uploaded '{result['filename']}' via FTP service.",
                "transfer": result,
            },
            status=status.HTTP_201_CREATED,
        )
    except FTPTransferError as exc:
        return Response({"status": "error", "message": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


def api_ftp_download(request, filename: str):
    ftp_service = FTPResourceService()
    try:
        raw_bytes = ftp_service.download_file(filename)
        safe_name = Path(filename).name
        response = HttpResponse(raw_bytes, content_type="application/octet-stream")
        response["Content-Disposition"] = f'attachment; filename="{safe_name}"'
        return response
    except FTPTransferError as exc:
        return HttpResponse(f"FTP Download Error: {exc}", status=404, content_type="text/plain")


# ==========================================================
# RESOURCES & FILE EXPORTS (TXT & CSV)
# ==========================================================
@api_view(["GET", "POST"])
def api_resources_list_upload(request):
    if request.method == "GET":
        file_type = request.query_params.get("type", "").upper()
        qs = StudyResource.objects.all()
        if file_type in ("PDF", "TXT", "CSV", "OTHER"):
            qs = qs.filter(file_type=file_type)
        return Response(
            {
                "status": "success",
                "resources": StudyResourceSerializer(qs, many=True).data,
            }
        )

    uploaded_file = request.FILES.get("file")
    title = request.data.get("title", "")
    subject = request.data.get("subject", "Python")
    try:
        resource = FileManager.save_uploaded_resource(uploaded_file, title=title, subject=subject)
        return Response(
            {
                "status": "success",
                "message": f"Resource '{resource.filename}' uploaded successfully.",
                "resource": StudyResourceSerializer(resource).data,
            },
            status=status.HTTP_201_CREATED,
        )
    except FileHandlingError as exc:
        return Response({"status": "error", "message": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(["DELETE"])
def api_resource_delete(request, pk: int):
    try:
        FileManager.delete_resource(pk)
        return Response({"status": "success", "message": "Resource deleted successfully."})
    except FileHandlingError as exc:
        return Response({"status": "error", "message": str(exc)}, status=status.HTTP_404_NOT_FOUND)


def export_notes_txt_view(request):
    """Stream `notes.txt` download using the `FileManager.stream_notes_txt` generator."""
    subject = request.GET.get("subject")
    FileManager.generate_notes_txt_content(subject=subject, save_to_resources=True)
    response = StreamingHttpResponse(
        FileManager.stream_notes_txt(subject=subject),
        content_type="text/plain; charset=utf-8",
    )
    response["Content-Disposition"] = 'attachment; filename="notes.txt"'
    return response


def export_csv_view(request, export_type: str):
    """Stream `notes.csv`, `quiz_results.csv`, `tasks.csv`, or `progress.csv` using Python's `csv` module."""
    try:
        clean_type = export_type.replace(".csv", "").strip().lower()
        FileManager.generate_csv_content(clean_type, save_to_resources=True)
        stream = FileManager.get_csv_export_stream(clean_type)
        filename = f"{clean_type}.csv"
        response = StreamingHttpResponse(stream, content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response
    except FileHandlingError as exc:
        return HttpResponse(str(exc), status=400, content_type="text/plain")


def download_resource_view(request, pk: int):
    """Download a stored StudyResource file by ID."""
    try:
        resource = StudyResource.objects.get(pk=pk)
        return FileResponse(
            resource.file.open("rb"),
            as_attachment=True,
            filename=resource.filename,
        )
    except (StudyResource.DoesNotExist, OSError):
        return HttpResponse("Requested study resource file was not found.", status=404, content_type="text/plain")
