"""Tests for the notification adapter — health check, send, caching, protocol, CLI, and health endpoint."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from httpx import ASGITransport, AsyncClient
from typer.testing import CliRunner

from quote_agent.adapters.email import get_email_adapter
from quote_agent.adapters.erp import get_erp_adapter
from quote_agent.adapters.llm import get_llm_adapter
from quote_agent.adapters.notification import get_notification_adapter
from quote_agent.adapters.notification.models import NotificationPayload, NotificationResult
from quote_agent.adapters.notification.protocol import NotificationAdapter
from quote_agent.adapters.notification.teams import TeamsAdapter
from quote_agent.exceptions import ConfigurationError
from quote_agent.models.base import get_async_session
from tests.conftest import create_test_app, mock_healthy_adapter, mock_healthy_session


@pytest.fixture()
def notification_settings(env_vars: dict[str, str], _clear_settings_cache: None) -> Any:
    """Provide NotificationSettings with a valid webhook URL for tests."""
    import os

    os.environ["NOTIFICATION__TEAMS_WEBHOOK_URL"] = "https://test.webhook.office.com/webhook/test"
    from quote_agent.config import get_settings

    get_settings.cache_clear()
    settings = get_settings().notification
    yield settings
    os.environ.pop("NOTIFICATION__TEAMS_WEBHOOK_URL", None)
    get_settings.cache_clear()


@pytest.fixture()
def adapter(notification_settings: Any) -> TeamsAdapter:
    """Create adapter with test settings."""
    return TeamsAdapter(notification_settings)


# --- Health Check Tests ---


@patch("quote_agent.adapters.notification.teams.httpx.AsyncClient")
async def test_health_check_returns_healthy_on_success(
    mock_client_cls: MagicMock,
    adapter: TeamsAdapter,
) -> None:
    """health_check() returns healthy when webhook responds."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(return_value=mock_response)
    mock_client_cls.return_value = mock_client

    result = await adapter.health_check()

    assert result.status == "healthy"
    assert result.error is None


@patch("quote_agent.adapters.notification.teams.httpx.AsyncClient")
async def test_health_check_returns_unhealthy_on_connection_error(
    mock_client_cls: MagicMock,
    adapter: TeamsAdapter,
) -> None:
    """health_check() returns unhealthy when connection is refused."""
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))
    mock_client_cls.return_value = mock_client

    result = await adapter.health_check()

    assert result.status == "unhealthy"
    assert "Connection refused" in (result.error or "")


@patch("quote_agent.adapters.notification.teams.httpx.AsyncClient")
async def test_health_check_returns_unhealthy_on_timeout(
    mock_client_cls: MagicMock,
    adapter: TeamsAdapter,
) -> None:
    """health_check() returns unhealthy when webhook times out."""
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(side_effect=httpx.TimeoutException("Timed out"))
    mock_client_cls.return_value = mock_client

    result = await adapter.health_check()

    assert result.status == "unhealthy"
    assert "Timed out" in (result.error or "")


def test_health_check_returns_unhealthy_on_empty_webhook_url(
    env_vars: dict[str, str],
    _clear_settings_cache: None,
) -> None:
    """TeamsAdapter raises ConfigurationError when webhook URL is empty."""
    from quote_agent.config import NotificationSettings

    settings = NotificationSettings(channel="teams", teams_webhook_url="")
    with pytest.raises(ConfigurationError, match="must not be empty"):
        TeamsAdapter(settings)


def test_health_check_returns_unhealthy_on_non_https_url(
    env_vars: dict[str, str],
    _clear_settings_cache: None,
) -> None:
    """TeamsAdapter raises ConfigurationError when webhook URL is not HTTPS."""
    from quote_agent.config import NotificationSettings

    settings = NotificationSettings(channel="teams", teams_webhook_url="http://insecure.example.com/webhook")
    with pytest.raises(ConfigurationError, match="must be an HTTPS URL"):
        TeamsAdapter(settings)


