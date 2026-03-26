"""IMAP email adapter implementation."""

from __future__ import annotations

import asyncio
import contextlib
import email as email_lib
import email.utils
import imaplib
import logging
import re
import time
from typing import TYPE_CHECKING

from quote_agent.adapters.email.models import IncomingEmail
from quote_agent.api.health import ServiceHealth
from quote_agent.exceptions import EmailConnectionError

if TYPE_CHECKING:
    from quote_agent.config import EmailSettings

logger = logging.getLogger(__name__)

_HEALTH_CHECK_TIMEOUT = 5.0
_HEALTH_CACHE_TTL = 30.0
_FETCH_TIMEOUT = 30.0

_HTML_TAG_RE = re.compile(r"<[^>]+>")


class IMAPAdapter:
    """Email adapter for IMAP — health check and email fetching."""

    def __init__(self, settings: EmailSettings) -> None:
        self._settings = settings
        self._last_health: ServiceHealth | None = None
        self._last_health_time: float = 0.0

    async def health_check(self) -> ServiceHealth:
        """Check IMAP connectivity and authentication with 30s caching."""
        now = time.monotonic()
        if self._last_health and (now - self._last_health_time) < _HEALTH_CACHE_TTL:
            return self._last_health

        try:
            health = await asyncio.wait_for(
                self._perform_health_check(),
                timeout=_HEALTH_CHECK_TIMEOUT,
            )
        except TimeoutError:
            health = ServiceHealth(status="unhealthy", error="Health check timed out")
        except (imaplib.IMAP4.error, ConnectionRefusedError, OSError) as exc:
            logger.warning("Email health check failed: %s", exc)
            health = ServiceHealth(status="unhealthy", error=str(exc))

        self._last_health = health
        self._last_health_time = time.monotonic()
        return health

    async def _perform_health_check(self) -> ServiceHealth:
        """Execute IMAP connect-login-select-logout sequence."""
        health = await asyncio.to_thread(self._imap_health_sync)
        return health

    def _imap_health_sync(self) -> ServiceHealth:
        """Synchronous IMAP health check — run via asyncio.to_thread."""
        conn = imaplib.IMAP4_SSL(
            self._settings.imap_server,
            self._settings.imap_port,
        )
        try:
            conn.login(
                self._settings.username,
                self._settings.password.get_secret_value(),
            )
            conn.select(self._settings.folder)
        finally:
            with contextlib.suppress(Exception):
                conn.logout()
        return ServiceHealth(status="healthy")

    async def fetch_new_emails(self) -> list[IncomingEmail]:
        """Fetch unread emails from IMAP server."""
        try:
            return await asyncio.wait_for(
                asyncio.to_thread(self._fetch_unseen_sync),
                timeout=_FETCH_TIMEOUT,
            )
        except (imaplib.IMAP4.error, ConnectionRefusedError, OSError) as exc:
            raise EmailConnectionError(str(exc)) from exc
        except TimeoutError as exc:
            raise EmailConnectionError("IMAP fetch timed out") from exc

    def _fetch_unseen_sync(self) -> list[IncomingEmail]:
        """Synchronous IMAP fetch of UNSEEN emails — run via asyncio.to_thread."""
        conn = imaplib.IMAP4_SSL(
            self._settings.imap_server,
            self._settings.imap_port,
        )
        try:
            conn.login(
                self._settings.username,
                self._settings.password.get_secret_value(),
            )
            conn.select(self._settings.folder)
            _, data = conn.search(None, "UNSEEN")
            msg_nums = data[0].split() if data[0] else []

            emails: list[IncomingEmail] = []
            for msg_num in msg_nums:
                _, msg_data = conn.fetch(msg_num, "(RFC822)")
                if not msg_data or not msg_data[0] or not isinstance(msg_data[0], tuple):
                    continue
                raw_bytes: bytes = msg_data[0][1]
                parsed = self._parse_email(raw_bytes)
                if parsed:
                    emails.append(parsed)

            return emails
        finally:
            with contextlib.suppress(Exception):
                conn.logout()

    async def mark_emails_seen(self, message_ids: list[str]) -> None:
        """Mark emails as seen on IMAP server by Message-ID header."""
        if not message_ids:
            return
        try:
            await asyncio.wait_for(
                asyncio.to_thread(self._mark_seen_sync, message_ids),
                timeout=_FETCH_TIMEOUT,
            )
        except (imaplib.IMAP4.error, ConnectionRefusedError, OSError) as exc:
            raise EmailConnectionError(str(exc)) from exc
        except TimeoutError as exc:
            raise EmailConnectionError("IMAP mark-seen timed out") from exc

    def _mark_seen_sync(self, message_ids: list[str]) -> None:
        """Mark emails as \\Seen on IMAP — run via asyncio.to_thread."""
        conn = imaplib.IMAP4_SSL(
            self._settings.imap_server,
            self._settings.imap_port,
        )
        try:
            conn.login(
                self._settings.username,
                self._settings.password.get_secret_value(),
            )
            conn.select(self._settings.folder)
            for mid in message_ids:
                _, data = conn.search(None, f'HEADER Message-ID "{mid}"')
                if data[0]:
                    for num in data[0].split():
                        conn.store(num, "+FLAGS", "\\Seen")
        finally:
            with contextlib.suppress(Exception):
                conn.logout()

    def _parse_email(self, raw_bytes: bytes) -> IncomingEmail | None:
        """Parse raw email bytes into an IncomingEmail DTO."""
        msg = email_lib.message_from_bytes(raw_bytes)

        message_id = msg.get("Message-ID", "")
        if not message_id:
            logger.warning("Email without Message-ID, skipping")
            return None

        subject = msg.get("Subject", "")
        sender = msg.get("From", "")

        recipients: list[str] = []
        for header in ("To", "Cc"):
            value = msg.get(header)
            if value:
                recipients.extend(addr.strip() for addr in value.split(",") if addr.strip())

        received_at = None
        date_str = msg.get("Date")
        if date_str:
            with contextlib.suppress(Exception):
                dt = email.utils.parsedate_to_datetime(date_str)
                # DB column is TIMESTAMP WITHOUT TIME ZONE — store as naive UTC
                if dt.tzinfo is not None:
                    from datetime import UTC

                    dt = dt.astimezone(UTC).replace(tzinfo=None)
                received_at = dt

        body = self._extract_body(msg)

        return IncomingEmail(
            message_id=message_id,
            subject=subject,
            sender=sender,
            recipients=recipients,
            raw_content=body,
            received_at=received_at,
        )

    @staticmethod
    def _extract_body(msg: email_lib.message.Message) -> str:
        """Extract plain text body, falling back to stripped HTML."""
        if msg.is_multipart():
            text_parts: list[str] = []
            html_parts: list[str] = []
            for part in msg.walk():
                content_type = part.get_content_type()
                if content_type == "text/plain":
                    payload = part.get_payload(decode=True)
                    if isinstance(payload, bytes):
                        charset = part.get_content_charset() or "utf-8"
                        text_parts.append(payload.decode(charset, errors="replace"))
                elif content_type == "text/html":
                    payload = part.get_payload(decode=True)
                    if isinstance(payload, bytes):
                        charset = part.get_content_charset() or "utf-8"
                        html_parts.append(payload.decode(charset, errors="replace"))
            if text_parts:
                return "\n".join(text_parts)
            if html_parts:
                return _HTML_TAG_RE.sub("", "\n".join(html_parts))
        else:
            payload = msg.get_payload(decode=True)
            if isinstance(payload, bytes):
                charset = msg.get_content_charset() or "utf-8"
                decoded = payload.decode(charset, errors="replace")
                if msg.get_content_type() == "text/html":
                    return _HTML_TAG_RE.sub("", decoded)
                return decoded
        return ""
