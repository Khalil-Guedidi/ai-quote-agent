"""Tests for the email adapter — health check, caching, protocol compliance, fetch, and health endpoint."""

from __future__ import annotations

import email as email_lib
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from quote_agent.adapters.email import get_email_adapter
from quote_agent.adapters.email.imap import IMAPAdapter
from quote_agent.adapters.email.models import IncomingEmail
from quote_agent.adapters.email.protocol import EmailAdapter
from quote_agent.adapters.erp import get_erp_adapter
from quote_agent.adapters.llm import get_llm_adapter
from quote_agent.adapters.notification import get_notification_adapter
from quote_agent.exceptions import EmailConnectionError
from quote_agent.models.base import get_async_session
from tests.conftest import create_test_app, mock_healthy_adapter, mock_healthy_session


@pytest.fixture()
def email_settings(env_vars: dict[str, str], _clear_settings_cache: None) -> Any:
    """Provide EmailSettings for tests."""
    from quote_agent.config import get_settings

    return get_settings().email


@pytest.fixture()
def adapter(email_settings: Any) -> IMAPAdapter:
    """Create adapter with test settings."""
    return IMAPAdapter(email_settings)


# --- Health Check Tests ---


@patch("quote_agent.adapters.email.imap.imaplib.IMAP4_SSL")
async def test_health_check_returns_healthy_on_success(
    mock_imap_cls: MagicMock,
    adapter: IMAPAdapter,
) -> None:
    """health_check() returns healthy when IMAP login + select succeed."""
    mock_conn = MagicMock()
    mock_conn.login.return_value = ("OK", [b"Logged in"])
    mock_conn.select.return_value = ("OK", [b"42"])
    mock_imap_cls.return_value = mock_conn

    result = await adapter.health_check()

    assert result.status == "healthy"
    assert result.error is None


@patch("quote_agent.adapters.email.imap.imaplib.IMAP4_SSL")
async def test_health_check_returns_unhealthy_on_connection_error(
    mock_imap_cls: MagicMock,
    adapter: IMAPAdapter,
) -> None:
    """health_check() returns unhealthy when IMAP connection is refused."""
    mock_imap_cls.side_effect = ConnectionRefusedError("Connection refused")

    result = await adapter.health_check()

    assert result.status == "unhealthy"
    assert "Connection refused" in (result.error or "")


@patch("quote_agent.adapters.email.imap.imaplib.IMAP4_SSL")
async def test_health_check_returns_unhealthy_on_auth_failure(
    mock_imap_cls: MagicMock,
    adapter: IMAPAdapter,
) -> None:
    """health_check() returns unhealthy when IMAP login fails."""
    import imaplib

    mock_conn = MagicMock()
    mock_conn.login.side_effect = imaplib.IMAP4.error("LOGIN failed")
    mock_imap_cls.return_value = mock_conn

    result = await adapter.health_check()

    assert result.status == "unhealthy"
    assert result.error is not None


@patch("quote_agent.adapters.email.imap.imaplib.IMAP4_SSL")
async def test_health_check_returns_unhealthy_on_bad_folder(
    mock_imap_cls: MagicMock,
    adapter: IMAPAdapter,
) -> None:
    """health_check() returns unhealthy when IMAP folder select fails."""
    import imaplib

    mock_conn = MagicMock()
    mock_conn.login.return_value = ("OK", [b"Logged in"])
    mock_conn.select.side_effect = imaplib.IMAP4.error("Folder not found")
    mock_imap_cls.return_value = mock_conn

    result = await adapter.health_check()

    assert result.status == "unhealthy"
    assert result.error is not None


@patch("quote_agent.adapters.email.imap.imaplib.IMAP4_SSL")
async def test_health_check_caches_result(
    mock_imap_cls: MagicMock,
    adapter: IMAPAdapter,
) -> None:
    """Second health_check() call within 30s returns cached result."""
    mock_conn = MagicMock()
    mock_conn.login.return_value = ("OK", [b"Logged in"])
    mock_conn.select.return_value = ("OK", [b"42"])
    mock_imap_cls.return_value = mock_conn

    result1 = await adapter.health_check()
    result2 = await adapter.health_check()

    assert result1.status == "healthy"
    assert result2.status == "healthy"
    # IMAP4_SSL should only be constructed once (for the first call)
    assert mock_imap_cls.call_count == 1


# --- Protocol Compliance ---


def test_adapter_conforms_to_protocol(adapter: IMAPAdapter) -> None:
    """IMAPAdapter satisfies the EmailAdapter protocol."""
    assert isinstance(adapter, EmailAdapter)


# --- Health Endpoint Integration ---


@pytest.fixture()
def _app_env(env_vars: dict[str, str], _clear_settings_cache: None) -> None:
    """Combine env_vars and cache clearing for app instantiation."""


@pytest.mark.usefixtures("_app_env")
async def test_health_endpoint_includes_email_service() -> None:
    """GET /health response includes services.email key."""
    app = create_test_app()
    app.dependency_overrides[get_async_session] = mock_healthy_session
    app.dependency_overrides[get_llm_adapter] = mock_healthy_adapter
    app.dependency_overrides[get_erp_adapter] = mock_healthy_adapter
    app.dependency_overrides[get_email_adapter] = mock_healthy_adapter
    app.dependency_overrides[get_notification_adapter] = mock_healthy_adapter

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")

    body = response.json()
    assert "email" in body["data"]["services"]
    assert body["data"]["services"]["email"]["status"] == "healthy"

    app.dependency_overrides.clear()


# --- IncomingEmail DTO Tests ---


