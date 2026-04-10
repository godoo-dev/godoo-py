# Coding Conventions

**Analysis Date:** 2026-04-10

## Naming Patterns

**Files:**
- Module files: `snake_case.py` (e.g., `transport.py`, `functions.py`, `types.py`)
- Test files: `test_*.py` (e.g., `test_transport.py`, `test_accounting.py`)
- Private modules/functions: Leading underscore prefix (e.g., `_m2o_id()`, `_UNDEFINED`)
- Service modules follow pattern: `{service_name}/functions.py`, `{service_name}/service.py`, `{service_name}/types.py`

**Functions:**
- Async functions: `async def async_function_name()` — all service functions are async
- Private helper functions: Leading underscore (e.g., `_m2o_id()`, `_m2o_name()`)
- Regular snake_case: `discover_cash_accounts()`, `trace_reconciliation()`, `get_cash_balance()`
- Example from `packages/godoo/src/godoo/services/accounting/functions.py`: Helper functions like `_m2o_id()` and `_m2o_name()` extract Odoo field values before main async functions use them

**Variables:**
- Constants: `UPPER_SNAKE_CASE` (e.g., `BASE_URL`, `DB`)
- Sentinel values: `_UNDEFINED = object()` (used in `packages/godoo/src/godoo/client.py`)
- Regular variables: `snake_case`
- Type-hinted kwargs: `kwargs: dict[str, Any]`, `domain: list[Any] | None = None`

**Types & Classes:**
- Classes: `PascalCase` (e.g., `OdooClient`, `AccountingService`, `JsonRpcTransport`)
- Dataclasses: `PascalCase` (e.g., `OdooClientConfig`, `CashAccount`, `ReconciliationTrace`)
- Exceptions: `PascalCase` with `Error` suffix (e.g., `OdooError`, `OdooRpcError`, `OdooAuthError`)
- Type aliases: `PascalCase` (internal use only, no exports)

## Code Style

**Formatting:**
- Tool: `ruff` (format and lint)
- Line length: 120 characters
- Python version: 3.14+

**Linting:**
- Tool: `ruff check`
- Select rules: `["E", "F", "W", "I", "UP", "B", "SIM", "TCH", "RUF"]`
  - `E`: PEP8 errors
  - `F`: PyFlakes (undefined names, unused imports)
  - `W`: PEP8 warnings
  - `I`: Import sorting (isort-compatible)
  - `UP`: pyupgrade (modern Python syntax)
  - `B`: flake8-bugbear (common bugs)
  - `SIM`: flake8-simplify (code simplification)
  - `TCH`: flake8-type-checking (TYPE_CHECKING guard optimization)
  - `RUF`: ruff-specific rules
- Run: `uv run ruff check . && uv run ruff format .`

**Type Checking:**
- Tool: `mypy --strict`
- Python version: 3.14
- Key flags:
  - `disallow_untyped_defs = true` — all functions must have type hints
  - `warn_return_any = true` — catch untyped returns
  - `warn_unused_configs = true`
- Overrides: testcontainers module is exempted from missing imports check (line 35-36 in root `pyproject.toml`)
- Run: `uv run mypy packages/godoo/src packages/godoo-testcontainers/src`

## Import Organization

**Order:**
1. `from __future__ import annotations` (always first, in every file)
2. Standard library imports (e.g., `import logging`, `import asyncio`, `import os`)
3. Third-party imports (e.g., `import httpx`, `import pytest`, `from testcontainers.*`)
4. Local/relative imports (e.g., `from godoo.client import OdooClient`, `from .functions import ...`)
5. `TYPE_CHECKING` block with conditional imports (prevents circular dependencies)

**Pattern:** `TYPE_CHECKING` block wraps imports only needed for type hints:
```python
if TYPE_CHECKING:
    from godoo.client import OdooClient
    from godoo.services.accounting.service import AccountingService
```
- Used extensively in `packages/godoo/src/godoo/services/` to prevent circular imports
- Example from `packages/godoo/src/godoo/services/accounting/functions.py` lines 16-17
- Example from `packages/godoo/src/godoo/client.py` lines 19-27 (lazy imports of all services)

**Path Aliases:**
- Absolute imports from package root: `from godoo.client import OdooClient`
- No relative imports (no `from . import`, no `from .. import`)
- Services use absolute imports: `from godoo.services.accounting.types import ...`

**Barrel Files:**
- Service `__init__.py` re-exports: `from .functions import *` and `from .service import ServiceClass`
- Example: `packages/godoo/src/godoo/services/accounting/__init__.py`
- Root `packages/godoo/src/godoo/__init__.py` exports public API with explicit `__all__` (lines 24-48)

## Error Handling

**Patterns:**
- Base exception: `OdooError(Exception)` — all errors inherit from this
- Specific error types for different failure modes:
  - `OdooRpcError` — generic JSON-RPC errors from server
  - `OdooAuthError` — authentication/access denied
  - `OdooValidationError` — ValidationError or UserError
  - `OdooAccessError` — ACL violation
  - `OdooMissingError` — record not found
  - `OdooNetworkError` — connection/HTTP errors
  - `OdooTimeoutError` — request timeout
  - `OdooSafetyError` — local safety guard blocked operation (not from server)
- All errors have `to_json()` method returning `dict[str, Any]` for serialization
- Errors include context: `code`, `data`, `cause` (wrapped with `__cause__`)
- Location: `packages/godoo/src/godoo/errors.py`

**Raising errors:**
```python
# From transport.py
raise OdooAuthError("Authentication failed: invalid credentials or database")
raise OdooNetworkError(f"Connection error: {exc}", cause=exc) from exc
```

