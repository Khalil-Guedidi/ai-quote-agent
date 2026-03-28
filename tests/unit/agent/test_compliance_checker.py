"""Unit tests for the compliance checker node."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

if TYPE_CHECKING:
    from collections.abc import Generator

import pytest

from quote_agent.agent.nodes.compliance_checker import (
    ComplianceCheckResult,
    ComplianceFlag,
    ExportControlConcern,
    LLMExportControlOutput,
    LLMSanctionOutput,
    SanctionMatch,
    check_compliance,
)
from quote_agent.exceptions import AdapterError, LLMTimeoutError
from quote_agent.services.extraction_models import ExtractedQuoteRequest, QuoteLineItem


def _make_request(
    *,
    description: str = "Tube inox 304L DN50",
    client_name: str | None = None,
) -> ExtractedQuoteRequest:
    """Build a minimal ExtractedQuoteRequest for testing."""
    return ExtractedQuoteRequest(
        line_items=[QuoteLineItem(description=description)],
        client_name=client_name,
        raw_text=description,
    )


def _make_adapter_mock(
    export_result: LLMExportControlOutput,
    sanction_result: LLMSanctionOutput,
) -> MagicMock:
    """Create a mock adapter that returns sequential results for two LLM calls."""
    mock_structured = AsyncMock()
    mock_structured.ainvoke = AsyncMock(side_effect=[export_result, sanction_result])
    mock_model = MagicMock()
    mock_model.with_structured_output = MagicMock(return_value=mock_structured)
    mock_adapter = MagicMock()
    mock_adapter.get_model = MagicMock(return_value=mock_model)
    return mock_adapter


def _clean_export_result() -> LLMExportControlOutput:
    return LLMExportControlOutput(
        has_concerns=False,
        concerns=[],
        reasoning="No export control concerns detected.",
    )


def _flagged_export_result() -> LLMExportControlOutput:
    return LLMExportControlOutput(
        has_concerns=True,
        concerns=[
            ExportControlConcern(
                category="nuclear",
                detail="Zirconium tubes of nuclear grade are controlled under EU Dual-Use Regulation",
                matched_term="zirconium grade nucléaire",
            ),
        ],
        reasoning="Product matches nuclear-related export control categories.",
    )


def _clean_sanction_result() -> LLMSanctionOutput:
    return LLMSanctionOutput(
        has_matches=False,
        matches=[],
        reasoning="No sanctioned entity matches found.",
    )


def _flagged_sanction_result() -> LLMSanctionOutput:
    return LLMSanctionOutput(
        has_matches=True,
        matches=[
            SanctionMatch(
                entity_name="DPRK Trading Corp",
                matched_against="DPRK Trading",
                list_source="OFAC SDN",
            ),
        ],
        reasoning="Client name matches OFAC SDN list entry.",
    )


@pytest.fixture(autouse=True)
def _mock_settings() -> Generator[None]:
    """Mock settings for all compliance checker tests."""
    from quote_agent.config import ComplianceSettings, Settings

    mock_settings = MagicMock(spec=Settings)
    mock_settings.compliance = ComplianceSettings()

    with patch("quote_agent.config.get_settings", return_value=mock_settings):
        yield


class TestExportControlDetection:
    """AC-1: Export-controlled product detection."""

    async def test_export_control_detected_when_controlled_product(self) -> None:
        """AC-1: Controlled product keyword → flag with type export_control."""
        adapter = _make_adapter_mock(_flagged_export_result(), _clean_sanction_result())
        request = _make_request(description="tubes zirconium grade nucléaire Ø25")

        result = await check_compliance(request, adapter)

        assert not result.is_compliant
        assert len(result.flags) == 1
        assert result.flags[0].flag_type == "export_control"
        assert result.flags[0].severity == "warning"
        assert "nuclear" in result.flags[0].detail
        assert result.flags[0].matched_term == "zirconium grade nucléaire"

    async def test_no_flag_when_normal_industrial_product(self) -> None:
        """AC-1: Normal industrial product → no flag."""
        adapter = _make_adapter_mock(_clean_export_result(), _clean_sanction_result())
        request = _make_request(description="Tube inox 304L DN50")

        result = await check_compliance(request, adapter)

        assert result.is_compliant
        assert len(result.flags) == 0


class TestSanctionedEntityDetection:
    """AC-2: Sanctioned entity detection."""

    async def test_sanctioned_entity_detected_when_sanctioned_name(self) -> None:
        """AC-2: Sanctioned name → flag with type sanctioned_entity, severity block."""
        adapter = _make_adapter_mock(_clean_export_result(), _flagged_sanction_result())
        request = _make_request(description="Steel plates")

        result = await check_compliance(request, adapter, client_name="DPRK Trading Corp")

        assert not result.is_compliant
        assert len(result.flags) == 1
        assert result.flags[0].flag_type == "sanctioned_entity"
        assert result.flags[0].severity == "block"
        assert "DPRK Trading Corp" in result.flags[0].detail
        assert "OFAC SDN" in result.flags[0].detail

    async def test_no_flag_when_normal_client_name(self) -> None:
        """AC-2: Normal client name → no flag."""
        adapter = _make_adapter_mock(_clean_export_result(), _clean_sanction_result())
        request = _make_request(description="Steel plates")

        result = await check_compliance(request, adapter, client_name="ACME Industries")

        assert result.is_compliant
        assert len(result.flags) == 0


class TestCombinedDetection:
    """AC-1 + AC-2: Combined detection scenarios."""

    async def test_both_flags_when_export_controlled_and_sanctioned(self) -> None:
        """Combined: export-controlled product + sanctioned entity → two flags."""
        adapter = _make_adapter_mock(_flagged_export_result(), _flagged_sanction_result())
        request = _make_request(description="tubes zirconium grade nucléaire")

        result = await check_compliance(request, adapter, client_name="DPRK Trading Corp")

        assert not result.is_compliant
        assert len(result.flags) == 2
        flag_types = {f.flag_type for f in result.flags}
        assert flag_types == {"export_control", "sanctioned_entity"}

    async def test_compliant_when_clean_request(self) -> None:
        """Combined: clean request → is_compliant=True, empty flags."""
        adapter = _make_adapter_mock(_clean_export_result(), _clean_sanction_result())
        request = _make_request(description="Tube inox 304L DN50")

        result = await check_compliance(request, adapter, client_name="ACME Industries")

        assert result.is_compliant
        assert result.flags == []


class TestFailSafe:
    """AC-7: Fail-safe behavior on LLM errors."""

    async def test_fail_safe_on_llm_timeout(self) -> None:
        """AC-7: LLM timeout → is_compliant=False with error flag."""
        mock_structured = AsyncMock()
        mock_structured.ainvoke = AsyncMock(side_effect=TimeoutError("LLM timed out"))
        mock_model = MagicMock()
        mock_model.with_structured_output = MagicMock(return_value=mock_structured)
        mock_adapter = MagicMock()
        mock_adapter.get_model = MagicMock(return_value=mock_model)

        request = _make_request(description="Some product")
        result = await check_compliance(request, mock_adapter)

        assert not result.is_compliant
        assert len(result.flags) == 2  # Both checks fail
        assert all(f.flag_type == "error" for f in result.flags)
        assert all(f.severity == "block" for f in result.flags)

    async def test_fail_safe_on_adapter_error(self) -> None:
        """AC-7: Adapter error → is_compliant=False with error flag."""
        mock_structured = AsyncMock()
        mock_structured.ainvoke = AsyncMock(side_effect=AdapterError("Connection failed"))
        mock_model = MagicMock()
        mock_model.with_structured_output = MagicMock(return_value=mock_structured)
        mock_adapter = MagicMock()
        mock_adapter.get_model = MagicMock(return_value=mock_model)

        request = _make_request(description="Some product")
        result = await check_compliance(request, mock_adapter)

        assert not result.is_compliant
        assert len(result.flags) == 2
        assert all(f.severity == "block" for f in result.flags)

    async def test_fail_safe_on_llm_timeout_error(self) -> None:
        """AC-7: LLMTimeoutError → is_compliant=False with error flag."""
        mock_structured = AsyncMock()
        mock_structured.ainvoke = AsyncMock(side_effect=LLMTimeoutError("Timeout"))
        mock_model = MagicMock()
        mock_model.with_structured_output = MagicMock(return_value=mock_structured)
        mock_adapter = MagicMock()
        mock_adapter.get_model = MagicMock(return_value=mock_model)

        request = _make_request(description="Some product")
        result = await check_compliance(request, mock_adapter)

        assert not result.is_compliant
        assert len(result.flags) == 2

    async def test_fail_safe_partial_error_export_ok_sanction_fails(self) -> None:
        """AC-7: Export OK but sanctions check fails → still not compliant."""
        # First call succeeds (export control - clean), second fails (sanction - error)
        mock_structured = AsyncMock()
        clean_export = _clean_export_result()
        mock_structured.ainvoke = AsyncMock(side_effect=[clean_export, AdapterError("Sanction check failed")])
        mock_model = MagicMock()
        mock_model.with_structured_output = MagicMock(return_value=mock_structured)
        mock_adapter = MagicMock()
        mock_adapter.get_model = MagicMock(return_value=mock_model)

        request = _make_request(description="Normal product")
        result = await check_compliance(request, mock_adapter)

        assert not result.is_compliant
        assert len(result.flags) == 1
        assert result.flags[0].flag_type == "error"
        assert result.flags[0].severity == "block"


class TestDurationTracking:
    """AC-4: check_duration_ms populated."""

    async def test_duration_tracked(self) -> None:
        """AC-4: check_duration_ms is populated."""
        adapter = _make_adapter_mock(_clean_export_result(), _clean_sanction_result())
        request = _make_request()

        result = await check_compliance(request, adapter)

        assert result.check_duration_ms >= 0


class TestStructuredLogging:
    """AC-9: Structured logging for compliance results."""

    async def test_logging_emitted_for_compliant_result(self, caplog: pytest.LogCaptureFixture) -> None:
        """AC-9: Structured log emitted with correct component for compliant result."""
        adapter = _make_adapter_mock(_clean_export_result(), _clean_sanction_result())
        request = _make_request()

        with caplog.at_level(logging.INFO, logger="quote_agent.agent.nodes.compliance_checker"):
            result = await check_compliance(request, adapter)

        assert result.is_compliant
        assert any("compliant" in record.message for record in caplog.records)

    async def test_logging_emitted_for_flagged_result(self, caplog: pytest.LogCaptureFixture) -> None:
        """AC-9: Structured log emitted with correct component for flagged result."""
        adapter = _make_adapter_mock(_flagged_export_result(), _clean_sanction_result())
        request = _make_request(description="uranium centrifuge parts")

        with caplog.at_level(logging.INFO, logger="quote_agent.agent.nodes.compliance_checker"):
            result = await check_compliance(request, adapter)

        assert not result.is_compliant
        assert any("flagged" in record.message for record in caplog.records)


class TestDTOModels:
    """AC-4: DTO model validation."""

    def test_compliance_flag_model(self) -> None:
        """AC-4: ComplianceFlag model has correct fields."""
        flag = ComplianceFlag(
            flag_type="export_control",
            severity="warning",
            detail="Test detail",
            matched_term="test",
        )
        assert flag.flag_type == "export_control"
        assert flag.severity == "warning"
        assert flag.detail == "Test detail"
        assert flag.matched_term == "test"

    def test_compliance_check_result_model(self) -> None:
        """AC-4: ComplianceCheckResult model has correct fields."""
        result = ComplianceCheckResult(
            is_compliant=True,
            flags=[],
            check_duration_ms=100,
        )
        assert result.is_compliant is True
        assert result.flags == []
        assert result.check_duration_ms == 100

    def test_compliance_check_result_defaults(self) -> None:
        """AC-4: ComplianceCheckResult defaults are correct."""
        result = ComplianceCheckResult(is_compliant=True)
        assert result.flags == []
        assert result.check_duration_ms == 0

    def test_compliance_flag_literal_types(self) -> None:
        """AC-4: flag_type and severity are Literal constrained."""
        # Valid values should work
        ComplianceFlag(flag_type="export_control", severity="warning", detail="x", matched_term="y")
        ComplianceFlag(flag_type="sanctioned_entity", severity="block", detail="x", matched_term="y")
        ComplianceFlag(flag_type="error", severity="block", detail="x", matched_term="y")

        # Invalid flag_type should fail
        with pytest.raises(Exception):  # noqa: B017
            ComplianceFlag(flag_type="invalid", severity="warning", detail="x", matched_term="y")  # type: ignore[arg-type]
