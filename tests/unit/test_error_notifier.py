"""Tests for the shared error notifier service."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def _reset_cache(_clear_settings_cache: None) -> None:
    """Ensure settings cache is cleared for every test."""


class TestSendErrorNotification:
    """Shared error notification helper works correctly."""

    async def test_sends_notification_payload(self, env_vars: dict[str, str]) -> None:
        """AC-3: Error notification is sent with correct payload."""
        from quote_agent.services.error_notifier import send_error_notification

        mock_adapter = AsyncMock()
        mock_adapter.send_notification.return_value = MagicMock(success=True)

        with patch("quote_agent.adapters.notification.get_notification_adapter", return_value=mock_adapter):
            await send_error_notification("Test error message")

        mock_adapter.send_notification.assert_awaited_once()
        payload = mock_adapter.send_notification.call_args[0][0]
        assert payload.title == "Erreur pipeline"
        assert "Test error message" in payload.message
        assert payload.card_type == "escalation"

    async def test_does_not_raise_on_notification_failure(self, env_vars: dict[str, str]) -> None:
        """AC-3: Fire-and-forget — exception in notification doesn't propagate."""
        from quote_agent.services.error_notifier import send_error_notification

        with patch("quote_agent.adapters.notification.get_notification_adapter", side_effect=RuntimeError("Boom")):
            # Should not raise
            await send_error_notification("Test error")

    async def test_cli_process_delegates_to_shared_helper(self, env_vars: dict[str, str]) -> None:
        """AC-7: CLI _send_error_notification delegates to shared helper."""
        from quote_agent.cli.process import _send_error_notification

        with patch("quote_agent.services.error_notifier.send_error_notification") as mock_shared:
            await _send_error_notification("CLI error")

        mock_shared.assert_awaited_once_with("CLI error")
