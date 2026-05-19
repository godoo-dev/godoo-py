# Phase 1: Client Parity - Pattern Map

**Mapped:** 2026-05-19
**Files analyzed:** 5 (3 modified source files + 2 modified test files + 1 new file)
**Analogs found:** 6 / 6

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `packages/godoo/src/godoo/client.py` | client-facade | request-response | `packages/godoo/src/godoo/client.py` (self — extend existing CRUD block) | exact |
| `packages/godoo/src/godoo/rpc/transport.py` | transport | request-response | `packages/godoo/src/godoo/rpc/transport.py` (self — patch `call_rpc` + `__init__`) | exact |
| `packages/godoo/src/godoo/services/cdc/service.py` | service-wrapper | event-driven (async generator) | `packages/godoo/src/godoo/services/cdc/functions.py` (`get_feed` function is the generator) | exact |
| `packages/godoo/src/godoo/py.typed` | marker | — | `packages/godoo/pyproject.toml` (`packages = ["src/godoo"]` — hatchling auto-includes) | n/a |
| `packages/godoo/tests/test_client.py` | test | request-response (mock HTTP) | `packages/godoo/tests/test_client.py` (self — add new test functions) | exact |
| `packages/godoo/tests/test_transport.py` | test | request-response (mock HTTP) | `packages/godoo/tests/test_transport.py` (self — add timeout tests) | exact |

---

## Pattern Assignments

### `packages/godoo/src/godoo/client.py` — all new methods

**Analog:** the existing file itself. All new methods join the `# CRUD helpers` block (CLIENT-02/04/05/06/07/08) or the `# Lifecycle` block (CLIENT-01/03). `OdooClientConfig` dataclass gains one field.

---

#### CLIENT-01: `__aenter__` / `__aexit__`

**Pattern source:** existing `authenticate()` (line 60) + `aclose()` (line 248-249).

Place in the `# Lifecycle` block after `aclose()`. These are the only two async lifecycle methods — the context manager simply delegates to them.

```python
# packages/godoo/src/godoo/client.py — add to Lifecycle block

async def __aenter__(self) -> OdooClient:
    await self.authenticate()
    return self

async def __aexit__(
    self,
    exc_type: type[BaseException] | None,
    exc_val: BaseException | None,
    exc_tb: object,
) -> None:
    await self.aclose()
```

---

#### CLIENT-03: `with_context()` + `_OdooContextScope` + module-level `_ambient_context`

**Pattern source:** the existing sentinel pattern (lines 31-32: `_UNDEFINED = object()`) and the `_effective_safety()` method (lines 76-82) show how module-level sentinels and per-instance state coexist. The `ContextVar` must be at **module level** (outside the class), like `_UNDEFINED`.

**Module-level addition** (after `_UNDEFINED = object()`, before `@dataclass class OdooClientConfig`):

```python
# packages/godoo/src/godoo/client.py — module level, after _UNDEFINED sentinel

import contextvars  # add to existing imports block

_ambient_context: contextvars.ContextVar[dict[str, Any]] = contextvars.ContextVar(
    "_ambient_context", default={}
)


class _OdooContextScope:
    """Sync context manager that threads ambient RPC context for the duration of a with block."""

    def __init__(self, layer: dict[str, Any]) -> None:
        self._layer = layer
        self._token: contextvars.Token[dict[str, Any]] | None = None

    def __enter__(self) -> _OdooContextScope:
        current = _ambient_context.get()
        self._token = _ambient_context.set({**current, **self._layer})
        return self

    def __exit__(self, *_: object) -> None:
        if self._token is not None:
            _ambient_context.reset(self._token)
            self._token = None
```

**`with_context()` method on `OdooClient`** (add to CRUD helpers block):

```python
def with_context(self, **kwargs: Any) -> _OdooContextScope:
    """Return a sync context manager that merges kwargs into every RPC call in its block."""
    return _OdooContextScope(kwargs)
```

