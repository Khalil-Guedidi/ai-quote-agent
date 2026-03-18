# Story 1.4: Configuration LLM Provider & Adapter

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an **IT operator**,
I want to configure the LLM provider (endpoint, API key, model) and model routing rules,
So that the agent can use the company's chosen AI provider without code changes.

## Acceptance Criteria

1. **AC-1.4.1**: LLM adapter connects using OpenAI-compatible API
   - Given LLM provider settings are in `.env` (endpoint, API key, model name)
   - When the application loads the LLM adapter
   - Then it connects using the OpenAI-compatible API abstraction via `langchain-openai` `ChatOpenAI`
   - And the adapter exposes an async `health_check()` method returning `ServiceHealth`
   - And credentials (`api_key`) are never logged or exposed (use `SecretStr`)

2. **AC-1.4.2**: Model routing rules are typed and validated
   - Given model routing rules are configured (e.g., `simple_model=gpt-4o-mini`, `complex_model=gpt-4o`)
   - When the configuration is loaded via `settings.llm`
   - Then the routing rules are available as typed `LLMSettings` fields
   - And `get_model(complexity)` returns the correct `ChatOpenAI` instance for `"simple"`, `"complex"`, or `"default"`
   - And invalid routing rules (empty model name) produce clear validation errors at startup

3. **AC-1.4.3**: Health check detects LLM provider unavailability
   - Given the LLM provider is unavailable (wrong URL, invalid key, timeout)
   - When the adapter's `health_check()` is called
   - Then it returns `ServiceHealth(status="unhealthy", error="<descriptive message>")`
   - And the `/health` endpoint reflects LLM degradation in `services.llm`

4. **AC-1.4.4**: Adapter follows the project Protocol pattern
   - Given the adapter follows the architecture's adapter pattern
   - Then `adapters/llm/protocol.py` defines an `LLMAdapter` Protocol class
   - And `adapters/llm/openai_compat.py` implements `OpenAICompatAdapter`
   - And `adapters/llm/models.py` defines typed request/response DTOs
   - And all methods are async and return typed DTOs (never raw `dict`)

5. **AC-1.4.5**: Tests pass
   - Given the test suite exists
   - When I run `uv run pytest tests/unit/test_llm_adapter.py`
   - Then all LLM adapter tests pass (healthy check, unhealthy check, model routing, adapter protocol compliance)
   - And `uv run ruff check src/ tests/` and `uv run mypy src/` both succeed

## Tasks / Subtasks

- [x] Task 1: Create LLM adapter DTOs (AC: 4)
  - [x] 1.1: Create `src/quote_agent/adapters/llm/models.py` with Pydantic DTOs:
    - `LLMRequest` — `messages: list[LLMMessage]`, `model: str | None = None`, `temperature: float = 0.0`, `max_tokens: int | None = None`
    - `LLMMessage` — `role: Literal["system", "user", "assistant"]`, `content: str`
    - `LLMResponse` — `content: str`, `model: str`, `usage: LLMUsage | None = None`
    - `LLMUsage` — `prompt_tokens: int`, `completion_tokens: int`, `total_tokens: int`

- [x] Task 2: Create LLM adapter Protocol (AC: 4)
  - [x] 2.1: Create `src/quote_agent/adapters/llm/protocol.py` with:
    - `LLMAdapter` Protocol class with:
      - `async def invoke(self, request: LLMRequest) -> LLMResponse` — send a request to the LLM
      - `async def health_check(self) -> ServiceHealth` — check provider connectivity
      - `def get_model(self, complexity: str) -> ChatOpenAI` — return configured model for complexity level

