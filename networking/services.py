"""
Networking Services Module demonstrating:
1. Part 23 — Socket Programming (`socket` TCP Server & Client heartbeat/status exchange)
2. Part 24 — SMTP Email Reports (`smtplib`, `email.mime` progress summary delivery)
3. Part 25 — FTP File Transfer (`ftplib.FTP` with safe local/mock fallback mode)
4. Part 26 — Exception Handling (Socket, SMTP, and FTP specific exceptions)
"""
import ftplib
import io
import json
import re
import smtplib
import socket
import threading
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any, Dict, List, Optional
from django.conf import settings
from django.utils import timezone
from progress.services import ProgressTracker
from .models import NetworkActivityLog


class SocketServiceError(RuntimeError):
    """Raised when TCP socket connection or message exchange fails."""


class EmailReportError(ValueError):
    """Raised when email validation or SMTP transmission fails."""


class FTPTransferError(RuntimeError):
    """Raised when an FTP upload, download, or directory listing fails."""


# ==========================================================
# PART 23: PYTHON SOCKET PROGRAMMING SERVICE
# ==========================================================
class StudySocketService:
    """
    Demonstrates Python `socket` programming (TCP AF_INET, SOCK_STREAM).
    Starts a lightweight background daemon TCP server on localhost and communicates
    via a TCP client socket to verify connection, exchange status JSON, and disconnect cleanly.
    """

    _server_thread: Optional[threading.Thread] = None
    _server_running: bool = False
    _bound_host: str = "127.0.0.1"
    _bound_port: int = 65432
    _ping_count: int = 0
    _lock = threading.Lock()

    @classmethod
    def ensure_server_started(cls) -> None:
        """Start the local TCP study status socket server in a daemon thread if not already running."""
        with cls._lock:
            if cls._server_running and cls._server_thread and cls._server_thread.is_alive():
                return

            preferred_host = getattr(settings, "SOCKET_HOST", "127.0.0.1") or "127.0.0.1"
            preferred_port = int(getattr(settings, "SOCKET_PORT", 65432) or 65432)

            server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

            try:
                server_sock.bind((preferred_host, preferred_port))
            except OSError:
                # Fallback to an available ephemeral local port if preferred port is occupied
                server_sock.bind((preferred_host, 0))

            server_sock.listen(5)
            cls._bound_host, cls._bound_port = server_sock.getsockname()
            cls._server_running = True

            def _serve_forever(sock: socket.socket) -> None:
                while cls._server_running:
                    try:
                        conn, addr = sock.accept()
                        conn.settimeout(3.0)
                        try:
                            raw_msg = conn.recv(2048).decode("utf-8", errors="replace").strip()
                            cls._ping_count += 1
                            payload = {
                                "server": "Online",
                                "socket_service": "Connected",
                                "command_received": raw_msg or "STATUS",
                                "client_address": f"{addr[0]}:{addr[1]}",
                                "server_endpoint": f"{cls._bound_host}:{cls._bound_port}",
                                "session_pings": cls._ping_count,
                                "timestamp": timezone.localtime().strftime("%Y-%m-%d %H:%M:%S"),
                            }
                            conn.sendall(json.dumps(payload).encode("utf-8"))
                        except (socket.timeout, OSError):
                            pass
                        finally:
                            # Explicitly close client socket connection
                            try:
                                conn.close()
                            except OSError:
                                pass
                    except OSError:
                        break

            cls._server_thread = threading.Thread(
                target=_serve_forever,
                args=(server_sock,),
                name="NotesManagerSocketServer",
                daemon=True,
            )
            cls._server_thread.start()

    @classmethod
    def check_status(cls, message: str = "STUDY_SESSION_PING") -> Dict[str, Any]:
        """
        Connect to the local TCP socket server as a client, send `message`,
        receive the JSON telemetry response, measure round-trip latency, and disconnect.
        """
        try:
            cls.ensure_server_started()
            start_time = time.perf_counter()

            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_sock:
                client_sock.settimeout(3.0)
                client_sock.connect((cls._bound_host, cls._bound_port))
                client_sock.sendall(message.encode("utf-8"))
                response_bytes = client_sock.recv(4096)

            latency_ms = round((time.perf_counter() - start_time) * 1000.0, 2)
            data = json.loads(response_bytes.decode("utf-8"))
            data["latency_ms"] = latency_ms
            data["protocol"] = "TCP/IP (AF_INET, SOCK_STREAM)"
            return data
        except (socket.timeout, socket.error, OSError, ValueError) as exc:
            return {
                "server": "Online",
                "socket_service": "Disconnected",
                "error": f"Socket communication error: {exc}",
                "server_endpoint": f"{cls._bound_host}:{cls._bound_port}",
                "latency_ms": 0.0,
                "protocol": "TCP/IP (AF_INET, SOCK_STREAM)",
            }


