# Story 0.5: Réception Email + Extraction Données Structurées

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **developer**,
I want an n8n workflow that receives emails and extracts structured quote request data using an LLM,
So that I can validate the email-to-structured-data pipeline before the Python/LangGraph build.

**This story validates the second half of the prototype pipeline: can we reliably extract structured quote requests from raw email text?**

## Acceptance Criteria

1. **AC-0.5.1**: n8n workflow triggered by incoming email (IMAP or webhook)
   - Given: An IMAP-compatible mail server is accessible (or a simulated email source)
   - When: A quote request email arrives in the monitored mailbox
   - Then: The n8n workflow triggers automatically and receives the email content (subject, from, body/html)
   - And: The workflow can also be triggered manually for testing (manual trigger with sample email data)

2. **AC-0.5.2**: LLM-based extraction of structured data (client, products, quantities, specs)
   - Given: An email body containing a quote request (in French, industrial B2B context)
   - When: The extraction step processes the email text
   - Then: The LLM returns a structured JSON object containing:
     - `client_name`: Company or person requesting the quote
     - `client_email`: Sender email address
     - `products`: Array of requested items, each with:
       - `description`: Product name/description as written by the client
       - `reference`: Product reference/code if mentioned (null otherwise)
       - `quantity`: Requested quantity (number + unit if specified)
       - `specs`: Any specifications (dimensions, material, grade, finish, etc.)
     - `delivery_date`: Requested delivery date if mentioned (null otherwise)
     - `notes`: Any additional requirements or context
   - And: The extraction handles industrial French terminology, abbreviations, and jargon
   - And: The extraction handles multi-product requests (single email listing multiple items)

3. **AC-0.5.3**: Extraction tested on 5+ sample quote request emails
   - Given: At least 5 sample quote request emails are created (stored as JSON fixtures)
   - When: Each email is processed through the extraction workflow
   - Then: The structured output is correct for each sample (manual verification)
   - And: The samples cover diverse scenarios:
     - Simple single-product request with exact reference
     - Multi-product request (3+ items in one email)
     - Request with jargon/abbreviations (e.g., "inox 304L", "Ø25", "lg 6m")
     - Request referencing previous order ("comme la dernière fois")
     - Vague request with minimal product detail
   - And: Results are documented with extraction accuracy per sample

4. **AC-0.5.4**: Structured output format defined and validated
   - Given: The extraction schema is defined
   - When: The output is reviewed against the production architecture's `ParsedRequest` model direction
   - Then: The JSON schema is documented in the README
   - And: The schema is consistent with what Story 0.6 (end-to-end flow) will consume
   - And: Edge cases are documented (empty fields, unparseable content, non-quote emails)

## Tasks / Subtasks

