# Testing Patterns

**Analysis Date:** 2026-04-10

## Test Framework

**Runner:**
- Framework: pytest 8+
- Config: `pyproject.toml` (root level, lines 38-45)

**Async Support:**
- Plugin: `pytest-asyncio>=0.24`
- Mode: `asyncio_mode = "auto"` — automatically marks async test functions
- Event loop: `asyncio_default_fixture_loop_scope = "session"` — single event loop per session

**Assertion Library:**
- pytest's built-in assertions (no external library needed)
- Error assertions: `pytest.raises(ExceptionType)`

**Assertion Patterns:**
```python
# Direct assertions
assert result == [1, 2, 3]
assert result is True
assert len(accounts) == 2

# Error assertions
with pytest.raises(OdooAuthError):
    await client.call(...)
with pytest.raises(OdooValidationError, match="message"):
    ...

# Attribute assertions
assert accounts[0].name == "Cash"
assert session.uid == 2
```

**Run Commands:**
```bash
uv run pytest packages/                          # Run all tests
uv run pytest packages/ -m "not integration"     # Skip integration tests (unit only)
uv run pytest -m integration                     # Run only integration tests
uv run pytest packages/godoo/tests/test_client.py -v  # Run specific file with verbose
uv run pytest --cov                              # Run with coverage
```

## Test File Organization

**Location:**
- Unit tests: `packages/{package}/tests/test_*.py` (co-located with source, not in source directory)
- Examples:
  - `packages/godoo/tests/test_accounting.py`
  - `packages/godoo/tests/test_transport.py`
  - `packages/godoo/tests/test_client.py`
  - `packages/godoo-testcontainers/tests/test_container.py`
- Global integration test setup: `tests/conftest.py` (root level)

**Naming:**
- Test modules: `test_*.py` (matches what they test: `test_accounting.py` tests `accounting` service)
- Test functions: `test_<what_it_tests>` or `test_<function>_<scenario>`
  - Examples: `test_m2o_id_list()`, `test_discover_cash_accounts()`, `test_call_before_auth_raises()`
  - Bad example: `test_1()`, `test_accounting()` (too vague)

**Structure:**
```
packages/godoo/tests/
├── test_accounting.py       # Tests for accounting service
├── test_attendance.py       # Tests for attendance service
├── test_client.py           # Tests for OdooClient
├── test_transport.py        # Tests for JSON-RPC transport
├── test_safety.py           # Tests for safety guard
├── test_module_manager.py   # Tests for module management
├── test_mail.py             # Tests for mail service
├── test_urls.py             # Tests for URL service
├── test_timesheets.py       # Tests for timesheets service
├── test_properties.py       # Tests for properties service
├── test_cdc.py              # Tests for CDC service
├── test_config.py           # Tests for config helpers
├── test_errors.py           # Tests for error types
└── __init__.py              # Empty

tests/
├── conftest.py              # Session-scoped Odoo container fixture
```

## Test Structure

**Suite Organization:**

From `packages/godoo/tests/test_accounting.py`:
```python
# 1. Module docstring
"""Tests for the accounting service."""

# 2. Imports
from __future__ import annotations
import httpx
import pytest
import respx
from godoo.client import OdooClient, OdooClientConfig
from godoo.services.accounting import ...

# 3. Constants/helpers
BASE_URL = "http://odoo.test"
DB = "testdb"

def _rpc_response(result, id=1) -> httpx.Response:
    return httpx.Response(200, json={"jsonrpc": "2.0", "id": id, "result": result})

def _make_client() -> OdooClient:
    return OdooClient(OdooClientConfig(...))

# 4. Fixtures
@pytest.fixture
async def auth_client():
    client = _make_client()
    with respx.mock:
        respx.post(...).mock(return_value=_rpc_response(2))
        await client.authenticate()
    yield client
    await client.aclose()

# 5. Test functions grouped by feature
# test_m2o_id_* functions (unit tests)
# test_discover_cash_accounts (integration test)
# etc.
```

**Patterns:**

**Unit Test Pattern:**
```python
def test_m2o_id_list():
    assert _m2o_id([42, "Partner"]) == 42

def test_m2o_id_false():
    assert _m2o_id(False) is None
```
- No fixtures needed for pure functions
- Tests each return path explicitly
- One assertion per test (typically)

**Async Test Pattern:**
```python
@respx.mock
@pytest.mark.asyncio
async def test_discover_cash_accounts(auth_client):
    respx.post(f"{BASE_URL}/jsonrpc").mock(
        return_value=_rpc_response([
            {"id": 1, "name": "Cash", ...},
            {"id": 2, "name": "Bank", ...},
        ])
    )
    svc = AccountingService(auth_client)
    accounts = await svc.discover_cash_accounts()
    assert len(accounts) == 2
    assert accounts[0].name == "Cash"
```
- Decorated with `@pytest.mark.asyncio` (explicit, though `asyncio_mode = "auto"` makes it optional)
- Uses fixture for pre-authenticated client
- Single async/await operation tested
- Multiple related assertions allowed

