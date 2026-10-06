"""
Service layer for PDF extraction, External AI Quiz Generation API, and Quiz Assessment.

Architecture:
PDF -> Django View -> PDFExtractor -> APIService -> External API -> JSON Validation -> QuizManager -> Database -> Frontend

Python Concepts Demonstrated:
- OOP (PDFExtractor, APIService, QuizManager classes)
- Generators / yield (extract_pages_generator, stream_questions, stream_quiz_results_for_export)
- Lambda Functions (Sorting quiz history by percentage, score, and date)
- Exception Handling (PDFExtractionError, ExternalAPIError, QuizValidationError)
"""
import io
import json
import re
from typing import Any, Dict, Generator, Iterable, List, Optional
import requests
from django.conf import settings
from django.db import transaction
from pypdf import PdfReader
from pypdf.errors import PdfReadError
from .models import Question, Quiz


class QuizValidationError(ValueError):
    """Raised when quiz parameters or answers fail validation."""


class PDFExtractionError(ValueError):
    """Raised when an uploaded PDF cannot be parsed or contains no extractable text."""


class ExternalAPIError(RuntimeError):
    """Raised when the external quiz generation API fails, times out, or returns invalid JSON."""


class PDFExtractor:
    """
    OOP utility for validating and extracting text from uploaded PDF files.
    Uses a Python generator (`yield`) to stream text page-by-page.
    """

    MAX_FILE_SIZE_BYTES = 15 * 1024 * 1024  # 15 MB

    @classmethod
    def validate_pdf_file(cls, uploaded_file: Any) -> None:
        if uploaded_file is None:
            raise PDFExtractionError("No PDF file was provided.")

        filename = getattr(uploaded_file, "name", "document.pdf")
        if not str(filename).lower().endswith(".pdf"):
            raise PDFExtractionError("Invalid file format. Only .pdf files are allowed for quiz generation.")

        size = getattr(uploaded_file, "size", None)
        if size is not None:
            if size == 0:
                raise PDFExtractionError("The uploaded PDF file is empty (0 bytes).")
            if size > cls.MAX_FILE_SIZE_BYTES:
                raise PDFExtractionError("PDF file exceeds the 15 MB maximum upload size.")

    @classmethod
    def extract_pages_generator(cls, pdf_file: Any) -> Generator[str, None, None]:
        """
        Generator using `yield` that lazily reads and cleans text from each page of a PDF.
        """
        cls.validate_pdf_file(pdf_file)
        try:
            if hasattr(pdf_file, "seek"):
                pdf_file.seek(0)
            raw_bytes = pdf_file.read()
            if not raw_bytes:
                raise PDFExtractionError("The uploaded PDF file is empty.")

            reader = PdfReader(io.BytesIO(raw_bytes))
            if len(reader.pages) == 0:
                raise PDFExtractionError("The uploaded PDF has no pages.")

            for page in reader.pages:
                page_text = page.extract_text() or ""
                cleaned = re.sub(r"\s+", " ", page_text).strip()
                if cleaned:
                    yield cleaned
        except PDFExtractionError:
            raise
        except (PdfReadError, Exception) as exc:
            raise PDFExtractionError(f"Could not read PDF file: {exc}") from exc

    @classmethod
    def extract_text(cls, pdf_file: Any, max_chars: int = 12000) -> str:
        """Combine streamed pages into a single cleaned string up to `max_chars`."""
        chunks: List[str] = []
        total_len = 0
        for page_text in cls.extract_pages_generator(pdf_file):
            chunks.append(page_text)
            total_len += len(page_text)
            if total_len >= max_chars:
                break

        combined = "\n\n".join(chunks)[:max_chars].strip()
        if not combined:
            raise PDFExtractionError(
                "No readable text could be extracted from the PDF. Please upload a text-based PDF."
            )
        return combined