**Ambient-context injection in `call()`** (lines 102-120 — extend the existing `call` method body, after `await self._guard(op)` and before the `return`):

```python
# Copy pattern: never mutate kwargs in-place (callers may reuse the same dict)
ambient = _ambient_context.get()
if ambient or "context" in kwargs:
    merged_ctx = {**ambient, **kwargs.get("context", {})}
    if merged_ctx:
        kwargs = {**kwargs, "context": merged_ctx}

return await self._transport.call(model, method, args, kwargs)
```

---

#### CLIENT-02: `iter_search_read()`

**Pattern source:** `search_read` (lines 146-165) — same signature shape (model, domain, keyword-only named params, `**kwargs` forwarded to `call`). Also mirrors `get_feed` in `packages/godoo/src/godoo/services/cdc/functions.py` (lines 128-222) for the keyset cursor loop and `yield` pattern.

**Return type annotation:** `collections.abc.AsyncIterator` — already imported under `TYPE_CHECKING` in `services/cdc/service.py`; add the same import to `client.py` under `TYPE_CHECKING`.

```python
# packages/godoo/src/godoo/client.py — TYPE_CHECKING block addition
if TYPE_CHECKING:
    from collections.abc import AsyncIterator
    ...  # existing service imports unchanged
```

```python
# Add to CRUD helpers block, after search_read

async def iter_search_read(
    self,
    model: str,
    domain: list[Any] | None = None,
    *,
    fields: list[str] | None = None,
    batch_size: int = 500,
    limit: int | None = None,
    **kwargs: Any,
) -> AsyncIterator[dict[str, Any]]:
    """Async generator yielding all records using keyset (id-cursor) pagination.

    Always orders by id ascending; does not accept a custom order parameter.
    Inject id field internally; strip from yielded records if caller did not request it.
    """
    base_domain = list(domain or [])
    last_id = 0
    yielded = 0
    # Always fetch id for cursor advancement; strip later if not requested by caller
    caller_requested_id = fields is None or "id" in fields
    fetch_fields = fields if fields is None else list(dict.fromkeys(["id"] + list(fields)))

    while True:
        page_domain = base_domain + [("id", ">", last_id)]
        remaining = (limit - yielded) if limit is not None else None
        fetch_size = min(batch_size, remaining) if remaining is not None else batch_size

        batch = await self.search_read(
            model,
            page_domain,
            fields=fetch_fields,
            limit=fetch_size,
            order="id",
            **kwargs,
        )
        if not batch:
            break

        for record in batch:
            if not caller_requested_id:
                record = {k: v for k, v in record.items() if k != "id"}
            yield record
            yielded += 1
            if limit is not None and yielded >= limit:
                return

        if len(batch) < fetch_size:
            break
        last_id = batch[-1]["id"]
```

---

#### CLIENT-04: `fields_get()`

**Pattern source:** `search_count` (line 167-168) — the minimal one-liner `call()` dispatch pattern. `fields_get` is already in `READ_METHODS` (safety/__init__.py line 17).

```python
async def fields_get(
    self,
    model: str,
    attributes: list[str] | None = None,
) -> dict[str, Any]:
    """Return field metadata dict keyed by field name (Odoo's native fields_get shape)."""
    kw: dict[str, Any] = {}
    if attributes is not None:
        kw["attributes"] = attributes
    return cast("dict[str, Any]", await self.call(model, "fields_get", [], kw))
```

---

#### CLIENT-05: `ref()`

**Pattern source:** the pattern in `timesheets/functions.py` lines 90-97 (local precondition raises `OdooValidationError` before RPC) + `search_read` usage pattern from `cdc/functions.py` lines 44-49 (query `ir.model.fields`). Raises `OdooMissingError` — already imported via `godoo.errors`; add it to the `from godoo.errors import ...` line in `client.py`.

