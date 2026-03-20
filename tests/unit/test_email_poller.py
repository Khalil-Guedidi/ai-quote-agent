"""Tests for the EmailPollerService."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from quote_agent.adapters.email.models import IncomingEmail
from quote_agent.exceptions import AdapterError, EmailConnectionError, LLMTimeoutError
from quote_agent.models.quote_request import QuoteRequest
from quote_agent.services.email_poller import (
    _CIRCUIT_BREAKER_PAUSE,
    _CIRCUIT_BREAKER_THRESHOLD,
    EmailPollerService,
)
from quote_agent.services.extraction_models import (
    ExtractedQuoteRequest,
    ExtractionResult,
    QuoteLineItem,
    SplitResult,
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


@patch("quote_agent.services.email_poller.split_requests", new_callable=AsyncMock)
@patch("quote_agent.services.email_poller.extract", new_callable=AsyncMock)
async def test_successful_poll_persists_emails(
    mock_extract: AsyncMock,
    mock_split: AsyncMock,
    poller: EmailPollerService,
    mock_adapter: MagicMock,
    mock_session: MagicMock,
) -> None:
    """Successful poll via run() persists emails with status 'received'."""
    extraction = ExtractionResult(
        request=ExtractedQuoteRequest(raw_text="test body"),
        confidence=0.5,
        missing_fields=[],
        extraction_duration_ms=50,
    )
    mock_extract.return_value = extraction
    mock_split.return_value = SplitResult(
        requests=[extraction.request],
        split_count=1,
        split_rationale="Single or no line items",
        split_duration_ms=0,
    )
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
    # 1 EmailRequest + 1 QuoteRequest = 2 add calls
    assert mock_session.add.call_count == 2
    mock_session.commit.assert_called()
    # First poll marks the fetched email as seen; second poll marks empty list
    assert mock_adapter.mark_emails_seen.call_args_list[0].args[0] == ["<test-1@example.com>"]


@patch("quote_agent.services.email_poller.split_requests", new_callable=AsyncMock)
@patch("quote_agent.services.email_poller.extract", new_callable=AsyncMock)
async def test_cleaning_called_after_persistence(
    mock_extract: AsyncMock,
    mock_split: AsyncMock,
    poller: EmailPollerService,
    mock_adapter: MagicMock,
    mock_session: MagicMock,
) -> None:
    """Cleaning is called after successful email persistence, then extraction and splitting run."""
    extraction = ExtractionResult(
        request=ExtractedQuoteRequest(
            client_name="Test",
            line_items=[QuoteLineItem(description="test product", quantity=1.0)],
            raw_text="test body",
        ),
        confidence=0.9,
        missing_fields=[],
        extraction_duration_ms=100,
    )
    mock_extract.return_value = extraction
    mock_split.return_value = SplitResult(
        requests=[extraction.request],
        split_count=1,
        split_rationale="Single item",
        split_duration_ms=0,
    )

    email = _make_incoming_email()
    mock_adapter.fetch_new_emails = AsyncMock(return_value=[email])

    persisted = await poller._persist_emails([email])

    assert persisted == 1
    # First add is the EmailRequest, subsequent adds are QuoteRequests
    email_record = mock_session.add.call_args_list[0][0][0]
    assert email_record.status == "split"
    assert email_record.cleaned_content is not None
    assert email_record.extracted_data is not None
    mock_extract.assert_called_once()
    mock_split.assert_called_once()


@patch("quote_agent.services.email_poller.split_requests", new_callable=AsyncMock)
@patch("quote_agent.services.email_poller.extract", new_callable=AsyncMock)
async def test_extraction_called_after_cleaning(
    mock_extract: AsyncMock,
    mock_split: AsyncMock,
    poller: EmailPollerService,
    mock_adapter: MagicMock,
    mock_session: MagicMock,
) -> None:
    """Extraction is called after successful cleaning with correct arguments."""
    extraction = ExtractionResult(
        request=ExtractedQuoteRequest(
            client_name="Jean",
            line_items=[QuoteLineItem(description="Vis M8", quantity=10.0)],
            raw_text="test body",
        ),
        confidence=0.8,
        missing_fields=[],
        extraction_duration_ms=200,
    )
    mock_extract.return_value = extraction
    mock_split.return_value = SplitResult(
        requests=[extraction.request],
        split_count=1,
        split_rationale="Single item",
        split_duration_ms=0,
    )

    email = _make_incoming_email(subject="Demande de devis")
    persisted = await poller._persist_emails([email])

    assert persisted == 1
    mock_extract.assert_called_once()
    call_kwargs = mock_extract.call_args
    assert call_kwargs.kwargs["sender"] == "sender@example.com"
    assert call_kwargs.kwargs["subject"] == "Demande de devis"


@patch("quote_agent.services.email_poller.extract", new_callable=AsyncMock)
async def test_extraction_failure_does_not_block_pipeline(
    mock_extract: AsyncMock,
    poller: EmailPollerService,
    mock_adapter: MagicMock,
    mock_session: MagicMock,
) -> None:
    """Extraction failure sets extraction_failed status but doesn't block the pipeline."""
    mock_extract.side_effect = AdapterError("LLM connection failed")

    email = _make_incoming_email()
    persisted = await poller._persist_emails([email])

    assert persisted == 1
    added_record = mock_session.add.call_args[0][0]
    assert added_record.status == "extraction_failed"
    assert added_record.error_message == "LLM connection failed"


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


