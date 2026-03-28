"""Unit tests for the KnowledgeDocument SQLAlchemy model."""

from __future__ import annotations

import uuid

from quote_agent.models.knowledge_document import KnowledgeDocument


class TestKnowledgeDocumentModel:
    """Test KnowledgeDocument model creation and defaults."""

    def test_model_creates_with_minimal_fields(self) -> None:
        doc = KnowledgeDocument(
            title="Test Document",
            content="Some content",
            source="test.md",
        )
        assert doc.title == "Test Document"
        assert doc.content == "Some content"
        assert doc.source == "test.md"
        # mapped_column defaults are server-side; Python-side values are None before flush
        assert doc.metadata_ is None
        assert doc.vector is None
        assert doc.search_vector is None

    def test_model_accepts_all_fields(self) -> None:
        doc_id = uuid.uuid4()
        vector = [0.1] * 1024
        doc = KnowledgeDocument(
            id=doc_id,
            title="NF EN 10088",
            content="Stainless steel norms",
            source="norms/en10088.md",
            chunk_index=3,
            vector=vector,
            metadata_={"domain": "metallurgy", "norms": ["EN10088"]},
            is_active=False,
        )
        assert doc.id == doc_id
        assert doc.title == "NF EN 10088"
        assert doc.chunk_index == 3
        assert doc.is_active is False
        assert doc.metadata_ == {"domain": "metallurgy", "norms": ["EN10088"]}
        assert doc.vector == vector

    def test_tablename(self) -> None:
        assert KnowledgeDocument.__tablename__ == "knowledge_documents"

    def test_model_registered_in_package(self) -> None:
        """KnowledgeDocument is importable from models package."""
        from quote_agent.models import KnowledgeDocument as KnowledgeDocumentFromPkg

        assert KnowledgeDocumentFromPkg is KnowledgeDocument