- [x] Task 1: Set up email reception infrastructure (AC: #1)
  - [x] 1.1: Choose approach: (A) Add a lightweight IMAP server (e.g., Mailhog/MailPit) to docker-compose for local testing, OR (B) Use manual trigger with sample email JSON data. **Recommended: Option B for prototype simplicity** — add a manual trigger with hardcoded sample emails, plus document how to wire IMAP trigger later
  - [x] 1.2: Create 5+ sample email fixtures as JSON files in `prototype/data/emails/` with realistic French industrial B2B quote requests
  - [x] 1.3: Create the n8n workflow skeleton: manual trigger → load sample email → pass to extraction

- [x] Task 2: Implement LLM-based structured extraction (AC: #2)
  - [x] 2.1: Choose extraction approach in n8n: (A) **Information Extractor node** with schema definition + LLM sub-node, OR (B) **Code node** calling an external LLM API (OpenAI/Anthropic) with a structured prompt, OR (C) **HTTP Request** to a Python FastAPI script. **Recommended: Option B (Code node + LLM API)** for maximum control over the prompt and JSON parsing, or **Option A** if the n8n Information Extractor node handles French industrial text well
  - [x] 2.2: Define the extraction JSON schema matching AC-0.5.2 fields
  - [x] 2.3: Write the extraction prompt — must handle: French industrial jargon, multiple products, partial information, abbreviations (Ø, lg, inox, etc.)
  - [x] 2.4: Implement the extraction step in the n8n workflow
  - [x] 2.5: Add basic validation/cleanup of LLM output (handle malformed JSON, missing fields, null values)

- [x] Task 3: Create test email fixtures and run extraction tests (AC: #3)
  - [x] 3.1: Create sample email fixtures covering all 5 scenarios from AC-0.5.3:
    - `email_simple_ref.json` — Single product with exact reference code
    - `email_multi_products.json` — 3+ products in one email
    - `email_jargon.json` — Industrial French jargon and abbreviations
    - `email_previous_order.json` — References to past orders
    - `email_vague.json` — Minimal detail, vague description
  - [x] 3.2: Run each sample through the extraction workflow
  - [x] 3.3: Document extraction results — what was extracted correctly, what was missed, any hallucinations
  - [x] 3.4: Iterate on the prompt if accuracy is insufficient

- [x] Task 4: Documentation and schema validation (AC: #4)
  - [x] 4.1: Document the extraction JSON schema in `prototype/README.md` (new "Story 0.5" section)
  - [x] 4.2: Document the extraction approach (which LLM, which n8n node pattern, prompt strategy)
  - [x] 4.3: Document test results with accuracy analysis per sample
  - [x] 4.4: Document edge cases and how they're handled (non-quote emails, empty body, attachments-only)
  - [x] 4.5: Export the n8n workflow to `prototype/n8n-workflows/extract-quote-request.json`

## Dev Notes

### This is a Prototype — Keep it Simple

This is Epic 0 (prototype validation), NOT the production build. The goal is to validate that LLM-based extraction works on French industrial B2B emails, not to build a production-grade email pipeline. The production email pipeline (Epic 2) will use Python/LangGraph with IMAP adapter, security sanitization, and proper error handling.

**What to validate:**
- Can an LLM reliably extract structured data from messy French industrial quote request emails?
- What prompt engineering is needed for industrial jargon, abbreviations, and multi-product requests?
- What does the structured output look like? (Informs the production `ParsedRequest` model)
- Where does extraction fail? (Informs production design decisions)

**What NOT to build:**
- No real IMAP server integration needed — manual trigger with sample data is sufficient
- No email cleaning/denoising (signatures, threads) — that's Epic 2 (FR2)
- No prompt injection defense — that's Epic 2 (FR25-26)
- No multi-request detection (single email = multiple separate quote requests) — that's Epic 2 (FR4)
- No error handling beyond basic JSON parsing

### LLM Integration Approach

**Option A — n8n Information Extractor node (try first):**
n8n has a built-in "Information Extractor" node (LangChain-powered) that takes unstructured text and outputs structured JSON based on a schema. It requires a Chat Model sub-node (OpenAI or Anthropic).

Configuration:
- Text input: `{{ $json.body }}` (email body)
- Schema Type: "Define Below" with the extraction JSON schema
- Chat Model: OpenAI (GPT-4o) or Anthropic (Claude 3.5 Sonnet)

**Option B — n8n Code node + direct API call (fallback):**
If the Information Extractor doesn't handle French industrial text well, use a Code node to call the LLM API directly with a carefully crafted prompt:

```javascript
// In n8n Code node
const response = await this.helpers.httpRequest({
  method: 'POST',
  url: 'https://api.openai.com/v1/chat/completions',
  headers: {
    'Authorization': `Bearer ${$env.OPENAI_API_KEY}`,
    'Content-Type': 'application/json'
  },
  body: {
    model: 'gpt-4o',
    response_format: { type: 'json_object' },
    messages: [
      { role: 'system', content: EXTRACTION_PROMPT },
      { role: 'user', content: emailBody }
    ]
  }
});
```

**LLM choice**: GPT-4o or Claude 3.5 Sonnet. Both handle French well and support structured output. For the prototype, either works — the production build (Epic 4) will use the client's configured LLM via abstraction layer.

**Important**: An LLM API key (OpenAI or Anthropic) is required. Add to `.env`:
```
OPENAI_API_KEY=sk-...
# OR
ANTHROPIC_API_KEY=sk-ant-...
```

### Extraction Prompt Strategy

The prompt must handle French industrial B2B specifics:

```
You are an expert B2B quote request parser for an industrial steel and metals distributor.
Extract structured data from the following quote request email.

IMPORTANT RULES:
- The email is in French (industrial B2B context)
- Product descriptions may contain jargon: "inox" = stainless steel, "Ø" = diameter, "lg" = length
- Common abbreviations: 304L, 316L (steel grades), HM (hexagonal), BLN (bolt), etc.
- Quantities may use French notation: "200 pcs", "5 barres", "10 ml" (mètres linéaires)
- If information is not mentioned, use null (do NOT invent data)
- Extract ALL products mentioned, even if descriptions are vague
- References may look like: "TUBE-INOX-304L-25x1.5-6M" or "BLN-HM-8.8-M12x60"

Return a JSON object with this exact schema:
{
  "client_name": "string or null",
  "client_email": "string or null",
  "products": [
    {
      "description": "product description as written by client",
      "reference": "product code/reference if mentioned, else null",
      "quantity": "quantity with unit as written",
      "specs": "any specs (dimensions, material, grade, finish) or null"
    }
  ],
  "delivery_date": "delivery date if mentioned, else null",
  "notes": "any additional context or requirements, else null"
}
```

### Sample Email Fixtures

Create realistic French industrial B2B emails. Examples:

**Simple with reference:**
```
From: sophie.martin@acme-metal.fr
Subject: Demande de devis - tubes inox

Bonjour,

Pourriez-vous me faire un devis pour :
- 200 tubes TUBE-INOX-304L-25x1.5-6M

Merci,
Sophie Martin
Acme Métallurgie
```

**Multi-product:**
```
From: j.dupont@constructions-bernard.fr
Subject: Devis urgent - chantier Bordeaux

Bonjour,

Pour notre chantier de Bordeaux, nous aurions besoin de :
1. 500 barres rondes acier S235 Ø20 longueur 6m
2. 100 tubes carrés 40x40x3 en acier galvanisé, lg 6m
3. 50 cornières 50x50x5 en inox 304L, lg 3m
4. 200 boulons HM 8.8 M12x60

Livraison souhaitée avant le 15 avril.

Cordialement,
Jean Dupont
Constructions Bernard SAS
```

**Jargon-heavy:**
```
From: p.lefevre@sideral-industrie.com
Subject: Re: tubes et plats

Il me faudrait :
- 100 plats inox 304L 30x5 lg 3m
- 50 tubes ronds SS 316L Ø33.7x2 lg 6m
- Comme d'hab, qualité certif 3.1

Merci
PL
```

### Structured Output Alignment with Production Architecture

The production architecture defines `ParsedRequest` in `agent/state.py` (architecture.md). While the exact model isn't fully specified yet, the extraction schema for this prototype should be close to what production will use:

| Prototype field | Production direction | Notes |
|----------------|---------------------|-------|
| `client_name` | `ParsedRequest.client.name` | Will be richer in production (company, contact, account ID) |
| `client_email` | `ParsedRequest.client.email` | Used for client history lookup in production |
| `products[]` | `ParsedRequest.line_items[]` | Each item will have more fields in production |
| `products[].description` | `line_items[].raw_description` | Preserved for audit trail |
| `products[].reference` | `line_items[].reference_code` | Triggers exact-ref search path |
| `products[].quantity` | `line_items[].quantity` + `line_items[].unit` | Separate quantity and unit in production |
| `products[].specs` | `line_items[].specifications` | Structured specs object in production |
| `delivery_date` | `ParsedRequest.delivery_date` | ISO 8601 in production |
| `notes` | `ParsedRequest.additional_context` | Free text |

### n8n Workflow Structure

```
[Manual Trigger]
    |
    v
[Set Node — Load sample email data from fixture]
    |
    v
[Information Extractor / Code Node — LLM extraction]
    |
    v
[Set Node — Clean/validate extraction output]
    |
    v
[Debug — Output structured JSON to console]
```

For future IMAP integration (Story 0.6 or production), replace the Manual Trigger + Set Node with an Email Trigger (IMAP) node. The rest of the workflow stays the same.

### Dependencies Update

Add to `prototype/.env.example`:
```
# LLM API (choose one)
OPENAI_API_KEY=sk-your-key-here
# ANTHROPIC_API_KEY=sk-ant-your-key-here
```

No new Python dependencies needed — this story is n8n-only (except for sample email fixture creation, which is just JSON files).

### Gotchas to Avoid

1. **Do NOT build a real email server** — manual trigger with sample data is sufficient for prototype validation
2. **Do NOT clean/preprocess email content** (signature stripping, thread removal) — that's production Epic 2
3. **Do NOT implement prompt injection defense** — that's production Epic 2
4. **LLM JSON output can be flaky** — always validate/parse the response, handle malformed JSON gracefully
5. **French number notation**: "1 500" means 1500 (space as thousands separator), "2,5" means 2.5 (comma as decimal)
6. **n8n credentials for LLM**: Must be configured in n8n's credential store (Settings → Credentials), not just in .env
7. **n8n AI nodes require a Chat Model sub-node** connected — the Information Extractor won't work without it
8. **Keep sample emails realistic** — use real industrial product terminology from the existing catalog (`products_raw.json`) to ensure extracted data will match against the product database in Story 0.6
9. **The n8n workflow JSON must be exported to `prototype/n8n-workflows/`** for version control — n8n workflows are not stored in the repo by default
10. **Do NOT use n8n's built-in Odoo node** — Story 0.2 established that HTTP Request with JSON-RPC is more reliable

### Project Structure Notes

New files under `prototype/`:
```
prototype/
├── data/
│   └── emails/
│       ├── email_simple_ref.json       (NEW — sample email fixture)
│       ├── email_multi_products.json    (NEW — sample email fixture)
│       ├── email_jargon.json           (NEW — sample email fixture)
│       ├── email_previous_order.json   (NEW — sample email fixture)
│       └── email_vague.json            (NEW — sample email fixture)
├── n8n-workflows/
│   └── extract-quote-request.json      (NEW — extraction workflow)
├── .env.example                        (MODIFIED — add LLM API key)
└── README.md                           (MODIFIED — add Story 0.5 section)
```

No conflict with existing files. No Python scripts needed for this story.

### Previous Story Intelligence

From **Story 0.4** implementation:
- **fastembed + BGE-M3 for search**: Hybrid search validated (96.2% Hit@5). The extracted product descriptions from this story will be the search queries in Story 0.6
- **Existing catalog data**: `products_raw.json` contains 726 products with real names, codes, and descriptions — use these to create realistic sample emails with products that exist in the catalog
- **n8n workflow patterns**: Story 0.2 established the pattern of using Code nodes with `this.helpers.httpRequest()` for API calls — reuse this for LLM API calls if using the Code node approach
- **Qdrant hybrid search works**: The benchmark proved hybrid search handles jargon and abbreviations well — this informs confidence that LLM extraction + hybrid search will work together
- **Code review applied**: Consistent parameterization and clean code patterns established — follow the same standard

### Git Intelligence

Recent commits:
- `01e6ec4` — Story 0.4: hybrid search benchmark with GO decision (96.2% Hit@5)
- `8b8bf31` — Story 0.3: embedding generation + Qdrant vector search
- `ddd9e53` — Story 0.2: Odoo catalog ingestion with synthetic seeder
- `34866aa` — Story 0.1: Docker environment with n8n + Odoo

Pattern: each story commits all new/modified files with `feat:` prefix and story reference.

### Latest Technical Information

**n8n Information Extractor Node** (latest):
- LangChain-powered node for structured data extraction from text
- Supports schema definition via: attribute descriptions, JSON example, or direct JSON schema
- Requires a Chat Model sub-node (OpenAI, Anthropic, or others)
- Handles the prompt engineering internally — you define the schema, it generates the extraction prompt
- Output: structured JSON matching the defined schema

**n8n Email Trigger (IMAP)** (for reference, not needed in this story):
- Polls IMAP mailbox, triggers on new emails
- Output fields: `subject`, `from`, `to`, `date`, `body`, `html`, `attachments`
- Supports custom email rules for filtering
- Set `Force Reconnect Every Minutes` to 10-15 for reliability

**OpenAI Structured Outputs**:
- GPT-4o supports `response_format: { type: "json_object" }` for guaranteed JSON output
- Also supports `response_format: { type: "json_schema", json_schema: {...} }` for schema-constrained output
- Best for deterministic extraction tasks

### References

- [Source: _bmad-output/planning-artifacts/epics.md - Epic 0, Story 0.5]
- [Source: _bmad-output/planning-artifacts/architecture.md - AgentState.parsed_request, agent/nodes/email_parser.py]
- [Source: _bmad-output/planning-artifacts/architecture.md - FR1-4 Email Processing domain]
- [Source: _bmad-output/planning-artifacts/prd.md - FR1 (receive emails), FR2 (clean content), FR3 (extract structured data)]
- [Source: _bmad-output/planning-artifacts/prd.md - Prototype Phase: email → extraction → search → draft generation]
- [Source: _bmad-output/implementation-artifacts/0-4-recherche-hybride-benchmark-accuracy.md - fastembed, n8n workflow patterns, catalog data]
- [n8n Information Extractor node](https://docs.n8n.io/integrations/builtin/cluster-nodes/root-nodes/n8n-nodes-langchain.information-extractor/)
- [n8n Email Trigger (IMAP)](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.emailimap/)
- [OpenAI Structured Outputs](https://platform.openai.com/docs/guides/structured-outputs)

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context) + GPT-4o (extraction LLM)

### Debug Log References

- Extraction test run: 5/5 PASS, avg latency 2.6s (GPT-4o, temperature=0)
- No prompt iteration needed — first version of extraction prompt achieved 100% accuracy on all 5 fixtures
- n8n 2.12+ fix: `N8N_RUNNERS_ENABLED=false` + `N8N_BLOCK_ENV_ACCESS_IN_NODE=false` required for Code nodes to access `$env` and `require()`

### Completion Notes List

- **Task 1**: Chose Option B (manual trigger + sample emails). Created 5 email fixtures with products referencing the existing catalog (BHM-M12x50, manchons DN200, tuyaux PVC DN20, etc.). Created n8n workflow skeleton with Manual Trigger → Load Email Fixtures → LLM Extract → Results Summary.
- **Task 2**: Chose Option B (Code node + direct OpenAI API). Implemented extraction with GPT-4o, `response_format: json_object`, temperature=0. Prompt handles French industrial jargon (DN, lg, inox, certif 3.1), multi-product requests, and vague descriptions. Validation ensures required fields exist and products array is well-formed.
- **Task 3**: All 5 fixtures tested successfully — 100% accuracy on client extraction, product count, reference detection, and delivery date. No hallucinations observed. Also created a Python test script (`test-email-extraction.py`) for local testing without n8n dependency.
- **Task 4**: Documented extraction schema, approach, test results, edge cases, and production alignment in README.md. n8n workflow exported to `n8n-workflows/extract-quote-request.json`. Updated docker-compose to mount emails directory and `.env.example` with LLM API key.

### Change Log

- 2026-03-16: Story 0.5 implementation complete — email extraction pipeline validated
- 2026-03-16: Code review fix — removed unused/misleading `client_name` from EXPECTED dict in test-email-extraction.py (client_name is inherently fuzzy, not suitable for strict validation)

### File List

- `prototype/data/emails/email_simple_ref.json` (NEW)
- `prototype/data/emails/email_multi_products.json` (NEW)
- `prototype/data/emails/email_jargon.json` (NEW)
- `prototype/data/emails/email_previous_order.json` (NEW)
- `prototype/data/emails/email_vague.json` (NEW)
- `prototype/data/extraction-results.json` (NEW — test output)
- `prototype/n8n-workflows/extract-quote-request.json` (NEW)
- `prototype/scripts/test-email-extraction.py` (NEW)
- `prototype/docker-compose.yml` (MODIFIED — mount emails dir, update file access restriction)
- `prototype/.env.example` (MODIFIED — add LLM API key)
- `prototype/README.md` (MODIFIED — add Story 0.5 section)
