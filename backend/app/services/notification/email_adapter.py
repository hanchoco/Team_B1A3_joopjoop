"""SMTP-backed email delivery adapter."""

from __future__ import annotations

import asyncio
import smtplib
from email.mime.text import MIMEText

from app.core.config import settings


def _send_email_sync(*, recipient: str, title: str, body: str) -> None:
    message = MIMEText(body)
    message["Subject"] = title
    message["From"] = settings.smtp_from_email
    message["To"] = recipient

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as smtp:
        if settings.smtp_use_tls:
            smtp.starttls()
        if settings.smtp_username and settings.smtp_password:
            smtp.login(settings.smtp_username, settings.smtp_password)
        smtp.send_message(message)


class SmtpEmailAdapter:
    """Sends one email per call over SMTP, off the event loop thread."""

    async def send_email(
        self,
        *,
        recipient: str,
        title: str,
        body: str,
        dedup_key: str,
    ) -> None:
        del dedup_key
        await asyncio.to_thread(_send_email_sync, recipient=recipient, title=title, body=body)


def get_email_adapter() -> SmtpEmailAdapter | None:
    """Return an SMTP adapter only when fully configured, else None."""

    if not settings.smtp_host or not settings.smtp_from_email:
        return None
    return SmtpEmailAdapter()


__all__ = ["SmtpEmailAdapter", "get_email_adapter"]
