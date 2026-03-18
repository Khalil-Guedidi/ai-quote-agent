"""API v1 base router — version and info endpoint."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from quote_agent.api.schemas import make_response
from quote_agent.config import get_settings

router = APIRouter(prefix="/api/v1")


@router.get("/")
async def api_v1_base() -> dict[str, Any]:
    """Return application name and version."""
    settings = get_settings()
    return make_response({"name": settings.app.name, "version": settings.app.version})