@patch("quote_agent.adapters.notification.teams.httpx.AsyncClient")
async def test_health_check_caches_result(
    mock_client_cls: MagicMock,
    adapter: TeamsAdapter,
) -> None:
    """Second health_check() call within 30s returns cached result without hitting httpx."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(return_value=mock_response)
    mock_client_cls.return_value = mock_client

    result1 = await adapter.health_check()
    result2 = await adapter.health_check()

    assert result1.status == "healthy"
    assert result2.status == "healthy"
    # AsyncClient should only be constructed once (for the first call)
    assert mock_client_cls.call_count == 1


# --- Protocol Compliance ---


def test_adapter_conforms_to_protocol(adapter: TeamsAdapter) -> None:
    """TeamsAdapter satisfies the NotificationAdapter protocol."""
    assert isinstance(adapter, NotificationAdapter)


# --- Health Endpoint Integration ---


@pytest.fixture()
def _app_env(env_vars: dict[str, str], _clear_settings_cache: None) -> None:
    """Combine env_vars and cache clearing for app instantiation."""


@pytest.mark.usefixtures("_app_env")
async def test_health_endpoint_includes_notification_service() -> None:
    """GET /health response includes services.notification key."""
    app = create_test_app()
    app.dependency_overrides[get_async_session] = mock_healthy_session
    app.dependency_overrides[get_llm_adapter] = mock_healthy_adapter
    app.dependency_overrides[get_erp_adapter] = mock_healthy_adapter
    app.dependency_overrides[get_email_adapter] = mock_healthy_adapter
    app.dependency_overrides[get_notification_adapter] = mock_healthy_adapter

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")

    body = response.json()
    assert "notification" in body["data"]["services"]
    assert body["data"]["services"]["notification"]["status"] == "healthy"

    app.dependency_overrides.clear()


# --- send_notification() Tests ---


def _mock_httpx_client(status_code: int = 200) -> tuple[MagicMock, AsyncMock]:
    """Helper to create a mock httpx client returning a given status code."""
    mock_response = MagicMock()
    mock_response.status_code = status_code
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(return_value=mock_response)
    mock_cls = MagicMock(return_value=mock_client)
    return mock_cls, mock_client


@pytest.fixture()
def test_payload() -> NotificationPayload:
    """Standard test notification payload."""
    return NotificationPayload(title="Test", message="Hello Teams")


@patch("quote_agent.adapters.notification.teams.httpx.AsyncClient")
async def test_send_notification_returns_success_on_200(
    mock_client_cls: MagicMock,
    adapter: TeamsAdapter,
    test_payload: NotificationPayload,
) -> None:
    """AC-1: send_notification() returns success=True on HTTP 200."""
    mock_cls, _mock_client = _mock_httpx_client(200)
    mock_client_cls.return_value = mock_cls.return_value

    result = await adapter.send_notification(test_payload)

    assert result.success is True
    assert result.status_code == 200
    assert result.error is None
    assert result.timestamp is not None


@patch("quote_agent.adapters.notification.teams.httpx.AsyncClient")
async def test_send_notification_returns_failure_on_connection_error(
    mock_client_cls: MagicMock,
    adapter: TeamsAdapter,
    test_payload: NotificationPayload,
) -> None:
    """AC-1: send_notification() returns success=False on connection error."""
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))
    mock_client_cls.return_value = mock_client

    result = await adapter.send_notification(test_payload)

    assert result.success is False
    assert result.status_code is None
    assert "Connection refused" in (result.error or "")


@patch("quote_agent.adapters.notification.teams.httpx.AsyncClient")
async def test_send_notification_returns_failure_on_timeout(
    mock_client_cls: MagicMock,
    adapter: TeamsAdapter,
    test_payload: NotificationPayload,
) -> None:
    """AC-1: send_notification() returns success=False on timeout."""
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(side_effect=httpx.TimeoutException("Timed out"))
    mock_client_cls.return_value = mock_client

    result = await adapter.send_notification(test_payload)

    assert result.success is False
    assert "Timed out" in (result.error or "")


@patch("quote_agent.adapters.notification.teams.httpx.AsyncClient")
async def test_send_notification_returns_failure_on_http_error(
    mock_client_cls: MagicMock,
    adapter: TeamsAdapter,
    test_payload: NotificationPayload,
) -> None:
    """AC-1: send_notification() returns success=False on HTTP 4xx/5xx."""
    mock_cls, _mock_client = _mock_httpx_client(500)
    mock_client_cls.return_value = mock_cls.return_value

    result = await adapter.send_notification(test_payload)

    assert result.success is False
    assert result.status_code == 500
    assert result.error is None
    assert result.timestamp is not None


# --- _build_adaptive_card() Tests ---


def test_build_adaptive_card_has_valid_schema(
    adapter: TeamsAdapter,
    test_payload: NotificationPayload,
) -> None:
    """AC-4: Card JSON conforms to Adaptive Card schema structure."""
    envelope = adapter._build_adaptive_card(test_payload)

    assert envelope["type"] == "message"
    assert len(envelope["attachments"]) == 1
    attachment = envelope["attachments"][0]
    assert attachment["contentType"] == "application/vnd.microsoft.card.adaptive"

    card = attachment["content"]
    assert card["type"] == "AdaptiveCard"
    assert card["version"] == "1.4"
    assert "$schema" in card


def test_build_adaptive_card_body_structure(
    adapter: TeamsAdapter,
    test_payload: NotificationPayload,
) -> None:
    """AC-4: Card body has accent container, timestamp, and message."""
    envelope = adapter._build_adaptive_card(test_payload)
    body = envelope["attachments"][0]["content"]["body"]

    assert len(body) == 3
    # Accent container with bot name
    assert body[0]["type"] == "Container"
    assert body[0]["style"] == "accent"
    assert body[0]["items"][0]["text"] == "Q \u2014 AI Quote Agent"
    # Timestamp
    assert body[1]["type"] == "TextBlock"
    assert body[1]["isSubtle"] is True
    # Message
    assert body[2]["type"] == "TextBlock"
    assert body[2]["text"] == "Hello Teams"
    assert body[2]["wrap"] is True


# --- Protocol Compliance with send_notification ---


def test_adapter_conforms_to_protocol_with_send(adapter: TeamsAdapter) -> None:
    """AC-3: TeamsAdapter still satisfies NotificationAdapter after adding send_notification."""
    assert isinstance(adapter, NotificationAdapter)
    assert hasattr(adapter, "send_notification")
    assert hasattr(adapter, "health_check")


# --- CLI notify-test Tests ---


runner = CliRunner()


@patch("quote_agent.adapters.notification.get_notification_adapter")
def test_cli_notify_test_success_output(
    mock_get_adapter: MagicMock,
    env_vars: dict[str, str],
    _clear_settings_cache: None,
) -> None:
    """AC-5: CLI displays success status and webhook hostname."""
    from datetime import UTC, datetime

    from quote_agent.cli.main import app

    mock_adapter = MagicMock()
    mock_adapter._hostname = "test.webhook.office.com"
    mock_adapter.send_notification = AsyncMock(
        return_value=NotificationResult(
            success=True,
            status_code=200,
            timestamp=datetime.now(tz=UTC),
        )
    )
    mock_get_adapter.return_value = mock_adapter

    result = runner.invoke(app, ["notify-test"])

    assert result.exit_code == 0
    assert "success" in result.output.lower()
    assert "200" in result.output
    assert "test.webhook.office.com" in result.output


@patch("quote_agent.adapters.notification.get_notification_adapter")
def test_cli_notify_test_failure_output(
    mock_get_adapter: MagicMock,
    env_vars: dict[str, str],
    _clear_settings_cache: None,
) -> None:
    """AC-5: CLI displays failure status on send error."""
    from datetime import UTC, datetime

    from quote_agent.cli.main import app

    mock_adapter = MagicMock()
    mock_adapter._hostname = "test.webhook.office.com"
    mock_adapter.send_notification = AsyncMock(
        return_value=NotificationResult(
            success=False,
            error="Connection refused",
            timestamp=datetime.now(tz=UTC),
        )
    )
    mock_get_adapter.return_value = mock_adapter

    result = runner.invoke(app, ["notify-test"])

    assert result.exit_code == 1
    assert "failure" in result.output.lower()
    assert "Connection refused" in result.output


@patch("quote_agent.adapters.notification.get_notification_adapter")
def test_cli_notify_test_json_output(
    mock_get_adapter: MagicMock,
    env_vars: dict[str, str],
    _clear_settings_cache: None,
) -> None:
    """AC-5: CLI --json flag produces valid JSON with webhook_hostname."""
    from datetime import UTC, datetime

    from quote_agent.cli.main import app

    mock_adapter = MagicMock()
    mock_adapter._hostname = "test.webhook.office.com"
    mock_adapter.send_notification = AsyncMock(
        return_value=NotificationResult(
            success=True,
            status_code=200,
            timestamp=datetime.now(tz=UTC),
        )
    )
    mock_get_adapter.return_value = mock_adapter

    result = runner.invoke(app, ["notify-test", "--json"])

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["success"] is True
    assert data["status_code"] == 200
    assert data["webhook_hostname"] == "test.webhook.office.com"


# --- _build_quote_ready_card() Tests ---


def test_build_quote_ready_card_has_green_accent(
    adapter: TeamsAdapter,
) -> None:
    """AC-1: quote-ready card uses green accent container (style=good)."""
    payload = NotificationPayload(
        title="Devis prêt",
        message="Salut ! Devis pour Durand prêt. Check quand t'as le temps.",
        card_type="quote-ready",
        data={
            "client": "Durand",
            "product": "Tube Inox 304L",
            "quantity": "100",
            "confidence_pct": "92",
            "erp_url": "https://odoo.example.com/web#id=42&model=sale.order&view_type=form",
        },
    )
    envelope = adapter._build_adaptive_card(payload)
    card = envelope["attachments"][0]["content"]
    accent_container = card["body"][0]

    assert accent_container["type"] == "Container"
    assert accent_container["style"] == "good"
    assert accent_container["items"][0]["text"] == "Q — AI Quote Agent"


def test_build_quote_ready_card_has_factset(
    adapter: TeamsAdapter,
) -> None:
    """AC-1: quote-ready card includes FactSet with Client, Product, Quantity, Confidence."""
    payload = NotificationPayload(
        title="Devis prêt",
        message="Salut ! Devis pour Durand prêt. Check quand t'as le temps.",
        card_type="quote-ready",
        data={
            "client": "Durand",
            "product": "Tube Inox 304L",
            "quantity": "100",
            "confidence_pct": "92",
            "erp_url": "https://odoo.example.com/web#id=42&model=sale.order&view_type=form",
        },
    )
    envelope = adapter._build_adaptive_card(payload)
    card = envelope["attachments"][0]["content"]

    # Find FactSet in body
    factsets = [b for b in card["body"] if b["type"] == "FactSet"]
    assert len(factsets) == 1
    facts = factsets[0]["facts"]
    fact_titles = [f["title"] for f in facts]
    assert "Client" in fact_titles
    assert "Produit" in fact_titles
    assert "Quantité" in fact_titles
    assert "Confiance" in fact_titles

    # Verify values
    fact_dict = {f["title"]: f["value"] for f in facts}
    assert fact_dict["Client"] == "Durand"
    assert fact_dict["Produit"] == "Tube Inox 304L"
    assert fact_dict["Quantité"] == "100"
    assert fact_dict["Confiance"] == "92%"


def test_build_quote_ready_card_has_openurl_action(
    adapter: TeamsAdapter,
) -> None:
    """AC-1: quote-ready card has 'Voir dans l'ERP' OpenUrl action button."""
    erp_url = "https://odoo.example.com/web#id=42&model=sale.order&view_type=form"
    payload = NotificationPayload(
        title="Devis prêt",
        message="Salut ! Devis pour Durand prêt. Check quand t'as le temps.",
        card_type="quote-ready",
        data={
            "client": "Durand",
            "product": "Tube Inox 304L",
            "quantity": "100",
            "confidence_pct": "92",
            "erp_url": erp_url,
        },
    )
    envelope = adapter._build_adaptive_card(payload)
    card = envelope["attachments"][0]["content"]

    assert "actions" in card
    assert len(card["actions"]) == 1
    action = card["actions"][0]
    assert action["type"] == "Action.OpenUrl"
    assert action["title"] == "Voir dans l'ERP"
    assert action["url"] == erp_url