- [x] Task 3: Implement OpenAI-compatible adapter (AC: 1, 2, 3, 4)
  - [x] 3.1: Create `src/quote_agent/adapters/llm/openai_compat.py` with `OpenAICompatAdapter`:
    - Constructor takes `LLMSettings` (from `settings.llm`)
    - Creates `ChatOpenAI` instances via `langchain-openai` package:
      - `_default_model`: `ChatOpenAI(model=settings.llm.default_model, api_key=settings.llm.api_key, base_url=settings.llm.base_url, timeout=settings.llm.timeout, max_retries=settings.llm.max_retries)`
      - `_simple_model`: same but with `model=settings.llm.simple_model`
      - `_complex_model`: same but with `model=settings.llm.complex_model`
    - `get_model(complexity: str) -> ChatOpenAI`: returns `_simple_model` for `"simple"`, `_complex_model` for `"complex"`, `_default_model` for anything else
    - `invoke(request: LLMRequest) -> LLMResponse`: converts `LLMRequest` to langchain messages, calls the default model's `.ainvoke()`, wraps result in `LLMResponse`
    - `health_check() -> ServiceHealth`: calls `_default_model.ainvoke([HumanMessage("ping")])` with a short timeout override, returns `ServiceHealth(status="healthy")` on success, `ServiceHealth(status="unhealthy", error=str(exc))` on any exception
  - [x] 3.2: Handle exceptions: catch `openai.AuthenticationError`, `openai.APIConnectionError`, `openai.APITimeoutError`, `openai.RateLimitError` and map to `LLMTimeoutError` or return unhealthy `ServiceHealth`

- [x] Task 4: Wire LLM adapter into health endpoint (AC: 3)
  - [x] 4.1: Create a cached singleton factory function `get_llm_adapter() -> OpenAICompatAdapter` (similar pattern to `get_async_session`)
  - [x] 4.2: Update `src/quote_agent/api/health.py`:
    - Add LLM health check: call `adapter.health_check()` alongside the existing DB check
    - Add `"llm"` key to the `services` dict in `HealthResponse`
    - Overall status is `"degraded"` if ANY service is unhealthy
  - [x] 4.3: Export `get_llm_adapter` from `adapters/llm/__init__.py` for clean imports

- [x] Task 5: Update `adapters/llm/__init__.py` (AC: 4)
  - [x] 5.1: Export key classes: `LLMAdapter`, `OpenAICompatAdapter`, `LLMRequest`, `LLMResponse`, `get_llm_adapter`

- [x] Task 6: Add `langchain-openai` dependency (AC: 1)
  - [x] 6.1: Run `uv add langchain-openai` — this provides `ChatOpenAI` with OpenAI-compatible API support

- [x] Task 7: Write tests (AC: 5)
  - [x] 7.1: Create `tests/unit/test_llm_adapter.py` with:
    - `test_get_model_returns_simple_model_for_simple_complexity` — verify `get_model("simple")` returns model configured with `simple_model`
    - `test_get_model_returns_complex_model_for_complex_complexity` — verify `get_model("complex")` returns model configured with `complex_model`
    - `test_get_model_returns_default_model_for_unknown_complexity` — verify `get_model("default")` and `get_model("anything")` return default model
    - `test_health_check_returns_healthy_on_success` — mock `ChatOpenAI.ainvoke` to return a valid response, assert `ServiceHealth(status="healthy")`
    - `test_health_check_returns_unhealthy_on_connection_error` — mock `ChatOpenAI.ainvoke` to raise `openai.APIConnectionError`, assert unhealthy with error
    - `test_health_check_returns_unhealthy_on_auth_error` — mock to raise `openai.AuthenticationError`, assert unhealthy
    - `test_health_endpoint_includes_llm_service` — use `httpx.AsyncClient` with `ASGITransport` to hit `/health`, assert `services.llm` is present in response
    - `test_health_endpoint_degraded_when_llm_unhealthy` — override `get_llm_adapter` dependency, assert overall status is `"degraded"`
    - `test_invoke_returns_typed_response` — mock `ChatOpenAI.ainvoke`, verify `LLMResponse` structure
    - `test_adapter_conforms_to_protocol` — verify `OpenAICompatAdapter` satisfies `LLMAdapter` protocol via `isinstance` or structural check
  - [x] 7.2: Use `unittest.mock.patch` or `app.dependency_overrides` to mock LLM calls (never hit real API in tests)
  - [x] 7.3: Verify `uv run ruff check src/ tests/` and `uv run mypy src/` both pass

## Dev Notes

### Architecture Compliance

