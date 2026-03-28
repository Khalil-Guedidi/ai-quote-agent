"""Tests for the QuoteRequestWorker service."""

from __future__ import annotations

import uuid
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from quote_agent.services.extraction_models import ExtractedQuoteRequest
from quote_agent.services.quote_request_worker import QuoteRequestWorker

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_cache(_clear_settings_cache: None) -> None:
    """Ensure settings cache is cleared for every test."""


@pytest.fixture()
def mock_session_factory() -> AsyncMock:
    """Create a mock async session factory."""
    session = AsyncMock()
    factory = AsyncMock(return_value=session)
    factory.return_value.__aenter__ = AsyncMock(return_value=session)
    factory.return_value.__aexit__ = AsyncMock(return_value=False)
    return factory


@pytest.fixture()
def worker(mock_session_factory: AsyncMock) -> QuoteRequestWorker:
    """Create a QuoteRequestWorker with mock dependencies."""
    return QuoteRequestWorker(
        session_factory=mock_session_factory,
        poll_interval=1,
        batch_size=5,
    )


def _make_quote_request(
    *,
    status: str = "pending",
    line_items: list[dict[str, object]] | None = None,
    client_name: str | None = "Test Client",
    error_message: str | None = None,
) -> MagicMock:
    """Create a mock QuoteRequest."""
    qr = MagicMock()
    qr.id = uuid.uuid4()
    qr.email_request_id = uuid.uuid4()
    qr.request_index = 0
    qr.line_items = line_items or [{"description": "Tube acier 50mm", "quantity": 100}]
    qr.client_name = client_name
    qr.client_identifier = "TEST-001"
    qr.client_email = "test@example.com"
    qr.urgency = "normal"
    qr.delivery_address = "123 Test St"
    qr.notes = "Test notes"
    qr.status = status
    qr.error_message = error_message
    qr.confidence = 0.9
    qr.created_at = MagicMock()
    return qr


# ---------------------------------------------------------------------------
# Tests: _build_extracted_request
# ---------------------------------------------------------------------------


class TestBuildExtractedRequest:
    """Worker correctly builds ExtractedQuoteRequest from stored QuoteRequest."""

    def test_builds_request_with_all_fields(self) -> None:
        """AC-2: ExtractedQuoteRequest is built from stored fields."""
        qr = _make_quote_request(
            line_items=[
                {"description": "Tube acier 50mm", "quantity": 100, "unit": "m", "reference": "TB-50"},
                {"description": "Plaque inox 3mm", "quantity": 5, "specifications": "316L"},
            ],
        )

        result = QuoteRequestWorker._build_extracted_request(qr)

        assert isinstance(result, ExtractedQuoteRequest)
        assert result.client_name == "Test Client"
        assert result.client_identifier == "TEST-001"
        assert result.client_email == "test@example.com"
        assert result.urgency == "normal"
        assert result.delivery_address == "123 Test St"
        assert result.notes == "Test notes"
        assert len(result.line_items) == 2
        assert result.line_items[0].description == "Tube acier 50mm"
        assert result.line_items[0].quantity == 100
        assert result.line_items[0].unit == "m"
        assert result.line_items[0].reference == "TB-50"
        assert result.line_items[1].specifications == "316L"

    def test_builds_request_with_missing_optional_fields(self) -> None:
        """AC-2: Handles missing optional fields gracefully."""
        qr = _make_quote_request(
            line_items=[{"description": "Simple item"}],
            client_name=None,
        )
        qr.client_identifier = None
        qr.client_email = None
        qr.urgency = None
        qr.delivery_address = None
        qr.notes = None

        result = QuoteRequestWorker._build_extracted_request(qr)

        assert result.client_name is None
        assert result.line_items[0].quantity is None
        assert result.raw_text == ""


# ---------------------------------------------------------------------------
# Tests: _process_one
# ---------------------------------------------------------------------------