def test_build_quote_ready_card_has_casual_french_message(
    adapter: TeamsAdapter,
) -> None:
    """AC-1: quote-ready card displays the casual French message."""
    msg = "Salut ! Devis pour Durand prêt. Check quand t'as le temps."
    payload = NotificationPayload(
        title="Devis prêt",
        message=msg,
        card_type="quote-ready",
        data={
            "client": "Durand",
            "product": "Tube Inox 304L",
            "quantity": "100",
            "confidence_pct": "92",
            "erp_url": "https://odoo.example.com/web#id=42&model=sale.order&view_type=form",
        },
    )
    envelope = adapter._build_adaptive_card(payload)
    card = envelope["attachments"][0]["content"]

    # Find the message text block (should have wrap=True)
    message_blocks = [b for b in card["body"] if b.get("type") == "TextBlock" and b.get("wrap") is True]
    assert len(message_blocks) == 1
    assert message_blocks[0]["text"] == msg


def test_build_adaptive_card_dispatches_to_generic_for_test_type(
    adapter: TeamsAdapter,
) -> None:
    """AC-1: card_type='test' still uses the generic card (no FactSet, no actions)."""
    payload = NotificationPayload(title="Test", message="Hello Teams")
    envelope = adapter._build_adaptive_card(payload)
    card = envelope["attachments"][0]["content"]

    # Generic card: accent style, no FactSet, no actions
    assert card["body"][0]["style"] == "accent"
    factsets = [b for b in card["body"] if b.get("type") == "FactSet"]
    assert len(factsets) == 0
    assert "actions" not in card