```python
async def ref(self, xml_id: str) -> int:
    """Resolve an external ID (module.name) to a numeric record id.

    Raises OdooValidationError for malformed xml_id.
    Raises OdooMissingError when the xml_id is not found.
    """
    parts = xml_id.split(".", 1)
    if len(parts) != 2:
        raise OdooValidationError(f"Invalid XML ID format (expected 'module.name'): {xml_id!r}")
    module, name = parts
    records = await self.search_read(
        "ir.model.data",
        [("module", "=", module), ("name", "=", name)],
        fields=["res_id"],
    )
    if not records:
        raise OdooMissingError(f"XML ID not found: {xml_id!r}")
    return cast("int", records[0]["res_id"])
```

**Import addition required:** add `OdooMissingError, OdooValidationError` to the `from godoo.errors import` line (line 10 of client.py currently only imports `OdooAuthError, OdooSafetyError`).

---

#### CLIENT-06: `execute_kw()`

**Pattern source:** `search` (lines 126-132) — minimal wrapper that forwards to `self.call()`. The safety guard inside `call()` classifies `method` via `infer_safety_level`, so no additional safety code is needed here.

```python
async def execute_kw(
    self,
    model: str,
    method: str,
    args: list[Any],
    kwargs: dict[str, Any] | None = None,
) -> Any:
    """Raw RPC passthrough for non-standard Odoo methods.

    Routes through call() so the safety guard still classifies and gates it.
    """
    return await self.call(model, method, args, kwargs or {})
```

---

#### CLIENT-07: `read_binary()`

**Pattern source:** `read` (lines 137-144) — uses `self.read()` with a `fields=` list, then post-processes the result. Error pattern (`OdooMissingError`) follows `ref()` / timesheets `stop_timer` (lines 60-62).

**Import addition required:** `import base64` at the top of `client.py`.

```python
async def read_binary(self, model: str, record_id: int, field: str) -> bytes:
    """Fetch a binary field and return decoded bytes.

    Returns b"" when the field is unset (Odoo returns False for empty binary fields).
    Raises OdooMissingError when the record does not exist.
    """
    records = await self.read(model, record_id, fields=[field])
    if not records:
        raise OdooMissingError(f"Record {model}:{record_id} not found")
    raw = records[0].get(field)
    if raw is False or raw is None:
        return b""
    return base64.b64decode(raw)
```

---

#### CLIENT-08: bulk `create()` with `@typing.overload`

**Pattern source:** existing `create` (lines 170-171) — replace with the overloaded version. The `isinstance` guard + local `OdooValidationError` raise follows `timesheets/functions.py` lines 96-97 (`if options.hours <= 0: raise OdooValidationError(...)`).

**Import addition required:** `from typing import overload` (add `overload` to the existing `from typing import TYPE_CHECKING, Any, cast` line).

```python
@overload
async def create(self, model: str, values: dict[str, Any], **kwargs: Any) -> int: ...
@overload
async def create(self, model: str, values: list[dict[str, Any]], **kwargs: Any) -> list[int]: ...

async def create(
    self,
    model: str,
    values: dict[str, Any] | list[dict[str, Any]],
    **kwargs: Any,
) -> int | list[int]:
    if isinstance(values, list):
        if not values:
            raise OdooValidationError("Cannot create with empty list of values")
        return cast("list[int]", await self.call(model, "create", [values], kwargs))
    return cast("int", await self.call(model, "create", [values], kwargs))
```

---

#### FIXES-03: `OdooClientConfig.timeout` field

**Pattern source:** `OdooClientConfig` dataclass (lines 35-42) — existing `safety: SafetyContext | None = field(default=None)` shows the exact pattern for an optional dataclass field with a `None` default.

```python
@dataclass
class OdooClientConfig:
    url: str
    database: str
    username: str
    password: str
    safety: SafetyContext | None = field(default=None)
    timeout: float | None = field(default=None)  # NEW — threaded to httpx.AsyncClient
```

---

### `packages/godoo/src/godoo/rpc/transport.py` — FIXES-02 and FIXES-03

**Analog:** the file itself. Two surgical edits.

---

