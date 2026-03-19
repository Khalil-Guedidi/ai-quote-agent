"""SentenceTransformer-based embedding adapter."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import TYPE_CHECKING, Any

from quote_agent.api.health import ServiceHealth

if TYPE_CHECKING:
    from quote_agent.config import EmbeddingSettings

logger = logging.getLogger(__name__)


class SentenceTransformerAdapter:
    """Embedding adapter using sentence-transformers library."""

    def __init__(self, settings: EmbeddingSettings) -> None:
        self._model_name = settings.model_name
        self._batch_size = settings.batch_size
        self._device = settings.device
        self._expected_dim = settings.embedding_dim
        self._model: Any = None

        # Health check caching
        self._last_health: ServiceHealth | None = None
        self._last_health_time: float = 0.0

    def _get_model(self) -> Any:
        """Lazy-load the SentenceTransformer model."""
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            logger.info(
                "Loading embedding model",
                extra={
                    "context": {"component": "adapters.embedding", "model": self._model_name, "device": self._device}
                },
            )
            self._model = SentenceTransformer(self._model_name, device=self._device)
        return self._model

    def _encode_sync(self, texts: list[str]) -> Any:
        """Synchronous encoding — called via asyncio.to_thread."""
        model = self._get_model()
        return model.encode(
            texts,
            batch_size=self._batch_size,
            normalize_embeddings=True,
            show_progress_bar=False,
        )

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Generate embedding vectors for a batch of texts."""
        if not texts:
            return []

        vectors = await asyncio.to_thread(self._encode_sync, texts)
        result = [row.tolist() for row in vectors]

        # Validate output dimension matches expected configuration
        if result and len(result[0]) != self._expected_dim:
            msg = (
                f"Embedding dimension mismatch: model produced {len(result[0])}, "
                f"expected {self._expected_dim} (EMBEDDING__EMBEDDING_DIM)"
            )
            raise ValueError(msg)

        return result

    async def health_check(self) -> ServiceHealth:
        """Check model availability — caches result for 30s."""
        now = time.monotonic()
        if self._last_health is not None and (now - self._last_health_time) < 30.0:
            return self._last_health

        try:
            await asyncio.to_thread(self._get_model)
            self._last_health = ServiceHealth(status="healthy")
        except Exception as exc:
            logger.warning("Embedding model health check failed: %s", exc)
            self._last_health = ServiceHealth(status="unhealthy", error=str(exc))

        self._last_health_time = time.monotonic()
        return self._last_health
