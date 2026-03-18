"""Health check endpoint — reports system and service status."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from quote_agent.api.schemas import make_response
from quote_agent.models.base import get_async_session

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

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
) -> dict[str, object]:
    """Check system health including database connectivity."""
    db_health = await _check_database(session)

    overall_status: Literal["healthy", "degraded"] = "healthy"
    if db_health.status == "unhealthy":
        overall_status = "degraded"

    return make_response(
        HealthResponse(
            status=overall_status,
            services={"database": db_health},
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
