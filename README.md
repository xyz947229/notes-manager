# Notes Manager — Full-Stack Academic Study & Productivity Suite

**Notes Manager** is a complete Python and Django college project built to manage academic study notes, generate multiple-choice quizzes from PDFs via an external AI API, track daily tasks and study streaks, perform numerical/statistical analytics with **NumPy**, **SciPy**, **Matplotlib**, and **NetworkX**, export streaming **TXT** and **CSV** files, and demonstrate **TCP Socket**, **SMTP**, and **FTP** networking in Python.

---

## 1. Project Description

Notes Manager provides college students with an integrated workspace to:
- Organize notes across subjects (**Python**, **DSA**, **DBMS**, **Computer Organization**, **Java**, **Mathematics**, **Other**, plus custom subjects) with **Covered** and **Not Covered** tabs.
- Read notes in a distraction-free **Note Reading Experience** with Previous/Next navigation and an end-of-note completion prompt.
- Upload academic **PDFs** to automatically extract text and generate interactive multiple-choice quizzes.
- Manage **Daily Tasks** categorized into **Today**, **Upcoming**, and **Completed** with live completion progress (`"3 of 5 tasks completed"`).
- Track **Three-Pillar Study Progress** (`Notes Progress`, `Quiz Progress`, `Task Progress`, and `Overall Progress`) alongside a **28-Day Study Consistency Heatmap** and streak counter.
- Analyze academic performance using **NumPy**, **SciPy**, **Matplotlib**, and a **NetworkX Knowledge Map** (`Subjects → Topics → Notes`).
- Export study data to `.txt` and `.csv` files and transfer study resources using **Python `ftplib`**, **Python `smtplib`**, and **Python `socket`**.

---

## 2. Features

1. **Dashboard (Home)**: Displays Total Notes, Covered Notes, Pending Notes, Average Quiz Score, Today's Tasks, Overall Progress, Current Study Streak, a **"Continue Studying"** banner, and live TCP Socket telemetry.
2. **Notes Management**: Subject filtering, custom subject creation, Covered vs Not Covered tabs, full-text search, dynamic sorting via Python `lambda` functions, and full CRUD operations.
3. **Note Reading Experience**: Displays subject, topic, progress bar, Previous/Next note buttons, and the end-of-note prompt (`"You've reached the end of this note. Do you want to mark this note as covered?"`).
4. **PDF Quiz System**: Drag-and-drop PDF upload (`pypdf`), page-by-page generator streaming, external AI API integration (`quizzes/services.py`) with JSON schema validation and offline contextual fallback, interactive question stepper, and graded quiz history.
5. **Daily Tasks**: Add, edit, delete, complete, and uncomplete tasks across **Today**, **Upcoming**, and **Completed** sections with priority sorting (`High`, `Medium`, `Low`).
6. **Consistency & Progress Tracker**: Calculates Notes, Quiz, Task, and Overall Progress (`(notes + quiz + tasks) / 3`), tracks Current Streak & Best Streak, and renders a 28-day calendar heatmap from database records.
7. **Scientific Study Analytics**: Vectorized score analysis (**NumPy**), linear regression & Z-score distribution modeling (**SciPy**), and theme-matched backend charts (**Matplotlib**).
8. **Knowledge Map**: Directed graph (`nx.DiGraph`) built with **NetworkX** connecting `Subjects → Topics → Notes`, rendered both on an interactive HTML5 Canvas and via Matplotlib.
9. **TXT & CSV Exports**: Memory-efficient streaming exports (`notes.txt`, `notes.csv`, `quiz_results.csv`, `tasks.csv`, `progress.csv`) using Python generators (`yield`) and the standard `csv` module.
10. **Networking Suite**:
    - **TCP Socket Service (`socket`)**: Background TCP server and client ping protocol reporting `Server: Online` and `Socket Service: Connected`.
    - **SMTP Progress Report (`smtplib`)**: Emails formatted study progress reports with TLS and local `.eml` outbox fallback.
    - **FTP Resource Transfer (`ftplib`)**: Lists, uploads (`STOR`), and downloads (`RETR`) study files with a safe local development mode (`FTP_MOCK_MODE=True`).