# --- Splitting integration tests (Story 2.4) ---


@patch("quote_agent.services.email_poller.split_requests", new_callable=AsyncMock)
@patch("quote_agent.services.email_poller.extract", new_callable=AsyncMock)
async def test_successful_extraction_and_split_creates_quote_requests(
    mock_extract: AsyncMock,
    mock_split: AsyncMock,
    poller: EmailPollerService,
    mock_adapter: MagicMock,
    mock_session: MagicMock,
) -> None:
    """Successful extraction + split creates QuoteRequest records with status 'split'."""
    items = [
        QuoteLineItem(description="Tube cuivre", quantity=50.0),
        QuoteLineItem(description="Câble 2.5mm²", quantity=100.0),
    ]
    extraction = ExtractionResult(
        request=ExtractedQuoteRequest(
            client_name="Dupont SA",
            line_items=items,
            raw_text="test body",
        ),
        confidence=0.8,
        missing_fields=[],
        extraction_duration_ms=100,
    )
    mock_extract.return_value = extraction

    # LLM splits into 2 sub-requests
    req1 = extraction.request.model_copy(update={"line_items": [items[0]]})
    req2 = extraction.request.model_copy(update={"line_items": [items[1]]})
    mock_split.return_value = SplitResult(
        requests=[req1, req2],
        split_count=2,
        split_rationale="Plumbing; Electrical",
        split_duration_ms=150,
    )

    email = _make_incoming_email()
    persisted = await poller._persist_emails([email])

    assert persisted == 1
    # session.add called: 1 EmailRequest + 2 QuoteRequests = 3 times
    assert mock_session.add.call_count == 3
    email_record = mock_session.add.call_args_list[0][0][0]
    assert email_record.status == "split"
    qr1 = mock_session.add.call_args_list[1][0][0]
    qr2 = mock_session.add.call_args_list[2][0][0]
    assert isinstance(qr1, QuoteRequest)
    assert isinstance(qr2, QuoteRequest)
    assert qr1.request_index == 0
    assert qr2.request_index == 1
    assert qr1.status == "pending"
    assert qr2.status == "pending"


@patch("quote_agent.services.email_poller.split_requests", new_callable=AsyncMock)
@patch("quote_agent.services.email_poller.extract", new_callable=AsyncMock)
async def test_single_request_email_creates_one_quote_request(
    mock_extract: AsyncMock,
    mock_split: AsyncMock,
    poller: EmailPollerService,
    mock_adapter: MagicMock,
    mock_session: MagicMock,
) -> None:
    """Single-request email creates exactly 1 QuoteRequest."""
    extraction = ExtractionResult(
        request=ExtractedQuoteRequest(
            client_name="Martin",
            line_items=[QuoteLineItem(description="Vis M8", quantity=10.0)],
            raw_text="test body",
        ),
        confidence=0.9,
        missing_fields=[],
        extraction_duration_ms=80,
    )
    mock_extract.return_value = extraction
    mock_split.return_value = SplitResult(
        requests=[extraction.request],
        split_count=1,
        split_rationale="Single item",
        split_duration_ms=0,
    )

    email = _make_incoming_email()
    persisted = await poller._persist_emails([email])

    assert persisted == 1
    # session.add called: 1 EmailRequest + 1 QuoteRequest = 2 times
    assert mock_session.add.call_count == 2
    qr = mock_session.add.call_args_list[1][0][0]
    assert isinstance(qr, QuoteRequest)
    assert qr.request_index == 0
    assert qr.client_name == "Martin"


