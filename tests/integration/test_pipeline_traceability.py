"""Integration tests for pipeline traceability logging (Story 2.6 AC-3)."""

from __future__ import annotations

import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest  # noqa: TC002

from quote_agent.adapters.email.models import IncomingEmail
from quote_agent.exceptions import LLMTimeoutError
from quote_agent.services.email_poller import EmailPollerService
from quote_agent.services.extraction_models import (
    ExtractedQuoteRequest,
    ExtractionResult,
    QuoteLineItem,
    SplitResult,
)


def _make_incoming_email(
    message_id: str = "<trace-test@example.com>",
    subject: str = "Devis tubes acier",
) -> IncomingEmail:
    return IncomingEmail(
        message_id=message_id,
        subject=subject,
        sender="client@industrie.fr",
        recipients=["devis@company.com"],
        raw_content="Bonjour, je voudrais 100 tubes acier.",
    )


def _make_mock_session() -> MagicMock:
    session = MagicMock()
    session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)))
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()

    nested_ctx = MagicMock()
    nested_ctx.__aenter__ = AsyncMock(return_value=None)
    nested_ctx.__aexit__ = AsyncMock(return_value=False)
    session.begin_nested = MagicMock(return_value=nested_ctx)
    return session


def _make_session_factory(session: MagicMock) -> MagicMock:
    factory = MagicMock()
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=session)
    ctx.__aexit__ = AsyncMock(return_value=False)
    factory.return_value = ctx
    return factory


@patch("quote_agent.services.email_poller.split_requests", new_callable=AsyncMock)
@patch("quote_agent.services.email_poller.extract", new_callable=AsyncMock)
async def test_successful_pipeline_produces_structured_logs_per_stage(
    mock_extract: AsyncMock,
    mock_split: AsyncMock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Successful email processing produces structured logs for each stage."""
    extraction = ExtractionResult(
        request=ExtractedQuoteRequest(
            client_name="Client Test",
            line_items=[QuoteLineItem(description="tubes acier", quantity=100.0)],
            raw_text="Bonjour, je voudrais 100 tubes acier.",
        ),
        confidence=0.9,
        missing_fields=[],
        extraction_duration_ms=150,
    )
    mock_extract.return_value = extraction
    mock_split.return_value = SplitResult(
        requests=[extraction.request],
        split_count=1,
        split_rationale="Single request",
        split_duration_ms=50,
    )

    session = _make_mock_session()
    factory = _make_session_factory(session)
    poller = EmailPollerService(
        adapter=MagicMock(),
        session_factory=factory,
        poll_interval=0,
        folder="INBOX",
    )

    email = _make_incoming_email()
    with caplog.at_level(logging.INFO):
        await poller._persist_emails([email])

    messages = [r.message for r in caplog.records]

    assert "Email received" in messages
    assert "Email cleaned" in messages
    assert "Extraction complete" in messages
    assert "Request splitting complete" in messages
    assert "Email pipeline complete" in messages


@patch("quote_agent.services.email_poller.extract", new_callable=AsyncMock)
async def test_failed_extraction_produces_logs_up_to_failure(
    mock_extract: AsyncMock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Failed processing (extraction failure) produces logs up to failure point with error context."""
    mock_extract.side_effect = LLMTimeoutError("LLM timed out")

    session = _make_mock_session()
    factory = _make_session_factory(session)
    poller = EmailPollerService(
        adapter=MagicMock(),
        session_factory=factory,
        poll_interval=0,
        folder="INBOX",
    )

    email = _make_incoming_email()
    with caplog.at_level(logging.INFO):
        await poller._persist_emails([email])

    messages = [r.message for r in caplog.records]

    # Should have received and cleaned logs
    assert "Email received" in messages
    assert "Email cleaned" in messages
    # Extraction failed — no extraction complete or splitting logs
    assert "Extraction complete" not in messages
    assert "Request splitting complete" not in messages
    # Pipeline complete should still be logged
    assert "Email pipeline complete" in messages
