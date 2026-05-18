# Testing Patterns

**Analysis Date:** 2026-05-18

## Test Framework

**Runner:**
- pytest >= 8
- Config: root `pyproject.toml` under `[tool.pytest.ini_options]`

**Async:**
- `pytest-asyncio >= 0.24` with `asyncio_mode = "auto"` (no `@pytest.mark.asyncio` required by default, though some tests still carry it explicitly)
- `asyncio_default_fixture_loop_scope = "session"` — single event loop across the session

**HTTP Mocking:**
- `respx >= 0.22` — intercepts `httpx.AsyncClient` calls

**Coverage:**
- `pytest-cov >= 6`
- Config: `[tool.coverage.run]` with `branch = true`, sources `godoo`, `godoo_testcontainers`, `godoo_introspection`

**Run Commands:**
```bash
uv run pytest packages/ -m "not integration"   # Unit tests only
uv run pytest -m integration                    # Integration tests (requires Docker)
uv run pytest                                   # All tests
uv run pytest --cov --cov-report=term-missing   # With coverage
```

Default addopts: `--tb=short -q`

## Test File Organization

**Location:**
- Unit tests: co-located with the package under `packages/{pkg}/tests/`
  - `packages/godoo/tests/` — 13 test files
  - `packages/godoo-testcontainers/tests/` — 2 test files
- Integration tests: top-level `tests/integration/` directory
  - `tests/integration/test_crud.py`
  - `tests/integration/test_modules.py`

**Naming:**
- Files: `test_{module_name}.py` matching the source module
- Test functions: `test_{what_is_tested}` (snake_case, descriptive)
- Test classes: `Test{ConceptUnderTest}` (PascalCase)

**Structure:**
```
packages/godoo/tests/
├── __init__.py
├── test_accounting.py
├── test_attendance.py
├── test_cdc.py
├── test_client.py
├── test_config.py
├── test_errors.py
├── test_mail.py
├── test_module_manager.py
├── test_properties.py
├── test_safety.py
├── test_timesheets.py
├── test_transport.py
└── test_urls.py
tests/
├── conftest.py              # Integration session fixture
└── integration/
    ├── test_crud.py
    └── test_modules.py
```

## Test Structure

**Suite Organisation:**

Tests mix two styles depending on test count and cohesion:

1. **Class-based** (for related unit tests on a single type/concept):
```python
class TestOdooRpcError:
    def test_inherits_odoo_error(self) -> None:
        err = OdooRpcError("rpc failed")
        assert isinstance(err, OdooError)

    def test_stores_code_and_data(self) -> None:
        data = {"debug": "traceback here"}
        err = OdooRpcError("rpc error", code=200, data=data)
        assert err.code == 200
        assert err.data == data
```

2. **Function-based** (for async/HTTP mock tests and simple pure-function tests):
```python
@respx.mock
@pytest.mark.asyncio
async def test_discover_cash_accounts(auth_client):
    respx.post(f"{BASE_URL}/jsonrpc").mock(return_value=_rpc_response([...]))
    svc = AccountingService(auth_client)
    accounts = await svc.discover_cash_accounts()
    assert len(accounts) == 2
```

**Section separators** divide logical groups within a test file:
```python
# ---------------------------------------------------------------------------
# discover_cash_accounts — mock
# ---------------------------------------------------------------------------
```

**Setup/Teardown:**
- `setup_method` / `teardown_method` on test classes for global state reset (e.g., safety context)
- `yield` fixtures for async resource lifecycle

## Mocking

**Framework:** `respx` — wraps `httpx.AsyncClient` at the transport level

**Patterns:**

Single call mock (decorator style):
```python
@respx.mock
@pytest.mark.asyncio
async def test_authenticate_success(transport):
    respx.post(f"{BASE_URL}/jsonrpc").mock(
        return_value=httpx.Response(200, json=_jsonrpc_result(2))
    )
    session = await transport.authenticate("admin", "admin")
    assert session.uid == 2
```

Context manager style (used in fixtures):
```python
@pytest.fixture
async def auth_client():
    client = _make_client()
    with respx.mock:
        respx.post(f"{BASE_URL}/jsonrpc").mock(return_value=_rpc_response(2))
        await client.authenticate()
    yield client
    await client.aclose()
```

Sequential calls with `side_effect`:
```python
respx.post(f"{BASE_URL}/jsonrpc").mock(
    side_effect=[
        httpx.Response(200, json=_jsonrpc_result(2)),           # authenticate
        httpx.Response(200, json=_jsonrpc_result([1, 2, 3])),   # search
    ]
)
```

Network error injection:
```python
respx.post(f"{BASE_URL}/jsonrpc").mock(side_effect=httpx.ConnectError("Connection refused"))
```

