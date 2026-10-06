"""
Database model for logging FTP transfers, SMTP progress reports, and Socket checks.
"""
from django.db import models


class NetworkActivityLog(models.Model):
    """Stores recent SMTP, FTP, and Socket events for status display on the frontend."""

    PROTOCOL_SOCKET = "SOCKET"
    PROTOCOL_SMTP = "SMTP"
    PROTOCOL_FTP = "FTP"

    PROTOCOL_CHOICES = [
        (PROTOCOL_SOCKET, "TCP Socket"),
        (PROTOCOL_SMTP, "SMTP Email"),
        (PROTOCOL_FTP, "FTP Transfer"),
    ]

    protocol = models.CharField(max_length=20, choices=PROTOCOL_CHOICES)
    action = models.CharField(max_length=120)
    status = models.CharField(max_length=40, default="Success")
    details = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"[{self.protocol}] {self.action} - {self.status}"
