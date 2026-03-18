"""Tests for the EmailPollerService."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from quote_agent.adapters.email.models import IncomingEmail
from quote_agent.exceptions import EmailConnectionError
from quote_agent.services.email_poller import (
    _CIRCUIT_BREAKER_PAUSE,
    _CIRCUIT_BREAKER_THRESHOLD,
    EmailPollerService,
)


def _make_incoming_email(
    message_id: str = "<test-1@example.com>",
    subject: str = "Test",
) -> IncomingEmail:
    """Create a test IncomingEmail DTO."""
    return IncomingEmail(
        message_id=message_id,
        subject=subject,
        sender="sender@example.com",
        recipients=["recipient@example.com"],
        raw_content="test body",
    )


@pytest.fixture()
def mock_adapter() -> MagicMock:
    """Create a mock IMAPAdapter."""
    adapter = MagicMock()
    adapter._settings = MagicMock()
    adapter._settings.folder = "INBOX"
    adapter.fetch_new_emails = AsyncMock(return_value=[])
    adapter.mark_emails_seen = AsyncMock()
    return adapter


@pytest.fixture()
def mock_session() -> MagicMock:
    """Create a mock async session with context manager support."""
    session = MagicMock()
    session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)))
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()

    # Support begin_nested() as async context manager (savepoints)
    nested_ctx = MagicMock()
    nested_ctx.__aenter__ = AsyncMock(return_value=None)
    nested_ctx.__aexit__ = AsyncMock(return_value=False)
    session.begin_nested = MagicMock(return_value=nested_ctx)

    return session


@pytest.fixture()
def mock_session_factory(mock_session: MagicMock) -> MagicMock:
    """Create a mock session factory."""
    factory = MagicMock()
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=mock_session)
    ctx.__aexit__ = AsyncMock(return_value=False)
    factory.return_value = ctx
    return factory


@pytest.fixture()
def poller(mock_adapter: MagicMock, mock_session_factory: MagicMock) -> EmailPollerService:
    """Create an EmailPollerService with mocked dependencies."""
    return EmailPollerService(
        adapter=mock_adapter,
        session_factory=mock_session_factory,
        poll_interval=0,  # No delay in tests
        folder="INBOX",
    )


async def test_successful_poll_persists_emails(
    poller: EmailPollerService,
    mock_adapter: MagicMock,
    mock_session: MagicMock,
) -> None:
    """Successful poll via run() persists emails with status 'received'."""
    email = _make_incoming_email()
    call_count = 0

    async def _fetch_side_effect() -> list[IncomingEmail]:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return [email]
        await poller.stop()
        return []

    mock_adapter.fetch_new_emails = AsyncMock(side_effect=_fetch_side_effect)

    with patch("quote_agent.services.email_poller.asyncio.sleep", new_callable=AsyncMock):
        await poller.run()

    assert poller.total_emails_processed == 1
    mock_session.add.assert_called_once()
    mock_session.commit.assert_called()
    # First poll marks the fetched email as seen; second poll marks empty list
    assert mock_adapter.mark_emails_seen.call_args_list[0].args[0] == ["<test-1@example.com>"]


async def test_cleaning_called_after_persistence(
    poller: EmailPollerService,
    mock_adapter: MagicMock,
    mock_session: MagicMock,
) -> None:
    """Cleaning is called after successful email persistence."""
    email = _make_incoming_email()
    mock_adapter.fetch_new_emails = AsyncMock(return_value=[email])

    persisted = await poller._persist_emails([email])

    assert persisted == 1
    # Verify the record was added and has cleaned status
    added_record = mock_session.add.call_args[0][0]
    assert added_record.status == "cleaned"
    assert added_record.cleaned_content is not None


async def test_duplicate_message_id_is_skipped(
    poller: EmailPollerService,
    mock_adapter: MagicMock,
    mock_session: MagicMock,
) -> None:
    """Duplicate message_id is skipped during persistence."""
    email = _make_incoming_email()
    mock_adapter.fetch_new_emails = AsyncMock(return_value=[email])

    # Simulate existing record found
    mock_result = MagicMock()
    mock_result.scalar_one_or_none = MagicMock(return_value="existing-uuid")
    mock_session.execute = AsyncMock(return_value=mock_result)

    persisted = await poller._persist_emails([email])

    assert persisted == 0
    mock_session.add.assert_not_called()


async def test_imap_failure_triggers_exponential_backoff(
    poller: EmailPollerService,
    mock_adapter: MagicMock,
) -> None:
    """IMAP failure in run() triggers exponential backoff (1s, 2s, 4s)."""
    call_count = 0

    async def _failing_fetch() -> list[IncomingEmail]:
        nonlocal call_count
        call_count += 1
        if call_count > 3:
            await poller.stop()
            raise EmailConnectionError("done")
        raise EmailConnectionError("Connection refused")

    mock_adapter.fetch_new_emails = AsyncMock(side_effect=_failing_fetch)

    with patch("quote_agent.services.email_poller.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        await poller.run()

    # Verify backoff pattern: 1s, 2s, 4s
    backoff_calls = [c.args[0] for c in mock_sleep.call_args_list]
    assert backoff_calls[:3] == [1, 2, 4]


async def test_circuit_breaker_triggers_after_threshold(
    poller: EmailPollerService,
    mock_adapter: MagicMock,
) -> None:
    """5 consecutive failures triggers circuit breaker (60s pause)."""
    call_count = 0

    async def _failing_fetch() -> list[IncomingEmail]:
        nonlocal call_count
        call_count += 1
        if call_count > _CIRCUIT_BREAKER_THRESHOLD:
            await poller.stop()
            raise EmailConnectionError("done")
        raise EmailConnectionError("Connection refused")

    mock_adapter.fetch_new_emails = AsyncMock(side_effect=_failing_fetch)

    with patch("quote_agent.services.email_poller.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        await poller.run()

    # The 5th failure triggers circuit breaker with 60s pause
    sleep_args = [c.args[0] for c in mock_sleep.call_args_list]
    assert _CIRCUIT_BREAKER_PAUSE in sleep_args


async def test_circuit_breaker_resets_after_success(
    poller: EmailPollerService,
    mock_adapter: MagicMock,
) -> None:
    """Circuit breaker resets consecutive_failures to 0 after successful poll via run()."""
    call_count = 0

    async def _fetch_side_effect() -> list[IncomingEmail]:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise EmailConnectionError("fail")
        if call_count == 2:
            return []  # success — should reset failures
        await poller.stop()
        return []

    mock_adapter.fetch_new_emails = AsyncMock(side_effect=_fetch_side_effect)

    with patch("quote_agent.services.email_poller.asyncio.sleep", new_callable=AsyncMock):
        await poller.run()

    assert poller.consecutive_failures == 0


async def test_graceful_shutdown_cancels_polling(
    poller: EmailPollerService,
    mock_adapter: MagicMock,
) -> None:
    """Graceful shutdown cancels the polling task."""
    mock_adapter.fetch_new_emails = AsyncMock(return_value=[])

    task = asyncio.create_task(poller.run())

    # Let it run briefly
    await asyncio.sleep(0.05)
    assert poller.is_running

    await poller.stop()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    assert not poller.is_running


async def test_poller_properties(poller: EmailPollerService) -> None:
    """Poller properties return correct initial values."""
    assert poller.is_running is False
    assert poller.total_emails_processed == 0
    assert poller.last_poll_time is None
    assert poller.consecutive_failures == 0


async def test_unexpected_error_does_not_crash_poller(
    poller: EmailPollerService,
    mock_adapter: MagicMock,
) -> None:
    """Unexpected exceptions in run() are caught and polling continues."""
    call_count = 0

    async def _fetch_side_effect() -> list[IncomingEmail]:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise RuntimeError("DB exploded")
        await poller.stop()
        return []

    mock_adapter.fetch_new_emails = AsyncMock(side_effect=_fetch_side_effect)

    with patch("quote_agent.services.email_poller.asyncio.sleep", new_callable=AsyncMock):
        await poller.run()  # Should not raise

    # Poller survived the unexpected error and continued
    assert call_count == 2