**What to Mock:**
- All HTTP calls to Odoo (`/jsonrpc` endpoint) in unit tests
- The `respx.mock` decorator/context must wrap the entire interaction including auth setup

**What NOT to Mock:**
- Pure Python logic (error classes, dataclass construction, helper functions like `_m2o_id`)
- Integration tests — they use a real Odoo container

## Fixtures and Factories

**Test Data Helpers (module-level functions, not fixtures):**

```python
BASE_URL = "http://odoo.test"
DB = "testdb"

def _rpc_response(result, id=1) -> httpx.Response:
    return httpx.Response(200, json={"jsonrpc": "2.0", "id": id, "result": result})

def _make_client() -> OdooClient:
    return OdooClient(OdooClientConfig(url=BASE_URL, database=DB, username="admin", password="admin"))
```

This helper pattern is duplicated across test files (each file is self-contained).

**Standard `auth_client` fixture** (repeated in almost every service test file):
```python
@pytest.fixture
async def auth_client():
    client = _make_client()
    with respx.mock:
        respx.post(f"{BASE_URL}/jsonrpc").mock(return_value=_rpc_response(2))
        await client.authenticate()
    yield client
    await client.aclose()
```

Some fixtures also clear module-level caches on setup/teardown:
```python
@pytest.fixture
async def auth_client():
    ...
    clear_cache()       # clear before
    yield client
    await client.aclose()
    clear_cache()       # clear after
```

**Integration fixtures** (`tests/conftest.py`):
```python
@pytest_asyncio.fixture(scope="session")
async def odoo():
    """Session-scoped Odoo instance for all integration tests."""
    container = OdooTestContainer(modules=["crm", "sale", "project"])
    started = await container.start()
    yield started
    await started.cleanup()

@pytest_asyncio.fixture
async def client(odoo):
    """Per-test authenticated client."""
    return odoo.client
```

**Location:**
- Helpers: defined at top of each test file (not shared)
- Integration fixtures: `tests/conftest.py`

## Coverage

**Requirements:** No enforced minimum threshold.

**Configuration (`pyproject.toml`):**
```toml
[tool.coverage.run]
source_pkgs = ["godoo", "godoo_testcontainers", "godoo_introspection"]
branch = true

[tool.coverage.report]
show_missing = true
skip_empty = true
```

**View Coverage:**
```bash
uv run pytest --cov --cov-report=term-missing packages/ -m "not integration"
```

## Test Types

**Unit Tests (`packages/*/tests/`):**
- Scope: single module or function
- HTTP layer mocked with `respx`
- Run without Docker or network
- Include pure-function tests (no mock needed) for helpers, dataclasses, error classes

**Integration Tests (`tests/integration/`):**
- Scope: real Odoo instance via Docker
- Marked `@pytest.mark.integration` (class-level or function-level)
- Require Docker daemon and pull `odoo:{version}` + `postgres:15-alpine` images
- Session-scoped container shared across all integration tests
- `ODOO_VERSION` env var controls which Odoo image version is used

## Common Patterns

**Error Testing:**
```python
with pytest.raises(OdooAuthError, match="authenticate"):
    await client.call("res.partner", "search", [[]], {})

# Check exception type in hierarchy
with pytest.raises(OdooValidationError):
    await transport.call_rpc("common.authenticate", {})
```

**Async Testing:**
```python
@respx.mock
@pytest.mark.asyncio
async def test_search(auth_client):
    respx.post(f"{BASE_URL}/jsonrpc").mock(return_value=httpx.Response(200, json=_jsonrpc_result([1, 2, 3])))
    result = await auth_client.search("res.partner", [[("is_company", "=", True)]])
    assert result == [1, 2, 3]
```

**Testing with `monkeypatch` (env vars):**
```python
def test_config_from_env_default_prefix(monkeypatch):
    monkeypatch.setenv("ODOO_URL", "http://odoo.test")
    monkeypatch.setenv("ODOO_DB", "mydb")
    monkeypatch.setenv("ODOO_USER", "admin")
    monkeypatch.setenv("ODOO_PASSWORD", "secret")
    from godoo.config import config_from_env
    config = config_from_env()
    assert config.url == "http://odoo.test"
```

**State isolation (global safety context):**
```python
class TestResolveSafetyContext:
    def setup_method(self) -> None:
        set_default_safety_context(None)   # reset before each test

    def teardown_method(self) -> None:
        set_default_safety_context(None)   # reset after each test
```

**Testcontainers async wrapping (for sync Docker API):**
All `testcontainers` sync calls are wrapped in `asyncio.to_thread()`:
```python
await asyncio.to_thread(network.create)
await asyncio.to_thread(pg.start)
await asyncio.to_thread(wait_for_logs, pg, "PostgreSQL init process complete...", 90)
```

---

*Testing analysis: 2026-05-18*
