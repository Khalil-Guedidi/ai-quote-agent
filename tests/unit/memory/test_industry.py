"""Unit tests for IndustryMemory — RAG retrieval, ingestion, and chunking."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from quote_agent.memory.industry import IndustryMemory, _chunk_text
from quote_agent.memory.models import IngestionResult, KnowledgeChunk

# ---------------------------------------------------------------------------
# Chunking tests
# ---------------------------------------------------------------------------


class TestChunkText:
    """Test the paragraph-based text chunking."""

    def test_empty_content_returns_empty(self) -> None:
        assert _chunk_text("") == []

    def test_whitespace_only_returns_empty(self) -> None:
        assert _chunk_text("   \n\n   ") == []

    def test_single_short_paragraph(self) -> None:
        text = "This is a short paragraph."
        result = _chunk_text(text, max_tokens=100, overlap_tokens=10)
        assert len(result) == 1
        assert result[0] == text

    def test_two_paragraphs_within_limit(self) -> None:
        text = "First paragraph.\n\nSecond paragraph."
        result = _chunk_text(text, max_tokens=100, overlap_tokens=10)
        assert len(result) == 1
        assert "First paragraph." in result[0]
        assert "Second paragraph." in result[0]

    def test_two_paragraphs_exceeding_limit(self) -> None:
        text = "word " * 50 + "\n\n" + "other " * 50
        result = _chunk_text(text, max_tokens=60, overlap_tokens=10)
        assert len(result) == 2

    def test_overlap_tokens_between_chunks(self) -> None:
        # Create 3 paragraphs that each fit separately but not together
        p1 = " ".join(f"w{i}" for i in range(30))
        p2 = " ".join(f"x{i}" for i in range(30))
        p3 = " ".join(f"y{i}" for i in range(30))
        text = f"{p1}\n\n{p2}\n\n{p3}"
        result = _chunk_text(text, max_tokens=35, overlap_tokens=10)
        assert len(result) >= 2
        # Check overlap: last words of chunk 1 should appear at start of chunk 2
        chunk1_words = result[0].split()
        chunk2_words = result[1].split()
        last_10_of_chunk1 = chunk1_words[-10:]
        first_10_of_chunk2 = chunk2_words[:10]
        assert last_10_of_chunk1 == first_10_of_chunk2

    def test_zero_overlap(self) -> None:
        text = "word " * 50 + "\n\n" + "other " * 50
        result = _chunk_text(text, max_tokens=60, overlap_tokens=0)
        assert len(result) == 2

    def test_large_single_paragraph(self) -> None:
        """A single paragraph exceeding max_tokens is flushed immediately."""
        text = " ".join(f"w{i}" for i in range(100))
        result = _chunk_text(text, max_tokens=50, overlap_tokens=5)
        assert len(result) >= 1


# ---------------------------------------------------------------------------
# IndustryMemory.retrieve tests
# ---------------------------------------------------------------------------


class TestIndustryMemoryRetrieve:
    """Test RAG retrieval from knowledge base."""

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        session = AsyncMock()
        session.execute = AsyncMock()
        return session

    @pytest.fixture
    def mock_embedding(self) -> AsyncMock:
        adapter = AsyncMock()
        adapter.embed_texts = AsyncMock(return_value=[[0.1] * 1024])
        return adapter

    async def test_retrieve_returns_chunks(self, mock_session: AsyncMock, mock_embedding: AsyncMock) -> None:
        """AC-1: Retrieve returns KnowledgeChunk objects."""
        # Mock DB result
        mock_doc = MagicMock()
        mock_doc.content = "NF EN 10088 stainless steel norms"
        mock_doc.title = "NF EN 10088"
        mock_doc.source = "norms/en10088.md"
        mock_doc.metadata_ = {"domain": "metallurgy"}
        mock_distance = 0.15

        mock_result = MagicMock()
        mock_result.all.return_value = [(mock_doc, mock_distance)]
        mock_session.execute = AsyncMock(return_value=mock_result)

        with patch("quote_agent.memory.industry.get_settings") as mock_settings:
            mock_settings.return_value.search.hnsw_ef_search = 100
            memory = IndustryMemory(mock_session, mock_embedding)
            chunks = await memory.retrieve("stainless steel norms", top_k=5)

        assert len(chunks) == 1
        assert isinstance(chunks[0], KnowledgeChunk)
        assert chunks[0].content == "NF EN 10088 stainless steel norms"
        assert chunks[0].title == "NF EN 10088"
        assert chunks[0].score == pytest.approx(0.85)

    async def test_retrieve_empty_kb_returns_empty(self, mock_session: AsyncMock, mock_embedding: AsyncMock) -> None:
        """AC-2: Empty knowledge base returns empty list."""
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_result)

        with patch("quote_agent.memory.industry.get_settings") as mock_settings:
            mock_settings.return_value.search.hnsw_ef_search = 100
            memory = IndustryMemory(mock_session, mock_embedding)
            chunks = await memory.retrieve("anything", top_k=5)

        assert chunks == []


# ---------------------------------------------------------------------------
# IndustryMemory.ingest tests
# ---------------------------------------------------------------------------


class TestIndustryMemoryIngest:
    """Test document ingestion into knowledge base."""

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        session = AsyncMock()
        session.add = MagicMock()
        session.flush = AsyncMock()
        return session

    @pytest.fixture
    def mock_embedding(self) -> AsyncMock:
        adapter = AsyncMock()
        # Return embeddings matching chunk count
        adapter.embed_texts = AsyncMock(side_effect=lambda texts: [[0.1] * 1024 for _ in texts])
        return adapter

    async def test_ingest_creates_chunks(self, mock_session: AsyncMock, mock_embedding: AsyncMock) -> None:
        """AC-1: Ingestion creates knowledge document chunks with embeddings."""
        content = "First paragraph about norms.\n\nSecond paragraph about standards."

        with patch("quote_agent.memory.industry.get_settings") as mock_settings:
            mock_settings.return_value.industry_memory.chunk_max_tokens = 512
            mock_settings.return_value.industry_memory.chunk_overlap_tokens = 50
            memory = IndustryMemory(mock_session, mock_embedding)
            result = await memory.ingest(
                title="Industry Norms",
                content=content,
                source="norms.md",
                metadata={"domain": "metallurgy"},
            )

        assert isinstance(result, IngestionResult)
        assert result.document_title == "Industry Norms"
        assert result.chunks_created >= 1
        assert result.source == "norms.md"
        mock_session.add.assert_called()
        mock_session.flush.assert_awaited_once()

    async def test_ingest_empty_content_returns_zero_chunks(
        self, mock_session: AsyncMock, mock_embedding: AsyncMock
    ) -> None:
        """Ingesting empty content returns zero chunks."""
        with patch("quote_agent.memory.industry.get_settings") as mock_settings:
            mock_settings.return_value.industry_memory.chunk_max_tokens = 512
            mock_settings.return_value.industry_memory.chunk_overlap_tokens = 50
            memory = IndustryMemory(mock_session, mock_embedding)
            result = await memory.ingest(title="Empty", content="", source="empty.md")

        assert result.chunks_created == 0
        mock_session.add.assert_not_called()

    async def test_ingest_calls_embed_texts(self, mock_session: AsyncMock, mock_embedding: AsyncMock) -> None:
        """Ingestion embeds all chunks in a single batch."""
        content = "Para one.\n\nPara two.\n\nPara three."

        with patch("quote_agent.memory.industry.get_settings") as mock_settings:
            mock_settings.return_value.industry_memory.chunk_max_tokens = 512
            mock_settings.return_value.industry_memory.chunk_overlap_tokens = 50
            memory = IndustryMemory(mock_session, mock_embedding)
            await memory.ingest(title="Test", content=content, source="test.md")

        mock_embedding.embed_texts.assert_awaited_once()
        # All 3 paragraphs fit in one chunk (< 512 tokens), so 1 chunk
        call_args = mock_embedding.embed_texts.call_args[0][0]
        assert isinstance(call_args, list)


# ---------------------------------------------------------------------------
# IndustryMemory.list_documents tests
# ---------------------------------------------------------------------------


class TestIndustryMemoryListDocuments:
    """Test document listing."""

    async def test_list_documents_empty(self) -> None:
        session = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = []
        session.execute = AsyncMock(return_value=mock_result)

        memory = IndustryMemory(session, AsyncMock())
        docs = await memory.list_documents()
        assert docs == []

    async def test_list_documents_returns_aggregated(self) -> None:
        session = AsyncMock()
        mock_row = MagicMock()
        mock_row.title = "Norms"
        mock_row.source = "norms.md"
        mock_row.chunk_count = 3
        mock_row.created_at = "2026-03-28"
        mock_result = MagicMock()
        mock_result.all.return_value = [mock_row]
        session.execute = AsyncMock(return_value=mock_result)

        memory = IndustryMemory(session, AsyncMock())
        docs = await memory.list_documents()
        assert len(docs) == 1
        assert docs[0]["title"] == "Norms"
        assert docs[0]["chunk_count"] == 3