@patch("quote_agent.adapters.notification.get_notification_adapter")
def test_cli_notify_test_custom_message(
    mock_get_adapter: MagicMock,
    env_vars: dict[str, str],
    _clear_settings_cache: None,
) -> None:
    """AC-5: CLI --message option passes custom message to adapter."""
    from datetime import UTC, datetime

    from quote_agent.cli.main import app

    mock_adapter = MagicMock()
    mock_adapter._hostname = "test.webhook.office.com"
    mock_adapter.send_notification = AsyncMock(
        return_value=NotificationResult(
            success=True,
            status_code=200,
            timestamp=datetime.now(tz=UTC),
        )
    )
    mock_get_adapter.return_value = mock_adapter

    result = runner.invoke(app, ["notify-test", "--message", "Custom test msg"])

    assert result.exit_code == 0
    # Verify the adapter was called with the custom message
    call_args = mock_adapter.send_notification.call_args
    payload = call_args[0][0]
    assert payload.message == "Custom test msg"


# --- _build_multi_proposal_card() Tests ---


def _multi_proposal_payload() -> NotificationPayload:
    """Build a standard multi-proposal payload for tests."""
    return NotificationPayload(
        title="Propositions",
        message="Pas sûr à 100% sur le produit. Voici mes 3 options",
        card_type="multi-proposal",
        data={
            "client": "Durand",
            "proposals": [
                {
                    "name": "Tube Inox 304L DN50",
                    "reference": "TUB-304L-50",
                    "confidence_pct": "78",
                    "match_quality": "Good semantic match on material and diameter",
                },
                {
                    "name": "Tube Inox 316L DN50",
                    "reference": "TUB-316L-50",
                    "confidence_pct": "65",
                    "match_quality": "Similar dimensions, different grade",
                },
                {
                    "name": "Tube Acier DN50",
                    "reference": "TUB-ACR-50",
                    "confidence_pct": "42",
                    "match_quality": "Same diameter, different material",
                },
            ],
            "erp_url": "https://odoo.example.com/web#model=sale.order&view_type=list",
        },
    )