class APIService:
    """
    OOP Service Layer for communicating with the external AI / Quiz Generation API.
    Reads API_KEY and API_URL from Django settings (loaded from .env).
    """

    VALID_ANSWERS = {"A", "B", "C", "D"}

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_url: Optional[str] = None,
        timeout: Optional[int] = None,
    ):
        self.api_key = api_key if api_key is not None else getattr(settings, "QUIZ_API_KEY", "")
        self.api_url = api_url if api_url is not None else getattr(settings, "QUIZ_API_URL", "")
        self.timeout = timeout if timeout is not None else getattr(settings, "QUIZ_API_TIMEOUT", 30)

    def _build_prompt(self, text: str, subject: str, num_questions: int) -> str:
        return (
            f"You are an academic computer science professor creating a college multiple-choice quiz "
            f"for the subject '{subject}'.\n"
            f"Generate exactly {num_questions} multiple-choice questions based on the study material below.\n"
            f"Return ONLY valid JSON matching this structure:\n"
            f'{{"questions": [{{"question": "...", "option_a": "...", "option_b": "...", '
            f'"option_c": "...", "option_d": "...", "correct_answer": "A", "explanation": "..."}}]}}\n\n'
            f"Study Material:\n{text[:8000]}"
        )

    @classmethod
    def validate_questions_payload(cls, payload: Any) -> List[Dict[str, str]]:
        """
        Validate and normalize parsed JSON response from the external API.
        Raises ExternalAPIError if structure or required fields are invalid.
        """
        if isinstance(payload, str):
            try:
                # Strip markdown code fences if present
                cleaned_json = re.sub(r"^```(?:json)?|```$", "", payload.strip(), flags=re.MULTILINE).strip()
                payload = json.loads(cleaned_json)
            except json.JSONDecodeError as exc:
                raise ExternalAPIError(f"API returned invalid JSON: {exc}") from exc

        if isinstance(payload, dict):
            questions_raw = payload.get("questions") or payload.get("data") or payload.get("items")
        elif isinstance(payload, list):
            questions_raw = payload
        else:
            raise ExternalAPIError("API response must be a JSON object containing a 'questions' list.")

        if not isinstance(questions_raw, list) or len(questions_raw) == 0:
            raise ExternalAPIError("API response did not contain any valid questions.")

        validated: List[Dict[str, str]] = []
        for idx, item in enumerate(questions_raw, start=1):
            if not isinstance(item, dict):
                raise ExternalAPIError(f"Question #{idx} is not a JSON object.")

            q_text = str(item.get("question", "")).strip()
            opt_a = str(item.get("option_a", "")).strip()
            opt_b = str(item.get("option_b", "")).strip()
            opt_c = str(item.get("option_c", "")).strip()
            opt_d = str(item.get("option_d", "")).strip()
            ans = str(item.get("correct_answer", "A")).strip().upper()[:1]
            explanation = str(item.get("explanation", "")).strip()

            if not q_text or not all([opt_a, opt_b, opt_c, opt_d]):
                raise ExternalAPIError(f"Question #{idx} is missing question text or one of the four options.")

            if ans not in cls.VALID_ANSWERS:
                raise ExternalAPIError(
                    f"Question #{idx} has invalid correct_answer '{ans}'. Must be A, B, C, or D."
                )

            validated.append(
                {
                    "question_number": idx,
                    "question": q_text,
                    "option_a": opt_a[:350],
                    "option_b": opt_b[:350],
                    "option_c": opt_c[:350],
                    "option_d": opt_d[:350],
                    "correct_answer": ans,
                    "explanation": explanation or f"The correct option is {ans}.",
                }
            )
        return validated

    def call_external_api(self, extracted_text: str, subject: str = "Python", num_questions: int = 5) -> List[Dict[str, str]]:
        """
        Send extracted text to the configured external API, parse JSON, and validate questions.
        Raises ExternalAPIError on missing key, timeout, network error, or invalid response.
        """
        if not (extracted_text or "").strip():
            raise QuizValidationError("Cannot generate quiz from empty text.")

        if not self.api_key:
            raise ExternalAPIError("API_KEY is not configured in environment variables (.env).")
        if not self.api_url:
            raise ExternalAPIError("API_URL is not configured in environment variables (.env).")

        prompt = self._build_prompt(extracted_text, subject, num_questions)

        try:
            if "generativelanguage.googleapis.com" in self.api_url:
                # Google Gemini REST API payload
                separator = "&" if "?" in self.api_url else "?"
                request_url = f"{self.api_url}{separator}key={self.api_key}"
                headers = {"Content-Type": "application/json"}
                body = {
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {"responseMimeType": "application/json"},
                }
                response = requests.post(request_url, headers=headers, json=body, timeout=self.timeout)
            else:
                # Generic REST / OpenAI-compatible endpoint
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                }
                body = {
                    "subject": subject,
                    "num_questions": num_questions,
                    "text": extracted_text[:8000],
                    "messages": [{"role": "user", "content": prompt}],
                }
                response = requests.post(self.api_url, headers=headers, json=body, timeout=self.timeout)

            response.raise_for_status()
            data = response.json()

            # Unwrap Gemini or OpenAI chat structure if applicable
            if isinstance(data, dict) and "candidates" in data:
                raw_text = (
                    data["candidates"][0]
                    .get("content", {})
                    .get("parts", [{}])[0]
                    .get("text", "")
                )
                return self.validate_questions_payload(raw_text)
            if isinstance(data, dict) and "choices" in data:
                raw_text = data["choices"][0].get("message", {}).get("content", "")
                return self.validate_questions_payload(raw_text)

            return self.validate_questions_payload(data)

        except requests.exceptions.Timeout as exc:
            raise ExternalAPIError("External Quiz API request timed out. Please try again.") from exc
        except requests.exceptions.RequestException as exc:
            raise ExternalAPIError(f"Network error communicating with Quiz API: {exc}") from exc
        except ValueError as exc:
            raise ExternalAPIError(f"Failed to decode JSON response from Quiz API: {exc}") from exc

    def generate_questions_from_text(
        self,
        extracted_text: str,
        subject: str = "Python",
        num_questions: int = 5,
        allow_fallback: bool = True,
    ) -> List[Dict[str, str]]:
        """
        Primary method used by QuizManager:
        Attempts external API call if API_KEY is configured; if API_KEY is absent or
        allow_fallback=True on network error during local demonstration, synthesizes
        context-aware questions directly from the extracted PDF text.
        """
        cleaned_text = (extracted_text or "").strip()
        if not cleaned_text:
            raise QuizValidationError("Extracted text cannot be empty.")

        if self.api_key:
            try:
                return self.call_external_api(cleaned_text, subject=subject, num_questions=num_questions)
            except ExternalAPIError:
                if not allow_fallback:
                    raise

        if not allow_fallback:
            raise ExternalAPIError("API_KEY is missing and fallback generation is disabled.")

        return self.build_contextual_questions(cleaned_text, subject=subject, num_questions=num_questions)

    @classmethod
    def build_contextual_questions(
        cls,
        extracted_text: str,
        subject: str = "Python",
        num_questions: int = 5,
    ) -> List[Dict[str, str]]:
        """
        Intelligent deterministic question generator that extracts key sentences and technical terms
        from the uploaded PDF text so college demonstrations work reliably even without an internet API key.
        """
        sentences = [
            s.strip()
            for s in re.split(r"(?<=[.!?])\s+", extracted_text)
            if len(s.strip().split()) >= 6
        ]
        words = re.findall(r"\b[A-Za-z][A-Za-z0-9_+-]{3,}\b", extracted_text)
        stop_words = {
            "this", "that", "with", "from", "have", "will", "your", "they", "their",
            "about", "which", "when", "where", "while", "there", "these", "those",
            "into", "using", "used", "also", "such", "more", "some", "than", "then",
        }
        keywords = []
        for w in words:
            if w.lower() not in stop_words and w not in keywords:
                keywords.append(w)

        distractor_pool = [
            "Manual memory deallocation without garbage collection",
            "Unindexed full-table sequential scan only",
            "Static hardware interrupt masking at ring 0",
            "Synchronous blocking UDP broadcast frame",
            "Non-deterministic polynomial backtracking",
        ]

        generated: List[Dict[str, str]] = []
        for idx in range(1, num_questions + 1):
            if idx - 1 < len(sentences):
                sent = sentences[idx - 1][:220]
                focus_term = keywords[(idx - 1) % len(keywords)] if keywords else subject
                correct_letter = ["A", "B", "C", "D"][(idx - 1) % 4]
                correct_statement = sent if len(sent) <= 180 else sent[:177] + "..."

                options_map = {
                    "A": distractor_pool[(idx + 0) % len(distractor_pool)],
                    "B": distractor_pool[(idx + 1) % len(distractor_pool)],
                    "C": distractor_pool[(idx + 2) % len(distractor_pool)],
                    "D": distractor_pool[(idx + 3) % len(distractor_pool)],
                }
                options_map[correct_letter] = correct_statement

                generated.append(
                    {
                        "question_number": idx,
                        "question": (
                            f"According to the uploaded {subject} document regarding '{focus_term}', "
                            f"which of the following statements is accurate?"
                        ),
                        "option_a": options_map["A"],
                        "option_b": options_map["B"],
                        "option_c": options_map["C"],
                        "option_d": options_map["D"],
                        "correct_answer": correct_letter,
                        "explanation": f"Derived directly from the uploaded PDF: \"{correct_statement}\"",
                    }
                )
            else:
                focus_term = keywords[(idx - 1) % len(keywords)] if keywords else subject
                generated.append(
                    {
                        "question_number": idx,
                        "question": f"Which primary concept is emphasized in this {subject} study material ({focus_term})?",
                        "option_a": f"Core principles and practical application of {focus_term} in {subject}",
                        "option_b": "Deprecated assembly register addressing modes",
                        "option_c": "Analog vacuum tube signal amplification",
                        "option_d": "Unrelated network coaxial cable termination",
                        "correct_answer": "A",
                        "explanation": f"The study material focuses on {focus_term} within {subject}.",
                    }
                )

        return cls.validate_questions_payload(generated)


