"""Protocol definition for embedding adapters."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from quote_agent.api.health import ServiceHealth


@runtime_checkable
class EmbeddingAdapter(Protocol):
    """Interface contract for embedding model adapters."""

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Generate embedding vectors for a batch of texts."""
        ...

    async def health_check(self) -> ServiceHealth:
        """Check model availability and return health status."""
        ...