#### FIXES-03: Thread `timeout` to `httpx.AsyncClient`

**Pattern source:** `__init__` (lines 27-31). Change `__init__` signature to accept `timeout` and pass it to `httpx.AsyncClient`. Pattern for optional param with `None` default follows the existing `_session: OdooSessionInfo | None = None` field.

```python
# transport.py lines 27-31 — BEFORE:
def __init__(self, base_url: str, db: str) -> None:
    self._base_url = base_url.rstrip("/")
    self._db = db
    self._client = httpx.AsyncClient()

# AFTER:
def __init__(self, base_url: str, db: str, timeout: float | None = None) -> None:
    self._base_url = base_url.rstrip("/")
    self._db = db
    self._client = httpx.AsyncClient(timeout=timeout)
```

**Wiring in `client.py` `__init__`** (line 49):

```python
# client.py line 49 — BEFORE:
self._transport = JsonRpcTransport(config.url, config.database)

# AFTER:
self._transport = JsonRpcTransport(config.url, config.database, timeout=config.timeout)
```

---

#### FIXES-02: Catch `httpx.TimeoutException` before `httpx.RequestError`

**Pattern source:** `call_rpc` exception block (lines 81-87). The bug is that `httpx.TimeoutException` is a subclass of `httpx.RequestError` so the generic handler catches it first. Insert the specific handler before the generic one.

```python
# transport.py call_rpc exception block — BEFORE (lines 81-87):
        except httpx.HTTPStatusError as exc:
            raise OdooNetworkError(
                f"HTTP error {exc.response.status_code}: {exc.response.text}",
                cause=exc,
            ) from exc
        except httpx.RequestError as exc:
            raise OdooNetworkError(f"Connection error: {exc}", cause=exc) from exc

# AFTER — insert TimeoutException handler between HTTPStatusError and RequestError:
        except httpx.HTTPStatusError as exc:
            raise OdooNetworkError(
                f"HTTP error {exc.response.status_code}: {exc.response.text}",
                cause=exc,
            ) from exc
        except httpx.TimeoutException as exc:          # NEW — must precede RequestError
            raise OdooTimeoutError(f"Request timed out: {exc}", cause=exc) from exc
        except httpx.RequestError as exc:
            raise OdooNetworkError(f"Connection error: {exc}", cause=exc) from exc
```

**Import addition required:** add `OdooTimeoutError` to the `from godoo.errors import` block (line 11-18 of transport.py).

---

### `packages/godoo/src/godoo/services/cdc/service.py` — FIXES-01

**Analog:** `functions.py` `get_feed` (lines 128-131) — that function is an `async def` generator. The service wrapper must be a plain `def` that returns the generator object directly.

**Pattern source:** `check()` and `get_history()` in the same file (lines 27-36) show the correct async-method delegation pattern. `get_feed` is the odd one out because the function it delegates to is an async generator, not a coroutine.

```python
# service.py lines 38-39 — BEFORE (bug):
async def get_feed(self, options: GetFeedOptions) -> AsyncIterator[TrackingEvent]:
    return get_feed(self._client, options)

# AFTER (fix: remove async):
def get_feed(self, options: GetFeedOptions) -> AsyncIterator[TrackingEvent]:
    return get_feed(self._client, options)
```

No other changes to this file.

---

### `packages/godoo/src/godoo/py.typed` — CLIENT-10

**Pattern source:** `packages/godoo/pyproject.toml` line 28: `packages = ["src/godoo"]`. Hatchling includes all files under the package directory automatically — no `[tool.hatch.build.targets.wheel]` include config needed.

Create an **empty file** at `packages/godoo/src/godoo/py.typed`. No content.

---

### `packages/godoo/tests/test_client.py` — new tests for CLIENT-01 through CLIENT-08

**Analog:** the existing file. All new test functions follow the exact same structure already in use.

**Fixture pattern** (lines 26-38):