class QuizManager:
    """
    OOP Manager for creating quizzes, streaming questions with a generator (`yield`),
    grading quiz submissions, and sorting quiz history with lambda functions.
    """

    def __init__(self, api_service: Optional[APIService] = None):
        self.api_service = api_service or APIService()

    def create_quiz_from_pdf(
        self,
        pdf_file: Any,
        title: str = "",
        subject: str = "Python",
        num_questions: int = 5,
        allow_fallback: bool = True,
    ) -> Quiz:
        """
        Full pipeline:
        1. Extract text from uploaded PDF
        2. Generate & validate questions via APIService
        3. Persist Quiz and Question models in database
        """
        extracted_text = PDFExtractor.extract_text(pdf_file)
        pdf_name = getattr(pdf_file, "name", "study_material.pdf")
        quiz_title = (title or "").strip() or f"Quiz: {pdf_name.rsplit('.', 1)[0]}"

        questions_data = self.api_service.generate_questions_from_text(
            extracted_text,
            subject=subject,
            num_questions=num_questions,
            allow_fallback=allow_fallback,
        )
        return self.save_quiz_with_questions(
            title=quiz_title,
            subject=subject,
            questions_data=questions_data,
            source_pdf_name=pdf_name,
        )

    def save_quiz_with_questions(
        self,
        title: str,
        subject: str,
        questions_data: List[Dict[str, Any]],
        source_pdf_name: str = "",
    ) -> Quiz:
        validated_questions = APIService.validate_questions_payload(questions_data)
        with transaction.atomic():
            quiz = Quiz.objects.create(
                title=(title or "Generated Quiz").strip(),
                subject=(subject or "Python").strip() or "Python",
                source_pdf_name=source_pdf_name,
                score=0,
                total_questions=len(validated_questions),
                completed=False,
            )
            for idx, q_item in enumerate(validated_questions, start=1):
                Question.objects.create(
                    quiz=quiz,
                    question_number=idx,
                    question=q_item["question"],
                    option_a=q_item["option_a"],
                    option_b=q_item["option_b"],
                    option_c=q_item["option_c"],
                    option_d=q_item["option_d"],
                    correct_answer=q_item["correct_answer"],
                    explanation=q_item.get("explanation", ""),
                )
        return quiz

    @staticmethod
    def stream_questions(quiz: Quiz) -> Generator[Question, None, None]:
        """
        Generator using `yield` to process quiz questions one at a time during grading or export.
        """
        for question in quiz.questions.all().order_by("question_number", "id").iterator():
            yield question

    def submit_quiz(
        self,
        quiz_id: int,
        user_answers: Dict[str, str],
        time_taken_seconds: int = 0,
    ) -> Dict[str, Any]:
        """
        Evaluate submitted answers using the `stream_questions` generator,
        calculate score & percentage, update database, and return detailed summary.
        """
        try:
            quiz = Quiz.objects.get(pk=quiz_id)
        except Quiz.DoesNotExist as exc:
            raise QuizValidationError(f"Quiz with ID {quiz_id} does not exist.") from exc

        normalized_answers = {
            str(k).strip(): str(v).strip().upper()[:1]
            for k, v in (user_answers or {}).items()
            if v
        }

        correct_count = 0
        total_count = 0
        question_review: List[Dict[str, Any]] = []

        with transaction.atomic():
            for question in self.stream_questions(quiz):
                total_count += 1
                ans = (
                    normalized_answers.get(str(question.id))
                    or normalized_answers.get(f"q_{question.id}")
                    or normalized_answers.get(str(question.question_number))
                    or ""
                )
                question.user_answer = ans
                question.save(update_fields=["user_answer"])

                is_correct = ans == question.correct_answer
                if is_correct:
                    correct_count += 1

                question_review.append(
                    {
                        "id": question.id,
                        "question_number": question.question_number,
                        "question": question.question,
                        "user_answer": ans or "Not Answered",
                        "correct_answer": question.correct_answer,
                        "is_correct": is_correct,
                        "explanation": question.explanation,
                    }
                )

            incorrect_count = max(0, total_count - correct_count)
            percentage = round((correct_count / total_count) * 100.0, 2) if total_count > 0 else 0.0

            quiz.score = correct_count
            quiz.total_questions = total_count
            quiz.correct_answers = correct_count
            quiz.incorrect_answers = incorrect_count
            quiz.percentage = percentage
            quiz.time_taken_seconds = max(0, int(time_taken_seconds or 0))
            quiz.completed = True
            quiz.save()

        return {
            "quiz_id": quiz.id,
            "title": quiz.title,
            "subject": quiz.subject,
            "correct_answers": correct_count,
            "incorrect_answers": incorrect_count,
            "score": correct_count,
            "total_questions": total_count,
            "percentage": percentage,
            "time_taken_seconds": quiz.time_taken_seconds,
            "review": question_review,
        }

    @staticmethod
    def get_sorted_quizzes(sort_by: str = "date_desc") -> List[Quiz]:
        """
        Sort quizzes using Python lambda functions:
        - score_desc: highest percentage and raw score first
        - score_asc: lowest percentage first
        - date_desc: newest quiz first
        """
        quizzes = list(Quiz.objects.all())
        sort_lambdas = {
            "score_desc": lambda q: (q.percentage, q.score, q.created_at.timestamp() if q.created_at else 0.0),
            "score_asc": lambda q: (q.percentage, q.score),
            "date_desc": lambda q: q.created_at.timestamp() if q.created_at else 0.0,
            "title_asc": lambda q: q.title.lower(),
        }
        key_fn = sort_lambdas.get(sort_by, sort_lambdas["date_desc"])
        reverse = sort_by in ("score_desc", "date_desc")
        return sorted(quizzes, key=key_fn, reverse=reverse)

    @staticmethod
    def stream_quiz_results_for_export(quizzes_iterable: Optional[Iterable[Quiz]] = None) -> Generator[Dict[str, str], None, None]:
        """Generator using `yield` to stream quiz results for CSV export."""
        source = quizzes_iterable if quizzes_iterable is not None else Quiz.objects.all().iterator()
        for quiz in source:
            yield {
                "id": str(quiz.id),
                "title": quiz.title,
                "subject": quiz.subject,
                "score": str(quiz.score),
                "total_questions": str(quiz.total_questions),
                "percentage": f"{quiz.percentage:.1f}%",
                "time_taken_seconds": str(quiz.time_taken_seconds),
                "completed": "Yes" if quiz.completed else "No",
                "created_at": quiz.created_at.strftime("%Y-%m-%d %H:%M") if quiz.created_at else "",
            }