---

## 3. Technology Stack

- **Backend**: Python 3.11+, Django 5.x, Django REST Framework (DRF)
- **Database**: SQLite (`db.sqlite3`) via Django ORM
- **Frontend**: Semantic HTML5 (`<dialog closedby="any">`), Custom CSS3 (Dusty Rose `#C17876` & Dark Burgundy `#853737` palette), Vanilla JavaScript (`fetch` REST integration & HTML5 Canvas)
- **Scientific & Graph Libraries**: `numpy`, `scipy`, `matplotlib`, `networkx`
- **File & Document Processing**: `pypdf`, `csv`, `json`, `pathlib`, `io`
- **Networking & External Integration**: `requests`, `socket`, `smtplib`, `ftplib`, `python-dotenv`

---

## 4. Project Structure

```text
notes_manager/
├── manage.py
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
│
├── notes_manager/          # Project configuration & root URL routing
│   ├── settings.py
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
│
├── notes/                  # Notes CRUD, Subjects, Seed data, Views & REST API
│   ├── models.py           # Subject & Note models
│   ├── services.py         # NoteManager OOP class, lambda sorting, yield generators
│   ├── serializers.py
│   ├── views.py            # All 9 page views
│   ├── api_views.py        # DRF REST API endpoints
│   ├── seed.py             # Initial academic seed data & searchable PDF builder
│   └── tests.py            # Comprehensive automated test suite
│
├── quizzes/                # PDF extraction, External AI Quiz API & Quiz runner
│   ├── models.py           # Quiz & Question models
│   ├── services.py         # PDFExtractor, APIService & QuizManager classes
│   └── serializers.py
│
├── tasks/                  # Daily Tasks management
│   ├── models.py           # Task model
│   ├── services.py         # TaskManager OOP class & priority lambda sorting
│   └── serializers.py
│
├── progress/               # Three-Pillar Progress & Consistency Heatmap
│   ├── models.py           # StudyLog model
│   ├── services.py         # ProgressTracker OOP class & streak engine
│   └── serializers.py
│
├── files/                  # TXT/CSV streaming exports & StudyResource library
│   ├── models.py           # StudyResource model
│   ├── services.py         # FileManager OOP class, TXT/CSV generators & file security
│   └── serializers.py
│
├── analytics/              # NumPy, SciPy, Matplotlib & NetworkX engine
│   └── services.py         # AnalyticsManager OOP class
│
├── networking/             # TCP Socket, SMTP Email & FTP Resource Transfer
│   ├── models.py           # NetworkActivityLog model
│   └── services.py         # StudySocketService, SMTPReportService, FTPResourceService
│
├── templates/              # Responsive HTML5 templates
├── static/                 # Dusty Rose & Dark Burgundy CSS and client JS
├── media/                  # Uploaded resources & generated exports
└── ftp_local_storage/      # Local FTP repository directory for mock mode
```

---

## 5. Installation

Clone the repository from GitHub:

```bash
git clone https://github.com/xyz947229/notes-manager.git
cd notes-manager
```

---

## 6. Virtual Environment Setup

Create and activate an isolated Python virtual environment:

```powershell
# Windows PowerShell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

```bash
# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate
```

---

## 7. Dependencies

Install all required packages from `requirements.txt`:

```bash
pip install -r requirements.txt
```

---

## 8. Environment Variables

Copy `.env.example` to `.env` and customize any credentials as needed:

```bash
cp .env.example .env
```

Required variables documented in `.env.example`:
- `DJANGO_SECRET_KEY`, `DJANGO_DEBUG`, `DJANGO_ALLOWED_HOSTS`
- `API_KEY`, `API_URL`, `API_TIMEOUT` (for external AI quiz generation)
- `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_USE_TLS`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD` (for SMTP reports)
- `FTP_MOCK_MODE`, `FTP_HOST`, `FTP_PORT`, `FTP_USER`, `FTP_PASSWORD` (for FTP transfers)
- `SOCKET_HOST`, `SOCKET_PORT` (for the local TCP socket status service)