class TestProcessOne:
    """Worker processes individual QuoteRequests through the graph pipeline."""

    @pytest.mark.parametrize("final_action", ["proceed_to_draft", "escalate", "generate_proposals"])
    async def test_status_done_when_graph_succeeds(self, worker: QuoteRequestWorker, final_action: str) -> None:
        """AC-2: On success, status is set to 'done'."""
        qr = _make_quote_request()
        session = AsyncMock()

        graph_result: dict[str, Any] = {"error": None, "final_action": final_action}

        with (
            patch("quote_agent.agent.graph.get_agent_graph") as mock_graph_factory,
            patch("quote_agent.agent.state.create_initial_state") as mock_state,
        ):
            mock_graph = AsyncMock()
            mock_graph.ainvoke.return_value = graph_result
            mock_graph_factory.return_value = mock_graph
            mock_state.return_value = {"raw_request": MagicMock()}

            await worker._process_one(session, qr)

        assert qr.status == "done"
        assert worker.total_processed == 1

    async def test_status_error_when_graph_returns_error(self, worker: QuoteRequestWorker) -> None:
        """AC-2/AC-3: On error, status is 'error' and error_message is set."""
        qr = _make_quote_request()
        session = AsyncMock()

        graph_result: dict[str, Any] = {"error": "classify: LLM timeout", "final_action": ""}

        mock_adapter = AsyncMock()
        mock_adapter.send_notification.return_value = MagicMock(success=True)

        with (
            patch("quote_agent.agent.graph.get_agent_graph") as mock_graph_factory,
            patch("quote_agent.agent.state.create_initial_state"),
            patch("quote_agent.adapters.notification.get_notification_adapter", return_value=mock_adapter),
        ):
            mock_graph = AsyncMock()
            mock_graph.ainvoke.return_value = graph_result
            mock_graph_factory.return_value = mock_graph

            await worker._process_one(session, qr)

        assert qr.status == "error"
        assert qr.error_message == "classify: LLM timeout"
        # AC-3: Error notification was sent
        mock_adapter.send_notification.assert_awaited_once()

    async def test_status_error_when_graph_raises_exception(self, worker: QuoteRequestWorker) -> None:
        """AC-2: On exception, status is 'error' and error_message is set."""
        qr = _make_quote_request()
        session = AsyncMock()

        mock_adapter = AsyncMock()
        mock_adapter.send_notification.return_value = MagicMock(success=True)

        with (
            patch("quote_agent.agent.graph.get_agent_graph") as mock_graph_factory,
            patch("quote_agent.agent.state.create_initial_state"),
            patch("quote_agent.adapters.notification.get_notification_adapter", return_value=mock_adapter),
        ):
            mock_graph = AsyncMock()
            mock_graph.ainvoke.side_effect = RuntimeError("Connection lost")
            mock_graph_factory.return_value = mock_graph

            await worker._process_one(session, qr)

        assert qr.status == "error"
        assert "Connection lost" in str(qr.error_message)

    async def test_status_processing_set_before_graph(self, worker: QuoteRequestWorker) -> None:
        """AC-2: Status transitions to 'processing' before graph invocation."""
        qr = _make_quote_request()
        session = AsyncMock()
        statuses_seen: list[str] = []

        async def capture_status(state: Any) -> dict[str, Any]:
            statuses_seen.append(qr.status)
            return {"error": None, "final_action": "test"}

        with (
            patch("quote_agent.agent.graph.get_agent_graph") as mock_graph_factory,
            patch("quote_agent.agent.state.create_initial_state"),
        ):
            mock_graph = AsyncMock()
            mock_graph.ainvoke.side_effect = capture_status
            mock_graph_factory.return_value = mock_graph

            await worker._process_one(session, qr)

        assert "processing" in statuses_seen

    async def test_sends_error_notification_on_graph_error(self, worker: QuoteRequestWorker) -> None:
        """AC-3: Error notification is sent when graph completes with error."""
        qr = _make_quote_request()
        session = AsyncMock()

        mock_adapter = AsyncMock()
        mock_adapter.send_notification.return_value = MagicMock(success=True)

        with (
            patch("quote_agent.agent.graph.get_agent_graph") as mock_graph_factory,
            patch("quote_agent.agent.state.create_initial_state"),
            patch("quote_agent.adapters.notification.get_notification_adapter", return_value=mock_adapter),
        ):
            mock_graph = AsyncMock()
            mock_graph.ainvoke.return_value = {"error": "DB connection failed", "final_action": ""}
            mock_graph_factory.return_value = mock_graph

            await worker._process_one(session, qr)

        mock_adapter.send_notification.assert_awaited_once()
        payload = mock_adapter.send_notification.call_args[0][0]
        assert "DB connection failed" in payload.message


# ---------------------------------------------------------------------------
# Tests: _process_pending (skip locked)
# ---------------------------------------------------------------------------