**Error Testing Pattern:**
```python
@respx.mock
@pytest.mark.asyncio
async def test_authenticate_false_uid_raises(transport):
    respx.post(f"{BASE_URL}/jsonrpc").mock(
        return_value=httpx.Response(200, json=_jsonrpc_result(False))
    )
    with pytest.raises(OdooAuthError):
        await transport.authenticate("admin", "wrong")
```
- Arrange: Mock is set up
- Act: Code that should raise is in `with pytest.raises(...):` block
- Assert: Exception type is the assertion

**Fixture Pattern:**
```python
@pytest.fixture
async def auth_client():
    client = _make_client()
    with respx.mock:
        respx.post(...).mock(return_value=...)
        await client.authenticate()
    yield client
    await client.aclose()  # Cleanup
```
- Set up state
- `yield` returns the object to test
- Code after `yield` runs cleanup (always runs, even on failure)
- Async fixtures for async setup

## Mocking

**Framework:** `respx>=0.22`

**Purpose:** Mock HTTP requests/responses (replacing actual Odoo server)

**Pattern:**
```python
@respx.mock
@pytest.mark.asyncio
async def test_something():
    respx.post(f"{BASE_URL}/jsonrpc").mock(return_value=_rpc_response(...))
    # Test code
```

**How respx works:**
- `@respx.mock` decorator or context manager: `with respx.mock:`
- Intercepts HTTP calls to matching URL patterns
- Returns mocked `httpx.Response` objects
- No actual network calls

**Example HTTP Response Mocking:**
```python
def _rpc_response(result, id=1) -> httpx.Response:
    return httpx.Response(200, json={"jsonrpc": "2.0", "id": id, "result": result})

respx.post(f"{BASE_URL}/jsonrpc").mock(return_value=_rpc_response([1, 2, 3]))
```

**Error Response Mocking:**
```python
def _jsonrpc_error(exception_type=None, name=None, message="Error", code=-32000):
    data = {}
    if exception_type:
        data["exception_type"] = exception_type
    if name:
        data["name"] = name
    return {
        "jsonrpc": "2.0",
        "id": 1,
        "error": {
            "code": code,
            "message": message,
            "data": data,
        },
    }

respx.post(...).mock(return_value=httpx.Response(200, json=_jsonrpc_error(exception_type="validation_error")))
```

**Side-effect Mocking (Multiple Calls):**
```python
respx.post(f"{BASE_URL}/jsonrpc").mock(
    side_effect=[
        httpx.Response(200, json=_jsonrpc_result(2)),           # First call (auth)
        httpx.Response(200, json=_jsonrpc_result([{"id": 1}])), # Second call (search_read)
    ]
)
```

**Testcontainers-Python:**
- Framework: `testcontainers[postgres]>=4`
- Wrapper: `godoo-testcontainers` package
- Purpose: Real Odoo instance in Docker for integration tests
- Pattern from `tests/conftest.py`:
  ```python
  @pytest_asyncio.fixture(scope="session")
  async def odoo():
      """Session-scoped Odoo instance for all integration tests."""
      container = OdooTestContainer(modules=["crm", "sale", "project"])
      started = await container.start()
      yield started
      await started.cleanup()
  ```
- Implementation: `packages/godoo-testcontainers/src/godoo_testcontainers/container.py`
- Key detail: Testcontainers sync API wrapped in `asyncio.to_thread()` (container.py lines 65, 77, 78, 91, 112, 123)

**What to Mock:**
- HTTP requests (always use respx for unit tests)
- External dependencies with side effects
- Time-dependent operations (use freezegun if needed; not currently in use)

**What NOT to Mock:**
- Client logic itself (test with real client, mocked transport)
- Dataclass constructors (not needed)
- Pure functions like `_m2o_id()` (no mocking needed)
- Odoo container in integration tests (actually start it)

## Fixtures and Factories

**Test Data:**

From `packages/godoo/tests/test_accounting.py`:
```python
def _rpc_response(result, id=1) -> httpx.Response:
    """Factory for RPC response."""
    return httpx.Response(200, json={"jsonrpc": "2.0", "id": id, "result": result})

def _make_client() -> OdooClient:
    """Factory for test client."""
    return OdooClient(OdooClientConfig(url=BASE_URL, database=DB, username="admin", password="admin"))

# Constants
BASE_URL = "http://odoo.test"
DB = "testdb"
```

**Reusable Fixtures:**

From `packages/godoo/tests/test_transport.py`:
```python
@pytest.fixture
def transport():
    t = JsonRpcTransport(BASE_URL, DB)
    yield t

@pytest.fixture
async def auth_client():
    client = _make_client()
    with respx.mock:
        respx.post(...).mock(return_value=_rpc_response(2))
        await client.authenticate()
    yield client
    await client.aclose()
```

