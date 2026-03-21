"""Unit tests for the CLI draft-create command."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

from typer.testing import CliRunner

from quote_agent.adapters.erp.models import QuoteDraftResult
from quote_agent.cli.main import app

runner = CliRunner()

_PATCH_TARGET = "quote_agent.adapters.erp.get_erp_adapter"


def _make_result() -> QuoteDraftResult:
    """Build a sample QuoteDraftResult."""
    return QuoteDraftResult(
        odoo_id=123,
        order_reference="SO042",
        state="draft",
        line_count=1,
    )


def _mock_adapter_with_create(return_value: object = None, side_effect: object = None) -> MagicMock:
    """Create a mock adapter with create_draft_quote configured."""
    mock_adapter = MagicMock()
    mock_adapter.create_draft_quote = AsyncMock(return_value=return_value, side_effect=side_effect)
    return mock_adapter


class TestDraftCreateSuccess:
    """AC-6: CLI draft-create success cases."""

    def test_formatted_output(self) -> None:
        """AC-6: Displays draft result in formatted output."""
        mock_adapter = _mock_adapter_with_create(return_value=_make_result())
        with patch(_PATCH_TARGET, return_value=mock_adapter):
            result = runner.invoke(app, [
                "draft-create", "--client", "42", "--product", "55", "--quantity", "100",
            ])

        assert result.exit_code == 0
        assert "SO042" in result.output
        assert "123" in result.output
        assert "draft" in result.output

    def test_json_output(self) -> None:
        """AC-6: Displays draft result as JSON."""
        mock_adapter = _mock_adapter_with_create(return_value=_make_result())
        with patch(_PATCH_TARGET, return_value=mock_adapter):
            result = runner.invoke(app, [
                "draft-create", "--client", "42", "--product", "55", "--quantity", "100", "--json",
            ])

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["odoo_id"] == 123
        assert data["order_reference"] == "SO042"
        assert data["state"] == "draft"
        assert data["line_count"] == 1

    def test_with_price_override(self) -> None:
        """AC-6: Supports --price optional flag."""
        mock_adapter = _mock_adapter_with_create(return_value=_make_result())
        with patch(_PATCH_TARGET, return_value=mock_adapter):
            result = runner.invoke(app, [
                "draft-create", "--client", "42", "--product", "55",
                "--quantity", "100", "--price", "0.50",
            ])

        assert result.exit_code == 0
        # Verify the quote was built with the price
        call_args = mock_adapter.create_draft_quote.call_args[0][0]
        assert call_args.lines[0].unit_price == 0.50

    def test_with_description(self) -> None:
        """AC-6: Supports --description optional flag."""
        mock_adapter = _mock_adapter_with_create(return_value=_make_result())
        with patch(_PATCH_TARGET, return_value=mock_adapter):
            result = runner.invoke(app, [
                "draft-create", "--client", "42", "--product", "55",
                "--quantity", "100", "--description", "Grade 8.8",
            ])

        assert result.exit_code == 0
        call_args = mock_adapter.create_draft_quote.call_args[0][0]
        assert call_args.lines[0].description == "Grade 8.8"


class TestDraftCreateErrors:
    """AC-6: CLI draft-create error handling."""

    def test_missing_required_flags(self) -> None:
        """AC-6: Missing required flags exits with error."""
        result = runner.invoke(app, ["draft-create"])
        assert result.exit_code != 0

    def test_missing_client_flag(self) -> None:
        """AC-6: Missing --client flag exits with error."""
        result = runner.invoke(app, ["draft-create", "--product", "55", "--quantity", "100"])
        assert result.exit_code != 0

    def test_missing_product_flag(self) -> None:
        """AC-6: Missing --product flag exits with error."""
        result = runner.invoke(app, ["draft-create", "--client", "42", "--quantity", "100"])
        assert result.exit_code != 0

    def test_missing_quantity_flag(self) -> None:
        """AC-6: Missing --quantity flag exits with error."""
        result = runner.invoke(app, ["draft-create", "--client", "42", "--product", "55"])
        assert result.exit_code != 0

    def test_not_found_error(self) -> None:
        """AC-6: ValueError (client/product not found) exits with code 1."""
        mock_adapter = _mock_adapter_with_create(side_effect=ValueError("Client not found: 999"))
        with patch(_PATCH_TARGET, return_value=mock_adapter):
            result = runner.invoke(app, [
                "draft-create", "--client", "999", "--product", "55", "--quantity", "100",
            ])

        assert result.exit_code == 1
        assert "Not found" in result.output

    def test_connection_error(self) -> None:
        """AC-6: Connection error exits with code 1."""
        mock_adapter = _mock_adapter_with_create(side_effect=ConnectionRefusedError("Connection refused"))
        with patch(_PATCH_TARGET, return_value=mock_adapter):
            result = runner.invoke(app, [
                "draft-create", "--client", "42", "--product", "55", "--quantity", "100",
            ])

        assert result.exit_code == 1
        assert "Error" in result.output
