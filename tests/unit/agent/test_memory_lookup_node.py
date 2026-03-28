"""Unit tests for the memory_lookup graph node — fire-and-forget industry context retrieval."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from quote_agent.agent.graph import _build_memory_query, build_agent_graph
from quote_agent.agent.state import create_initial_state
from quote_agent.memory.models import KnowledgeChunk
from quote_agent.services.extraction_models import ExtractedQuoteRequest, QuoteLineItem

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_request(desc: str = "tubes inox 304L DN50", qty: float = 100.0) -> ExtractedQuoteRequest:
    return ExtractedQuoteRequest(
        client_name="ACME Corp",
        line_items=[QuoteLineItem(description=desc, quantity=qty)],
        raw_text=desc,
    )


def _make_settings_mock(*, industry_memory_enabled: bool = True) -> MagicMock:
    from quote_agent.config import IndustryMemorySettings, NotificationBatchSettings

    return MagicMock(
        confidence_scoring=MagicMock(),
        notification_batch=NotificationBatchSettings(),
        industry_memory=IndustryMemorySettings(enabled=industry_memory_enabled, top_k=3),
    )


def _make_session_factory() -> MagicMock:
    mock_session = AsyncMock()
    factory = MagicMock()
    cm = AsyncMock()
    cm.__aenter__ = AsyncMock(return_value=mock_session)
    cm.__aexit__ = AsyncMock(return_value=False)
    factory.return_value = cm
    return factory


# Patch targets for nodes
_CLASSIFY = "quote_agent.agent.nodes.classifier.classify_request"
_REASON = "quote_agent.agent.nodes.reasoning_strategy.apply_reasoning_strategy"
_SCORE = "quote_agent.agent.nodes.confidence_scorer.score_confidence"
_ROUTE = "quote_agent.agent.nodes.router.route_by_confidence"
_NOTIF = "quote_agent.adapters.notification.get_notification_adapter"
_INDUSTRY_MEMORY = "quote_agent.memory.industry.IndustryMemory"
_EMBEDDING = "quote_agent.adapters.embedding.get_embedding_adapter"


# ---------------------------------------------------------------------------
# _build_memory_query tests
# ---------------------------------------------------------------------------


class TestBuildMemoryQuery:
    """Test query construction from agent state."""

    def test_builds_query_from_line_item(self) -> None:
        state = create_initial_state(_make_request("tube inox 304L DN50"))
        query = _build_memory_query(state)
        assert "tube inox 304L DN50" in query

    def test_builds_query_with_specifications(self) -> None:
        request = ExtractedQuoteRequest(
            line_items=[QuoteLineItem(description="tube", specifications="DN50 lg 2m")],
            raw_text="tube DN50",
        )
        state = create_initial_state(request)
        query = _build_memory_query(state)
        assert "tube" in query
        assert "DN50 lg 2m" in query

    def test_falls_back_to_raw_text(self) -> None:
        request = ExtractedQuoteRequest(line_items=[], raw_text="raw query text")
        state = create_initial_state(request)
        query = _build_memory_query(state)
        assert query == "raw query text"

    def test_empty_state_returns_empty(self) -> None:
        state: dict[str, object] = {}
        query = _build_memory_query(state)  # type: ignore[arg-type]
        assert query == ""


# ---------------------------------------------------------------------------
# memory_lookup node integration tests
# ---------------------------------------------------------------------------


class TestMemoryLookupNode:
    """Test the memory_lookup node behavior within the graph."""

    def test_memory_lookup_node_is_wired(self) -> None:
        """AC-4: memory_lookup node exists in the compiled graph."""
        settings = _make_settings_mock(industry_memory_enabled=False)
        graph = build_agent_graph(
            MagicMock(),
            _make_session_factory(),
            MagicMock(),
            settings,
        )
        node_names = list(graph.get_graph().nodes.keys())
        assert "memory_lookup" in node_names

    def test_memory_lookup_between_classify_and_reason(self) -> None:
        """AC-4: memory_lookup is positioned between classify and reason."""
        settings = _make_settings_mock(industry_memory_enabled=False)
        graph = build_agent_graph(
            MagicMock(),
            _make_session_factory(),
            MagicMock(),
            settings,
        )
        node_names = list(graph.get_graph().nodes.keys())
        assert node_names.index("memory_lookup") > node_names.index("classify")
        assert node_names.index("memory_lookup") < node_names.index("reason")

    async def test_memory_lookup_enabled_retrieves_context(self) -> None:
        """AC-4: When enabled, node retrieves industry context and sets state."""
        mock_chunks = [
            KnowledgeChunk(
                content="NF EN 10088 stainless steel norms",
                title="NF EN 10088",
                source="norms.md",
                score=0.85,
            ),
        ]

        mock_memory_instance = AsyncMock()
        mock_memory_instance.retrieve = AsyncMock(return_value=mock_chunks)

        mock_notif = AsyncMock()
        mock_notif.send_notification = AsyncMock()

        settings = _make_settings_mock(industry_memory_enabled=True)

        with (
            patch(_CLASSIFY, new_callable=AsyncMock, return_value=MagicMock(complexity="simple")),
            patch(_REASON, new_callable=AsyncMock, return_value=MagicMock(strategy="direct_match")),
            patch(_SCORE, new_callable=AsyncMock, return_value=MagicMock()),
            patch(_ROUTE, return_value=MagicMock(action="escalate")),
            patch(_NOTIF, return_value=mock_notif),
            patch(_INDUSTRY_MEMORY, return_value=mock_memory_instance),
            patch(_EMBEDDING, return_value=MagicMock()),
        ):
            graph = build_agent_graph(MagicMock(), _make_session_factory(), MagicMock(), settings)
            state = create_initial_state(_make_request())
            result = await graph.ainvoke(state)

        assert result.get("industry_context") == mock_chunks

    async def test_memory_lookup_disabled_returns_none(self) -> None:
        """AC-4: When disabled, industry_context is None."""
        mock_notif = AsyncMock()
        mock_notif.send_notification = AsyncMock()

        settings = _make_settings_mock(industry_memory_enabled=False)

        with (
            patch(_CLASSIFY, new_callable=AsyncMock, return_value=MagicMock(complexity="simple")),
            patch(_REASON, new_callable=AsyncMock, return_value=MagicMock(strategy="direct_match")),
            patch(_SCORE, new_callable=AsyncMock, return_value=MagicMock()),
            patch(_ROUTE, return_value=MagicMock(action="escalate")),
            patch(_NOTIF, return_value=mock_notif),
        ):
            graph = build_agent_graph(MagicMock(), _make_session_factory(), MagicMock(), settings)
            state = create_initial_state(_make_request())
            result = await graph.ainvoke(state)

        assert result.get("industry_context") is None

    async def test_memory_lookup_failure_graceful_degradation(self) -> None:
        """AC-4: If retrieval fails, industry_context is None and pipeline continues."""
        mock_notif = AsyncMock()
        mock_notif.send_notification = AsyncMock()

        settings = _make_settings_mock(industry_memory_enabled=True)

        with (
            patch(_CLASSIFY, new_callable=AsyncMock, return_value=MagicMock(complexity="simple")),
            patch(_REASON, new_callable=AsyncMock, return_value=MagicMock(strategy="direct_match")),
            patch(_SCORE, new_callable=AsyncMock, return_value=MagicMock()),
            patch(_ROUTE, return_value=MagicMock(action="escalate")),
            patch(_NOTIF, return_value=mock_notif),
            patch(_INDUSTRY_MEMORY, side_effect=RuntimeError("DB down")),
            patch(_EMBEDDING, return_value=MagicMock()),
        ):
            graph = build_agent_graph(MagicMock(), _make_session_factory(), MagicMock(), settings)
            state = create_initial_state(_make_request())
            result = await graph.ainvoke(state)

        # Fire-and-forget: no error set, industry_context is None
        assert result.get("industry_context") is None
        assert result.get("error") is None