def test_build_multi_proposal_card_has_amber_accent(
    adapter: TeamsAdapter,
) -> None:
    """AC-1: multi-proposal card uses amber accent container (style=warning)."""
    payload = _multi_proposal_payload()
    envelope = adapter._build_adaptive_card(payload)
    card = envelope["attachments"][0]["content"]
    accent_container = card["body"][0]

    assert accent_container["type"] == "Container"
    assert accent_container["style"] == "warning"
    assert accent_container["items"][0]["text"] == "Q — AI Quote Agent"
    assert accent_container["items"][0]["weight"] == "Bolder"
    assert accent_container["items"][0]["color"] == "Light"


def test_build_multi_proposal_card_has_proposals_rendered(
    adapter: TeamsAdapter,
) -> None:
    """AC-1: multi-proposal card renders each proposal as a ColumnSet row."""
    payload = _multi_proposal_payload()
    envelope = adapter._build_adaptive_card(payload)
    card = envelope["attachments"][0]["content"]

    # Find ColumnSets in body (proposals)
    column_sets = [b for b in card["body"] if b["type"] == "ColumnSet"]
    assert len(column_sets) == 3

    # First proposal
    first = column_sets[0]
    assert len(first["columns"]) == 3
    assert first["columns"][0]["items"][0]["text"] == "Tube Inox 304L DN50"
    assert first["columns"][0]["items"][0]["weight"] == "Bolder"
    assert first["columns"][1]["items"][0]["text"] == "Good semantic match on material and diameter"
    assert first["columns"][1]["items"][0]["isSubtle"] is True
    assert first["columns"][2]["items"][0]["text"] == "78%"
    assert first["columns"][2]["items"][0]["weight"] == "Bolder"


