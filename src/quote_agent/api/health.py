"""Health check endpoint — reports system and service status."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from quote_agent.adapters.email import get_email_adapter
from quote_agent.adapters.erp import get_erp_adapter
from quote_agent.adapters.llm import get_llm_adapter
from quote_agent.api.schemas import make_response
from quote_agent.models.base import get_async_session

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from quote_agent.adapters.email.imap import IMAPAdapter
    from quote_agent.adapters.erp.odoo import OdooAdapter
    from quote_agent.adapters.llm.openai_compat import OpenAICompatAdapter

logger = logging.getLogger(__name__)

router = APIRouter()


class ServiceHealth(BaseModel):
    """Health status for an individual service."""

    status: Literal["healthy", "unhealthy"]
    error: str | None = None


class HealthResponse(BaseModel):
    """Aggregated health check response."""

    status: Literal["healthy", "degraded"]
    services: dict[str, ServiceHealth]


@router.get("/health")
async def health_check(
    session: AsyncSession = Depends(get_async_session),  # noqa: B008
    llm_adapter: OpenAICompatAdapter = Depends(get_llm_adapter),  # noqa: B008
    erp_adapter: OdooAdapter = Depends(get_erp_adapter),  # noqa: B008
    email_adapter: IMAPAdapter = Depends(get_email_adapter),  # noqa: B008
) -> dict[str, object]:
    """Check system health including database, LLM, ERP, and email connectivity."""
    db_health = await _check_database(session)
    llm_health = await llm_adapter.health_check()
    erp_health = await erp_adapter.health_check()
    email_health = await email_adapter.health_check()

    services = {
        "database": db_health,
        "llm": llm_health,
        "erp": erp_health,
        "email": email_health,
    }

    overall_status: Literal["healthy", "degraded"] = "healthy"
    if any(svc.status == "unhealthy" for svc in services.values()):
        overall_status = "degraded"

    return make_response(
        HealthResponse(
            status=overall_status,
            services=services,
        ).model_dump()
    )


async def _check_database(session: AsyncSession) -> ServiceHealth:
    """Execute a simple query to verify database connectivity."""
    try:
        await session.execute(text("SELECT 1"))
        return ServiceHealth(status="healthy")
    except (SQLAlchemyError, OSError) as exc:
        logger.warning("Database health check failed: %s", exc)
        return ServiceHealth(status="unhealthy", error=str(exc))