# ==========================================================
# PART 24: PYTHON SMTP PROGRESS REPORT SERVICE
# ==========================================================
class SMTPReportService:
    """
    OOP Service for formatting and sending student progress reports via Python's `smtplib`.
    Reads EMAIL_HOST, EMAIL_PORT, EMAIL_HOST_USER, EMAIL_HOST_PASSWORD from environment variables.
    """

    EMAIL_REGEX = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        use_tls: Optional[bool] = None,
    ):
        self.host = host if host is not None else getattr(settings, "EMAIL_HOST", "smtp.gmail.com")
        self.port = int(port if port is not None else getattr(settings, "EMAIL_PORT", 587))
        self.username = username if username is not None else getattr(settings, "EMAIL_HOST_USER", "")
        self.password = password if password is not None else getattr(settings, "EMAIL_HOST_PASSWORD", "")
        self.use_tls = use_tls if use_tls is not None else getattr(settings, "EMAIL_USE_TLS", True)
        self.from_email = getattr(settings, "DEFAULT_FROM_EMAIL", self.username or "notesmanager@localhost")

    @classmethod
    def validate_email_address(cls, recipient_email: str) -> str:
        cleaned = (recipient_email or "").strip()
        if not cleaned or not cls.EMAIL_REGEX.match(cleaned):
            raise EmailReportError("Please provide a valid email address (e.g., student@college.edu).")
        return cleaned

    @staticmethod
    def build_report_body(metrics: Dict[str, Any]) -> str:
        """Create a readable plain-text progress report summarizing all key metrics."""
        return (
            "========================================================\n"
            "NOTES MANAGER — ACADEMIC PROGRESS REPORT\n"
            f"Generated On: {timezone.localtime().strftime('%Y-%m-%d %H:%M:%S')}\n"
            "========================================================\n\n"
            "1. THREE-PILLAR STUDY PROGRESS:\n"
            f"   • Notes Progress   : {metrics['notes_progress']}% "
            f"({metrics['covered_notes']}/{metrics['total_notes']} notes covered)\n"
            f"   • Quiz Progress    : {metrics['quiz_progress']}% "
            f"({metrics['completed_quizzes']} quizzes completed)\n"
            f"   • Task Progress    : {metrics['task_progress']}% "
            f"({metrics['completed_tasks']}/{metrics['total_tasks']} tasks completed)\n"
            "--------------------------------------------------------\n"
            f"   ★ OVERALL PROGRESS : {metrics['overall_progress']}%\n"
            f"   Formula: {metrics['formula']}\n"
            "--------------------------------------------------------\n\n"
            "2. STUDY CONSISTENCY & STREAK:\n"
            f"   • Current Study Streak : {metrics['current_streak']} day(s)\n"
            f"   • Best Study Streak    : {metrics['best_streak']} day(s)\n"
            f"   • Weekly Consistency   : {metrics['consistency']['weekly_consistency']}%\n\n"
            "Keep up the consistent study routine!\n"
            "— Notes Manager Automated SMTP Service\n"
        )

    def send_progress_report(
        self,
        recipient_email: str,
        strict_smtp: bool = False,
    ) -> Dict[str, Any]:
        """
        Generate the progress summary and send it via `smtplib.SMTP`.
        If SMTP credentials are not configured in `.env` and `strict_smtp=False`,
        saves a local `.eml` copy and returns the full preview so college demos work offline.
        """
        recipient = self.validate_email_address(recipient_email)
        metrics = ProgressTracker.calculate_progress_metrics(update_today_log=False)
        report_text = self.build_report_body(metrics)

        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"Notes Manager Progress Report — {metrics['overall_progress']}% Overall"
        msg["From"] = self.from_email
        msg["To"] = recipient
        msg.attach(MIMEText(report_text, "plain", "utf-8"))

        if not self.username or not self.password:
            if strict_smtp:
                raise EmailReportError(
                    "SMTP credentials (EMAIL_HOST_USER / EMAIL_HOST_PASSWORD) are not configured in .env."
                )
            # Save a local .eml record for college viva demonstration when no live SMTP password is set
            outbox_dir = Path(settings.MEDIA_ROOT) / "exports"
            outbox_dir.mkdir(parents=True, exist_ok=True)
            eml_path = outbox_dir / "latest_progress_report.eml"
            eml_path.write_text(msg.as_string(), encoding="utf-8")

            NetworkActivityLog.objects.create(
                protocol=NetworkActivityLog.PROTOCOL_SMTP,
                action=f"Progress Report to {recipient}",
                status="Simulated (Local Outbox)",
                details=f"Overall Progress: {metrics['overall_progress']}% | Saved to {eml_path.name}",
            )
            return {
                "sent": True,
                "mode": "local_outbox_preview",
                "recipient": recipient,
                "smtp_host": f"{self.host}:{self.port}",
                "message": (
                    f"Progress report generated for {recipient}. "
                    "(Configure EMAIL_HOST_USER & EMAIL_HOST_PASSWORD in .env for live external SMTP delivery.)"
                ),
                "report_preview": report_text,
                "metrics": {
                    "notes_progress": metrics["notes_progress"],
                    "quiz_progress": metrics["quiz_progress"],
                    "task_progress": metrics["task_progress"],
                    "overall_progress": metrics["overall_progress"],
                    "current_streak": metrics["current_streak"],
                },
            }

        try:
            with smtplib.SMTP(self.host, self.port, timeout=15) as server:
                server.ehlo()
                if self.use_tls:
                    server.starttls()
                    server.ehlo()
                server.login(self.username, self.password)
                server.send_message(msg)

            NetworkActivityLog.objects.create(
                protocol=NetworkActivityLog.PROTOCOL_SMTP,
                action=f"Progress Report to {recipient}",
                status="Delivered via SMTP",
                details=f"Sent via {self.host}:{self.port} ({metrics['overall_progress']}%)",
            )
            return {
                "sent": True,
                "mode": "live_smtp",
                "recipient": recipient,
                "smtp_host": f"{self.host}:{self.port}",
                "message": f"Progress report successfully sent to {recipient} via {self.host}!",
                "report_preview": report_text,
                "metrics": {
                    "notes_progress": metrics["notes_progress"],
                    "quiz_progress": metrics["quiz_progress"],
                    "task_progress": metrics["task_progress"],
                    "overall_progress": metrics["overall_progress"],
                    "current_streak": metrics["current_streak"],
                },
            }
        except smtplib.SMTPAuthenticationError as exc:
            raise EmailReportError("SMTP authentication failed. Check EMAIL_HOST_USER and EMAIL_HOST_PASSWORD.") from exc
        except (smtplib.SMTPException, OSError) as exc:
            raise EmailReportError(f"SMTP error while sending progress report: {exc}") from exc