**Handling errors:**
- Errors are caught and re-categorized by exception type/name from Odoo (see `_categorize_error()` in transport.py)
- Tests verify error types: `with pytest.raises(OdooValidationError):`
- No silent failures or generic `except Exception`

## Logging

**Framework:** `logging` (Python standard library)

**Patterns:**
- Logger per module: `logger = logging.getLogger("godoo.{module}")`
  - Root logger: `"godoo"` (in client.py line 29)
  - Submodule loggers: `"godoo.client.rpc"` (in transport.py line 21)
  - testcontainers logger: `"godoo.testcontainers"` (in container.py line 20)
- Log levels used:
  - `debug`: Low-level tracing (JSON-RPC calls in transport.py line 74)
  - `info`: Container lifecycle events (container.py lines 144, 150, 151)
  - `error`: Failures with context (container.py lines 125, 127)
- No logging in pure data transformation functions (e.g., `_m2o_id()` doesn't log)
- Logging is used for side-effectful operations (container management, auth)

## Comments

**When to Comment:**
- Module/file docstrings: Always (triple-quoted string as first statement)
  - Example: `"""OdooClient — high-level async client with safety guard."""` (client.py line 1)
  - Example: `"""JSON-RPC transport over httpx."""` (transport.py line 1)
- Function docstrings: For public APIs
  - Example: `"""Authenticate against Odoo; returns OdooSessionInfo."""` (transport.py line 50)
  - Example: `"""Trace the full reconciliation for a given move line."""` (functions.py line 82)
- Helper functions: Optional, brief docstring if non-obvious
  - Example: `"""Extract the integer ID from a many2one field value."""` (functions.py line 29)
- Complex logic: Inline comments before tricky sections
  - Example: `# Fetch all lines with the same full_reconcile_id` (functions.py line 94)
- Section separators: Use `# ---` (80 dashes) to delineate logical sections (e.g., functions.py lines 20-21, 44-45)

**JSDoc/TSDoc:**
- Not used (Python uses docstrings, not JSDoc)
- Type hints replace type comments in Python 3.10+

## Function Design

**Size:**
- Small, single-responsibility functions (2–20 lines typical)
- Async helper functions wrap data transformation functions
- Example: `discover_cash_accounts()` is 16 lines (functions.py lines 49-64)
- Example: `_m2o_id()` is 6 lines (functions.py lines 25-34)

**Parameters:**
- Explicit, type-hinted parameters (no `*args`, no `**kwargs` unless necessary)
- First parameter in service functions is always `client: OdooClient` (TYPE_CHECKING import)
- Keyword-only args (after `*`) used for optional config (e.g., `limit`, `order` in `get_posted_move_lines()`)
- Example: `async def get_posted_move_lines(client: OdooClient, domain: list[Any] | None = None, *, limit: int | None = None, ...)`

**Return Values:**
- Explicitly typed: `-> list[int]`, `-> DaysToPayResult`, `-> None`
- Use union types for optional returns: `-> ResolvedPartner | None`
- Never return bare `list` or `dict` — always specify element types: `list[dict[str, Any]]`
- Cast when necessary (rare): `cast("list[int]", await self.call(...))`

## Module Design

**Exports:**
- Public APIs explicitly listed in root `__all__` (packages/godoo/src/godoo/__init__.py)
- Private functions/classes NOT exported (prefixed with `_`)
- Service imports use TYPE_CHECKING in `__init__.py` to avoid circular deps (client.py lines 19-27)

**Barrel Files:**
- Used in service packages for convenience re-exports
- Example: `packages/godoo/src/godoo/services/accounting/__init__.py`
  - Imports and re-exports: `AccountingService`, `_m2o_id`, `_m2o_name`, `is_closing_entry_from_lines`
  - Allows: `from godoo.services.accounting import AccountingService`

**Lazy Loading Pattern:**
- Used in OdooClient for service accessors (client.py lines 193-239)
- Pattern: `@cached_property` with inline import inside method
  ```python
  @cached_property
  def mail(self) -> MailService:
      from godoo.services.mail.service import MailService
      return MailService(self)
  ```
- Reason: Avoids circular imports; services import OdooClient from TYPE_CHECKING block

## Async Patterns

**Rule: All service functions are async**
- Every function in `services/{name}/functions.py` is `async def`
- Pattern: Client is first parameter, always awaited
  - `await client.search_read(...)`
  - `await client.read(...)`
  - `await client.call(...)`
- Async operations wrapped in try/except for error handling (transport.py lines 81-87)

**Testcontainers Sync API Wrapping:**
- testcontainers-python uses sync API (`.start()`, `.stop()`, `wait_for_logs()`)
- Must wrap in `asyncio.to_thread()` for async context
- Pattern from container.py:
  ```python
  await asyncio.to_thread(network.create)
  await asyncio.to_thread(pg.start)
  await asyncio.to_thread(wait_for_logs, pg, "...", 90)
  ```
- This converts blocking calls to async-friendly threads

## Dataclass Patterns

**Standard pattern:**
- Use `dataclass` from `dataclasses` module (not Pydantic)
- All fields type-hinted: `id: int`, `name: str`, `vat: str | None = None`
- Default values in order (non-defaults before defaults)
- Example from types.py:
  ```python
  @dataclass
  class ReconciliationTrace:
      full_reconcile_id: int | None
      lines: list[ReconciliationLine] = field(default_factory=list)
  ```
- `field(default_factory=list)` used for mutable defaults (never `= []`)

---

*Convention analysis: 2026-04-10*