@patch("quote_agent.services.email_poller.split_requests", new_callable=AsyncMock)
@patch("quote_agent.services.email_poller.extract", new_callable=AsyncMock)
async def test_split_failure_creates_single_quote_request(
    mock_extract: AsyncMock,
    mock_split: AsyncMock,
    poller: EmailPollerService,
    mock_adapter: MagicMock,
    mock_session: MagicMock,
) -> None:
    """Split failure still creates 1 QuoteRequest (graceful degradation)."""
    items = [
        QuoteLineItem(description="Item A", quantity=1.0),
        QuoteLineItem(description="Item B", quantity=2.0),
    ]
    extraction = ExtractionResult(
        request=ExtractedQuoteRequest(
            client_name="Durand",
            line_items=items,
            raw_text="test body",
        ),
        confidence=0.7,
        missing_fields=[],
        extraction_duration_ms=90,
    )
    mock_extract.return_value = extraction
    mock_split.side_effect = LLMTimeoutError("Splitting timed out")

    email = _make_incoming_email()
    persisted = await poller._persist_emails([email])

    assert persisted == 1
    # session.add called: 1 EmailRequest + 1 QuoteRequest (fallback) = 2 times
    assert mock_session.add.call_count == 2
    email_record = mock_session.add.call_args_list[0][0][0]
    assert email_record.status == "split"  # still marked as split
    qr = mock_session.add.call_args_list[1][0][0]
    assert isinstance(qr, QuoteRequest)
    assert qr.request_index == 0
    assert len(qr.line_items) == 2  # all items in single request


@patch("quote_agent.services.email_poller.split_requests", new_callable=AsyncMock)
@patch("quote_agent.services.email_poller.extract", new_callable=AsyncMock)
async def test_parent_child_tracking_quote_requests(
    mock_extract: AsyncMock,
    mock_split: AsyncMock,
    poller: EmailPollerService,
    mock_adapter: MagicMock,
    mock_session: MagicMock,
) -> None:
    """Parent email_request links to child quote_requests via email_request_id."""
    items = [
        QuoteLineItem(description="Produit A", quantity=5.0),
        QuoteLineItem(description="Produit B", quantity=10.0),
        QuoteLineItem(description="Produit C", quantity=15.0),
    ]
    extraction = ExtractionResult(
        request=ExtractedQuoteRequest(
            client_name="Parent Corp",
            line_items=items,
            raw_text="test body",
        ),
        confidence=0.85,
        missing_fields=[],
        extraction_duration_ms=120,
    )
    mock_extract.return_value = extraction

    req1 = extraction.request.model_copy(update={"line_items": [items[0]]})
    req2 = extraction.request.model_copy(update={"line_items": [items[1], items[2]]})
    mock_split.return_value = SplitResult(
        requests=[req1, req2],
        split_count=2,
        split_rationale="Different projects",
        split_duration_ms=200,
    )

    email = _make_incoming_email()
    persisted = await poller._persist_emails([email])

    assert persisted == 1
    email_record = mock_session.add.call_args_list[0][0][0]
    qr1 = mock_session.add.call_args_list[1][0][0]
    qr2 = mock_session.add.call_args_list[2][0][0]

    # All QuoteRequests reference the same parent email_request
    assert qr1.email_request_id == email_record.id
    assert qr2.email_request_id == email_record.id
    assert qr1.request_index == 0
    assert qr2.request_index == 1
    # Confidence propagated from extraction
    assert qr1.confidence == 0.85
    assert qr2.confidence == 0.85
