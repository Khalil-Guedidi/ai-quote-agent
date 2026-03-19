# Story 3.0c: Génération Catalogue Test 50K Réaliste

Status: done

## Story

As a **QA engineer (Dana)**,
I want a realistic synthetic French industrial product catalog of 50,000 references,
So that Epic 3 search and matching features are validated against data representative of real-world conditions.

## Acceptance Criteria

1. **AC-1: Realistic product records**
   - Given public sources of French industrial product naming conventions (RS Components, Wurth, etc.)
   - When the catalog generation pipeline runs
   - Then it produces 50,000 product records with realistic attributes: reference codes, abbreviated French names (e.g., "TB RD INOX 304L 25x1.5 LG6000"), categories, prices, stock status, and metadata

2. **AC-2: Controlled noise and realism**
   - Given the generated catalog
   - When analyzed for realism
   - Then it includes controlled noise: ~30% missing metadata, naming inconsistencies, duplicates with variant names, mix of French/English descriptions, truncated fields

3. **AC-3: Versioned project asset**
   - Given the catalog is generated
   - When loaded into the test infrastructure
   - Then it is versioned as a project asset and reusable across epics

## Tasks / Subtasks

- [x] Task 1: Design the catalog data schema (AC: 1, 3)
  - [x] 1.1: Define the product record structure matching what Story 3.1 (ingestion) expects — align with `ERPAdapter` future `get_products()` return type and `adapters/erp/models.py` `Product` DTO (not yet implemented, define the shape here)
  - [x] 1.2: Required fields: `reference` (str), `name` (str), `description` (str|None), `category` (str), `unit_price` (float), `stock_status` (str: "in_stock"|"out_of_stock"|"on_order"), `is_active` (bool), `metadata` (dict with variable keys)
  - [x] 1.3: Metadata fields (variably present): `weight_kg`, `dimensions`, `material`, `supplier`, `country_of_origin`, `min_order_qty`, `lead_time_days`

- [x] Task 2: Build the catalog generator script (AC: 1, 2)
  - [x] 2.1: Create `scripts/generate_test_catalog.py` — standalone Python script, no project imports needed
  - [x] 2.2: Define product families covering real French industrial categories (~15-20 families): tubes/tuyaux, boulonnerie/visserie, roulements, joints/etancheite, toles/plaques, profiles, raccords, vannes/robinetterie, filtration, electrique/cables, outils de coupe, abrasifs, lubrifiants, EPI/securite, quincaillerie
  - [x] 2.3: Per family: define realistic reference code patterns (e.g., "TB-RD-{material}-{diameter}x{thickness}-LG{length}"), abbreviated naming templates in French, price ranges, typical materials, dimension ranges
  - [x] 2.4: Generate 50,000 records with realistic distribution across families (not uniform — heavy industrial families like tubes/boulonnerie should dominate)
  - [x] 2.5: Inject controlled noise per AC-2:
    - ~30% missing metadata fields (random subset of optional fields omitted)
    - ~5% duplicate products with variant names (e.g., "TUBE ROND INOX 304L" vs "TB RD SS 304L")
    - ~10% mixed French/English descriptions
    - ~5% truncated fields (e.g., cut-off descriptions)
    - ~3% inconsistent casing (ALLCAPS vs lowercase vs MixedCase)
    - ~2% obsolete/inactive products (`is_active: false`)
  - [x] 2.6: Use deterministic seeding (`random.seed(42)`) for reproducible output

- [x] Task 3: Output format and versioning (AC: 3)
  - [x] 3.1: Output as JSON Lines (`.jsonl`) — one product per line, efficient for streaming ingestion in Story 3.1
  - [x] 3.2: Save to `tests/fixtures/catalog_50k.jsonl`
  - [x] 3.3: Add `tests/fixtures/catalog_50k_sample.jsonl` with first 100 records for quick unit tests
  - [x] 3.4: Add `.gitattributes` entry for LFS tracking of `catalog_50k.jsonl` if >50MB, otherwise commit directly
  - [x] 3.5: Script should print generation stats: total records, per-family counts, noise distribution percentages

- [x] Task 4: Validation and quality checks (AC: 1, 2, 3)
  - [x] 4.1: Add `tests/unit/test_catalog_generator.py` — validate generation output:
    - Total record count == 50,000
    - All required fields present on every record
    - Noise percentages within tolerance (30% +/- 5% missing metadata, etc.)
    - Reference codes follow expected patterns
    - Price ranges are realistic (no negatives, no astronomically high values)
    - Category distribution is non-uniform
  - [x] 4.2: Validate JSON Lines format is parseable (each line is valid JSON)
  - [x] 4.3: Verify sample file is a proper subset of full catalog

