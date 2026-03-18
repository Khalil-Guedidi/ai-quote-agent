"""Typed DTOs for the LLM adapter layer."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class LLMMessage(BaseModel):
    """A single message in an LLM conversation."""

    role: Literal["system", "user", "assistant"]
    content: str


class LLMUsage(BaseModel):
    """Token usage statistics from an LLM response."""

    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class LLMRequest(BaseModel):
    """Request payload for the LLM adapter."""

    messages: list[LLMMessage]
    model: str | None = None
    temperature: float = 0.0
    max_tokens: int | None = None


class LLMResponse(BaseModel):
    """Response payload from the LLM adapter."""

    content: str
    model: str
    usage: LLMUsage | None = None
