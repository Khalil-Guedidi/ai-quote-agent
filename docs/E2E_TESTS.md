# End-to-End Tests

E2E tests validate the Epic 2 email pipeline with **real services** (PostgreSQL, LLM). No mocking is used.

## Required Environment Variables

| Variable | Example | Description |
|---|---|---|
| `DATABASE__URL` | `postgresql://quote_agent:quote_agent_secret@localhost:5432/quote_agent` | Real PostgreSQL connection |
| `LLM__API_KEY` | `sk-...` | OpenAI API key for real LLM calls |
| `LLM__SIMPLE_MODEL` | `gpt-4o-mini` | Model used by E2E tests (cost-optimized) |

Optional (for IMAP-specific tests only):
| `EMAIL__IMAP_SERVER` | `imap.provider.com` | IMAP server |
| `EMAIL__USERNAME` | `quotes@domain.com` | IMAP username |
| `EMAIL__PASSWORD` | `...` | IMAP password |

## How to Run

```bash
# Start PostgreSQL (docker-compose)
docker compose up -d postgres

# Load environment and run E2E tests
set -a && source .env && set +a
pytest tests/e2e/ -m e2e -v
```

E2E tests are **excluded by default** from `pytest` runs via `addopts = "-m 'not e2e'"` in `pyproject.toml`.

## Expected Costs

Each full E2E test run makes ~4-6 real LLM API calls using `gpt-4o-mini`:
- `test_pipeline_processes_french_quote_request_e2e`: 2 calls (extraction + splitting)
- `test_extraction_produces_structured_output_from_real_llm`: 1 call
- `test_splitting_groups_distinct_requests_from_real_llm`: 2 calls (extraction + splitting)
- `test_pipeline_survives_prompt_injection_e2e`: 2 calls (extraction + splitting)
- `test_pipeline_produces_complete_trace_e2e`: 2 calls (extraction + splitting)

Estimated cost: < $0.01 per run with gpt-4o-mini.

## Infrastructure

- **PostgreSQL**: Provided by `docker-compose.yml` (pgvector/pgvector:pg16, port 5432)
- **Alembic migrations**: Run automatically before each test session
- **Cleanup**: Test data (identified by `e2e-test` prefix in message_id) is deleted after each test

## CI Notes

PostgreSQL service container in CI is deferred (tracked separately). E2E tests run locally for now.