def _build_raw_email(
    message_id: str = "<test-123@example.com>",
    subject: str = "Test Subject",
    sender: str = "sender@example.com",
    to: str = "recipient@example.com",
    body: str = "Hello, this is a test email.",
    date: str = "Thu, 18 Mar 2026 10:00:00 +0000",
) -> bytes:
    """Build a minimal RFC822 email as bytes."""
    msg = email_lib.message.EmailMessage()
    msg["Message-ID"] = message_id
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = to
    msg["Date"] = date
    msg.set_content(body)
    return msg.as_bytes()


def test_incoming_email_dto_validation() -> None:
    """IncomingEmail validates and serializes correctly."""
    dto = IncomingEmail(
        message_id="<test@example.com>",
        subject="Test",
        sender="sender@test.com",
        recipients=["a@test.com", "b@test.com"],
        raw_content="body text",
    )
    assert dto.message_id == "<test@example.com>"
    assert dto.received_at is None
    assert len(dto.recipients) == 2


def test_incoming_email_dto_with_received_at() -> None:
    """IncomingEmail accepts a datetime for received_at."""
    from datetime import UTC, datetime

    dto = IncomingEmail(
        message_id="<test@example.com>",
        subject="Test",
        sender="sender@test.com",
        recipients=[],
        raw_content="body",
        received_at=datetime(2026, 3, 18, 10, 0, 0, tzinfo=UTC),
    )
    assert dto.received_at is not None
    assert dto.received_at.year == 2026


# --- fetch_new_emails Tests ---


@patch("quote_agent.adapters.email.imap.imaplib.IMAP4_SSL")
async def test_fetch_new_emails_returns_parsed_emails(
    mock_imap_cls: MagicMock,
    adapter: IMAPAdapter,
) -> None:
    """fetch_new_emails() fetches UNSEEN emails, parses correctly, marks as SEEN."""
    raw = _build_raw_email()
    mock_conn = MagicMock()
    mock_conn.login.return_value = ("OK", [b"Logged in"])
    mock_conn.select.return_value = ("OK", [b"1"])
    mock_conn.search.return_value = ("OK", [b"1"])
    mock_conn.fetch.return_value = ("OK", [(b"1 (RFC822 {1234})", raw)])
    mock_imap_cls.return_value = mock_conn

    result = await adapter.fetch_new_emails()

    assert len(result) == 1
    assert result[0].message_id == "<test-123@example.com>"
    assert result[0].subject == "Test Subject"
    assert result[0].sender == "sender@example.com"
    assert "recipient@example.com" in result[0].recipients
    assert "Hello, this is a test email." in result[0].raw_content
    mock_conn.store.assert_not_called()  # SEEN is marked separately after persistence


@patch("quote_agent.adapters.email.imap.imaplib.IMAP4_SSL")
async def test_fetch_new_emails_empty_mailbox(
    mock_imap_cls: MagicMock,
    adapter: IMAPAdapter,
) -> None:
    """fetch_new_emails() returns empty list when no UNSEEN emails."""
    mock_conn = MagicMock()
    mock_conn.login.return_value = ("OK", [b"Logged in"])
    mock_conn.select.return_value = ("OK", [b"0"])
    mock_conn.search.return_value = ("OK", [b""])
    mock_imap_cls.return_value = mock_conn

    result = await adapter.fetch_new_emails()

    assert result == []
    mock_conn.store.assert_not_called()


@patch("quote_agent.adapters.email.imap.imaplib.IMAP4_SSL")
async def test_fetch_new_emails_raises_on_connection_error(
    mock_imap_cls: MagicMock,
    adapter: IMAPAdapter,
) -> None:
    """fetch_new_emails() raises EmailConnectionError on connection failure."""
    mock_imap_cls.side_effect = ConnectionRefusedError("Connection refused")

    with pytest.raises(EmailConnectionError):
        await adapter.fetch_new_emails()


@patch("quote_agent.adapters.email.imap.imaplib.IMAP4_SSL")
async def test_fetch_new_emails_raises_on_auth_failure(
    mock_imap_cls: MagicMock,
    adapter: IMAPAdapter,
) -> None:
    """fetch_new_emails() raises EmailConnectionError on auth failure."""
    import imaplib

    mock_conn = MagicMock()
    mock_conn.login.side_effect = imaplib.IMAP4.error("LOGIN failed")
    mock_imap_cls.return_value = mock_conn

    with pytest.raises(EmailConnectionError):
        await adapter.fetch_new_emails()


# --- mark_emails_seen Tests ---


@patch("quote_agent.adapters.email.imap.imaplib.IMAP4_SSL")
async def test_mark_emails_seen_marks_by_message_id(
    mock_imap_cls: MagicMock,
    adapter: IMAPAdapter,
) -> None:
    """mark_emails_seen() searches by Message-ID and marks as \\Seen."""
    mock_conn = MagicMock()
    mock_conn.login.return_value = ("OK", [b"Logged in"])
    mock_conn.select.return_value = ("OK", [b"1"])
    mock_conn.search.return_value = ("OK", [b"1"])
    mock_imap_cls.return_value = mock_conn

    await adapter.mark_emails_seen(["<test-123@example.com>"])

    mock_conn.search.assert_called_once_with(None, 'HEADER Message-ID "<test-123@example.com>"')
    mock_conn.store.assert_called_once_with(b"1", "+FLAGS", "\\Seen")


@patch("quote_agent.adapters.email.imap.imaplib.IMAP4_SSL")
async def test_mark_emails_seen_skips_empty_list(
    mock_imap_cls: MagicMock,
    adapter: IMAPAdapter,
) -> None:
    """mark_emails_seen() does nothing for an empty list."""
    await adapter.mark_emails_seen([])

    mock_imap_cls.assert_not_called()