- **Adapter Pattern**: Every adapter follows `protocol.py` (interface) + `{impl}.py` (implementation) + `models.py` (DTOs). [Source: architecture.md#Structure-Patterns]
- **All methods async**: Every adapter method must be `async`. [Source: architecture.md#Adapter-Protocol-Pattern]
- **Typed DTOs**: Return Pydantic models, never raw `dict`. [Source: architecture.md#Enforcement-Guidelines]
- **Health check**: Every adapter exposes `health_check() -> ServiceHealth`. [Source: architecture.md#Adapter-Protocol-Pattern]
- **LLM hot-swap (NFR-I2)**: Provider interface supports hot-swapping without system restart — achieved by `ChatOpenAI` accepting `base_url` and `api_key` at init. Changing `.env` + restart = provider swap. [Source: architecture.md#Integration]
- **Credentials never logged**: `api_key` is `SecretStr` in `LLMSettings`. Never call `str(settings.llm.api_key)` — use `.get_secret_value()` only when passing to `ChatOpenAI`. [Source: architecture.md#Log-Sanitization]
- **Error handling**: Catch typed exceptions (`openai.APIConnectionError`, etc.), never bare `except Exception`. Map to `LLMTimeoutError` where appropriate. [Source: architecture.md#Process-Patterns]
- **Retry**: `ChatOpenAI` has built-in retry via `max_retries` parameter — matches architecture's retry requirement. No need to implement custom retry for basic LLM calls. [Source: architecture.md#Retry-Pattern-for-Adapters]

### langchain-openai Key Facts

- **Package**: `langchain-openai` (latest 1.1.10) — provides `ChatOpenAI` class
- **OpenAI-compatible**: Set `base_url` to any OpenAI-compatible endpoint (Azure OpenAI, vLLM, local LLM servers, etc.)
- **IMPORTANT**: `ChatOpenAI` targets official OpenAI API specs only. Non-standard response fields from providers like DeepSeek, OpenRouter, vLLM are NOT extracted. For MVP this is fine — client chooses an OpenAI-compatible provider. Provider-specific packages can be added post-MVP.
- **Import**: `from langchain_openai import ChatOpenAI`
- **api_key parameter**: Accepts `str` or `SecretStr` — pass `settings.llm.api_key.get_secret_value()`
- **LangChain message types**: Use `from langchain_core.messages import HumanMessage, SystemMessage, AIMessage`

### ChatOpenAI Constructor Reference

```python
from langchain_openai import ChatOpenAI

model = ChatOpenAI(
    model="gpt-4o",
    api_key=settings.llm.api_key.get_secret_value(),
    base_url=settings.llm.base_url,
    timeout=settings.llm.timeout,
    max_retries=settings.llm.max_retries,
    temperature=0.0,  # deterministic for quoting
)

# Async invocation (what we use)
response = await model.ainvoke([HumanMessage(content="hello")])
# response is AIMessage with .content, .response_metadata, .usage_metadata
```

### Health Check Design

The health check sends a minimal `ainvoke([HumanMessage("ping")])` to verify connectivity. This costs a small number of tokens but is the only reliable way to verify:
1. API key is valid
2. Endpoint is reachable
3. Model exists and is accessible

Use a short timeout (5s) for health check calls to avoid blocking the `/health` endpoint. Override `ChatOpenAI` timeout for this specific call:

```python
async def health_check(self) -> ServiceHealth:
    try:
        health_model = self._default_model.with_config(
            configurable={}  # no special config needed
        )
        # Use a short timeout for health checks
        await asyncio.wait_for(
            health_model.ainvoke([HumanMessage(content="ping")]),
            timeout=5.0,
        )
        return ServiceHealth(status="healthy")
    except Exception as exc:
        return ServiceHealth(status="unhealthy", error=str(exc))
```

**Cost consideration**: Health checks are called when `/health` is hit. Docker HEALTHCHECK runs every 30s by default. This means ~2880 minimal API calls/day. Consider caching the health result for 30-60s to reduce cost. Implementation choice: use a simple `_last_health` + `_last_health_time` cache.

### Existing Code to Build On

| File | What Exists | What to Do |
|------|-------------|------------|
| `src/quote_agent/config.py` | `LLMSettings` with `api_key`, `base_url`, `default_model`, `simple_model`, `complex_model`, `timeout`, `max_retries` | Already complete — use as-is |
| `src/quote_agent/exceptions.py` | `LLMTimeoutError(AdapterError)` | Already exists — use for timeout errors |
| `src/quote_agent/api/health.py` | `/health` endpoint with `services` dict (currently only `database`) | Add `llm` key to services dict |
| `src/quote_agent/api/health.py` | `ServiceHealth` model with `status` + `error` | Reuse for LLM health check return type |
| `src/quote_agent/adapters/llm/__init__.py` | Empty package placeholder | Populate with exports |
| `tests/conftest.py` | `env_vars` fixture, `_clear_settings_cache` fixture | Reuse for test setup |

### Testing Pattern

Mock `ChatOpenAI.ainvoke` to avoid real API calls:

```python
from unittest.mock import AsyncMock, patch

from quote_agent.adapters.llm.openai_compat import OpenAICompatAdapter

@pytest.fixture
def llm_settings(env_vars):
    """Provide LLMSettings for tests."""
    from quote_agent.config import get_settings
    return get_settings().llm

@pytest.fixture
def adapter(llm_settings):
    """Create adapter with test settings."""
    return OpenAICompatAdapter(llm_settings)

async def test_health_check_returns_healthy(adapter):
    with patch.object(adapter._default_model, "ainvoke", new_callable=AsyncMock) as mock:
        mock.return_value = AIMessage(content="pong")
        result = await adapter.health_check()
    assert result.status == "healthy"
```

For health endpoint integration tests, use FastAPI dependency overrides:

```python
from quote_agent.adapters.llm import get_llm_adapter

app.dependency_overrides[get_llm_adapter] = lambda: mock_adapter
```

### File Locations

```
ai-quote-agent/
├── src/quote_agent/
│   └── adapters/
│       └── llm/
│           ├── __init__.py              # MODIFY — add exports
│           ├── protocol.py              # NEW — LLMAdapter Protocol class
│           ├── openai_compat.py         # NEW — OpenAICompatAdapter implementation
│           └── models.py               # NEW — LLMRequest, LLMResponse, LLMUsage DTOs
│   └── api/
│       └── health.py                   # MODIFY — add LLM service to health check
└── tests/
    └── unit/
        └── test_llm_adapter.py         # NEW — adapter + health endpoint tests
```

### Critical Anti-Patterns to Avoid

| Do NOT | Do Instead |
|--------|-----------|
| Use `langchain-community` ChatOpenAI (deprecated) | Use `langchain-openai` package's `ChatOpenAI` |
| Call `str(settings.llm.api_key)` in logs | Use `.get_secret_value()` only when passing to ChatOpenAI |
| Hit real LLM API in unit tests | Mock `ChatOpenAI.ainvoke` with `AsyncMock` |
| Create sync methods on the adapter | ALL adapter methods must be `async` |
| Return raw `dict` from adapter methods | Return typed `LLMResponse`, `ServiceHealth` DTOs |
| Use bare `except Exception` in health check | Catch typed exceptions first, fall back to `Exception` only in health_check (which must never crash) |
| Import from `langchain.chat_models` | Import from `langchain_openai` directly |
| Hardcode model names in adapter | Read from `LLMSettings` (already configured in config.py) |
| Implement custom retry logic | Use `ChatOpenAI(max_retries=N)` built-in retry |
| Create a new `ServiceHealth` model | Import the existing one from `quote_agent.api.health` |

### Previous Story Intelligence (Story 1.3)

- **Health endpoint extensibility**: The `services` dict in `HealthResponse` was designed to accept new service keys. Each adapter adds its key (e.g., `"llm"`, `"erp"`, `"email"`, `"notification"` in stories 1.4-1.6).
- **`make_response()` helper**: Use for consistent API response wrapping.
- **Dependency override pattern**: Story 1.3 used `app.dependency_overrides[get_async_session]` for testing — use same pattern for `get_llm_adapter`.
- **`CatchAllExceptionMiddleware`**: Catches unhandled exceptions — adapter errors that escape should be caught at the node/service level, not here.
- **`env_vars` fixture**: Already provides `LLM__API_KEY`, `LLM__BASE_URL`, etc. from conftest — check and add any missing LLM vars if needed.
- **Cache clearing in tests**: Remember to clear `get_settings.cache_clear()` and any LLM adapter caches between tests.
- **PEP 695 generics**: Story 1.3 used `class ApiResponse[T](BaseModel)` — keep consistent with modern Python syntax.

### Git Intelligence

Recent commit pattern: `feat: add <description> (Story X.Y)`

Commits for Epic 1 so far:
- `98cc075` feat: add FastAPI server with health check and API v1 base endpoint (Story 1.3)
- `2482e07` feat: add PostgreSQL database foundation with async SQLAlchemy & Alembic migrations (Story 1.2)
- `7f9383a` feat: add project scaffolding & type-safe configuration system (Story 1.1)

### Dependencies to Add

- `langchain-openai` — core dependency for `ChatOpenAI` (`uv add langchain-openai`)

### Scope Boundaries

- **IN scope**: LLM adapter Protocol + OpenAI-compatible implementation, health check integration, model routing by complexity, typed DTOs, unit tests
- **OUT of scope**: Actual LLM invocations from agent nodes (Epic 4), embedding adapter (separate in `adapters/embedding/`), circuit breaker pattern (add when needed in production usage), structured logging setup (Epic 7), prompt templates, agent graph integration

### References

- [Source: architecture.md#Structure-Patterns] — adapter organization (protocol.py + impl.py + models.py)
- [Source: architecture.md#Adapter-Protocol-Pattern] — Protocol class design, async methods, health_check
- [Source: architecture.md#Process-Patterns] — error handling, retry pattern
- [Source: architecture.md#Enforcement-Guidelines] — typed DTOs, no raw dict, mypy --strict
- [Source: architecture.md#Architectural-Boundaries] — Agent → LLM Provider: HTTPS (OpenAI-compatible API)
- [Source: epics.md#Story-1.4] — acceptance criteria, user story
- [Source: prd.md#Integration-Architecture] — LLM: client's choice, abstraction layer
- [Source: prd.md#NFR-Integration] — NFR-I2: LLM hot-swap without restart
- [Source: _bmad-output/implementation-artifacts/1-3-serveur-api-health-check.md] — previous story learnings

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

- ChatOpenAI is a Pydantic model — `patch.object` on instances fails because Pydantic intercepts `__setattr__`/`__delattr__`. Fixed by patching at the class level (`patch.object(ChatOpenAI, "ainvoke", ...)`)
- Existing health tests needed updating to also mock `get_llm_adapter` dependency after health endpoint was extended

### Completion Notes List

- Implemented LLM adapter following protocol.py + impl.py + models.py pattern (AC-1.4.4)
- OpenAICompatAdapter connects via `langchain-openai` `ChatOpenAI` with `SecretStr` for api_key (AC-1.4.1)
- Model routing via `get_model(complexity)` returns simple/complex/default models (AC-1.4.2)
- Health check with 30s caching to reduce API costs, 5s timeout (AC-1.4.3)
- `/health` endpoint now includes `services.llm` key, overall status degrades when LLM unhealthy (AC-1.4.3)
- 14 new tests + 0 regressions on existing tests (AC-1.4.5)
- `ruff check` and `mypy` both pass clean (AC-1.4.5)

### Change Log

- 2026-03-18: Implemented Story 1.4 — LLM adapter with OpenAI-compatible provider, model routing, health check integration, 10 unit tests
- 2026-03-18: Code review fixes — added empty model name validation (H1), invoke() exception mapping to LLMTimeoutError/AdapterError (H2), moved get_llm_adapter factory to adapters/llm package (M1), removed dead code (L1/L2), added 4 new tests

### File List

New files:
- src/quote_agent/adapters/llm/models.py
- src/quote_agent/adapters/llm/protocol.py
- src/quote_agent/adapters/llm/openai_compat.py
- tests/unit/test_llm_adapter.py

Modified files:
- src/quote_agent/adapters/llm/__init__.py
- src/quote_agent/api/health.py
- src/quote_agent/config.py
- tests/unit/test_health.py
- pyproject.toml
- uv.lock
- _bmad-output/implementation-artifacts/sprint-status.yaml
