"""CLI async implementations for knowledge base management."""

from __future__ import annotations

import logging
from pathlib import Path

import typer

from quote_agent.adapters.embedding import get_embedding_adapter
from quote_agent.memory.industry import IndustryMemory
from quote_agent.models.base import _get_session_factory

logger = logging.getLogger(__name__)


async def kb_ingest(file_path: str, title: str | None = None) -> None:
    """Ingest a document into the industry knowledge base."""
    path = Path(file_path)
    if not path.exists():
        typer.echo(f"Error: file not found: {file_path}")
        raise typer.Exit(code=1)

    if path.suffix.lower() not in (".md", ".txt", ".text", ".markdown"):
        typer.echo(f"Error: unsupported file type '{path.suffix}'. Supported: .md, .txt")
        raise typer.Exit(code=1)

    content = path.read_text(encoding="utf-8")
    doc_title = title or path.stem

    session_factory = _get_session_factory()
    async with session_factory() as session:
        memory = IndustryMemory(session, get_embedding_adapter())
        result = await memory.ingest(
            title=doc_title,
            content=content,
            source=str(path),
            metadata={"file_type": path.suffix.lower()},
        )
        await session.commit()

    typer.echo(f"✅ Ingested '{result.document_title}' — {result.chunks_created} chunks created")
    typer.echo(f"   Source: {result.source}")


async def kb_search(query: str, top_k: int = 5) -> None:
    """Search the industry knowledge base and display results."""
    session_factory = _get_session_factory()
    async with session_factory() as session:
        memory = IndustryMemory(session, get_embedding_adapter())
        chunks = await memory.retrieve(query, top_k=top_k)

    if not chunks:
        typer.echo("No results found.")
        return

    typer.echo(f"Found {len(chunks)} result(s):\n")
    for i, chunk in enumerate(chunks, start=1):
        typer.echo(f"[{i}] {chunk.title} (score: {chunk.score:.3f})")
        typer.echo(f"    Source: {chunk.source}")
        # Show first 200 chars of content
        preview = chunk.content[:200] + "..." if len(chunk.content) > 200 else chunk.content
        typer.echo(f"    {preview}")
        typer.echo()


async def kb_list() -> None:
    """List all documents in the knowledge base with chunk counts."""
    session_factory = _get_session_factory()
    async with session_factory() as session:
        memory = IndustryMemory(session, get_embedding_adapter())
        documents = await memory.list_documents()

    if not documents:
        typer.echo("Knowledge base is empty.")
        return

    typer.echo(f"Knowledge base: {len(documents)} document(s)\n")
    for doc in documents:
        typer.echo(f"  📄 {doc['title']} — {doc['chunk_count']} chunk(s)")
        typer.echo(f"     Source: {doc['source']}")
        typer.echo(f"     Created: {doc['created_at']}")
        typer.echo()
