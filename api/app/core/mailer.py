"""Minimal SMTP adapter for transactional email. Infrastructure only.

Sends one plain-text message to the SMTP server configured in Settings. The
defaults target the local Mailpit catcher (Compose profile ``mail``), so no
email leaves the machine. There is no authentication, TLS or business flow
here: verification, password reset and provider choice belong to the learner
design (see Requirements) and must be added with their own tests.
"""

import smtplib
from email.message import EmailMessage
from email.utils import formatdate, make_msgid

from app.core.config import get_settings
from app.core.errors import MailDeliveryError


def _single_line(name: str, value: str) -> str:
    value = (value or "").strip()
    if not value or "\r" in value or "\n" in value:
        raise ValueError(f"{name} must be a nonempty single line")
    return value


def build_message(to: str, subject: str, body: str, sender: str | None = None) -> EmailMessage:
    """Build a plain-text message; reject header injection before any I/O."""
    settings = get_settings()
    message = EmailMessage()
    message["From"] = _single_line("sender", sender or settings.mail_from)
    message["To"] = _single_line("to", to)
    message["Subject"] = _single_line("subject", subject)
    message["Date"] = formatdate(localtime=False)
    message["Message-ID"] = make_msgid(domain="insighthub.local")
    message.set_content(body or "")
    return message


def send_email(to: str, subject: str, body: str, sender: str | None = None) -> str:
    """Send a plain-text email and return its Message-ID.

    Transport failures raise MailDeliveryError with a fixed message; the
    recipient, body and server response are never included or logged.
    """
    settings = get_settings()
    message = build_message(to, subject, body, sender)
    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=settings.smtp_timeout_seconds) as client:
            client.send_message(message)
    except (OSError, smtplib.SMTPException):
        raise MailDeliveryError() from None
    return message["Message-ID"]