def test_build_multi_proposal_card_has_erp_link(
    adapter: TeamsAdapter,
) -> None:
    """AC-1: multi-proposal card has 'Voir dans l'ERP' OpenUrl action."""
    payload = _multi_proposal_payload()
    envelope = adapter._build_adaptive_card(payload)
    card = envelope["attachments"][0]["content"]

    assert "actions" in card
    assert len(card["actions"]) == 1
    action = card["actions"][0]
    assert action["type"] == "Action.OpenUrl"
    assert action["title"] == "Voir dans l'ERP"
    assert action["url"] == "https://odoo.example.com/web#model=sale.order&view_type=list"


def test_build_multi_proposal_card_has_message(
    adapter: TeamsAdapter,
) -> None:
    """AC-1: multi-proposal card displays the casual French message."""
    payload = _multi_proposal_payload()
    envelope = adapter._build_adaptive_card(payload)
    card = envelope["attachments"][0]["content"]

    message_blocks = [b for b in card["body"] if b.get("type") == "TextBlock" and b.get("wrap") is True]
    assert len(message_blocks) >= 1
    assert any("Pas sûr à 100%" in b["text"] for b in message_blocks)


def test_build_multi_proposal_card_schema_valid(
    adapter: TeamsAdapter,
) -> None:
    """AC-4: multi-proposal card conforms to Adaptive Card v1.4 structure."""
    payload = _multi_proposal_payload()
    envelope = adapter._build_adaptive_card(payload)

    assert envelope["type"] == "message"
    assert len(envelope["attachments"]) == 1
    attachment = envelope["attachments"][0]
    assert attachment["contentType"] == "application/vnd.microsoft.card.adaptive"

    card = attachment["content"]
    assert card["type"] == "AdaptiveCard"
    assert card["version"] == "1.4"
    assert "$schema" in card


def test_build_multi_proposal_card_dispatches_correctly(
    adapter: TeamsAdapter,
) -> None:
    """AC-1: card_type='multi-proposal' dispatches to the multi-proposal builder, not generic."""
    payload = _multi_proposal_payload()
    envelope = adapter._build_adaptive_card(payload)
    card = envelope["attachments"][0]["content"]

    # Must have warning style (not accent from generic)
    assert card["body"][0]["style"] == "warning"
    # Must have actions (generic has none)
    assert "actions" in card


# --- _build_escalation_card() Tests ---


def _escalation_payload() -> NotificationPayload:
    """Build a standard escalation payload for tests."""
    return NotificationPayload(
        title="Escalade",
        message="Celui-là est compliqué. Durand demande quelque chose que je ne suis pas sûr de comprendre.",
        card_type="escalation",
        data={
            "client": "Durand",
            "understood": "Client demande des tubes inox; quantité 100 pièces",
            "uncertain": "Diamètre et grade exacts non précisés",
            "suggested_next_steps": [
                "Demander des precisions au client sur les produits souhaites",
                "Verifier les references produit avec le client",
                "Proposer un appel pour clarifier les besoins",
            ],
            "confidence_pct": "28",
            "erp_url": "https://odoo.example.com/web#model=sale.order&view_type=list",
        },
    )


