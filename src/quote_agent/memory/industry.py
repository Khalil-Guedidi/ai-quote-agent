"""Industry knowledge RAG retrieval and ingestion."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from sqlalchemy import select, text

from quote_agent.config import get_settings
from quote_agent.memory.models import IngestionResult, KnowledgeChunk
from quote_agent.models.knowledge_document import KnowledgeDocument

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from quote_agent.adapters.embedding.protocol import EmbeddingAdapter

logger = logging.getLogger(__name__)


def _chunk_text(content: str, max_tokens: int = 512, overlap_tokens: int = 50) -> list[str]:
    """Split text into overlapping chunks by paragraph boundaries.

    Uses word count as token estimate (no tiktoken dependency).
    """
    paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]

    if not paragraphs:
        return [content.strip()] if content.strip() else []

    chunks: list[str] = []
    current_words: list[str] = []

    for paragraph in paragraphs:
        para_words = paragraph.split()

        # If adding this paragraph would exceed max_tokens, flush current chunk
        if current_words and len(current_words) + len(para_words) > max_tokens:
            chunks.append(" ".join(current_words))
            # Overlap: keep last overlap_tokens words from previous chunk
            if overlap_tokens > 0 and len(current_words) > overlap_tokens:
                current_words = current_words[-overlap_tokens:]
            else:
                current_words = []

        current_words.extend(para_words)

        # If single paragraph exceeds max_tokens, flush immediately
        if len(current_words) > max_tokens:
            chunks.append(" ".join(current_words))
            if overlap_tokens > 0 and len(current_words) > overlap_tokens:
                current_words = current_words[-overlap_tokens:]
            else:
                current_words = []

    # Flush remaining words
    if current_words:
        chunks.append(" ".join(current_words))

    return chunks


class IndustryMemory:
    """RAG retrieval and ingestion for industry knowledge documents.

    Follows the SearchEngine pattern: instantiated per-request with a DB session
    and embedding adapter. No Protocol, no factory, no singleton.
    """

    def __init__(self, session: AsyncSession, embedding_adapter: EmbeddingAdapter) -> None:
        self._session = session
        self._embedding = embedding_adapter

    async def retrieve(self, query: str, top_k: int = 5) -> list[KnowledgeChunk]:
        """Embed query and run pgvector cosine similarity search on knowledge_documents."""
        settings = get_settings().search

        # Set HNSW ef_search for better recall
        ef_search = int(settings.hnsw_ef_search)
        await self._session.execute(text(f"SET LOCAL hnsw.ef_search = {ef_search}"))

        # Embed the query
        embeddings = await self._embedding.embed_texts([query])
        query_vector = embeddings[0]

        distance_expr = KnowledgeDocument.vector.cosine_distance(query_vector)

        stmt = (
            select(KnowledgeDocument, distance_expr.label("distance"))
            .where(KnowledgeDocument.vector.isnot(None))
            .where(KnowledgeDocument.is_active.is_(True))
            .order_by(distance_expr)
            .limit(top_k)
        )

        result = await self._session.execute(stmt)
        rows = result.all()

        return [
            KnowledgeChunk(
                content=doc.content,
                title=doc.title,
                source=doc.source,
                score=1.0 - float(distance),
                metadata=doc.metadata_,
            )
            for doc, distance in rows
        ]

    async def ingest(
        self,
        title: str,
        content: str,
        source: str,
        metadata: dict[str, object] | None = None,
    ) -> IngestionResult:
        """Chunk text, embed chunks, and upsert to DB. Returns ingestion result."""
        mem_settings = get_settings().industry_memory
        chunks = _chunk_text(
            content,
            max_tokens=mem_settings.chunk_max_tokens,
            overlap_tokens=mem_settings.chunk_overlap_tokens,
        )

        if not chunks:
            return IngestionResult(document_title=title, chunks_created=0, source=source)

        # Embed all chunks in one batch
        embeddings = await self._embedding.embed_texts(chunks)

        # Create DB records
        for idx, (chunk_text, embedding) in enumerate(zip(chunks, embeddings, strict=True)):
            doc = KnowledgeDocument(
                title=title,
                source=source,
                content=chunk_text,
                chunk_index=idx,
                vector=embedding,
                metadata_=metadata,
            )
            self._session.add(doc)

        await self._session.flush()

        logger.info(
            "Ingested knowledge document",
            extra={
                "context": {
                    "title": title,
                    "source": source,
                    "chunks_created": len(chunks),
                },
            },
        )

        return IngestionResult(
            document_title=title,
            chunks_created=len(chunks),
            source=source,
        )

    async def list_documents(self) -> list[dict[str, object]]:
        """List unique documents in the knowledge base with chunk counts."""
        from sqlalchemy import func

        stmt = (
            select(
                KnowledgeDocument.title,
                KnowledgeDocument.source,
                func.count().label("chunk_count"),
                func.min(KnowledgeDocument.created_at).label("created_at"),
            )
            .where(KnowledgeDocument.is_active.is_(True))
            .group_by(KnowledgeDocument.title, KnowledgeDocument.source)
            .order_by(func.min(KnowledgeDocument.created_at).desc())
        )

        result = await self._session.execute(stmt)
        rows = result.all()

        return [
            {
                "title": row.title,
                "source": row.source,
                "chunk_count": row.chunk_count,
                "created_at": str(row.created_at),
            }
            for row in rows
        ]
