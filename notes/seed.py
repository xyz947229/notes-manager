"""
Database Seeding Utility for Notes Manager.
Populates realistic college study notes, quizzes, tasks, study streak logs,
and a valid sample PDF resource when the database is initialized for demonstration.
"""
from datetime import timedelta
import sys
from django.core.files.base import ContentFile
from django.utils import timezone
from files.models import StudyResource
from notes.models import Note, Subject
from notes.services import NoteManager
from progress.models import StudyLog
from progress.services import ProgressTracker
from quizzes.models import Question, Quiz
from tasks.models import Task


def build_minimal_searchable_pdf(lines_of_text: list[str]) -> bytes:
    """
    Construct a standards-compliant, text-searchable PDF 1.4 byte stream
    without requiring external C libraries. `pypdf.PdfReader` extracts all lines cleanly.
    """
    escaped_lines = []
    for line in lines_of_text:
        clean = (
            line.replace("\\", "\\\\")
            .replace("(", "\\(")
            .replace(")", "\\)")
        )
        escaped_lines.append(clean)

    stream_commands = ["BT", "/F1 11 Tf", "50 750 Td", "16 TL"]
    for idx, text_line in enumerate(escaped_lines):
        if idx == 0:
            stream_commands.append(f"({text_line}) Tj")
        else:
            stream_commands.append(f"T* ({text_line}) Tj")
    stream_commands.append("ET")
    stream_body = "\n".join(stream_commands).encode("latin-1", errors="ignore")

    objects = [
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n",
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n",
        (
            b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>\nendobj\n"
        ),
        b"4 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n",
        f"5 0 obj\n<< /Length {len(stream_body)} >>\nstream\n".encode("latin-1")
        + stream_body
        + b"\nendstream\nendobj\n",
    ]

    output = bytearray(b"%PDF-1.4\n")
    offsets = []
    for obj in objects:
        offsets.append(len(output))
        output.extend(obj)

    xref_pos = len(output)
    output.extend(f"xref\n0 {len(objects) + 1}\n".encode("latin-1"))
    output.extend(b"0000000000 65535 f \n")
    for off in offsets:
        output.extend(f"{off:010d} 00000 n \n".encode("latin-1"))

    output.extend(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref_pos}\n%%EOF\n".encode("latin-1")
    )
    return bytes(output)


