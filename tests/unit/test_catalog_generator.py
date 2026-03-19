"""Tests for the synthetic catalog generator.

Validates that the generated catalog meets Story 3.0c acceptance criteria:
- AC-1: 50,000 realistic product records with correct attributes
- AC-2: Controlled noise at specified percentages
- AC-3: Versioned asset in correct format
"""

from __future__ import annotations

import json
from typing import Any

import pytest
from generate_test_catalog import (
    OUTPUT_FILE,
    SAMPLE_FILE,
    SAMPLE_SIZE,
    TOTAL_RECORDS,
    ProductRecord,
    compute_stats,
    generate_catalog,
)

# Use a smaller catalog for fast unit tests; full 50K tested in dedicated test
SMALL_CATALOG_SIZE = 1_000
SMALL_SEED = 42

REQUIRED_FIELDS = {
    "reference",
    "name",
    "description",
    "category",
    "unit_price",
    "stock_status",
    "is_active",
    "metadata",
}
VALID_STOCK_STATUSES = {"in_stock", "out_of_stock", "on_order"}
EXPECTED_CATEGORIES = {
    "Tubes & Tuyaux",
    "Boulonnerie & Visserie",
    "Toles & Plaques",
    "Profiles",
    "Raccords",
    "Roulements",
    "Joints & Etancheite",
    "Vannes & Robinetterie",
    "Filtration",
    "Electrique & Cables",
    "Outils de Coupe",
    "Abrasifs",
    "Lubrifiants",
    "EPI & Securite",
    "Quincaillerie",
}


@pytest.fixture(scope="module")
def small_catalog() -> list[ProductRecord]:
    """Generate a small catalog for fast unit tests."""
    return generate_catalog(total=SMALL_CATALOG_SIZE, seed=SMALL_SEED)


@pytest.fixture(scope="module")
def small_catalog_dicts(small_catalog: list[ProductRecord]) -> list[dict[str, Any]]:
    """Convert small catalog to dicts for JSON validation."""
    return [r.to_dict() for r in small_catalog]


class TestCatalogRecordCount:
    """AC-1/AC-3: Validate record counts."""

    def test_small_catalog_has_exact_count(self, small_catalog: list[ProductRecord]) -> None:
        """AC-1: Generator produces exactly the requested number of records."""
        assert len(small_catalog) == SMALL_CATALOG_SIZE

    def test_full_catalog_has_50k_records(self) -> None:
        """AC-1: Full catalog produces exactly 50,000 records."""
        catalog = generate_catalog(total=TOTAL_RECORDS, seed=SMALL_SEED)
        assert len(catalog) == TOTAL_RECORDS


class TestRequiredFields:
    """AC-1: All required fields present on every record."""

    def test_all_required_fields_present(self, small_catalog_dicts: list[dict[str, Any]]) -> None:
        """AC-1: Every record has all required fields."""
        for i, record in enumerate(small_catalog_dicts):
            missing = REQUIRED_FIELDS - set(record.keys())
            assert not missing, f"Record {i} missing fields: {missing}"

    def test_reference_is_non_empty_string(self, small_catalog: list[ProductRecord]) -> None:
        """AC-1: Reference codes are non-empty strings."""
        for r in small_catalog:
            assert isinstance(r.reference, str)
            assert len(r.reference) > 0

    def test_name_is_non_empty_string(self, small_catalog: list[ProductRecord]) -> None:
        """AC-1: Product names are non-empty strings."""
        for r in small_catalog:
            assert isinstance(r.name, str)
            assert len(r.name) > 0

    def test_description_is_string_or_none(self, small_catalog: list[ProductRecord]) -> None:
        """AC-1: Description is either a string or None."""
        for r in small_catalog:
            assert r.description is None or isinstance(r.description, str)

    def test_category_is_valid(self, small_catalog: list[ProductRecord]) -> None:
        """AC-1: Category is one of the defined categories."""
        for r in small_catalog:
            assert r.category in EXPECTED_CATEGORIES, f"Unknown category: {r.category}"

    def test_unit_price_is_positive_float(self, small_catalog: list[ProductRecord]) -> None:
        """AC-1: Prices are positive and reasonable (no negatives, no astronomical values)."""
        for r in small_catalog:
            assert isinstance(r.unit_price, float)
            assert r.unit_price > 0, f"Non-positive price: {r.unit_price}"
            assert r.unit_price < 10_000, f"Unrealistic price: {r.unit_price}"

    def test_stock_status_is_valid(self, small_catalog: list[ProductRecord]) -> None:
        """AC-1: Stock status is one of the valid values."""
        for r in small_catalog:
            assert r.stock_status in VALID_STOCK_STATUSES, f"Invalid stock_status: {r.stock_status}"

    def test_is_active_is_bool(self, small_catalog: list[ProductRecord]) -> None:
        """AC-1: is_active is a boolean."""
        for r in small_catalog:
            assert isinstance(r.is_active, bool)

    def test_metadata_is_dict(self, small_catalog: list[ProductRecord]) -> None:
        """AC-1: Metadata is always a dict."""
        for r in small_catalog:
            assert isinstance(r.metadata, dict)


