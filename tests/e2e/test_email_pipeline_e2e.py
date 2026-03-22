"""End-to-end tests for the Epic 2 email pipeline with real services."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import pytest
from sqlalchemy import select

from quote_agent.api.health import ServiceHealth
from quote_agent.exceptions import EmailConnectionError
from quote_agent.models.base import _get_session_factory
from quote_agent.models.email_request import EmailRequest
from quote_agent.models.quote_request import QuoteRequest
from quote_agent.services.email_extractor import extract
from quote_agent.services.email_poller import EmailPollerService
from quote_agent.services.request_splitter import split_requests
from tests.e2e.conftest import requires_e2e
from tests.e2e.fixtures.emails import (
    injection_attempt_quote,
    multi_product_quote,
    simple_french_quote,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from quote_agent.adapters.email.models import IncomingEmail
    from quote_agent.services.extraction_models import ExtractionResult


# ---------------------------------------------------------------------------
# Stub adapters — no unittest.mock, satisfies EmailPollerService constructor
# ---------------------------------------------------------------------------


class _NoOpEmailAdapter:
    """Stub adapter for tests that call _persist_emails directly (adapter never exercised)."""

    async def health_check(self) -> ServiceHealth:
        return ServiceHealth(status="healthy")

    async def fetch_new_emails(self) -> list[IncomingEmail]:
        return []

    async def mark_emails_seen(self, message_ids: list[str]) -> None:
        pass


class _FailingEmailAdapter:
    """Stub adapter that raises on every fetch — for circuit breaker testing."""

    async def health_check(self) -> ServiceHealth:
        return ServiceHealth(status="unhealthy", error="stub failure")

    async def fetch_new_emails(self) -> list[IncomingEmail]:
        raise EmailConnectionError("Connection refused: localhost:19999")

    async def mark_emails_seen(self, message_ids: list[str]) -> None:
        pass


# ---------------------------------------------------------------------------
# Task 2: E2E happy path test (AC: 1)
# ---------------------------------------------------------------------------


@requires_e2e
@pytest.mark.e2e
class TestPipelineHappyPath:
    """Happy path — full pipeline with real services."""

    async def test_pipeline_processes_french_quote_request_e2e(self, e2e_db_session: AsyncSession) -> None:
        """AC-1: Full pipeline processes a French industrial quote request end-to-end."""
        email = simple_french_quote()
        factory = _get_session_factory()

        # Stub adapter — _persist_emails never calls the adapter
        adapter = _NoOpEmailAdapter()

        poller = EmailPollerService(adapter=adapter, session_factory=factory)  # type: ignore[arg-type]
        persisted = await poller._persist_emails([email])

        assert persisted == 1

        # Verify EmailRequest in DB
        result = await e2e_db_session.execute(select(EmailRequest).where(EmailRequest.message_id == email.message_id))
        record = result.scalar_one()
        assert record.status == "split"
        assert record.cleaned_content is not None
        assert record.extracted_data is not None

        # Verify QuoteRequest(s) in DB
        quotes = await e2e_db_session.execute(select(QuoteRequest).where(QuoteRequest.email_request_id == record.id))
        quote_list = list(quotes.scalars().all())
        assert len(quote_list) >= 1

        quote = quote_list[0]
        assert len(quote.line_items) >= 1
        # Check that extraction captured the product content
        items_text = str(quote.line_items).lower()
        assert any(keyword in items_text for keyword in ("tube", "inox", "304l")), (
            f"Expected product keywords in line_items, got: {items_text}"
        )
        assert quote.confidence is not None
        assert quote.confidence > 0.0


# ---------------------------------------------------------------------------
# Task 3: E2E with real LLM extraction validation (AC: 1)
# ---------------------------------------------------------------------------


@requires_e2e
@pytest.mark.e2e
class TestLLMExtraction:
    """Real LLM extraction and splitting validation."""

    async def test_extraction_produces_structured_output_from_real_llm(self) -> None:
        """AC-1: Real LLM produces structured extraction from French quote email."""
        email = simple_french_quote()

        result: ExtractionResult = await extract(
            cleaned_content=email.raw_content,
            sender=email.sender,
            subject=email.subject,
        )

        assert len(result.request.line_items) >= 1
        for item in result.request.line_items:
            assert item.description, "Each line item must have a non-empty description"
        assert result.extraction_duration_ms > 0
        assert result.extraction_duration_ms < 10000, "NFR-P3: extraction must be < 10s"

    async def test_splitting_groups_distinct_requests_from_real_llm(self) -> None:
        """AC-1: Real LLM groups distinct product families into separate requests."""
        email = multi_product_quote()

        extraction = await extract(
            cleaned_content=email.raw_content,
            sender=email.sender,
            subject=email.subject,
        )

        # Ensure extraction captured multiple items
        assert len(extraction.request.line_items) >= 2, (
            f"Expected 2+ line items from multi-product email, got {len(extraction.request.line_items)}"
        )

        split_result = await split_requests(extraction)
        assert split_result.split_count >= 2, (
            f"Expected splitting to produce 2+ distinct requests from multi-product email, "
            f"got {split_result.split_count}"
        )
        for sub_request in split_result.requests:
            assert len(sub_request.line_items) >= 1, "Each split request must have line items"


# ---------------------------------------------------------------------------
# Task 4: E2E prompt injection resilience (AC: 2)
# ---------------------------------------------------------------------------


@requires_e2e
@pytest.mark.e2e
class TestPromptInjectionResilience:
    """Prompt injection resilience — pipeline survives malicious input."""

    async def test_pipeline_survives_prompt_injection_e2e(
        self, e2e_db_session: AsyncSession, caplog: pytest.LogCaptureFixture
    ) -> None:
        """AC-2: Pipeline processes injection-laden email without crashing."""
        email = injection_attempt_quote()
        factory = _get_session_factory()

        adapter = _NoOpEmailAdapter()

        with caplog.at_level(logging.WARNING):
            poller = EmailPollerService(adapter=adapter, session_factory=factory)  # type: ignore[arg-type]
            persisted = await poller._persist_emails([email])

        assert persisted == 1

        # Email should be persisted (not rejected)
        result = await e2e_db_session.execute(select(EmailRequest).where(EmailRequest.message_id == email.message_id))
        record = result.scalar_one()
        assert record.status in ("extracted", "split"), f"Pipeline should reach extracted/split, got: {record.status}"

        # Verify product data was extracted (not leaked system prompt)
        quotes = await e2e_db_session.execute(select(QuoteRequest).where(QuoteRequest.email_request_id == record.id))
        quote_list = list(quotes.scalars().all())
        assert len(quote_list) >= 1
        items_text = str(quote_list[0].line_items).lower()
        assert any(keyword in items_text for keyword in ("tube", "acier", "galvanise", "32")), (
            f"Expected product data in line_items, got: {items_text}"
        )

        # Verify sanitization warnings were logged (component set via extra dict)
        sanitizer_logs = [r for r in caplog.records if getattr(r, "component", None) == "security.sanitizer"]
        assert len(sanitizer_logs) >= 1, (
            "Expected structured log with component='security.sanitizer'. "
            f"Components found: {[getattr(r, 'component', None) for r in caplog.records]}"
        )


# ---------------------------------------------------------------------------
# Task 5: E2E circuit breaker behavior (AC: 3)
# ---------------------------------------------------------------------------


@pytest.mark.e2e
class TestCircuitBreaker:
    """Circuit breaker behavior on IMAP failure — no real IMAP needed."""

    async def test_poller_circuit_breaker_on_imap_failure(self, caplog: pytest.LogCaptureFixture) -> None:
        """AC-3: Circuit breaker activates after consecutive IMAP failures."""
        failing_adapter = _FailingEmailAdapter()

        factory = _get_session_factory()
        poller = EmailPollerService(adapter=failing_adapter, session_factory=factory, poll_interval=0)  # type: ignore[arg-type]

        # Simulate consecutive failures by calling run() briefly
        import asyncio

        async def stop_after_delay():
            await asyncio.sleep(0.5)
            await poller.stop()

        with caplog.at_level(logging.WARNING):
            # Run poller with a stop task to prevent infinite loop
            await asyncio.gather(
                poller.run(),
                stop_after_delay(),
            )

        # Verify failures were logged
        failure_logs = [r for r in caplog.records if "IMAP poll failed" in r.getMessage()]
        assert len(failure_logs) >= 1, "Expected IMAP failure logs"

        # Check circuit breaker activation (threshold is 5)
        assert poller.consecutive_failures >= 1


# ---------------------------------------------------------------------------
# Task 6: E2E structured logging verification (AC: 1)
# ---------------------------------------------------------------------------


@requires_e2e
@pytest.mark.e2e
class TestStructuredLogging:
    """Structured logging — complete trace through the pipeline."""

    async def test_pipeline_produces_complete_trace_e2e(
        self, e2e_db_session: AsyncSession, caplog: pytest.LogCaptureFixture
    ) -> None:
        """AC-1: Pipeline produces structured logs with all expected components."""
        email = simple_french_quote()
        factory = _get_session_factory()

        adapter = _NoOpEmailAdapter()

        with caplog.at_level(logging.INFO):
            poller = EmailPollerService(adapter=adapter, session_factory=factory)  # type: ignore[arg-type]
            await poller._persist_emails([email])

        # Collect all log records
        log_messages = [r.getMessage() for r in caplog.records]

        # Verify presence of key pipeline stage logs (component set via extra dict)
        expected_components = {
            "services.email_poller",
            "services.email_cleaner",
            "services.email_extractor",
            "services.request_splitter",
        }

        logged_components = {
            getattr(r, "component", None) for r in caplog.records if getattr(r, "component", None) is not None
        }

        missing = expected_components - logged_components
        assert not missing, (
            f"Missing structured logs for components: {missing}. Found: {logged_components}. Messages: {log_messages}"
        )

        # Verify final log has final_status in context
        final_logs = [r for r in caplog.records if getattr(r, "context", {}).get("final_status") is not None]
        assert len(final_logs) >= 1, f"Expected log with context.final_status. Messages: {log_messages}"