```python
# Unauthenticated client — no mock needed
@pytest.fixture
def client():
    c = OdooClient(_make_config())
    yield c

# Pre-authenticated client — single mock call consumed by authenticate()
@pytest.fixture
async def auth_client():
    c = OdooClient(_make_config())
    with respx.mock:
        respx.post(f"{BASE_URL}/jsonrpc").mock(return_value=httpx.Response(200, json=_jsonrpc_result(2)))
        await c.authenticate()
    yield c
```

**Single-call test with `@respx.mock` decorator** (lines 47-53 — `test_authenticate_success`):

```python
@respx.mock
@pytest.mark.asyncio
async def test_fields_get(auth_client):
    respx.post(f"{BASE_URL}/jsonrpc").mock(
        return_value=httpx.Response(200, json=_jsonrpc_result({"name": {"type": "char"}}))
    )
    result = await auth_client.fields_get("res.partner")
    assert result == {"name": {"type": "char"}}
```

**Multi-response side_effect pattern** (lines 113-127 — `test_safety_allows_read`):

```python
@pytest.mark.asyncio
async def test_iter_search_read_two_pages(auth_client):
    page1 = [{"id": 1, "name": "A"}, {"id": 2, "name": "B"}, {"id": 3, "name": "C"}]
    page2 = [{"id": 4, "name": "D"}]
    with respx.mock:
        respx.post(f"{BASE_URL}/jsonrpc").mock(
            side_effect=[
                httpx.Response(200, json=_jsonrpc_result(page1)),
                httpx.Response(200, json=_jsonrpc_result(page2)),
            ]
        )
        records = [r async for r in auth_client.iter_search_read("res.partner", batch_size=3)]
    assert len(records) == 4
    assert records[-1]["id"] == 4
```

**Local-precondition validation test** (pattern from existing `test_call_before_auth_raises` lines 42-44):

```python
@pytest.mark.asyncio
async def test_bulk_create_empty_list_raises(auth_client):
    with pytest.raises(OdooValidationError, match="empty"):
        await auth_client.create("res.partner", [])
```

**Async context manager test** (uses `auth_client` fixture pattern + `side_effect` list):

```python
@respx.mock
@pytest.mark.asyncio
async def test_async_context_manager_authenticates_and_closes():
    c = OdooClient(_make_config())
    respx.post(f"{BASE_URL}/jsonrpc").mock(return_value=httpx.Response(200, json=_jsonrpc_result(2)))
    async with c as opened:
        assert opened is c
        assert c.is_authenticated()
    # aclose() was called — transport httpx client is closed; no assertion needed here
    # (the mock consumed the one response for authenticate)
```

---

### `packages/godoo/tests/test_transport.py` — new tests for FIXES-02 and FIXES-03

**Analog:** the existing file. All new tests follow the same fixture + `@respx.mock` / `respx.mock` block pattern.

**`side_effect` with httpx exception pattern** (lines 159-164 — `test_connection_error_raises_network_error`):

```python
@pytest.mark.asyncio
async def test_connection_error_raises_network_error(transport):
    with respx.mock:
        respx.post(f"{BASE_URL}/jsonrpc").mock(side_effect=httpx.ConnectError("Connection refused"))
        with pytest.raises(OdooNetworkError):
            await transport.call_rpc("common.authenticate", {})
```

**New timeout tests** (copy the `side_effect=httpx.ConnectError(...)` pattern, substitute `httpx.ReadTimeout`):

```python
@pytest.mark.asyncio
async def test_read_timeout_raises_odoo_timeout_error(transport):
    with respx.mock:
        respx.post(f"{BASE_URL}/jsonrpc").mock(side_effect=httpx.ReadTimeout("timed out"))
        with pytest.raises(OdooTimeoutError):
            await transport.call_rpc("common.authenticate", {})


@pytest.mark.asyncio
async def test_connect_timeout_raises_odoo_timeout_error(transport):
    with respx.mock:
        respx.post(f"{BASE_URL}/jsonrpc").mock(side_effect=httpx.ConnectTimeout("timed out"))
        with pytest.raises(OdooTimeoutError):
            await transport.call_rpc("common.authenticate", {})
```