> **Security Note**: Never commit `.env` or real credentials to Git. `.env` is excluded via `.gitignore`.

---

## 9. Database Setup & 10. Migrations

 Notes Manager uses SQLite (`db.sqlite3`) out of the box for college demonstration. Run migrations to initialize all database tables:

```bash
python manage.py makemigrations
python manage.py migrate
```

---

## 11. How to Run

Start the Django development server:

```bash
python manage.py runserver
```

Open **`http://127.0.0.1:8000/`** in your browser. On first load, `notes/seed.py` automatically seeds realistic academic notes, quizzes, daily tasks, study logs, and a sample searchable PDF so every chart, heatmap, and graph works immediately.

Run the automated test suite at any time with:

```bash
python manage.py test
```

---

## 12. API Setup & 13. PDF Quiz Setup

- The PDF Quiz system (`quizzes/services.py`) follows a clean layered pipeline:
  `PDF Upload → Django View → PDFExtractor (pypdf generator) → APIService → JSON Validation → QuizManager → SQLite Database → Frontend`.
- Set `API_KEY` and `API_URL` in `.env` to use Google Gemini (`generateContent`) or an OpenAI-compatible JSON endpoint.
- If `API_KEY` is left empty during an offline college demonstration, `APIService.build_contextual_questions()` automatically analyzes key sentences and technical terminology inside the uploaded PDF to generate context-specific multiple-choice questions.

---

## 14. SMTP Setup

- Configured in `networking/services.py` (`SMTPReportService`) using Python's `smtplib.SMTP` and `email.mime`.
- Set `EMAIL_HOST_USER` and `EMAIL_HOST_PASSWORD` (e.g., a Gmail App Password) in `.env` for live external email delivery.
- When credentials are omitted in local demo mode, the formatted MIME report is saved to `media/exports/latest_progress_report.eml` and previewed directly in the UI.

---

## 15. FTP Setup

- Configured in `networking/services.py` (`FTPResourceService`) using Python's `ftplib.FTP` (`connect`, `login`, `nlst`, `storbinary`, `retrbinary`, `quit`).
- When `FTP_MOCK_MODE=True` (default for offline college demos), file uploads and downloads operate safely against `ftp_local_storage/`. Set `FTP_MOCK_MODE=False` with a live FTP server (`FTP_HOST`, `FTP_PORT`, `FTP_USER`, `FTP_PASSWORD`) to use live FTP sockets.

---

## 16. Socket Programming Feature

- Implemented in `networking/services.py` (`StudySocketService`) using `socket.socket(socket.AF_INET, socket.SOCK_STREAM)`.
- Launches a lightweight daemon TCP server on `127.0.0.1:65432` (with automatic ephemeral port fallback if busy).
- Whenever the dashboard or `/api/socket/status/` is queried, a TCP client connects, sends a heartbeat command, receives JSON telemetry (`Server: Online`, `Socket Service: Connected`, round-trip latency in ms), and closes the connection cleanly.

---

## 17. NumPy Usage

Implemented in `analytics/services.py` (`AnalyticsManager.compute_numpy_metrics`) and `progress/services.py`:
- Converts quiz percentage scores, note word counts, and daily study minutes into `np.ndarray` vectors.
- Computes vectorized arithmetic mean (`np.mean`), median, standard deviation (`np.std`), variance (`np.var`), quartiles & 90th percentile (`np.percentile`), and cumulative moving averages (`np.cumsum(scores) / np.arange(...)`).
- Computes the Three-Pillar Overall Progress formula:
  $$\text{Overall Progress} = \frac{\text{Notes Progress} + \text{Quiz Progress} + \text{Task Progress}}{3}$$

---

## 18. SciPy Usage