## Dev Notes

### What This Story IS

This is a **data generation** story. The primary output is a synthetic catalog file (`tests/fixtures/catalog_50k.jsonl`) and the script that generates it (`scripts/generate_test_catalog.py`). This is test infrastructure, not production code.

### What This Story Is NOT

- NOT a database migration or SQLAlchemy model — the catalog is a flat file consumed by Story 3.1
- NOT an ERP integration — this generates synthetic data, not real Odoo data
- NOT an embedding/vector story — just raw product records

### Technical Requirements

**No new dependencies needed.** The generator uses only Python stdlib (`json`, `random`, `string`, `pathlib`, `dataclasses`). No LLM calls, no database, no external services.

**Output format — JSON Lines (.jsonl):**
```json
{"reference": "TB-RD-INOX304L-025x1.5-LG6000", "name": "TUBE ROND INOX 304L 25x1.5 LG6000", "description": "Tube rond en acier inoxydable 304L, diametre 25mm, epaisseur 1.5mm, longueur 6000mm", "category": "Tubes & Tuyaux", "unit_price": 42.50, "stock_status": "in_stock", "is_active": true, "metadata": {"weight_kg": 3.2, "material": "INOX 304L", "dimensions": "25x1.5x6000", "supplier": "SAINT-GOBAIN"}}
```

**Product naming realism — French industrial abbreviation conventions:**
- `TB` = Tube, `RD` = Rond, `CR` = Carré, `HEX` = Hexagonal
- `INOX` = Inoxydable (stainless), `GALVA` = Galvanisé, `BRUT` = Raw
- `LG` = Longueur, `EP` = Epaisseur, `DN` = Diamètre Nominal
- `VIS` = Vis (screw), `ECR` = Ecrou (nut), `RDL` = Rondelle (washer)
- `CHC` = Vis à tête cylindrique creuse (socket head cap screw)
- `HM` = Huile Moteur, `HH` = Huile Hydraulique

**Realistic French industrial categories (weighted distribution):**
| Category | Weight | Example Products |
|----------|--------|------------------|
| Tubes & Tuyaux | 15% | Tubes ronds, carrés, rectangulaires en acier, inox, cuivre |
| Boulonnerie & Visserie | 15% | Vis CHC, HM, boulons, écrous, rondelles |
| Tôles & Plaques | 10% | Tôles laminées, plaques découpées |
| Profilés | 8% | IPE, HEA, cornières, fers en U |
| Raccords | 8% | Raccords filetés, soudés, à compression |
| Roulements | 7% | Roulements à billes, rouleaux, butées |
| Joints & Étanchéité | 6% | Joints toriques, plats, tresses |
| Vannes & Robinetterie | 6% | Vannes papillon, à bille, clapets |
| Filtration | 5% | Filtres hydrauliques, pneumatiques, air |
| Électrique & Câbles | 5% | Câbles, gaines, connecteurs |
| Outils de Coupe | 4% | Forets, fraises, plaquettes carbure |
| Abrasifs | 3% | Disques, meules, bandes abrasives |
| Lubrifiants | 3% | Huiles, graisses, sprays |
| EPI & Sécurité | 3% | Gants, lunettes, chaussures sécurité |
| Quincaillerie | 2% | Charnières, poignées, serrures |

### Architecture Compliance

- **File locations:** Generator script in `scripts/` (not `src/`). Output in `tests/fixtures/`. Tests in `tests/unit/`.
- **No production code changes.** This story does not touch `src/quote_agent/`.
- **Naming:** PEP 8 — `snake_case` for files, functions, variables. `PascalCase` for dataclasses if used.
- **Type safety:** The script should have type annotations and pass `mypy --strict` (add to mypy paths if needed, or use inline `# type: ignore` sparingly).
- **Quality gates:** `ruff check` and `ruff format` must pass on all new files.

### Data Schema Alignment with Story 3.1

