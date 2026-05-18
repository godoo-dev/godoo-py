# Coding Conventions

**Analysis Date:** 2026-05-18

## Naming Patterns

**Files:**
- Snake_case module names: `transport.py`, `field_cache.py`, `seed_resolver.py`
- Service directories match the service concept: `accounting/`, `timesheets/`, `cdc/`
- Test files prefixed with `test_`: `test_client.py`, `test_accounting.py`
- Internal helpers prefixed with underscore: `_m2o_id`, `_m2o_name`, `_base_url_cache`

**Classes:**
- PascalCase: `OdooClient`, `JsonRpcTransport`, `AccountingService`, `SafetyContext`
- Error classes follow `Odoo<Concept>Error` pattern: `OdooRpcError`, `OdooAuthError`, `OdooSafetyError`
- Dataclass names are noun phrases describing the concept: `OdooClientConfig`, `StartedOdooContainer`, `TrackingEvent`

**Functions:**
- Snake_case: `discover_cash_accounts`, `trace_reconciliation`, `resolve_partner_from_move`
- Async functions follow verb-noun pattern: `get_history`, `get_feed`, `calculate_days_to_pay`
- Boolean predicates are plain: `is_authenticated`, `is_module_installed`, `is_closing_entry`
- Private helpers prefixed with underscore: `_categorize_error`, `_effective_safety`, `_guard`, `_m2o_id`

**Variables:**
- Snake_case throughout
- Module-level constants in SCREAMING_SNAKE: `READ_METHODS`, `DELETE_METHODS`, `_TRACKING_FIELDS`
- Sentinels named `_UNDEFINED` (prefixed underscore for module-private)

**Types:**
- `Literal` types named descriptively: `SafetyLevel = Literal["READ", "WRITE", "DELETE"]`
- Type aliases at module level in `types.py` files
- `frozenset` for immutable method sets

## Code Style

**Formatting:**
- Tool: `ruff format`
- Line length: 120 characters (configured in root `pyproject.toml`)
- Target version: Python 3.14

**Linting:**
- Tool: `ruff check` with rules `["E", "F", "W", "I", "UP", "B", "SIM", "TCH", "RUF"]`
- `mypy --strict` on all `src/` directories
- `warn_return_any = true`, `disallow_untyped_defs = true`

## Import Organization

**Order (enforced by ruff `I` rule):**
1. `from __future__ import annotations` — always first, in every file
2. Standard library (`asyncio`, `os`, `dataclasses`, `logging`)
3. Third-party (`httpx`, `pytest`, `respx`)
4. Internal (`godoo.client`, `godoo.errors`, `godoo.services.*`)

**TYPE_CHECKING guard:**
- Used in every service file and `client.py` to prevent circular imports
- `OdooClient` is always imported under `TYPE_CHECKING` in service files
- Service classes are imported under `TYPE_CHECKING` in `client.py`

```python
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from godoo.client import OdooClient
```

**Path Aliases:** None — absolute imports from package root (`from godoo.errors import ...`)

## Error Handling

**Hierarchy:** All errors inherit from `OdooError` (base) → `OdooRpcError` → specialised subclasses.
- `OdooSafetyError` inherits directly from `OdooError` (NOT `OdooRpcError`, it is local-only).
- `OdooNetworkError` → `OdooTimeoutError` (network sub-hierarchy).

**Pattern:**
- Raise typed exceptions from the lowest layer (`transport.py` categorises RPC errors)
- Use `cause=exc` kwarg + `self.__cause__ = cause` chain to preserve original exception
- Every error class implements `to_json() -> dict[str, Any]` for serialisation
- Local validation raises `OdooValidationError` before any RPC call (e.g., `log_time` validates hours > 0)

**Categorisation at boundary:**
```python
# transport.py — map raw JSON-RPC error dict to typed exception
def _categorize_error(self, error_dict: dict[str, Any]) -> OdooRpcError:
    exception_type = (data.get("exception_type") or "").lower()
    # Check exception_type first, then fall back to data.name
```

## Logging

**Framework:** stdlib `logging`

**Patterns:**
- Logger per module with `logging.getLogger("godoo.client")` or `logging.getLogger("godoo.client.rpc")`
- `logger.debug(...)` for low-level RPC calls: `logger.debug("JSON-RPC call: method=%s", method)`
- `logger.info(...)` for lifecycle events in testcontainers: `logger.info("Odoo ready (attempt %d)", i + 1)`
- `logger.error(...)` for failure details: `logger.error("Odoo container logs:\n%s", logs[-3000:])`
- Use `%s`-style format strings (not f-strings) in log calls

## Comments

**When to Comment:**
- Module docstrings describing purpose: `"""JSON-RPC transport over httpx."""`
- Function docstrings for public API functions (one-liners or brief paragraphs)
- Inline comments for non-obvious behaviour: sentinel semantics, heuristics
- Section separators using dashes: `# ------------------------------------------------------------------`

**Docstring style:**
```python
"""Brief one-line description."""

async def discover_cash_accounts(client: OdooClient) -> list[CashAccount]:
    """Find all cash/bank journal accounts."""
```

**No docstrings on:** simple dataclass fields; private helpers with self-explanatory names.

## Function Design

**Size:** Functions stay focused; complex multi-step operations (like `get_feed`) are acceptable when the logic cannot be split cleanly.

**Parameters:**
- `client: OdooClient` is always the first positional argument in standalone functions
- Optional config objects use dedicated dataclasses (`GetHistoryOptions`, `LogTimeOptions`) rather than many keyword args
- Keyword-only arguments enforced with `*` for clarity: `search_read(..., *, fields=None, limit=None, ...)`
- `None` defaults for optional collections — never mutable defaults

**Return Values:**
- Typed with `cast()` at the `client.call()` level for JSON-RPC returns
- Return typed dataclasses or primitives — never raw `dict` from service functions
- Async generators use `AsyncIterator[T]` return type

## Module Design

**Exports:**
- Every `__init__.py` defines `__all__` explicitly: `packages/godoo/src/godoo/__init__.py`
- Service `__init__.py` barrel-exports both the service class, all functions, and all types

**Service pattern (4-file layout):**
```
services/{name}/
├── types.py      — @dataclass definitions only, no logic
├── functions.py  — standalone async functions (client as first arg)
├── service.py    — thin class delegating to functions
└── __init__.py   — barrel re-exports with __all__
```

**Circular import prevention:**
- `client.py` imports service classes inside `@cached_property` bodies (lazy imports)
- Services import `OdooClient` only under `TYPE_CHECKING`

**Dataclasses:**
- Preferred over Pydantic for all types
- `field(default_factory=list)` for mutable defaults
- `field(default=None, repr=False)` for sensitive/large fields

---

*Convention analysis: 2026-05-18*
