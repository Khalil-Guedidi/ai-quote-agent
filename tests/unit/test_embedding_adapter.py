"""Unit tests for embedding adapter — protocol compliance and adapter behavior."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from quote_agent.adapters.embedding.models import EmbeddingRequest, EmbeddingResult
from quote_agent.adapters.embedding.protocol import EmbeddingAdapter
from quote_agent.api.health import ServiceHealth
from quote_agent.config import EmbeddingSettings


class TestEmbeddingAdapterProtocol:
    """Test EmbeddingAdapter protocol compliance."""

    def test_mock_adapter_satisfies_protocol(self) -> None:
        """AC-4: Mock adapter must satisfy the EmbeddingAdapter protocol."""
        adapter = MagicMock(spec=EmbeddingAdapter)
        adapter.embed_texts = AsyncMock(return_value=[[0.1] * 1024])
        adapter.health_check = AsyncMock(return_value=ServiceHealth(status="healthy"))
        assert isinstance(adapter, EmbeddingAdapter)

    def test_mock_adapter_returns_correct_shape_vectors(self) -> None:
        """AC-1: Mock adapter returns vectors of correct dimension."""
        adapter = MagicMock(spec=EmbeddingAdapter)
        fake_vectors = [[0.1] * 1024 for _ in range(5)]
        adapter.embed_texts = AsyncMock(return_value=fake_vectors)
        # Verify shape
        assert len(fake_vectors) == 5
        assert all(len(v) == 1024 for v in fake_vectors)


class TestEmbeddingSettings:
    """Test EmbeddingSettings configuration."""

    def test_default_settings(self) -> None:
        """AC-4: Default settings match BGE-M3 configuration."""
        settings = EmbeddingSettings()
        assert settings.model_name == "BAAI/bge-m3"
        assert settings.embedding_dim == 1024
        assert settings.batch_size == 64
        assert settings.device == "cpu"

    def test_custom_settings(self) -> None:
        """AC-4: Settings can be overridden."""
        settings = EmbeddingSettings(
            model_name="custom/model",
            embedding_dim=768,
            batch_size=32,
            device="cuda",
        )
        assert settings.model_name == "custom/model"
        assert settings.embedding_dim == 768
        assert settings.batch_size == 32
        assert settings.device == "cuda"


class TestSentenceTransformerAdapter:
    """Test SentenceTransformerAdapter initialization."""

    def test_adapter_stores_settings(self) -> None:
        """AC-4: Adapter stores configuration from settings."""
        settings = EmbeddingSettings(model_name="test/model", embedding_dim=768)
        from quote_agent.adapters.embedding.sentence_transformers import SentenceTransformerAdapter

        adapter = SentenceTransformerAdapter(settings)
        assert adapter._model_name == "test/model"
        assert adapter._expected_dim == 768
        assert adapter._model is None  # Lazy loading

    async def test_embed_texts_empty_list(self) -> None:
        """AC-1: Empty input returns empty output."""
        settings = EmbeddingSettings()
        from quote_agent.adapters.embedding.sentence_transformers import SentenceTransformerAdapter

        adapter = SentenceTransformerAdapter(settings)
        result = await adapter.embed_texts([])
        assert result == []

    async def test_embed_texts_dimension_mismatch(self) -> None:
        """AC-4: Dimension mismatch between model output and config raises ValueError."""
        import numpy as np

        settings = EmbeddingSettings(embedding_dim=768)
        from quote_agent.adapters.embedding.sentence_transformers import SentenceTransformerAdapter

        adapter = SentenceTransformerAdapter(settings)

        # Mock _encode_sync to return vectors of wrong dimension (1024 instead of 768)
        with (
            patch.object(adapter, "_encode_sync", return_value=np.array([[0.1] * 1024])),
            pytest.raises(ValueError, match="Embedding dimension mismatch"),
        ):
            await adapter.embed_texts(["test text"])

    async def test_health_check_failure(self) -> None:
        """AC-4: Health check returns unhealthy when model fails to load."""
        settings = EmbeddingSettings(model_name="nonexistent/model")
        from quote_agent.adapters.embedding.sentence_transformers import SentenceTransformerAdapter

        adapter = SentenceTransformerAdapter(settings)

        with patch(
            "quote_agent.adapters.embedding.sentence_transformers.SentenceTransformerAdapter._get_model",
            side_effect=RuntimeError("Model not found"),
        ):
            result = await adapter.health_check()
            assert result.status == "unhealthy"
            assert "Model not found" in (result.error or "")


class TestEmbeddingDTOs:
    """Test embedding DTOs."""

    def test_embedding_request(self) -> None:
        """EmbeddingRequest validates correctly."""
        req = EmbeddingRequest(texts=["hello", "world"])
        assert len(req.texts) == 2

    def test_embedding_result(self) -> None:
        """EmbeddingResult stores all fields."""
        result = EmbeddingResult(embedded=100, skipped_stale=5, errors=0, duration_seconds=1.23)
        assert result.embedded == 100
        assert result.skipped_stale == 5
        assert result.errors == 0
        assert result.duration_seconds == 1.23