**Timeout config threading test** (verifies the new `timeout=` param threads through):

```python
def test_transport_timeout_param_accepted():
    t = JsonRpcTransport(BASE_URL, DB, timeout=30.0)
    assert t._client.timeout.read == 30.0  # httpx stores it on the client
```

**`OdooTimeoutError` import** — add to the existing `from godoo.errors import` block at the top of `test_transport.py`.

---

## Shared Patterns

### `from __future__ import annotations`

**Source:** every file in `packages/godoo/src/`
**Apply to:** all modified files — the `__future__` import is the first line of every source file in this project (enforced by CLAUDE.md and mypy --strict config).

### `cast()` for typed JSON-RPC return values

**Source:** `packages/godoo/src/godoo/client.py` lines 132, 144, 165, 168, 171, 182, 186
**Apply to:** every new `client.py` method that calls `self.call()` — the return type of `call()` is `Any`; the helper must `cast()` to the expected type.

```python
# Pattern: cast at the call() boundary
return cast("list[int]", await self.call(model, "create", [values], kwargs))
return cast("dict[str, Any]", await self.call(model, "fields_get", [], kw))
return cast("int", records[0]["res_id"])
```

### `TYPE_CHECKING` import guard for circular-import-prone types

**Source:** `packages/godoo/src/godoo/client.py` lines 19-27
**Apply to:** `AsyncIterator` return type annotation for `iter_search_read` — import `AsyncIterator` from `collections.abc` under `TYPE_CHECKING`.

```python
if TYPE_CHECKING:
    from collections.abc import AsyncIterator
    from godoo.services.accounting.service import AccountingService
    # ... existing service imports unchanged
```

### Local precondition raises `OdooValidationError` before any RPC

**Source:** `packages/godoo/src/godoo/services/timesheets/functions.py` lines 96-97
**Apply to:** `create(model, [])` empty-list guard (CLIENT-08 / D-08), `ref()` malformed xml_id guard (CLIENT-05 / D-16).

```python
# Pattern: guard first, RPC never reached on invalid input
if options.hours <= 0:
    raise OdooValidationError("Hours must be positive")
```

### `OdooMissingError` for "not found" post-RPC checks

**Source:** `packages/godoo/src/godoo/errors.py` lines 100-106
**Apply to:** `ref()` (no record in `ir.model.data`) and `read_binary()` (no record returned by `read()`).

```python
# Pattern: raise after checking empty result from search_read / read
if not records:
    raise OdooMissingError(f"XML ID not found: {xml_id!r}")
```

### `cause=exc` + `from exc` exception chaining

**Source:** `packages/godoo/src/godoo/rpc/transport.py` lines 81-87
**Apply to:** the new `OdooTimeoutError` raise in FIXES-02 — both `cause=exc` kwarg (for `.to_json()` serialization) and `from exc` (for Python traceback chaining).

```python
raise OdooTimeoutError(f"Request timed out: {exc}", cause=exc) from exc
```

### Test `_jsonrpc_result` / `_make_config` helpers

**Source:** `packages/godoo/tests/test_client.py` lines 16-23
**Apply to:** all new tests in `test_client.py` — reuse the existing helpers, do not define duplicates.

```python
def _jsonrpc_result(result):
    return {"jsonrpc": "2.0", "id": 1, "result": result}

def _make_config(**kwargs):
    defaults = dict(url=BASE_URL, database=DB, username="admin", password="admin")
    defaults.update(kwargs)
    return OdooClientConfig(**defaults)
```

---

## No Analog Found

No files in this phase lack a codebase analog. All patterns have direct counterparts in the existing source.

---

## Metadata

**Analog search scope:** `packages/godoo/src/godoo/`, `packages/godoo/tests/`
**Files scanned:** 6 source files + 2 test files read in full
**Pattern extraction date:** 2026-05-19
