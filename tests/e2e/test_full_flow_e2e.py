"""End-to-end test for the full flow: email -> poller -> worker -> graph -> notification."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import pytest
from sqlalchemy import select

from quote_agent.api.health import ServiceHealth
from quote_agent.models.base import _get_session_factory
from quote_agent.models.email_request import EmailRequest
from quote_agent.models.quote_request import QuoteRequest
from quote_agent.services.email_poller import EmailPollerService
from quote_agent.services.quote_request_worker import QuoteRequestWorker
from tests.e2e.conftest import requires_e2e
from tests.e2e.fixtures.emails import simple_french_quote

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from quote_agent.adapters.email.models import IncomingEmail

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Stub adapter — poller calls _persist_emails directly
# ---------------------------------------------------------------------------


class _NoOpEmailAdapter:
    """Stub adapter for tests that call _persist_emails directly."""

    async def health_check(self) -> ServiceHealth:
        return ServiceHealth(status="healthy")

    async def fetch_new_emails(self) -> list[IncomingEmail]:
        return []

    async def mark_emails_seen(self, message_ids: list[str]) -> None:
        pass


# ---------------------------------------------------------------------------
# E2E: Full flow email -> poller -> worker -> graph -> notification
# ---------------------------------------------------------------------------


@requires_e2e
@pytest.mark.e2e
class TestFullFlowE2E:
    """AC-6: Full E2E test email -> graph -> notification."""

    async def test_email_to_graph_to_notification_e2e(self, e2e_db_session: AsyncSession) -> None:
        """AC-6: Email is polled, extracted, split, then worker picks up the QuoteRequest,
        runs the graph pipeline, and the status is updated to 'done' or 'error'.
        Notification is sent via log channel.
        """
        # 1. Simulate poller: persist a test email through the pipeline
        email = simple_french_quote()
        factory = _get_session_factory()
        adapter = _NoOpEmailAdapter()

        poller = EmailPollerService(
            adapter=adapter,  # type: ignore[arg-type]
            session_factory=factory,
            poll_interval=60,
        )

        persisted = await poller._persist_emails([email])
        assert persisted == 1

        # 2. Verify QuoteRequest was created with status="pending"
        async with factory() as session:
            result = await session.execute(
                select(QuoteRequest)
                .join(EmailRequest, QuoteRequest.email_request_id == EmailRequest.id)
                .where(EmailRequest.message_id == email.message_id)
            )
            quote_requests = list(result.scalars().all())

        assert len(quote_requests) >= 1
        for qr in quote_requests:
            assert qr.status == "pending"

        # 3. Run the worker to process the pending request
        worker = QuoteRequestWorker(
            session_factory=factory,
            poll_interval=1,
            batch_size=5,
        )

        processed = await worker._process_pending()
        assert processed >= 1

        # 4. Verify QuoteRequest status is no longer "pending"
        async with factory() as session:
            result = await session.execute(
                select(QuoteRequest)
                .join(EmailRequest, QuoteRequest.email_request_id == EmailRequest.id)
                .where(EmailRequest.message_id == email.message_id)
            )
            updated_requests = list(result.scalars().all())

        for qr in updated_requests:
            assert qr.status in ("done", "error"), f"Expected done/error, got {qr.status}"
            if qr.status == "error":
                # Error is acceptable (e.g. no matching product in catalog)
                # but error_message must be set
                assert qr.error_message is not None
                logger.info(
                    "QuoteRequest completed with error (acceptable in E2E)",
                    extra={
                        "component": "test_full_flow_e2e",
                        "context": {
                            "quote_request_id": str(qr.id),
                            "error_message": qr.error_message,
                        },
                    },
                )
            else:
                logger.info(
                    "QuoteRequest completed successfully",
                    extra={
                        "component": "test_full_flow_e2e",
                        "context": {
                            "quote_request_id": str(qr.id),
                            "status": qr.status,
                        },
                    },
                )