# ==========================================================
# PART 25: PYTHON FTPLIB STUDY RESOURCE TRANSFER SERVICE
# ==========================================================
class FTPResourceService:
    """
    OOP Service using Python's `ftplib.FTP` for study resource file transfers.
    Includes a clearly separated local/mock mode (`FTP_MOCK_MODE=True`) when an external
    FTP server is not running during college demonstration.
    """

    ALLOWED_EXTENSIONS = {".pdf", ".txt", ".csv", ".md", ".json"}

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        mock_mode: Optional[bool] = None,
    ):
        self.host = host if host is not None else getattr(settings, "FTP_HOST", "127.0.0.1")
        self.port = int(port if port is not None else getattr(settings, "FTP_PORT", 2121))
        self.user = user if user is not None else getattr(settings, "FTP_USER", "student")
        self.password = password if password is not None else getattr(settings, "FTP_PASSWORD", "")
        self.mock_mode = mock_mode if mock_mode is not None else getattr(settings, "FTP_MOCK_MODE", True)
        self.local_dir = Path(getattr(settings, "FTP_LOCAL_STORAGE", Path(settings.BASE_DIR) / "ftp_local_storage"))
        self.local_dir.mkdir(parents=True, exist_ok=True)
        self._ensure_sample_ftp_file()

    def _ensure_sample_ftp_file(self) -> None:
        sample = self.local_dir / "python_syllabus_reference.txt"
        if not sample.exists():
            sample.write_text(
                "NOTES MANAGER — FTP STUDY RESOURCE REPOSITORY\n"
                "==============================================\n"
                "Key Python Syllabus Topics:\n"
                "1. Object-Oriented Programming (Classes, Encapsulation, Inheritance)\n"
                "2. Functional Programming (Lambda functions, Generators & yield)\n"
                "3. Scientific Computing (NumPy arrays, SciPy stats, Matplotlib charts, NetworkX graphs)\n"
                "4. Networking (TCP Sockets, SMTP email reports, FTP file transfer via ftplib)\n",
                encoding="utf-8",
            )

    def _connect_live_ftp(self) -> ftplib.FTP:
        ftp = ftplib.FTP()
        ftp.connect(self.host, self.port, timeout=10)
        ftp.login(self.user, self.password)
        return ftp

    def list_files(self) -> Dict[str, Any]:
        """List files on the FTP server (or local FTP storage directory in mock mode)."""
        if not self.mock_mode:
            try:
                ftp = self._connect_live_ftp()
                try:
                    filenames = ftp.nlst()
                finally:
                    ftp.quit()
                files_data = [
                    {
                        "filename": Path(name).name,
                        "size_bytes": 0,
                        "formatted_size": "Remote FTP",
                        "modified": timezone.localtime().strftime("%Y-%m-%d %H:%M"),
                        "source": f"ftp://{self.host}:{self.port}",
                    }
                    for name in filenames
                    if not Path(name).name.startswith(".")
                ]
                return {
                    "mode": "Live FTP Server (ftplib.FTP)",
                    "connected": True,
                    "endpoint": f"ftp://{self.host}:{self.port}",
                    "files": files_data,
                }
            except (ftplib.all_errors, OSError) as exc:
                raise FTPTransferError(f"Could not connect to live FTP server ({self.host}:{self.port}): {exc}") from exc

        # Local / Mock Development FTP mode
        files_list: List[Dict[str, Any]] = []
        for path in sorted(self.local_dir.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
            if path.is_file() and not path.name.startswith("."):
                stat = path.stat()
                kb = round(stat.st_size / 1024.0, 1)
                files_list.append(
                    {
                        "filename": path.name,
                        "size_bytes": stat.st_size,
                        "formatted_size": f"{kb} KB" if stat.st_size >= 1024 else f"{stat.st_size} B",
                        "modified": time.strftime("%Y-%m-%d %H:%M", time.localtime(stat.st_mtime)),
                        "source": "Local FTP Storage (Mock Mode)",
                    }
                )
        return {
            "mode": "Local Development Mode (ftplib compatible)",
            "connected": True,
            "endpoint": f"ftp://{self.host}:{self.port} (Mock Directory)",
            "files": files_list,
        }

    def upload_file(self, uploaded_file: Any) -> Dict[str, Any]:
        """Upload a study resource via FTP (`ftplib.FTP.storbinary`) or to local mock FTP storage."""
        if uploaded_file is None:
            raise FTPTransferError("No file provided for FTP upload.")

        safe_name = Path(getattr(uploaded_file, "name", "")).name
        if not safe_name:
            raise FTPTransferError("Invalid filename for FTP upload.")

        ext = Path(safe_name).suffix.lower()
        if ext not in self.ALLOWED_EXTENSIONS:
            raise FTPTransferError(
                f"File extension '{ext}' is not allowed for FTP transfer. Allowed: {', '.join(sorted(self.ALLOWED_EXTENSIONS))}"
            )

        raw_bytes = uploaded_file.read()
        if not raw_bytes:
            raise FTPTransferError("Cannot upload an empty (0-byte) file via FTP.")

        if not self.mock_mode:
            try:
                ftp = self._connect_live_ftp()
                try:
                    ftp.storbinary(f"STOR {safe_name}", io.BytesIO(raw_bytes))
                finally:
                    ftp.quit()
                mode_label = f"Live FTP STOR ({self.host}:{self.port})"
            except (ftplib.all_errors, OSError) as exc:
                raise FTPTransferError(f"FTP STOR upload failed: {exc}") from exc
        else:
            target_path = self.local_dir / safe_name
            target_path.write_bytes(raw_bytes)
            mode_label = "Local FTP Storage (Mock Mode)"

        NetworkActivityLog.objects.create(
            protocol=NetworkActivityLog.PROTOCOL_FTP,
            action=f"STOR {safe_name}",
            status="Completed",
            details=f"Uploaded {len(raw_bytes)} bytes via {mode_label}",
        )
        return {
            "filename": safe_name,
            "size_bytes": len(raw_bytes),
            "status": "Upload Complete",
            "mode": mode_label,
        }

    def download_file(self, filename: str) -> bytes:
        """Download a study resource via FTP (`ftplib.FTP.retrbinary`) or from local mock FTP storage."""
        safe_name = Path(filename or "").name
        if not safe_name:
            raise FTPTransferError("Filename is required for FTP download.")

        if not self.mock_mode:
            try:
                buffer = io.BytesIO()
                ftp = self._connect_live_ftp()
                try:
                    ftp.retrbinary(f"RETR {safe_name}", buffer.write)
                finally:
                    ftp.quit()
                data = buffer.getvalue()
            except (ftplib.all_errors, OSError) as exc:
                raise FTPTransferError(f"FTP RETR download failed for '{safe_name}': {exc}") from exc
        else:
            target_path = self.local_dir / safe_name
            if not target_path.exists() or not target_path.is_file():
                raise FTPTransferError(f"File '{safe_name}' does not exist in FTP storage.")
            data = target_path.read_bytes()

        NetworkActivityLog.objects.create(
            protocol=NetworkActivityLog.PROTOCOL_FTP,
            action=f"RETR {safe_name}",
            status="Completed",
            details=f"Downloaded {len(data)} bytes",
        )
        return data
