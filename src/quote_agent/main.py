"""Application entry point — FastAPI app factory."""

from __future__ import annotations

import asyncio
import contextlib
import logging
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from starlette.middleware.base import RequestResponseEndpoint
    from starlette.responses import Response
    from starlette.types import ASGIApp

from quote_agent.api.health import router as health_router
from quote_agent.api.v1.router import router as v1_router
from quote_agent.config import get_settings
from quote_agent.exceptions import QuoteAgentError
from quote_agent.models.base import (
    _get_session_factory,
    create_async_engine_from_settings,
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manage application startup and shutdown lifecycle."""
    settings = get_settings()

    from quote_agent.audit.logger import setup_logging

    setup_logging(settings.app.log_level)

    logger.info("Application starting up")

    from quote_agent.adapters.email import get_email_adapter
    from quote_agent.services.email_poller import EmailPollerService
    from quote_agent.services.quote_request_worker import QuoteRequestWorker

    adapter = get_email_adapter()
    session_factory = _get_session_factory()
    poller = EmailPollerService(
        adapter=adapter,
        session_factory=session_factory,
        poll_interval=settings.email.poll_interval,
        folder=settings.email.folder,
    )
    app.state.email_poller = poller
    poller_task = asyncio.create_task(poller.run())

    # Start quote request worker (polls pending QuoteRequests -> graph pipeline)
    worker: QuoteRequestWorker | None
    worker_task: asyncio.Task[None] | None
    if settings.worker.enabled:
        worker = QuoteRequestWorker(
            session_factory=session_factory,
            poll_interval=settings.worker.poll_interval,
            batch_size=settings.worker.batch_size,
        )
        app.state.quote_request_worker = worker
        worker_task = asyncio.create_task(worker.run())
        logger.info("Quote request worker started")
    else:
        worker = None
        worker_task = None
        logger.info("Quote request worker disabled (WORKER__ENABLED=false)")

    # Start notification scheduler (daily batch summary + weekly report)
    from quote_agent.adapters.notification import get_notification_adapter
    from quote_agent.services.notification_scheduler import NotificationScheduler

    notification_adapter = get_notification_adapter()
    _sched = NotificationScheduler(
        schedule_settings=settings.notification_schedule,
        session_factory=session_factory,
        adapter=notification_adapter,
    )

    scheduler: NotificationScheduler | None
    if _sched.should_run():
        _sched.start()
        app.state.notification_scheduler = _sched
        scheduler = _sched
        logger.info("Notification scheduler started")
    else:
        scheduler = None
        logger.info(
            "Notification scheduler disabled (scheduler_enabled=%s, webhook=%s)",
            settings.notification_schedule.scheduler_enabled,
            bool(settings.notification.teams_webhook_url),
        )

    yield

    logger.info("Application shutting down")

    if worker is not None and worker_task is not None:
        await worker.stop()
        worker_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await worker_task
        logger.info("Quote request worker shut down (processed=%d requests)", worker.total_processed)

    if scheduler is not None:
        scheduler.stop()
        logger.info("Notification scheduler stopped")

    await poller.stop()
    poller_task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await poller_task
    logger.info("Email poller shut down (processed=%d emails)", poller.total_emails_processed)

    create_async_engine_from_settings.cache_clear()
    _get_session_factory.cache_clear()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    application = FastAPI(
        title=settings.app.name,
        version=settings.app.version,
        debug=settings.app.debug,
        lifespan=lifespan,
    )

    from quote_agent.api.erp_redirect import router as erp_redirect_router

    application.include_router(health_router)
    application.include_router(v1_router)
    application.include_router(erp_redirect_router)

    @application.exception_handler(QuoteAgentError)
    async def handle_quote_agent_error(request: Request, exc: QuoteAgentError) -> JSONResponse:
        """Handle known application errors with structured response."""
        logger.error("Application error: %s", exc)
        error_code = type(exc).__name__.upper()
        return JSONResponse(
            status_code=400,
            content={
                "error": {"code": error_code, "message": str(exc), "detail": None},
                "meta": {"timestamp": datetime.now(UTC).isoformat()},
            },
        )

    application.add_middleware(CatchAllExceptionMiddleware)

    return application


class CatchAllExceptionMiddleware(BaseHTTPMiddleware):
    """Middleware that catches unhandled exceptions and returns structured JSON."""

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """Catch unhandled exceptions and return structured 500 response."""
        try:
            return await call_next(request)
        except Exception as exc:
            logger.exception("Unhandled exception: %s", exc)
            return JSONResponse(
                status_code=500,
                content={
                    "error": {
                        "code": "INTERNAL_SERVER_ERROR",
                        "message": "An unexpected error occurred",
                        "detail": None,
                    },
                    "meta": {"timestamp": datetime.now(UTC).isoformat()},
                },
            )


app = create_app()