def ensure_initial_demo_data(force: bool = False) -> bool:
    """
    Seed initial academic data if the database is empty (skipped automatically during `manage.py test`).
    """
    if "test" in sys.argv and not force:
        return False

    note_mgr = NoteManager(auto_seed=True)
    if not force and Note.objects.exists():
        return False

    subjects_map = {s.name: s for s in Subject.objects.all()}
    python_subj = subjects_map.get("Python") or note_mgr.add_subject("Python")
    dsa_subj = subjects_map.get("DSA") or note_mgr.add_subject("DSA")
    dbms_subj = subjects_map.get("DBMS") or note_mgr.add_subject("DBMS")
    co_subj = subjects_map.get("Computer Organization") or note_mgr.add_subject("Computer Organization")
    java_subj = subjects_map.get("Java") or note_mgr.add_subject("Java")
    math_subj = subjects_map.get("Mathematics") or note_mgr.add_subject("Mathematics")

    sample_notes = [
        {
            "title": "Functions and Lambda Functions",
            "subject": python_subj,
            "topic": "Functions & Functional Programming",
            "covered": False,
            "reading_progress": 60,
            "content": (
                "1. Overview of Python Functions\n"
                "Functions in Python are first-class objects defined using the `def` keyword. They encapsulate reusable logic, accept positional and keyword arguments (`*args`, `**kwargs`), and return values.\n\n"
                "2. Anonymous Lambda Functions\n"
                "A lambda function is a concise, single-expression anonymous function declared with the `lambda` keyword:\n"
                "Syntax: `lambda arguments: expression`\n\n"
                "Example in Notes Manager:\n"
                "We use `sorted(notes, key=lambda note: note.title.lower())` to dynamically sort study notes alphabetically without defining boilerplate helper functions.\n\n"
                "3. Higher-Order Functions\n"
                "Lambda expressions pair naturally with `sorted()`, `map()`, and `filter()`:\n"
                "- `sorted(tasks, key=lambda t: -priority_weights[t.priority])` orders high-priority tasks first.\n"
                "- `filter(lambda q: q.completed, quizzes)` isolates completed assessments.\n\n"
                "4. Viva Key Takeaways\n"
                "- Lambda functions are restricted to a single expression and cannot contain statements like `return` or `assert`.\n"
                "- Use standard `def` functions for multi-line algorithms and `lambda` for short key/callback functions."
            ),
        },
        {
            "title": "Object-Oriented Programming & Encapsulation",
            "subject": python_subj,
            "topic": "OOP",
            "covered": True,
            "reading_progress": 100,
            "content": (
                "1. Classes and Objects\n"
                "Object-Oriented Programming (OOP) structures software around classes (blueprints) and objects (instances). Every class in Python defines `__init__` as its constructor to initialize instance attributes.\n\n"
                "2. Encapsulation & Service Architecture\n"
                "In Notes Manager, domain logic is encapsulated inside dedicated manager classes:\n"
                "- `NoteManager`: handles CRUD, lambda sorting, and generator streaming.\n"
                "- `QuizManager` & `APIService`: encapsulate PDF parsing and external AI API calls.\n"
                "- `ProgressTracker`: computes streaks and vectorized progress scores.\n\n"
                "3. Inheritance in Practice\n"
                "Django models inherit from `django.db.models.Model`, and custom exceptions like `NoteValidationError(ValueError)` inherit from built-in Python exceptions."
            ),
        },
        {
            "title": "Generators, Iterators, and the yield Keyword",
            "subject": python_subj,
            "topic": "Generators & Memory Efficiency",
            "covered": True,
            "reading_progress": 100,
            "content": (
                "1. How Generators Work\n"
                "A Python generator is a function containing one or more `yield` statements. When called, it returns a lazy iterator object without executing the function body immediately.\n\n"
                "2. State Suspension with `yield`\n"
                "Each call to `next()` executes the generator until it hits `yield`, returning the yielded value and freezing local variable state until the next iteration.\n\n"
                "3. Real Usage in Notes Manager\n"
                "- `PDFExtractor.extract_pages_generator()` yields cleaned text page-by-page.\n"
                "- `NoteManager.stream_notes_for_export()` yields note dictionaries lazily for `notes.txt` and `notes.csv`.\n"
                "- `QuizManager.stream_questions()` yields questions one at a time during quiz grading."
            ),
        },
        {
            "title": "Scientific Computing with NumPy, SciPy & Matplotlib",
            "subject": python_subj,
            "topic": "NumPy & SciPy",
            "covered": True,
            "reading_progress": 100,
            "content": (
                "1. NumPy Vectorization\n"
                "NumPy provides homogeneous `ndarray` objects and C-optimized vectorized operations (`np.mean`, `np.std`, `np.percentile`, `np.cumsum`).\n\n"
                "2. SciPy Statistical Analysis\n"
                "`scipy.stats` builds on NumPy to provide linear regression (`stats.linregress`), standardized Z-scores (`stats.zscore`), normal distributions (`stats.norm.cdf`), and Pearson correlation (`stats.pearsonr`).\n\n"
                "3. Matplotlib Visualization\n"
                "Matplotlib renders publication-grade line, bar, and network plots into PNG/SVG buffers."
            ),
        },
        {
            "title": "Graph Theory, Trees & NetworkX Knowledge Maps",
            "subject": dsa_subj,
            "topic": "Graphs & Trees",
            "covered": True,
            "reading_progress": 100,
            "content": (
                "1. Graph Representation\n"
                "A graph G = (V, E) consists of vertices (nodes) and edges. Directed graphs (`nx.DiGraph`) represent hierarchical dependencies such as Subject -> Topic -> Note.\n\n"
                "2. Degree Centrality & Traversal\n"
                "Breadth-First Search (BFS) and Depth-First Search (DFS) traverse connected components in O(V + E) time. Degree centrality measures how connected a topic hub is within the knowledge graph."
            ),
        },
        {
            "title": "Hash Tables, Heaps, and Priority Queues",
            "subject": dsa_subj,
            "topic": "Sorting & Searching",
            "covered": False,
            "reading_progress": 45,
            "content": (
                "1. Hash Tables\n"
                "Provide O(1) average-case lookup, insertion, and deletion using a hash function and collision resolution.\n\n"
                "2. Binary Heaps & Task Prioritization\n"
                "Priority queues schedule High, Medium, and Low priority tasks efficiently."
            ),
        },
        {
            "title": "SQL Joins, Indexing, and Query Optimization",
            "subject": dbms_subj,
            "topic": "SQL & Indexing",
            "covered": True,
            "reading_progress": 100,
            "content": (
                "1. Relational Joins\n"
                "INNER JOIN, LEFT OUTER JOIN, and foreign key constraints connect `Subject` and `Note` tables.\n\n"
                "2. B-Tree Indexing\n"
                "Database indexes reduce lookup complexity from O(N) full table scans to O(log N) B-Tree traversals."
            ),
        },
        {
            "title": "Database Normalization (1NF, 2NF, 3NF, BCNF) & ACID",
            "subject": dbms_subj,
            "topic": "Normalization & Transactions",
            "covered": True,
            "reading_progress": 100,
            "content": (
                "1. Normal Forms\n"
                "- 1NF: Atomic column values.\n"
                "- 2NF: No partial dependency on composite keys.\n"
                "- 3NF: No transitive dependency for non-prime attributes.\n\n"
                "2. ACID Transactions\n"
                "Atomicity, Consistency, Isolation, and Durability guarantee safe database writes (`transaction.atomic()`)."
            ),
        },
        {
            "title": "Instruction Pipelining & Cache Memory Hierarchy",
            "subject": co_subj,
            "topic": "CPU & Memory Architecture",
            "covered": True,
            "reading_progress": 100,
            "content": (
                "1. 5-Stage RISC Pipeline\n"
                "Instruction Fetch (IF), Decode (ID), Execute (EX), Memory Access (MEM), and Write Back (WB).\n\n"
                "2. Cache Locality\n"
                "Temporal and spatial locality optimize L1/L2/L3 cache hit ratios."
            ),
        },
        {
            "title": "JVM Architecture, Collections Framework & Streams",
            "subject": java_subj,
            "topic": "JVM & Collections",
            "covered": False,
            "reading_progress": 35,
            "content": (
                "1. JVM Memory Areas\n"
                "ClassLoader subsystem, Method Area, Heap, Java Stacks, and Garbage Collection roots.\n\n"
                "2. Generics and Collections\n"
                "`ArrayList`, `HashMap`, and `TreeSet` provide type-safe data structures."
            ),
        },
        {
            "title": "Probability Distributions, Regression & Linear Algebra",
            "subject": math_subj,
            "topic": "Statistics & Linear Algebra",
            "covered": True,
            "reading_progress": 100,
            "content": (
                "1. Gaussian Distribution & Z-Scores\n"
                "The standard score Z = (X - mu) / sigma quantifies how many standard deviations an observation lies from the mean.\n\n"
                "2. Ordinary Least Squares Regression\n"
                "Fits y = mx + c by minimizing the sum of squared residuals."
            ),
        },
    ]

    for item in sample_notes:
        Note.objects.create(**item)

    # Seed Quizzes with Questions
    sample_quizzes = [
        {
            "title": "Python Core, Lambda & Generators Assessment",
            "subject": "Python",
            "source_pdf_name": "python_functions_and_generators.pdf",
            "score": 4,
            "total_questions": 5,
            "correct_answers": 4,
            "incorrect_answers": 1,
            "percentage": 80.0,
            "time_taken_seconds": 145,
            "completed": True,
            "questions": [
                ("Which keyword pauses a Python generator function and returns a value lazily?", "return", "yield", "await", "break", "B", "B"),
                ("What is the time complexity of looking up a key in a Python dict on average?", "O(1)", "O(N)", "O(log N)", "O(N log N)", "A", "A"),
                ("Which lambda expression sorts Note objects by lowercase title?", "lambda n: n.title.lower()", "def(n): n.title", "yield n.title", "sort(n.title)", "A", "A"),
                ("Which NumPy function computes the arithmetic mean of a score array?", "np.median()", "np.mean()", "np.std()", "np.var()", "B", "B"),
                ("Which module in Python's standard library is used to send emails via SMTP?", "ftplib", "socket", "smtplib", "urllib", "C", "A"),
            ],
        },
        {
            "title": "DBMS Normalization & SQL Transactions Quiz",
            "subject": "DBMS",
            "source_pdf_name": "dbms_acid_normalization.pdf",
            "score": 4,
            "total_questions": 5,
            "correct_answers": 4,
            "incorrect_answers": 1,
            "percentage": 80.0,
            "time_taken_seconds": 160,
            "completed": True,
            "questions": [
                ("Which normal form eliminates transitive dependencies?", "1NF", "2NF", "3NF", "Unnormalized", "C", "C"),
                ("What does the 'A' in ACID transactions stand for?", "Availability", "Atomicity", "Asynchronous", "Alignment", "B", "B"),
                ("Which SQL clause filters grouped aggregate rows?", "WHERE", "ORDER BY", "HAVING", "JOIN", "C", "C"),
                ("Which data structure is most commonly used for relational DB indexes?", "B+ Tree", "Linked List", "Stack", "Queue", "A", "A"),
                ("Which Django context manager wraps queries in an atomic database transaction?", "transaction.atomic()", "db.commit()", "models.lock()", "sql.batch()", "A", "B"),
            ],
        },
        {
            "title": "Data Structures, Graphs & NetworkX Mastery",
            "subject": "DSA",
            "source_pdf_name": "dsa_graphs_networkx.pdf",
            "score": 5,
            "total_questions": 5,
            "correct_answers": 5,
            "incorrect_answers": 0,
            "percentage": 100.0,
            "time_taken_seconds": 130,
            "completed": True,
            "questions": [
                ("What is the time complexity of Breadth-First Search on a graph G=(V,E)?", "O(V + E)", "O(V^2)", "O(log V)", "O(E log E)", "A", "A"),
                ("Which NetworkX class represents a directed graph?", "nx.Graph", "nx.DiGraph", "nx.Tree", "nx.Vector", "B", "B"),
                ("Which SciPy function computes linear regression slope and p-value?", "stats.linregress", "stats.norm", "stats.fft", "stats.ode", "A", "A"),
                ("Which data structure operates in Last-In First-Out (LIFO) order?", "Queue", "Stack", "Heap", "Graph", "B", "B"),
                ("Which NetworkX function computes node degree centrality?", "nx.degree_centrality()", "nx.shortest_path()", "nx.pagerank_numpy()", "nx.bfs()", "A", "A"),
            ],
        },
    ]

    for q_data in sample_quizzes:
        q_questions = q_data.pop("questions")
        quiz_obj = Quiz.objects.create(**q_data)
        for idx, (q_txt, a, b, c, d, corr, usr) in enumerate(q_questions, start=1):
            Question.objects.create(
                quiz=quiz_obj,
                question_number=idx,
                question=q_txt,
                option_a=a,
                option_b=b,
                option_c=c,
                option_d=d,
                correct_answer=corr,
                user_answer=usr,
                explanation=f"Correct answer is Option {corr}.",
            )

    # Seed Daily Tasks (3 of 5 completed for the exact Part 11 experience + 1 upcoming)
    today = timezone.localdate()
    now = timezone.now()
    sample_tasks = [
        {
            "title": "Revise Python Lambda Functions & Generators for Viva",
            "description": "Review NoteManager sorting lambdas and CSV streaming generators.",
            "subject": "Python",
            "priority": Task.PRIORITY_HIGH,
            "due_date": today,
            "completed": True,
            "completed_at": now - timedelta(hours=3),
        },
        {
            "title": "Practice PDF Quiz Upload & API Service Flow",
            "description": "Upload sample_python_notes.pdf and inspect generated MCQ JSON.",
            "subject": "Python",
            "priority": Task.PRIORITY_HIGH,
            "due_date": today,
            "completed": True,
            "completed_at": now - timedelta(hours=2),
        },
        {
            "title": "Verify DBMS 3NF and BCNF Normalization Examples",
            "description": "Complete functional dependency exercises in DBMS notes.",
            "subject": "DBMS",
            "priority": Task.PRIORITY_MEDIUM,
            "due_date": today,
            "completed": True,
            "completed_at": now - timedelta(hours=1),
        },
        {
            "title": "Complete DSA Graph Centrality & NetworkX Exercise",
            "description": "Inspect the Subject-Topic-Note hierarchy on the Knowledge Map page.",
            "subject": "DSA",
            "priority": Task.PRIORITY_HIGH,
            "due_date": today,
            "completed": False,
        },
        {
            "title": "Export Study Notes to TXT and CSV for Submission",
            "description": "Download notes.txt and quiz_results.csv from the Resources page.",
            "subject": "Python",
            "priority": Task.PRIORITY_MEDIUM,
            "due_date": today + timedelta(days=2),
            "completed": False,
        },
    ]
    for t_data in sample_tasks:
        Task.objects.create(**t_data)

    # Seed 10 days of StudyLog records (including consecutive 5-day current streak)
    streak_offsets = [12, 11, 10, 9, 8, 7, 4, 3, 2, 1, 0]
    for idx, day_offset in enumerate(streak_offsets):
        log_date = today - timedelta(days=day_offset)
        StudyLog.objects.update_or_create(
            date=log_date,
            defaults={
                "notes_covered_count": 1 + (idx % 2),
                "quizzes_completed_count": 1 if idx % 3 == 0 else 0,
                "tasks_completed_count": 1 + (idx % 3),
                "study_minutes": 35 + (idx * 5),
                "overall_progress_snapshot": min(92.0, 58.0 + idx * 2.5),
            },
        )

    # Seed a valid text-searchable sample PDF in StudyResource so Resources page has ready files
    if not StudyResource.objects.filter(filename="sample_python_notes.pdf").exists():
        pdf_bytes = build_minimal_searchable_pdf(
            [
                "Python Programming & Software Engineering Study Notes",
                "Python functions are defined using the def keyword and support modular code reuse.",
                "Lambda functions create concise anonymous functions for sorting and filtering collections.",
                "Generators use the yield keyword to lazily stream records one at a time in constant memory.",
                "NumPy provides high-performance multidimensional arrays and vectorized numerical operations.",
                "SciPy provides statistical analysis tools including linear regression and z-score normalization.",
                "NetworkX models complex relationships between subjects, topics, and study notes as graphs.",
                "Python socket programming uses AF_INET and SOCK_STREAM for reliable TCP client-server communication.",
            ]
        )
        StudyResource.objects.create(
            title="Sample Python Viva Study Guide (PDF)",
            file=ContentFile(pdf_bytes, name="sample_python_notes.pdf"),
            filename="sample_python_notes.pdf",
            file_type=StudyResource.TYPE_PDF,
            file_size=len(pdf_bytes),
            subject="Python",
        )

    ProgressTracker.calculate_progress_metrics(update_today_log=True)
    return True