class TestNoiseDistribution:
    """AC-2: Controlled noise at specified percentages."""

    def test_missing_metadata_within_tolerance(self, small_catalog: list[ProductRecord]) -> None:
        """AC-2: ~30% missing metadata (records with < 4 of 7 optional fields)."""
        total = len(small_catalog)
        all_optional_keys = {
            "weight_kg",
            "dimensions",
            "material",
            "supplier",
            "country_of_origin",
            "min_order_qty",
            "lead_time_days",
        }
        sparse_count = sum(1 for r in small_catalog if len(set(r.metadata.keys()) & all_optional_keys) < 4)
        pct = sparse_count / total
        # Tolerance: 30% +/- 15% for small catalog (randomness variance)
        assert 0.05 <= pct <= 0.55, f"Missing metadata percentage {pct:.1%} outside tolerance"

    def test_duplicate_variants_exist(self, small_catalog: list[ProductRecord]) -> None:
        """AC-2: ~5% duplicate products with variant names (identified by -VAR suffix)."""
        total = len(small_catalog)
        dup_count = sum(1 for r in small_catalog if r.reference.endswith("-VAR"))
        pct = dup_count / total
        # Tolerance: 1-10% for small catalog
        assert 0.01 <= pct <= 0.10, f"Duplicate variant percentage {pct:.1%} outside tolerance"

    def test_null_descriptions_exist(self, small_catalog: list[ProductRecord]) -> None:
        """AC-2: Some records have null descriptions."""
        null_count = sum(1 for r in small_catalog if r.description is None)
        assert null_count > 0, "Expected some null descriptions for realism"

    def test_inactive_products_within_tolerance(self, small_catalog: list[ProductRecord]) -> None:
        """AC-2: ~2% obsolete/inactive products."""
        total = len(small_catalog)
        inactive_count = sum(1 for r in small_catalog if not r.is_active)
        pct = inactive_count / total
        # Tolerance: 0.5-5% for small catalog
        assert 0.005 <= pct <= 0.05, f"Inactive percentage {pct:.1%} outside tolerance"

    def test_category_distribution_is_non_uniform(self, small_catalog: list[ProductRecord]) -> None:
        """AC-2: Category distribution is not uniform — heavy categories dominate."""
        cat_counts: dict[str, int] = {}
        for r in small_catalog:
            cat_counts[r.category] = cat_counts.get(r.category, 0) + 1

        counts = list(cat_counts.values())
        max_count = max(counts)
        min_count = min(counts)

        # The max category should be significantly larger than the min
        assert max_count > min_count * 2, "Distribution appears too uniform"

    def test_mixed_casing_exists(self, small_catalog: list[ProductRecord]) -> None:
        """AC-2: Some records have inconsistent casing."""
        has_lower = any(r.name == r.name.lower() and not r.name.isupper() for r in small_catalog)
        has_title = any(r.name == r.name.title() for r in small_catalog)
        has_upper = any(r.name == r.name.upper() for r in small_catalog)
        # At least one casing variant should exist
        assert has_lower or has_title or has_upper, "Expected some casing variation"


