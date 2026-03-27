"""Notification system — alerts via email and Slack webhooks.

Sends notifications when:
- Upload fails
- Publication needs a decision (evaluation period ended)
- Compliance alert triggered
- Daily summary (books published, revenue estimate)
"""

import json
import logging
from dataclasses import dataclass
from enum import Enum

import httpx

log = logging.getLogger(__name__)


class NotifyLevel(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass
class NotifyConfig:
    """Notification configuration."""
    slack_webhook_url: str = ""
    email_smtp_host: str = ""
    email_smtp_port: int = 587
    email_from: str = ""
    email_to: str = ""
    email_password: str = ""
    enabled: bool = True


_config = NotifyConfig()


def configure(
    slack_webhook_url: str = "",
    email_smtp_host: str = "",
    email_smtp_port: int = 587,
    email_from: str = "",
    email_to: str = "",
    email_password: str = "",
) -> None:
    """Configure notification channels."""
    global _config
    _config = NotifyConfig(
        slack_webhook_url=slack_webhook_url,
        email_smtp_host=email_smtp_host,
        email_smtp_port=email_smtp_port,
        email_from=email_from,
        email_to=email_to,
        email_password=email_password,
    )


def notify(message: str, level: NotifyLevel = NotifyLevel.INFO, title: str = "Libro") -> bool:
    """Send a notification to all configured channels.

    Returns True if at least one channel succeeded.
    """
    if not _config.enabled:
        return False

    sent = False

    if _config.slack_webhook_url:
        if _send_slack(message, level, title):
            sent = True

    if _config.email_smtp_host and _config.email_to:
        if _send_email(message, level, title):
            sent = True

    if not sent:
        # Fallback: log the notification
        log_fn = {
            NotifyLevel.INFO: log.info,
            NotifyLevel.WARNING: log.warning,
            NotifyLevel.ERROR: log.error,
        }.get(level, log.info)
        log_fn(f"[NOTIFY] {title}: {message}")

    return sent


def notify_upload_failed(variant_id: int, error: str) -> None:
    """Notify that a KDP upload failed."""
    notify(
        f"Upload failed for variant #{variant_id}: {error}",
        level=NotifyLevel.ERROR,
        title="KDP Upload Error",
    )


def notify_decision_needed(publication_id: int, variant_title: str, recommendation: str) -> None:
    """Notify that a publication needs a decision."""
    notify(
        f"Publication #{publication_id} ({variant_title}) needs a decision. "
        f"Recommendation: {recommendation}",
        level=NotifyLevel.WARNING,
        title="Decision Needed",
    )


def notify_compliance_alert(message: str) -> None:
    """Notify of a compliance issue."""
    notify(message, level=NotifyLevel.ERROR, title="Compliance Alert")


def notify_daily_summary(published: int, revenue_estimate: float, errors: int) -> None:
    """Send daily summary notification."""
    notify(
        f"Published: {published} books | "
        f"Est. revenue: ${revenue_estimate:.2f}/mo | "
        f"Errors: {errors}",
        level=NotifyLevel.INFO,
        title="Daily Summary",
    )


# --- Channel Implementations ---

def _send_slack(message: str, level: NotifyLevel, title: str) -> bool:
    """Send notification via Slack webhook."""
    emoji = {"info": ":large_blue_circle:", "warning": ":warning:", "error": ":red_circle:"}.get(
        level.value, ":speech_balloon:"
    )

    payload = {
        "text": f"{emoji} *{title}*\n{message}",
        "unfurl_links": False,
    }

    try:
        resp = httpx.post(
            _config.slack_webhook_url,
            json=payload,
            timeout=10,
        )
        if resp.status_code == 200:
            log.debug(f"Slack notification sent: {title}")
            return True
        else:
            log.warning(f"Slack returned {resp.status_code}: {resp.text}")
            return False
    except Exception as e:
        log.warning(f"Slack notification failed: {e}")
        return False


def _send_email(message: str, level: NotifyLevel, title: str) -> bool:
    """Send notification via email (SMTP)."""
    import smtplib
    from email.mime.text import MIMEText

    subject = f"[Libro {level.value.upper()}] {title}"
    msg = MIMEText(message)
    msg["Subject"] = subject
    msg["From"] = _config.email_from
    msg["To"] = _config.email_to

    try:
        with smtplib.SMTP(_config.email_smtp_host, _config.email_smtp_port) as server:
            server.starttls()
            server.login(_config.email_from, _config.email_password)
            server.send_message(msg)
        log.debug(f"Email notification sent: {subject}")
        return True
    except Exception as e:
        log.warning(f"Email notification failed: {e}")
        return False
