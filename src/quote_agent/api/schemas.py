"""Standard API response models for consistent response formatting."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel


class ApiMeta(BaseModel):
    """Metadata included in every API response."""

    timestamp: datetime


class ApiResponse[T](BaseModel):
    """Standard success response wrapper."""

    data: T
    meta: ApiMeta


class ApiError(BaseModel):
    """Error detail within an error response."""

    code: str
    message: str
    detail: str | None = None


class ApiErrorResponse(BaseModel):
    """Standard error response wrapper."""

    error: ApiError
    meta: ApiMeta


def make_response(data: Any) -> dict[str, Any]:
    """Wrap any data with standard meta.timestamp."""
    return {
        "data": data,
        "meta": {"timestamp": datetime.now(UTC).isoformat()},
    }
