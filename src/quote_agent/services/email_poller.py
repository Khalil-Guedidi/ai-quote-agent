"""Email polling service — fetches new emails on a configurable interval."""

from __future__ import annotations

import asyncio
import contextlib
import logging
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from quote_agent.exceptions import AdapterError, EmailConnectionError, LLMTimeoutError
from quote_agent.models.email_request import EmailRequest
from quote_agent.models.quote_request import QuoteRequest
from quote_agent.services.email_cleaner import clean
from quote_agent.services.email_extractor import extract
from quote_agent.services.request_splitter import split_requests

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    from quote_agent.adapters.email.imap import IMAPAdapter
    from quote_agent.adapters.email.models import IncomingEmail

logger = logging.getLogger(__name__)

_CIRCUIT_BREAKER_THRESHOLD = 5
_CIRCUIT_BREAKER_PAUSE = 60


class EmailPollerService:
    """Polls IMAP for new emails and persists them to the database."""

    def __init__(
        self,
        adapter: IMAPAdapter,
        session_factory: async_sessionmaker[AsyncSession],
        poll_interval: int = 60,
        folder: str = "INBOX",
    ) -> None:
        self._adapter = adapter
        self._session_factory = session_factory
        self._poll_interval = poll_interval
        self._folder = folder
        self._running = False
        self._consecutive_failures = 0
        self._total_emails_processed = 0
        self._last_poll_time: float | None = None

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def total_emails_processed(self) -> int:
        return self._total_emails_processed

    @property
    def last_poll_time(self) -> float | None:
        return self._last_poll_time

    @property
    def consecutive_failures(self) -> int:
        return self._consecutive_failures

    async def run(self) -> None:
        """Main polling loop — runs until stopped."""
        self._running = True
        logger.info("Email poller started (interval=%ds)", self._poll_interval)

        while self._running:
            try:
                emails = await self._adapter.fetch_new_emails()
                persisted = await self._persist_emails(emails)

                # Mark fetched emails as seen — safe to fail, dedup handles re-fetch
                with contextlib.suppress(EmailConnectionError):
                    await self._adapter.mark_emails_seen(
                        [e.message_id for e in emails]
                    )

                self._consecutive_failures = 0
                self._last_poll_time = asyncio.get_event_loop().time()

                logger.info(
                    "Poll complete: found=%d persisted=%d total=%d",
                    len(emails),
                    persisted,
                    self._total_emails_processed,
                )
            except EmailConnectionError as exc:
                self._consecutive_failures += 1
                logger.warning(
                    "IMAP poll failed (attempt %d): %s",
                    self._consecutive_failures,
                    exc,
                )

                if self._consecutive_failures >= _CIRCUIT_BREAKER_THRESHOLD:
                    logger.error(
                        "Circuit breaker triggered after %d consecutive failures, "
                        "pausing for %ds",
                        self._consecutive_failures,
                        _CIRCUIT_BREAKER_PAUSE,
                    )
                    await asyncio.sleep(_CIRCUIT_BREAKER_PAUSE)
                    continue

                backoff = 2 ** (self._consecutive_failures - 1)
                logger.info("Retrying in %ds (backoff)", backoff)
                await asyncio.sleep(backoff)
                continue
            except Exception as exc:
                logger.exception("Unexpected error during poll: %s", exc)
                continue

            await asyncio.sleep(self._poll_interval)

        logger.info("Email poller stopped")

    async def stop(self) -> None:
        """Signal the polling loop to stop."""
        self._running = False
        logger.info("Email poller stop requested")

    async def _persist_emails(self, emails: list[IncomingEmail]) -> int:
        """Persist fetched emails to the database, deduplicating by message_id."""
        persisted = 0
        async with self._session_factory() as session:
            for incoming in emails:
                existing = await session.execute(
                    select(EmailRequest.id).where(
                        EmailRequest.message_id == incoming.message_id
                    )
                )
                if existing.scalar_one_or_none() is not None:
                    logger.debug(
                        "Skipping duplicate email: message_id=%s",
                        incoming.message_id,
                    )
                    continue

                record = EmailRequest(
                    message_id=incoming.message_id,
                    subject=incoming.subject,
                    sender=incoming.sender,
                    recipients=incoming.recipients,
                    raw_content=incoming.raw_content,
                    folder=self._folder,
                    status="received",
                    received_at=incoming.received_at,
                )
                try:
                    async with session.begin_nested():
                        session.add(record)
                        await session.flush()
                    logger.info(
                        "Email received",
                        extra={
                            "component": "services.email_poller",
                            "context": {
                                "email_request_id": str(record.id),
                                "message_id": record.message_id,
                                "sender": record.sender,
                                "subject": record.subject,
                                "status": "received",
                            },
                        },
                    )
                    # Clean email content inline (pure CPU, <1ms)
                    try:
                        record.cleaned_content = clean(incoming.raw_content)
                        record.status = "cleaned"
                        logger.info(
                            "Email cleaned",
                            extra={
                                "component": "services.email_cleaner",
                                "context": {
                                    "email_request_id": str(record.id),
                                    "status": "cleaned",
                                    "raw_length": len(incoming.raw_content),
                                    "cleaned_length": len(record.cleaned_content),
                                },
                            },
                        )
                    except Exception as exc:
                        record.status = "cleaning_failed"
                        record.error_message = str(exc)
                        logger.warning(
                            "Cleaning failed",
                            extra={
                                "component": "services.email_cleaner",
                                "context": {
                                    "email_request_id": str(record.id),
                                    "message_id": incoming.message_id,
                                    "status": "cleaning_failed",
                                    "error": str(exc),
                                },
                            },
                        )

                    # Extract structured data via LLM (only if cleaning succeeded)
                    if record.status == "cleaned":
                        try:
                            extraction_result = await extract(
                                cleaned_content=record.cleaned_content,  # type: ignore[arg-type]
                                sender=record.sender,
                                subject=record.subject,
                            )
                            record.extracted_data = extraction_result.request.model_dump()
                            record.status = "extracted"
                            logger.info(
                                "Extraction complete",
                                extra={
                                    "component": "services.email_extractor",
                                    "context": {
                                        "email_request_id": str(record.id),
                                        "line_item_count": len(extraction_result.request.line_items),
                                        "missing_fields": extraction_result.missing_fields,
                                        "duration_ms": extraction_result.extraction_duration_ms,
                                    },
                                },
                            )
                        except (LLMTimeoutError, AdapterError) as exc:
                            record.status = "extraction_failed"
                            record.error_message = str(exc)
                            logger.warning(
                                "Extraction failed for %s: %s",
                                incoming.message_id,
                                exc,
                            )

                    # Split extracted data into sub-requests (only if extraction succeeded)
                    if record.status == "extracted":
                        try:
                            split_result = await split_requests(extraction_result)
                            for idx, sub_request in enumerate(split_result.requests):
                                quote_req = QuoteRequest(
                                    email_request_id=record.id,
                                    request_index=idx,
                                    line_items=[item.model_dump() for item in sub_request.line_items],
                                    client_name=sub_request.client_name,
                                    client_identifier=sub_request.client_identifier,
                                    client_email=sub_request.client_email,
                                    urgency=sub_request.urgency,
                                    delivery_address=sub_request.delivery_address,
                                    notes=sub_request.notes,
                                    status="pending",
                                    confidence=extraction_result.confidence,
                                )
                                session.add(quote_req)
                            record.status = "split"
                            logger.info(
                                "Request splitting complete",
                                extra={
                                    "component": "services.request_splitter",
                                    "context": {
                                        "email_request_id": str(record.id),
                                        "split_count": split_result.split_count,
                                        "split_rationale": split_result.split_rationale,
                                        "duration_ms": split_result.split_duration_ms,
                                    },
                                },
                            )
                        except (LLMTimeoutError, AdapterError) as exc:
                            # Graceful degradation: create single QuoteRequest with all items
                            quote_req = QuoteRequest(
                                email_request_id=record.id,
                                request_index=0,
                                line_items=[item.model_dump() for item in extraction_result.request.line_items],
                                client_name=extraction_result.request.client_name,
                                client_identifier=extraction_result.request.client_identifier,
                                client_email=extraction_result.request.client_email,
                                urgency=extraction_result.request.urgency,
                                delivery_address=extraction_result.request.delivery_address,
                                notes=extraction_result.request.notes,
                                status="pending",
                                confidence=extraction_result.confidence,
                            )
                            session.add(quote_req)
                            record.status = "split"
                            logger.warning(
                                "Splitting failed for %s, falling back to single request: %s",
                                incoming.message_id,
                                exc,
                            )
                    logger.info(
                        "Email pipeline complete",
                        extra={
                            "component": "services.email_poller",
                            "context": {
                                "email_request_id": str(record.id),
                                "message_id": record.message_id,
                                "final_status": record.status,
                            },
                        },
                    )
                    persisted += 1
                    self._total_emails_processed += 1
                except IntegrityError:
                    logger.debug(
                        "Duplicate email caught by constraint: message_id=%s",
                        incoming.message_id,
                    )

            await session.commit()
        return persisted