Implemented in `analytics/services.py` (`AnalyticsManager.compute_scipy_statistics`) using `scipy.stats`:
- **Linear Regression (`scipy.stats.linregress`)**: Computes the learning trend slope, intercept, correlation coefficient ($r$), $p$-value, and predicts the student's next quiz score.
- **Standardized Z-Scores (`scipy.stats.zscore`)**: Measures how many standard deviations each quiz score lies from the student's mean.
- **Normal Distribution Modeling (`scipy.stats.norm.cdf`)**: Estimates the probability of scoring above $75\%$ based on historical mean and standard deviation.
- **Study Efficiency Correlation (`scipy.stats.pearsonr`)**: Computes Pearson correlation between daily study minutes and completed study actions.

---

## 19. Matplotlib Usage

Implemented in `analytics/services.py` using the non-interactive `Agg` backend (`matplotlib.pyplot`):
1. **Quiz Performance & SciPy Regression Trend Chart**
2. **Notes Coverage by Subject (Horizontal Stacked Bar Chart)**
3. **Weekly Study Minutes & Completed Actions (Dual-Axis Chart)**
4. **NetworkX Knowledge Map Graph Plot**

All charts are styled in the application's Dusty Rose (`#C17876`) and Dark Burgundy (`#853737`) palette.

---

## 20. NetworkX Usage

Implemented in `analytics/services.py` (`AnalyticsManager.build_knowledge_graph` & `get_knowledge_map_data`):
- Constructs a directed graph (`nx.DiGraph`) connecting **Knowledge Hub → Subjects → Topics → Notes**.
- Computes graph topology metrics including total nodes, directed edges, graph density (`nx.density`), connected components (`nx.number_connected_components`), degree centrality (`nx.degree_centrality`), and force-directed node coordinates (`nx.spring_layout`).

---

## 21. Python Topics Demonstrated