**Session-Scoped Fixtures:**

From `tests/conftest.py`:
```python
@pytest_asyncio.fixture(scope="session")
async def odoo():
    """Session-scoped Odoo instance for all integration tests."""
    container = OdooTestContainer(modules=["crm", "sale", "project"])
    started = await container.start()
    yield started
    await started.cleanup()

@pytest_asyncio.fixture
async def client(odoo):  # Uses session-scoped odoo
    return odoo.client
```
- Odoo container starts once per session (expensive)
- Per-test `client` fixture gets fresh client from container
- Cleanup runs after all tests complete

**Location:**
- Test helpers: Top of test file (constants, factories)
- Fixtures: `conftest.py` at package or root level
- Shared fixtures: `tests/conftest.py` (root) — used by all packages

## Coverage

**Requirements:** None enforced by default

**View Coverage:**
```bash
uv run pytest --cov packages/
uv run pytest --cov packages/ --cov-report=html  # Generate HTML report
```

**Configuration:** `pyproject.toml` lines 47-53
```toml
[tool.coverage.run]
source_pkgs = ["godoo", "godoo_testcontainers", "godoo_introspection"]
branch = true

[tool.coverage.report]
show_missing = true
skip_empty = true
```

**Branch Coverage:**
- `branch = true` — tracks both sides of conditionals
- `show_missing = true` — reports uncovered lines
- `skip_empty = true` — ignores blank lines

## Test Types

**Unit Tests:**
- Scope: Single function or small module (e.g., `_m2o_id()`, `is_closing_entry_from_lines()`)
- Mocking: HTTP requests (respx), not business logic
- Speed: Fast (< 1s for full suite)
- Marker: None (default)
- Location: `packages/*/tests/test_*.py`
- Example: `packages/godoo/tests/test_accounting.py` lines 43–98 (helper functions)

**Integration Tests:**
- Scope: Full workflow with real Odoo container (e.g., authenticating, running methods)
- Mocking: None (real Docker container runs)
- Speed: Slow (30+ seconds per test)
- Marker: `@pytest.mark.integration`
- Location: `tests/` (root level) or marked in `packages/*/tests/`
- Example: Would test `await client.create()` against real Odoo instance
- Currently minimal (container infrastructure is tested in testcontainers package only)

**Marker Definition:**
```toml
markers = [
    "integration: marks tests requiring Docker/Odoo (deselect with '-m not integration')",
]
```

**Running by Type:**
```bash
uv run pytest packages/ -m "not integration"     # Unit only
uv run pytest -m integration                     # Integration only
uv run pytest                                    # All tests (unit + integration)
```

## Common Patterns

**Async Testing:**

Pattern 1 (with decorator):
```python
@pytest.mark.asyncio
async def test_something(client):
    result = await client.call(...)
    assert result == expected
```

Pattern 2 (with context manager):
```python
def test_something_sync():
    with respx.mock:
        respx.post(...).mock(return_value=...)
        # Can't use await here unless it's async

async def test_something_async():
    with respx.mock:
        respx.post(...).mock(return_value=...)
        result = await client.call(...)
```

**Fixture with respx Context:**
```python
@pytest.fixture
async def auth_client():
    client = _make_client()
    with respx.mock:
        respx.post(...).mock(return_value=_rpc_response(2))
        await client.authenticate()
    yield client
    await client.aclose()
```
- Fixture sets up respx mock, authenticates, then yields
- Tests using this fixture don't need to set up respx (it's already active)
- Cleanup (aclose) runs after test completes

**Error Testing:**
```python
@respx.mock
@pytest.mark.asyncio
async def test_error_categorization(transport):
    respx.post(...).mock(
        return_value=httpx.Response(200, json=_jsonrpc_error(exception_type="validation_error"))
    )
    with pytest.raises(OdooValidationError):
        await transport.call_rpc("common.authenticate", {})
```
- Error is returned in response (HTTP 200, but JSON contains error object)
- Transport converts Odoo error to specific Python exception
- Test verifies correct exception type is raised

**Parameterized Testing:**
- Not currently used in codebase
- Would use `@pytest.mark.parametrize` if needed
- Example (not in use):
  ```python
  @pytest.mark.parametrize("input,expected", [
      ([42, "Name"], 42),
      (False, None),
      ([], None),
  ])
  def test_m2o_id(input, expected):
      assert _m2o_id(input) == expected
  ```

## Test Discovery

**Testpaths:**
```toml
testpaths = ["packages", "tests"]
```
- pytest searches `packages/*/tests/test_*.py` and `tests/`
- Test files must be named `test_*.py` or `*_test.py` (convention is `test_*.py`)

**Addopts:**
```toml
addopts = "--tb=short -q"
```
- `--tb=short` — short traceback format
- `-q` — quiet mode (minimal output)

---

*Testing analysis: 2026-04-10*