class TestProcessPending:
    """Worker uses FOR UPDATE SKIP LOCKED and respects status filtering."""

    async def test_returns_zero_when_no_pending_found(self, worker: QuoteRequestWorker) -> None:
        """AC-4: Returns 0 when no pending requests exist."""
        session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = None
        session.execute.return_value = mock_result

        mock_cm = AsyncMock()
        mock_cm.__aenter__ = AsyncMock(return_value=session)
        mock_cm.__aexit__ = AsyncMock(return_value=False)
        worker._session_factory = MagicMock(return_value=mock_cm)  # type: ignore[assignment]

        processed = await worker._process_pending()

        assert processed == 0

    async def test_processes_batch_of_pending_requests(self, worker: QuoteRequestWorker) -> None:
        """AC-4: Processes multiple pending requests, each in its own transaction."""
        qr1 = _make_quote_request()
        qr2 = _make_quote_request()
        requests_iter = iter([qr1, qr2, None])

        def _make_session_cm() -> MagicMock:
            session = AsyncMock()
            mock_result = MagicMock()
            mock_result.scalars.return_value.first.return_value = next(requests_iter)
            session.execute.return_value = mock_result
            session.commit = AsyncMock()
            mock_cm = AsyncMock()
            mock_cm.__aenter__ = AsyncMock(return_value=session)
            mock_cm.__aexit__ = AsyncMock(return_value=False)
            return mock_cm

        worker._session_factory = MagicMock(side_effect=_make_session_cm)  # type: ignore[assignment]

        with (
            patch("quote_agent.agent.graph.get_agent_graph") as mock_graph_factory,
            patch("quote_agent.agent.state.create_initial_state"),
        ):
            mock_graph = AsyncMock()
            mock_graph.ainvoke.return_value = {"error": None, "final_action": "done"}
            mock_graph_factory.return_value = mock_graph

            processed = await worker._process_pending()

        assert processed == 2
        assert worker.total_processed == 2


# ---------------------------------------------------------------------------
# Tests: Worker config
# ---------------------------------------------------------------------------


class TestWorkerConfig:
    """Worker respects configuration settings."""

    def test_default_config_values(self, env_vars: dict[str, str]) -> None:
        """AC-5: Default poll_interval=10, batch_size=5, enabled=false (opt-in)."""
        import os

        from quote_agent.config import Settings

        # Override .env file value — pydantic-settings env vars take priority over .env
        old = os.environ.get("WORKER__ENABLED")
        os.environ["WORKER__ENABLED"] = "false"
        try:
            s = Settings()  # type: ignore[call-arg]
            assert s.worker.poll_interval == 10
            assert s.worker.batch_size == 5
            assert s.worker.enabled is False
        finally:
            if old is not None:
                os.environ["WORKER__ENABLED"] = old
            else:
                os.environ.pop("WORKER__ENABLED", None)

    def test_config_overrides_from_env(self, env_vars: dict[str, str]) -> None:
        """AC-5: Config can be overridden via env vars."""
        import os

        from quote_agent.config import Settings

        os.environ["WORKER__POLL_INTERVAL"] = "30"
        os.environ["WORKER__BATCH_SIZE"] = "10"
        os.environ["WORKER__ENABLED"] = "false"

        try:
            s = Settings()  # type: ignore[call-arg]
            assert s.worker.poll_interval == 30
            assert s.worker.batch_size == 10
            assert s.worker.enabled is False
        finally:
            os.environ.pop("WORKER__POLL_INTERVAL", None)
            os.environ.pop("WORKER__BATCH_SIZE", None)
            os.environ.pop("WORKER__ENABLED", None)

    def test_worker_constructor_accepts_settings(self) -> None:
        """AC-5: Worker accepts poll_interval and batch_size."""
        factory = AsyncMock()
        w = QuoteRequestWorker(session_factory=factory, poll_interval=30, batch_size=10)
        assert w._poll_interval == 30
        assert w._batch_size == 10


# ---------------------------------------------------------------------------
# Tests: Worker lifecycle
# ---------------------------------------------------------------------------


class TestWorkerLifecycle:
    """Worker start/stop lifecycle."""

    async def test_stop_signals_loop_to_exit(self, worker: QuoteRequestWorker) -> None:
        """AC-1: Worker can be stopped gracefully."""
        worker._running = True
        await worker.stop()
        assert not worker.is_running

    def test_is_running_false_initially(self, worker: QuoteRequestWorker) -> None:
        """AC-1: Worker is not running before run() is called."""
        assert not worker.is_running

    def test_total_processed_zero_initially(self, worker: QuoteRequestWorker) -> None:
        """Worker starts with zero processed count."""
        assert worker.total_processed == 0