def test_build_escalation_card_has_red_accent(
    adapter: TeamsAdapter,
) -> None:
    """AC-1: escalation card uses red accent container (style=attention)."""
    payload = _escalation_payload()
    envelope = adapter._build_adaptive_card(payload)
    card = envelope["attachments"][0]["content"]
    accent_container = card["body"][0]

    assert accent_container["type"] == "Container"
    assert accent_container["style"] == "attention"
    assert accent_container["items"][0]["text"] == "Q — AI Quote Agent"
    assert accent_container["items"][0]["weight"] == "Bolder"
    assert accent_container["items"][0]["color"] == "Light"


def test_build_escalation_card_has_context_sections(
    adapter: TeamsAdapter,
) -> None:
    """AC-2: escalation card renders understood, uncertain, and next steps sections."""
    payload = _escalation_payload()
    envelope = adapter._build_adaptive_card(payload)
    card = envelope["attachments"][0]["content"]

    # Find all containers (skip first accent container)
    containers = [b for b in card["body"] if b["type"] == "Container"]
    # accent + understood + uncertain + steps = 4 containers
    assert len(containers) == 4

    # "Ce que j'ai compris" section
    understood_container = containers[1]
    assert understood_container["items"][0]["text"] == "Ce que j'ai compris"
    assert understood_container["items"][0]["weight"] == "Bolder"
    assert understood_container["items"][1]["text"] == "Client demande des tubes inox; quantité 100 pièces"
    assert understood_container["items"][1]["wrap"] is True

    # "Ce qui est flou" section
    uncertain_container = containers[2]
    assert uncertain_container["items"][0]["text"] == "Ce qui est flou"
    assert uncertain_container["items"][0]["weight"] == "Bolder"
    assert uncertain_container["items"][1]["text"] == "Diamètre et grade exacts non précisés"
    assert uncertain_container["items"][1]["wrap"] is True
    assert uncertain_container["items"][1]["isSubtle"] is True

    # "Prochaines étapes suggérées" section
    steps_container = containers[3]
    assert steps_container["items"][0]["text"] == "Prochaines étapes suggérées"
    assert steps_container["items"][0]["weight"] == "Bolder"
    assert len(steps_container["items"]) == 4  # label + 3 steps
    assert steps_container["items"][1]["text"].startswith("• ")


def test_build_escalation_card_has_erp_link(
    adapter: TeamsAdapter,
) -> None:
    """AC-1: escalation card has 'Voir dans l'ERP' OpenUrl action."""
    payload = _escalation_payload()
    envelope = adapter._build_adaptive_card(payload)
    card = envelope["attachments"][0]["content"]

    assert "actions" in card
    assert len(card["actions"]) == 1
    action = card["actions"][0]
    assert action["type"] == "Action.OpenUrl"
    assert action["title"] == "Voir dans l'ERP"
    assert action["url"] == "https://odoo.example.com/web#model=sale.order&view_type=list"


def test_build_escalation_card_has_casual_french_message(
    adapter: TeamsAdapter,
) -> None:
    """AC-1: escalation card displays the casual French escalation message."""
    payload = _escalation_payload()
    envelope = adapter._build_adaptive_card(payload)
    card = envelope["attachments"][0]["content"]

    message_blocks = [b for b in card["body"] if b.get("type") == "TextBlock" and b.get("wrap") is True]
    assert any("Celui-là est compliqué" in b["text"] for b in message_blocks)


def test_build_escalation_card_schema_valid(
    adapter: TeamsAdapter,
) -> None:
    """AC-4: escalation card conforms to Adaptive Card v1.4 structure."""
    payload = _escalation_payload()
    envelope = adapter._build_adaptive_card(payload)

    assert envelope["type"] == "message"
    assert len(envelope["attachments"]) == 1
    attachment = envelope["attachments"][0]
    assert attachment["contentType"] == "application/vnd.microsoft.card.adaptive"

    card = attachment["content"]
    assert card["type"] == "AdaptiveCard"
    assert card["version"] == "1.4"
    assert "$schema" in card


def test_build_escalation_card_dispatches_correctly(
    adapter: TeamsAdapter,
) -> None:
    """AC-1: card_type='escalation' dispatches to the escalation builder, not generic."""
    payload = _escalation_payload()
    envelope = adapter._build_adaptive_card(payload)
    card = envelope["attachments"][0]["content"]

    # Must have attention style (not accent from generic)
    assert card["body"][0]["style"] == "attention"
    # Must have actions (generic has none)
    assert "actions" in card
