"""
Comprehensive Test Suite for Notes Manager (Part 33).

Tests all core features and Python syllabus concepts:
1. Note creation, retrieval, lambda sorting, and marking covered
2. Task creation, priority lambda sorting, and task completion ("X of Y tasks completed")
3. PDF extraction (generator/yield), API response validation, and Quiz score calculation
4. Progress calculation formula ((notes + quiz + task) / 3) and Consistency streaks
5. NumPy, SciPy, Matplotlib, and NetworkX analytics & knowledge map generation
6. TXT and CSV streaming exports using generators (`yield`) and Python's `csv` module
7. Socket programming service, SMTP progress report, and FTP resource transfer
8. Exception handling and security validation (blocked extensions, invalid JSON, bad input)
9. Full frontend view rendering across all 9 navigation pages
"""
import io
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse

from analytics.services import AnalyticsManager
from files.services import FileHandlingError, FileManager
from networking.services import (
    EmailReportError,
    FTPResourceService,
    FTPTransferError,
    SMTPReportService,
    StudySocketService,
)
from notes.models import Note
from notes.seed import build_minimal_searchable_pdf
from notes.services import NoteManager, NoteValidationError
from progress.services import ProgressTracker
from quizzes.services import (
    APIService,
    ExternalAPIError,
    PDFExtractionError,
    PDFExtractor,
    QuizManager,
)
from tasks.models import Task
from tasks.services import TaskManager, TaskValidationError