| # | Python Syllabus Topic | File / Module Location | Class / Method / Implementation | Purpose in Notes Manager |
|---|---|---|---|---|
| 1 | **Frontend (HTML/CSS/JS)** | `templates/*.html`, `static/css/style.css`, `static/js/app.js` | Responsive 9-page UI, `<dialog closedby="any">`, Canvas | Student productivity interface in Dusty Rose & Dark Burgundy |
| 2 | **Django Backend & DRF** | `notes/views.py`, `notes/api_views.py`, `*/serializers.py` | Template views + REST API (`GET`, `POST`, `PUT`, `PATCH`, `DELETE`) | Clean separation of HTML rendering and JSON API endpoints |
| 3 | **Database & Django ORM** | `notes/models.py`, `quizzes/models.py`, `tasks/models.py`, `progress/models.py` | `Subject`, `Note`, `Quiz`, `Question`, `Task`, `StudyLog`, `StudyResource` | Relational SQLite persistence with `ForeignKey` & `transaction.atomic()` |
| 4 | **External API Integration** | `quizzes/services.py` | `APIService.call_external_api()` (`requests.post`) | Sends extracted PDF text to AI API configured in `.env` and validates JSON |
| 5 | **File Handling** | `files/services.py` | `FileManager` (`pathlib.Path`, `ContentFile`, extension allowlist) | Uploads, validates, downloads, and deletes study resources safely |
| 6 | **PDF Processing** | `quizzes/services.py` | `PDFExtractor` (`pypdf.PdfReader`) | Validates uploaded PDFs and extracts text page-by-page |
| 7 | **Quiz Generation & Grading** | `quizzes/services.py` | `QuizManager.create_quiz_from_pdf()`, `submit_quiz()` | Generates MCQs from PDFs and grades user submissions |
| 8 | **Progress Tracking** | `progress/services.py` | `ProgressTracker.calculate_progress_metrics()` | Computes Notes, Quiz, Task, and Overall Progress + 28-day heatmap |
| 9 | **Daily Tasks** | `tasks/services.py` | `TaskManager.get_categorized_tasks()` | Organizes Today, Upcoming, and Completed tasks with progress bar |
| 10 | **TXT File Export** | `files/services.py` | `FileManager.stream_notes_txt()` | Streams formatted `notes.txt` with Subject, Title, Content, Status, Date |
| 11 | **CSV Functionality** | `files/services.py` | `FileManager.stream_csv_rows()` (`csv.DictWriter`) | Exports `notes.csv`, `quiz_results.csv`, `tasks.csv`, and `progress.csv` |
| 12 | **NumPy** | `analytics/services.py`, `progress/services.py` | `AnalyticsManager.compute_numpy_metrics()` | Vectorized score arrays, moving averages, percentiles, std dev |
| 13 | **SciPy** | `analytics/services.py` | `AnalyticsManager.compute_scipy_statistics()` (`scipy.stats`) | Linear regression (`linregress`), Z-scores (`zscore`), Normal CDF (`norm`), `pearsonr` |
| 14 | **Matplotlib** | `analytics/services.py` | `generate_quiz_trend_chart()`, `generate_notes_coverage_chart()` | Renders base64 PNG study analytics charts in Dusty Rose theme |
| 15 | **NetworkX** | `analytics/services.py` | `build_knowledge_graph()` (`nx.DiGraph`, `nx.degree_centrality`) | Models `Subject → Topic → Note` hierarchy and centrality hubs |
| 16 | **Socket Programming** | `networking/services.py` | `StudySocketService` (`socket.AF_INET`, `SOCK_STREAM`) | Background TCP server & client heartbeat checking server/socket status |
| 17 | **SMTP Email** | `networking/services.py` | `SMTPReportService.send_progress_report()` (`smtplib.SMTP`) | Emails formatted progress report with TLS and local outbox fallback |
| 18 | **FTP File Transfer** | `networking/services.py` | `FTPResourceService` (`ftplib.FTP`) | Lists (`NLST`), uploads (`STOR`), and downloads (`RETR`) study resources |
| 19 | **Exception Handling** | `*/services.py`, `notes/api_views.py` | `NoteValidationError`, `PDFExtractionError`, `ExternalAPIError`, `FTPTransferError` | Prevents raw tracebacks and returns clear user-friendly messages |
| 20 | **Object-Oriented Programming** | `*/services.py`, `*/models.py` | `NoteManager`, `QuizManager`, `APIService`, `TaskManager`, `ProgressTracker`, `FileManager`, `AnalyticsManager` | Encapsulates domain logic, state, constructors, and methods |
| 21 | **Lambda & Generators (`yield`)** | `notes/services.py`, `quizzes/services.py`, `tasks/services.py`, `files/services.py` | `SORT_STRATEGIES` (`lambda`), `extract_pages_generator` (`yield`), `stream_notes_for_export` (`yield`) | Dynamic sorting with `lambda` and lazy constant-memory streaming with `yield` |

---

## 22. Screenshots Section

When demonstrating the project, showcase the following pages:
1. **Home Dashboard (`/`)** — Continue Studying hero card, 6 live metric cards, Today's Tasks, and TCP Socket status.
2. **Notes Management (`/notes/`) & Note Reader (`/notes/1/`)** — Subject pills, Covered/Not Covered tabs, lambda sorting, and end-of-note completion prompt.
3. **PDF Quiz Generator (`/quiz/`)** — Drag-and-drop PDF upload, interactive question stepper, and graded review.
4. **Progress & Consistency Heatmap (`/progress/`)** — Three-Pillar progress formula, 28-day heatmap, and SMTP report sender.
5. **Scientific Analytics (`/analytics/`) & Knowledge Map (`/knowledge-map/`)** — NumPy/SciPy tables, Matplotlib charts, and interactive NetworkX graph.
6. **Resources & FTP Transfer (`/resources/`) & Settings (`/settings/`)** — TXT/CSV exports, FTP upload/download, and Python Viva reference table.

---

## 23. Future Improvements

- Multi-user authentication with student profiles and shared study groups.
- Spaced-repetition flashcard scheduling based on SciPy forgetting-curve decay models.
- Real-time collaborative note editing over WebSockets (Django Channels).
- OCR support (`pytesseract`) for scanned handwritten PDF notes.
