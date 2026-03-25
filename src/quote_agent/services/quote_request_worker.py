"""Quote request worker — polls pending QuoteRequests and runs the LangGraph pipeline."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import TYPE_CHECKING

from sqlalchemy import select

from quote_agent.models.quote_request import QuoteRequest
from quote_agent.services.extraction_models import ExtractedQuoteRequest, QuoteLineItem

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

logger = logging.getLogger(__name__)


class QuoteRequestWorker:
    """Background worker that picks up pending QuoteRequests and runs the graph pipeline."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        poll_interval: int = 10,
        batch_size: int = 5,
    ) -> None:
        self._session_factory = session_factory
        self._poll_interval = poll_interval
        self._batch_size = batch_size
        self._running = False
        self._total_processed = 0

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def total_processed(self) -> int:
        return self._total_processed

    async def run(self) -> None:
        """Main polling loop — runs until stopped."""
        self._running = True
        logger.info(
            "Quote request worker started",
            extra={
                "component": "services.quote_request_worker",
                "context": {
                    "poll_interval": self._poll_interval,
                    "batch_size": self._batch_size,
                },
            },
        )

        while self._running:
            try:
                processed = await self._process_pending()
                if processed > 0:
                    logger.info(
                        "Worker cycle complete",
                        extra={
                            "component": "services.quote_request_worker",
                            "context": {
                                "processed": processed,
                                "total_processed": self._total_processed,
                            },
                        },
                    )
            except Exception as exc:
                logger.exception(
                    "Unexpected error during worker cycle",
                    extra={
                        "component": "services.quote_request_worker",
                        "context": {"error": str(exc)},
                    },
                )

            await asyncio.sleep(self._poll_interval)

        logger.info(
            "Quote request worker stopped",
            extra={
                "component": "services.quote_request_worker",
                "context": {"total_processed": self._total_processed},
            },
        )

    async def stop(self) -> None:
        """Signal the polling loop to stop."""
        self._running = False
        logger.info("Quote request worker stop requested")

    async def _process_pending(self) -> int:
        """Pick up pending QuoteRequests one at a time with FOR UPDATE SKIP LOCKED.

        Each request is processed in its own transaction so that:
        - Row locks are held only for the duration of one graph invocation
        - A commit failure only loses one request, not the whole batch
        - Other workers can pick up remaining pending rows in parallel
        """
        processed = 0

        for _ in range(self._batch_size):
            async with self._session_factory() as session:
                stmt = (
                    select(QuoteRequest)
                    .where(QuoteRequest.status == "pending")
                    .order_by(QuoteRequest.created_at.asc())
                    .limit(1)
                    .with_for_update(skip_locked=True)
                )
                result = await session.execute(stmt)
                quote_request = result.scalars().first()

                if quote_request is None:
                    break

                await self._process_one(session, quote_request)
                await session.commit()
                processed += 1

        return processed

    async def _process_one(self, session: AsyncSession, quote_request: QuoteRequest) -> None:
        """Process a single QuoteRequest through the graph pipeline."""
        start_time = time.monotonic()
        request_id = str(quote_request.id)
        email_request_id = str(quote_request.email_request_id)

        logger.info(
            "Processing quote request",
            extra={
                "component": "services.quote_request_worker",
                "context": {
                    "quote_request_id": request_id,
                    "email_request_id": email_request_id,
                    "status": "processing",
                },
            },
        )

        # Mark as processing
        quote_request.status = "processing"
        await session.flush()

        try:
            # Build ExtractedQuoteRequest from stored fields
            extracted = self._build_extracted_request(quote_request)

            # Run the graph pipeline
            from quote_agent.agent.graph import get_agent_graph
            from quote_agent.agent.state import create_initial_state

            initial_state = create_initial_state(extracted)
            graph = get_agent_graph()
            graph_result = await graph.ainvoke(initial_state)

            duration_ms = int((time.monotonic() - start_time) * 1000)

            # Check for graph-level errors
            error = graph_result.get("error")
            if error:
                quote_request.status = "error"
                quote_request.error_message = str(error)

                logger.warning(
                    "Graph completed with error",
                    extra={
                        "component": "services.quote_request_worker",
                        "context": {
                            "quote_request_id": request_id,
                            "email_request_id": email_request_id,
                            "status": "error",
                            "error": str(error),
                            "duration_ms": duration_ms,
                        },
                    },
                )

                # Send error notification (fire-and-forget)
                from quote_agent.services.error_notifier import send_error_notification

                await send_error_notification(str(error))
            else:
                quote_request.status = "done"
                final_action = graph_result.get("final_action", "")

                logger.info(
                    "Quote request processed successfully",
                    extra={
                        "component": "services.quote_request_worker",
                        "context": {
                            "quote_request_id": request_id,
                            "email_request_id": email_request_id,
                            "status": "done",
                            "final_action": final_action,
                            "duration_ms": duration_ms,
                        },
                    },
                )

            self._total_processed += 1

        except Exception as exc:
            duration_ms = int((time.monotonic() - start_time) * 1000)
            quote_request.status = "error"
            quote_request.error_message = str(exc)

            logger.error(
                "Quote request processing failed",
                extra={
                    "component": "services.quote_request_worker",
                    "context": {
                        "quote_request_id": request_id,
                        "email_request_id": email_request_id,
                        "status": "error",
                        "error": str(exc),
                        "duration_ms": duration_ms,
                    },
                },
            )

            # Send error notification (fire-and-forget)
            try:
                from quote_agent.services.error_notifier import send_error_notification

                await send_error_notification(str(exc))
            except Exception:
                logger.warning("Failed to send error notification", exc_info=True)

    @staticmethod
    def _build_extracted_request(quote_request: QuoteRequest) -> ExtractedQuoteRequest:
        """Build an ExtractedQuoteRequest from stored QuoteRequest fields."""
        line_items: list[QuoteLineItem] = []
        for item_data in quote_request.line_items:
            line_items.append(
                QuoteLineItem(
                    description=str(item_data.get("description", "")),
                    quantity=item_data.get("quantity"),
                    unit=item_data.get("unit"),
                    specifications=item_data.get("specifications"),
                    reference=item_data.get("reference"),
                )
            )

        return ExtractedQuoteRequest(
            client_name=quote_request.client_name,
            client_identifier=quote_request.client_identifier,
            client_email=quote_request.client_email,
            line_items=line_items,
            urgency=quote_request.urgency,
            delivery_address=quote_request.delivery_address,
            notes=quote_request.notes,
            raw_text=quote_request.notes or "",
        )