class NotesManagerComprehensiveTests(TestCase):
    """End-to-end unit and integration tests for the Notes Manager college project."""

    def setUp(self):
        self.client = Client()
        self.note_mgr = NoteManager(auto_seed=True)
        self.task_mgr = TaskManager()
        self.quiz_mgr = QuizManager()

    # ----------------------------------------------------------
    # 1. NOTE CREATION, RETRIEVAL, LAMBDA SORTING & COVERED STATUS
    # ----------------------------------------------------------
    def test_note_creation_retrieval_and_mark_covered(self):
        note1 = self.note_mgr.create_note(
            title="Zeta Functions in Python",
            subject_name="Python",
            topic="Functions",
            content="Detailed explanation of higher-order functions.",
            covered=False,
        )
        note2 = self.note_mgr.create_note(
            title="Alpha Lambda Expressions",
            subject_name="Python",
            topic="Lambda",
            content="Anonymous single-expression functions in Python.",
            covered=False,
        )
        self.assertEqual(Note.objects.count(), 2)
        self.assertFalse(note1.covered)

        # Test Lambda sorting (title_asc should place Alpha before Zeta)
        sorted_notes = self.note_mgr.filter_and_sort_notes(subject="Python", sort_by="title_asc")
        self.assertEqual(sorted_notes[0].id, note2.id)
        self.assertEqual(sorted_notes[1].id, note1.id)

        # Test marking note as covered via REST API
        resp = self.client.patch(
            reverse("api_note_detail", args=[note1.id]),
            data='{"covered": true}',
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        note1.refresh_from_db()
        self.assertTrue(note1.covered)
        self.assertEqual(note1.reading_progress, 100)

    # ----------------------------------------------------------
    # 2. DAILY TASKS & COMPLETION PROGRESS
    # ----------------------------------------------------------
    def test_task_creation_priority_sorting_and_completion(self):
        t_low = self.task_mgr.create_task(title="Low Task", priority="Low", completed=False)
        t_high = self.task_mgr.create_task(title="High Task", priority="High", completed=False)

        categorized = self.task_mgr.get_categorized_tasks()
        # Lambda sort puts High priority first
        self.assertEqual(categorized["today_tasks"][0].id, t_high.id)
        self.assertEqual(categorized["summary_text"], "0 of 2 tasks completed")

        # Complete High priority task via API
        resp = self.client.patch(
            reverse("api_task_detail", args=[t_high.id]),
            data='{"completed": true}',
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        t_high.refresh_from_db()
        self.assertTrue(t_high.completed)

        updated = self.task_mgr.get_categorized_tasks()
        self.assertEqual(updated["summary_text"], "1 of 2 tasks completed")
        self.assertEqual(updated["progress_percentage"], 50.0)

    # ----------------------------------------------------------
    # 3. API VALIDATION, PDF EXTRACTION & QUIZ SCORE CALCULATION
    # ----------------------------------------------------------
    def test_api_response_validation_and_quiz_score_calculation(self):
        sample_payload = {
            "questions": [
                {
                    "question": "Which keyword creates a generator in Python?",
                    "option_a": "return",
                    "option_b": "yield",
                    "option_c": "lambda",
                    "option_d": "async",
                    "correct_answer": "B",
                    "explanation": "yield pauses function execution and yields a value.",
                },
                {
                    "question": "Which library builds the Knowledge Map graph?",
                    "option_a": "NetworkX",
                    "option_b": "smtplib",
                    "option_c": "ftplib",
                    "option_d": "csv",
                    "correct_answer": "A",
                    "explanation": "NetworkX constructs directed graphs.",
                },
            ]
        }
        validated = APIService.validate_questions_payload(sample_payload)
        self.assertEqual(len(validated), 2)

        quiz = self.quiz_mgr.save_quiz_with_questions(
            title="Unit Test Quiz",
            subject="Python",
            questions_data=validated,
        )
        questions = list(QuizManager.stream_questions(quiz))
        self.assertEqual(len(questions), 2)

        # Submit 1 correct and 1 incorrect answer (50% score)
        result = self.quiz_mgr.submit_quiz(
            quiz_id=quiz.id,
            user_answers={str(questions[0].id): "B", str(questions[1].id): "C"},
            time_taken_seconds=42,
        )
        self.assertEqual(result["correct_answers"], 1)
        self.assertEqual(result["incorrect_answers"], 1)
        self.assertEqual(result["score"], 1)
        self.assertEqual(result["total_questions"], 2)
        self.assertEqual(result["percentage"], 50.0)

    def test_pdf_upload_and_quiz_generation_endpoint(self):
        pdf_bytes = build_minimal_searchable_pdf(
            [
                "Python Object Oriented Programming encapsulates data and methods inside classes.",
                "Generators use yield to produce items lazily without storing entire lists in memory.",
                "NumPy arrays provide fast vectorized numerical operations for data analysis.",
            ]
        )
        uploaded_pdf = SimpleUploadedFile("test_python.pdf", pdf_bytes, content_type="application/pdf")
        resp = self.client.post(
            reverse("api_quiz_generate"),
            data={"pdf_file": uploaded_pdf, "subject": "Python", "num_questions": 3},
        )
        self.assertEqual(resp.status_code, 201)
        data = resp.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["quiz"]["total_questions"], 3)

    # ----------------------------------------------------------
    # 4. PROGRESS CALCULATION FORMULA & ANALYTICS (NUMPY, SCIPY, NETWORKX)
    # ----------------------------------------------------------
    def test_progress_formula_and_scientific_analytics(self):
        # Create 2 notes (1 covered -> 50% notes_progress)
        self.note_mgr.create_note("N1", "Python", "Content 1", covered=True)
        self.note_mgr.create_note("N2", "Python", "Content 2", covered=False)

        # Create 1 completed quiz with 80% score (-> 80% quiz_progress)
        quiz = self.quiz_mgr.save_quiz_with_questions(
            "Q1",
            "Python",
            [
                {
                    "question": "Q?",
                    "option_a": "1",
                    "option_b": "2",
                    "option_c": "3",
                    "option_d": "4",
                    "correct_answer": "A",
                }
            ],
        )
        quiz.completed = True
        quiz.percentage = 80.0
        quiz.score = 1
        quiz.save()

        # Create 2 tasks (1 completed -> 50% task_progress)
        self.task_mgr.create_task("T1", completed=True)
        self.task_mgr.create_task("T2", completed=False)

        metrics = ProgressTracker.calculate_progress_metrics()
        self.assertEqual(metrics["notes_progress"], 50.0)
        self.assertEqual(metrics["quiz_progress"], 80.0)
        self.assertEqual(metrics["task_progress"], 50.0)
        # Overall = (50 + 80 + 50) / 3 = 60.0%
        self.assertEqual(metrics["overall_progress"], 60.0)

        # Verify NumPy, SciPy, Matplotlib, and NetworkX analytics
        analytics = AnalyticsManager.get_full_analytics_payload(include_charts=True)
        self.assertEqual(analytics["numpy_analysis"]["mean_score"], 80.0)
        self.assertIn("regression_slope", analytics["scipy_analysis"])
        self.assertGreaterEqual(analytics["knowledge_map"]["total_nodes"], 4)
        self.assertTrue(analytics["charts"]["quiz_trend_chart"].startswith("data:image/png;base64,"))

    # ----------------------------------------------------------
    # 5. TXT & CSV STREAMING EXPORTS (GENERATORS / YIELD)
    # ----------------------------------------------------------
    def test_txt_and_csv_file_exports(self):
        self.note_mgr.create_note("Exported Note", "DBMS", "ACID properties content", covered=True)
        self.task_mgr.create_task("Exported Task", subject="DBMS", completed=True)

        txt_resp = self.client.get(reverse("export_notes_txt"))
        self.assertEqual(txt_resp.status_code, 200)
        txt_body = b"".join(txt_resp.streaming_content).decode("utf-8")
        self.assertIn("Exported Note", txt_body)
        self.assertIn("Covered", txt_body)

        for export_name in ("notes", "quiz_results", "tasks", "progress"):
            csv_resp = self.client.get(reverse("export_csv", args=[export_name]))
            self.assertEqual(csv_resp.status_code, 200)
            csv_body = b"".join(csv_resp.streaming_content).decode("utf-8")
            self.assertTrue(len(csv_body) > 10)

    # ----------------------------------------------------------
    # 6. SOCKET, SMTP & FTP NETWORKING SERVICES
    # ----------------------------------------------------------
    def test_socket_smtp_and_ftp_services(self):
        # Socket Status Check
        sock_status = StudySocketService.check_status("TEST_PING")
        self.assertEqual(sock_status["server"], "Online")
        self.assertEqual(sock_status["socket_service"], "Connected")

        # SMTP Progress Report (Local Outbox Preview Mode)
        smtp = SMTPReportService(username="", password="")
        report_res = smtp.send_progress_report("student@college.edu", strict_smtp=False)
        self.assertTrue(report_res["sent"])
        self.assertIn("OVERALL PROGRESS", report_res["report_preview"])

        # FTP Service (Local Mock Mode)
        ftp = FTPResourceService(mock_mode=True)
        sample_upload = SimpleUploadedFile("study_guide.txt", b"Hello FTP Study Resource", content_type="text/plain")
        up_res = ftp.upload_file(sample_upload)
        self.assertEqual(up_res["filename"], "study_guide.txt")
        downloaded = ftp.download_file("study_guide.txt")
        self.assertEqual(downloaded, b"Hello FTP Study Resource")

    # ----------------------------------------------------------
    # 7. EXCEPTION HANDLING & SECURITY VALIDATION
    # ----------------------------------------------------------
    def test_exception_handling_and_security_restrictions(self):
        # Empty note title should raise NoteValidationError
        with self.assertRaises(NoteValidationError):
            self.note_mgr.create_note(title="   ", subject_name="Python", content="Valid")

        # Invalid task due date should raise TaskValidationError
        with self.assertRaises(TaskValidationError):
            self.task_mgr.create_task(title="Bad Date Task", due_date="not-a-date")

        # Dangerous executable file upload should be rejected by FileManager
        bad_file = SimpleUploadedFile("malware.exe", b"MZ...", content_type="application/octet-stream")
        with self.assertRaises(FileHandlingError):
            FileManager.validate_uploaded_file(bad_file)

        # Empty PDF upload should raise PDFExtractionError
        empty_pdf = SimpleUploadedFile("empty.pdf", b"", content_type="application/pdf")
        with self.assertRaises(PDFExtractionError):
            PDFExtractor.extract_text(empty_pdf)

        # Invalid API JSON should raise ExternalAPIError
        with self.assertRaises(ExternalAPIError):
            APIService.validate_questions_payload("not valid json {{{")

        # Invalid email address should raise EmailReportError
        with self.assertRaises(EmailReportError):
            SMTPReportService.validate_email_address("invalid-email-format")

        # Missing file on FTP download should raise FTPTransferError
        with self.assertRaises(FTPTransferError):
            FTPResourceService(mock_mode=True).download_file("non_existent_12345.txt")

    # ----------------------------------------------------------
    # 8. FRONTEND NAVIGATION VIEWS RENDERING
    # ----------------------------------------------------------
    def test_all_frontend_pages_render_cleanly(self):
        note = self.note_mgr.create_note("Reader Test Note", "Python", "Paragraph 1\n\nParagraph 2")
        page_urls = [
            reverse("home"),
            reverse("notes"),
            reverse("note_detail", args=[note.id]),
            reverse("quiz"),
            reverse("tasks"),
            reverse("progress"),
            reverse("analytics"),
            reverse("knowledge_map"),
            reverse("resources"),
            reverse("settings"),
        ]
        for url in page_urls:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200, f"Page {url} failed to render")
