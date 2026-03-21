"""Tests for agent state schema and factory function."""

from __future__ import annotations

from quote_agent.agent.state import AgentState, create_initial_state
from quote_agent.services.extraction_models import ExtractedQuoteRequest, QuoteLineItem


class TestAgentState:
    """AC-2: AgentState TypedDict fields and structure."""

    def test_agent_state_has_all_required_fields(self) -> None:
        """AC-2: AgentState contains all specified fields."""
        annotations = AgentState.__annotations__
        expected_fields = {
            "raw_request",
            "classification",
            "reasoning",
            "confidence",
            "routing_decision",
            "self_review",
            "compliance",
            "draft_result",
            "error",
            "current_node",
            "final_action",
        }
        assert expected_fields == set(annotations.keys())

    def test_agent_state_is_typed_dict(self) -> None:
        """AC-2: AgentState is a TypedDict subclass."""
        assert hasattr(AgentState, "__annotations__")
        assert issubclass(AgentState, dict)

    def test_agent_state_total_false_allows_partial(self) -> None:
        """AC-2: total=False allows creating partial state dicts."""
        partial: AgentState = AgentState(current_node="classify")  # type: ignore[typeddict-item]
        assert partial["current_node"] == "classify"


class TestCreateInitialState:
    """AC-2: create_initial_state factory function."""

    def test_creates_state_with_request(self) -> None:
        """AC-2: Factory populates raw_request and nulls all other fields."""
        request = ExtractedQuoteRequest(
            client_name="ACME Corp",
            line_items=[QuoteLineItem(description="tubes inox 304L", quantity=100)],
            raw_text="tubes inox 304L qty 100",
        )
        state = create_initial_state(request)

        assert state["raw_request"] is request
        assert state["classification"] is None
        assert state["reasoning"] is None
        assert state["confidence"] is None
        assert state["routing_decision"] is None
        assert state["self_review"] is None
        assert state["compliance"] is None
        assert state["draft_result"] is None
        assert state["error"] is None
        assert state["current_node"] == ""
        assert state["final_action"] == ""

    def test_state_is_mutable_dict(self) -> None:
        """AC-2: State can be updated by nodes (dict mutation)."""
        request = ExtractedQuoteRequest(raw_text="test")
        state = create_initial_state(request)
        state["current_node"] = "classify"
        state["error"] = "something failed"
        assert state["current_node"] == "classify"
        assert state["error"] == "something failed"

    def test_state_with_minimal_request(self) -> None:
        """AC-2: Factory works with minimal ExtractedQuoteRequest."""
        request = ExtractedQuoteRequest(raw_text="")
        state = create_initial_state(request)
        assert state["raw_request"].raw_text == ""
        assert state["raw_request"].line_items == []
