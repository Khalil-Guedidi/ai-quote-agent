"""Unit tests for keyword search and reference code detection."""

from __future__ import annotations

import pytest

from quote_agent.search.keyword import is_reference_code


class TestReferenceCodeDetection:
    """AC-2: Reference code regex correctly identifies product references."""

    @pytest.mark.parametrize(
        "query",
        [
            "TUB-304L-025",
            "BHM-M12x60",
            "TCA_10mm",
            "PLQ-INOX-304L-2x1000x2000",
            "VIS-HEX-M8x40",
            "BR-CU-15x1.5",
            "ECR-M10",
        ],
    )
    def test_is_reference_code_positive(self, query: str) -> None:
        """AC-2: Known reference code patterns are detected."""
        assert is_reference_code(query) is True

    @pytest.mark.parametrize(
        "query",
        [
            "tubes inox",
            "hello",
            "12345",
            "acier inoxydable 304L",
            "",
            "a",
            "tube rond ss 304L 25x1.5",
            "recherche de produit",
        ],
    )
    def test_is_reference_code_negative(self, query: str) -> None:
        """AC-2: Natural language queries are NOT detected as references."""
        assert is_reference_code(query) is False

    def test_is_reference_code_with_whitespace(self) -> None:
        """AC-2: Leading/trailing whitespace is stripped."""
        assert is_reference_code("  TUB-304L-025  ") is True