Story 3.1 (Ingestion Catalogue depuis l'ERP) will consume this catalog. The record shape here **defines the contract** for ingestion. Key alignment points:

- `reference` field = primary product identifier (unique, used for exact-match search in Story 3.3)
- `name` field = abbreviated French product name (the "dirty" data that Story 3.3 semantic search must handle)
- `description` field = optional longer description (sometimes French, sometimes English, sometimes truncated — tests search robustness)
- `stock_status` field = used by Story 3.4 (Filtre de Proposabilité) to filter non-proposable products
- `is_active` field = used by Story 3.4 for obsolete product filtering
- `category` field = used for faceted search and distribution analysis

### Noise Design Rationale

The noise percentages (~30% missing metadata, ~5% duplicates, etc.) mirror real-world ERP catalog conditions documented in the PRD: "the agent works with dirty product catalogs out of the box" and "zero-preprocessing" promise. This noise is specifically what Epic 3 search features must handle gracefully.

### Previous Story Intelligence (Story 3.0b)

**Key learnings:**
- Documentation-only story executed cleanly — no production code issues
- Cross-referencing against retrospectives was thorough; apply same rigor to category/noise validation
- `docs/project-context.md` now exists and documents all established patterns

**Files from Story 3.0b:**
- `docs/project-context.md` — centralized patterns reference (don't duplicate its content)

### Git Intelligence

Recent commits show Stories 3.0a (E2E tests) and 3.0b (project-context.md) completed successfully. The project is in a clean state ready for new work. No existing `scripts/` directory — it will need to be created.

### Project Structure Notes

- `scripts/` directory does not exist yet — create it for the generator
- `tests/fixtures/` directory does not exist yet — create it for catalog output
- The generator is a standalone script, not a CLI command — no integration with `typer` or `quote_agent.cli`
- Keep the script self-contained: no imports from `quote_agent.*`

### What NOT to Do

- Do NOT create SQLAlchemy models for products — that's Story 3.1's job
- Do NOT add new pip/uv dependencies — stdlib only
- Do NOT modify any existing production code or tests
- Do NOT use LLM to generate the catalog — this is deterministic synthetic data
- Do NOT create an overly complex OOP hierarchy for the generator — a well-structured script with functions is fine
- Do NOT commit the catalog file if >50MB without Git LFS — check file size first

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 3.0c] — acceptance criteria and business context
- [Source: _bmad-output/planning-artifacts/epics.md#Story 3.1] — consumer of this catalog (ingestion story)
- [Source: _bmad-output/planning-artifacts/epics.md#Story 3.3] — search must handle dirty names/abbreviations
- [Source: _bmad-output/planning-artifacts/epics.md#Story 3.4] — proposability filter uses stock_status and is_active
- [Source: _bmad-output/planning-artifacts/architecture.md#Data Architecture] — HNSW for 50K refs, hybrid search strategy
- [Source: _bmad-output/planning-artifacts/prd.md#Journey 7] — zero-preprocessing onboarding, dirty catalog promise
- [Source: src/quote_agent/adapters/erp/models.py] — future Product DTO placeholder (align schema)
- [Source: src/quote_agent/adapters/erp/protocol.py] — future get_products() method (align return shape)
- [Source: docs/project-context.md] — established patterns and conventions

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

No debug issues encountered.

### Completion Notes List

- Implemented `ProductRecord` dataclass with all 8 required fields aligned with future Story 3.1 `Product` DTO contract
- Created 15 product families with realistic French industrial naming conventions, weighted distribution (Tubes & Boulonnerie at 15% each, Quincaillerie at 2%)
- Each family has dedicated dimension generators producing realistic physical attributes
- Noise injection: ~30% sparse metadata, ~5% duplicate variants (with -VAR suffix), ~10% mixed FR/EN descriptions, ~5% truncated descriptions, ~3% inconsistent casing, ~2% inactive products
- Deterministic output via `random.Random(42)` instance seeding
- Output: 17.4 MB JSONL file (under 50MB threshold, no Git LFS needed)
- 28 unit tests covering: record count, required fields, noise distributions, reference code patterns, JSONL format, deterministic reproducibility, stats computation
- All 215 unit tests pass (no regressions), ruff check/format clean, mypy --strict clean

### Change Log

- 2026-03-19: Implemented all 4 tasks — catalog generator script, 50K JSONL output, 100-record sample, 28 validation tests
- 2026-03-19: Code review fix — removed `sys.path` hack from test file, moved path setup to `tests/conftest.py`, added `mypy_path = ["scripts"]` to `pyproject.toml`. mypy --strict now clean on both files.

### File List

- `scripts/generate_test_catalog.py` (new) — standalone catalog generator script
- `tests/fixtures/catalog_50k.jsonl` (new) — 50,000 product records in JSONL format
- `tests/fixtures/catalog_50k_sample.jsonl` (new) — first 100 records for quick unit tests
- `tests/unit/test_catalog_generator.py` (new) — 28 validation tests for catalog generation
- `tests/conftest.py` (modified) — added `scripts/` to `sys.path` for script imports
- `pyproject.toml` (modified) — added `mypy_path = ["scripts"]` for static analysis