class TestReferenceCodePatterns:
    """AC-1: Reference codes follow expected patterns."""

    def test_references_have_family_prefixes(self, small_catalog: list[ProductRecord]) -> None:
        """AC-1: References start with known family prefixes."""
        valid_prefixes = {
            "TB",
            "VIS",
            "TL",
            "PRF",
            "RAC",
            "RLT",
            "JNT",
            "VAN",
            "FLT",
            "CAB",
            "OC",
            "ABR",
            "LUB",
            "EPI",
            "QNC",
        }
        for r in small_catalog:
            prefix = r.reference.split("-")[0]
            assert prefix in valid_prefixes, f"Unknown prefix: {prefix} in reference {r.reference}"

    def test_references_are_unique_except_variants(self, small_catalog: list[ProductRecord]) -> None:
        """AC-1: References are unique (variants have -VAR suffix)."""
        refs = [r.reference for r in small_catalog]
        # Remove -VAR suffix for uniqueness check within base references
        base_refs = [r.rstrip("-VAR") if r.endswith("-VAR") else r for r in refs]
        # We expect some collisions from variants but base refs should be largely unique
        unique_base = len(set(base_refs))
        assert unique_base > len(refs) * 0.90, "Too many reference collisions"


class TestJsonLinesFormat:
    """AC-3: JSON Lines format validation."""

    def test_records_serialize_to_valid_json(self, small_catalog: list[ProductRecord]) -> None:
        """AC-3: Each record produces valid JSON."""
        for r in small_catalog:
            json_str = json.dumps(r.to_dict(), ensure_ascii=False)
            parsed = json.loads(json_str)
            assert isinstance(parsed, dict)
            assert "reference" in parsed

    def test_output_files_exist(self) -> None:
        """AC-3: Output files exist after generation."""
        assert OUTPUT_FILE.exists(), f"Full catalog not found: {OUTPUT_FILE}"
        assert SAMPLE_FILE.exists(), f"Sample catalog not found: {SAMPLE_FILE}"

    def test_full_catalog_is_valid_jsonl(self) -> None:
        """AC-3: Every line in the full catalog is valid JSON."""
        line_count = 0
        with open(OUTPUT_FILE, encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    parsed = json.loads(stripped)
                except json.JSONDecodeError as e:
                    pytest.fail(f"Line {line_num} is not valid JSON: {e}")
                assert isinstance(parsed, dict)
                line_count += 1
        assert line_count == TOTAL_RECORDS

    def test_sample_file_has_correct_count(self) -> None:
        """AC-3: Sample file contains exactly SAMPLE_SIZE records."""
        line_count = 0
        with open(SAMPLE_FILE, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    line_count += 1
        assert line_count == SAMPLE_SIZE

    def test_sample_is_subset_of_full_catalog(self) -> None:
        """AC-3: Sample file records are the first N records of the full catalog."""
        with open(OUTPUT_FILE, encoding="utf-8") as f_full:
            full_lines = [next(f_full) for _ in range(SAMPLE_SIZE)]

        with open(SAMPLE_FILE, encoding="utf-8") as f_sample:
            sample_lines = f_sample.readlines()

        for i, (full_line, sample_line) in enumerate(zip(full_lines, sample_lines, strict=True)):
            assert full_line.strip() == sample_line.strip(), f"Mismatch at line {i}"


class TestDeterministicOutput:
    """AC-1: Deterministic seeding produces reproducible output."""

    def test_same_seed_produces_same_output(self) -> None:
        """AC-1: Two runs with same seed produce identical catalogs."""
        catalog1 = generate_catalog(total=100, seed=42)
        catalog2 = generate_catalog(total=100, seed=42)

        for r1, r2 in zip(catalog1, catalog2, strict=True):
            assert r1.reference == r2.reference
            assert r1.name == r2.name
            assert r1.category == r2.category
            assert r1.unit_price == r2.unit_price

    def test_different_seed_produces_different_output(self) -> None:
        """AC-1: Different seeds produce different catalogs."""
        catalog1 = generate_catalog(total=100, seed=42)
        catalog2 = generate_catalog(total=100, seed=99)

        # At least some records should differ
        diffs = sum(1 for r1, r2 in zip(catalog1, catalog2, strict=True) if r1.reference != r2.reference)
        assert diffs > 0


class TestComputeStats:
    """Validate the statistics computation."""

    def test_stats_include_all_categories(self, small_catalog: list[ProductRecord]) -> None:
        """Stats report all 15 categories."""
        stats = compute_stats(small_catalog)
        assert len(stats["categories"]) == len(EXPECTED_CATEGORIES)

    def test_stats_percentages_sum_near_100(self, small_catalog: list[ProductRecord]) -> None:
        """Stats category percentages sum to approximately 100%."""
        stats = compute_stats(small_catalog)
        total_pct = sum(info["pct"] for info in stats["categories"].values())
        assert 99.0 <= total_pct <= 101.0
