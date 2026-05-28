# Phase 6: Transport Seam & Typed Models Core - Pattern Map

**Mapped:** 2026-05-28
**Files analyzed:** 9 (5 new, 4 modified)
**Analogs found:** 9 / 9

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `packages/godoo-client/src/godoo/client/rpc/protocol.py` (NEW) | type-contract (Protocol) | request-response (structural) | `packages/godoo-client/src/godoo/client/rpc/transport.py` | exact (same layer; Protocol mirrors impl surface) |
| `packages/godoo-client/src/godoo/client/typed.py` (NEW) | public-types module | none (pure types) | `packages/godoo-client/src/godoo/client/rpc/types.py` | exact (stdlib-only frozen dataclass + Protocol) |
| `packages/godoo-client/src/godoo/client/_pydantic_transform.py` (NEW) | private transform helper | transform (dict → model) | `packages/godoo-client/src/godoo/client/services/cdc/field_cache.py` | role-match (private module-scoped cache + helpers) |
| `packages/godoo-client/src/godoo/client/client.py` (MODIFIED — `OdooClientConfig`, `__init__`, `read`, `search_read`) | controller/facade | request-response + dispatch | self (existing `create()` overload pair L336–341 + `read()` L182–192) | exact (same file, existing pattern to extend) |
| `packages/godoo-client/pyproject.toml` (MODIFIED — `[project.optional-dependencies]`) | packaging config | n/a | self (current `dependencies = ["httpx>=0.27"]` block L8) | role-match (no existing optional-extras precedent in this repo) |
| `packages/godoo-client/tests/test_typed_isolation.py` (NEW) | test (invariant guard) | subprocess | `packages/godoo-client/tests/test_namespace.py` | exact (PEP 420 guard pattern → import-isolation guard) |
| `packages/godoo-client/tests/test_transport_protocol.py` (NEW) | test (structural conformance) | type-check + smoke | `packages/godoo-client/tests/test_transport.py` | role-match (transport tests; mypy-as-assertion is a new variant) |
| `packages/godoo-client/tests/test_typed.py` (NEW) | test (unit, stdlib types) | n/a | `packages/godoo-client/tests/test_namespace.py` (style) | role-match |
| `packages/godoo-client/tests/test_pydantic_transform.py` (NEW) | test (unit, transforms) | transform validation | `packages/godoo-client/tests/test_transport.py` (style) | role-match |
| `packages/godoo-client/tests/test_typed_dispatch.py` (NEW) | test (respx-mocked unit) | request-response | `packages/godoo-client/tests/test_client.py` | exact (respx + OdooClient pattern) |

## Pattern Assignments

### `rpc/protocol.py` (NEW — Protocol definition)

**Analog:** `packages/godoo-client/src/godoo/client/rpc/transport.py` (mirror its public surface; never modify it)

**Imports pattern** (mirrors `rpc/transport.py` L1–19 — but stdlib + types-only, no httpx, no errors):
```python
"""Structural transport contract — Protocol that JsonRpcTransport satisfies."""
from __future__ import annotations

from typing import Any, Protocol

from godoo.client.rpc.types import OdooSessionInfo
```

**Surface to mirror** — extracted from `rpc/transport.py`:
- `session` property — `transport.py:38–40` returns `OdooSessionInfo | None`
- `authenticate(self, username: str, password: str) -> OdooSessionInfo` — `transport.py:49`
- `call(self, model: str, method: str, args: list[Any], kwargs: dict[str, Any]) -> Any` — `transport.py:98–104`
- `logout(self) -> None` — `transport.py:125`
- `aclose(self) -> None` — `transport.py:130`

**Protocol body** (synthesise from the surface above; D-06 minimal):
```python
class Transport(Protocol):
    """Structural type for transports OdooClient drives.

    JsonRpcTransport satisfies this Protocol without modification (D-06).
    Alternative transports (e.g. a future Pyodide pyfetch-backed transport,
    or a Mock for tests) only need to expose these five members.
    """

    @property
    def session(self) -> OdooSessionInfo | None: ...

    async def authenticate(self, username: str, password: str) -> OdooSessionInfo: ...

    async def call(
        self,
        model: str,
        method: str,
        args: list[Any],
        kwargs: dict[str, Any],
    ) -> Any: ...

    def logout(self) -> None: ...

    async def aclose(self) -> None: ...
```

**Module docstring + `from __future__ import annotations` first line** — established by every file in the codebase (see `transport.py:1–3`, `types.py:1–3`).

**No `__all__` needed** at the module level (Protocol is one symbol; barrel export happens in `rpc/__init__.py` per Open Q2).

---

### `client/typed.py` (NEW — public stdlib-only types)

**Analog:** `packages/godoo-client/src/godoo/client/rpc/types.py`

**Full reference body** of analog (`rpc/types.py`, all 12 lines):
```python
"""RPC data types."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class OdooSessionInfo:
    uid: int
    session_id: str
    db: str
```

**Patterns to copy from analog:**
- Module docstring (line 1)
- `from __future__ import annotations` (line 3)
- Bare `@dataclass` decorator with positional fields
- Single import block, no `TYPE_CHECKING` needed (stdlib-only)

**Patterns to ADD on top** (per D-08, D-09; not present in analog):
- `@dataclass(frozen=True)` — `Ref[T]` is immutable
- `Generic[T]` + `TypeVar("T")` — `Ref[T]` is generic
- `Protocol` import + class for `OdooModel`
- Explicit `__all__ = ["OdooModel", "Ref"]` (this module IS part of the public surface; users + Phase 7 codegen import from here)
- `ClassVar[str]` for `__odoo_model__` (Protocol member)

**Final body** (synthesise from RESEARCH.md Example C, lines 588–626):
```python
"""Stdlib-only typed-model primitives. Importable without pydantic [typed] extra."""
from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar, Generic, Protocol, TypeVar

T = TypeVar("T")


class OdooModel(Protocol):
    """Marker protocol for typed Odoo model classes.

    Concrete classes (emitted by Phase 7 codegen) declare:
        __odoo_model__: ClassVar[str] = "res.partner"

    Runtime dispatch in OdooClient.read/search_read keys on
    hasattr(model, "__odoo_model__") — never on isinstance(BaseModel) (D-04).
    """

    __odoo_model__: ClassVar[str]


@dataclass(frozen=True)
class Ref(Generic[T]):
    """Typed many2one reference: numeric id + display name."""

    id: int
    name: str


__all__ = ["OdooModel", "Ref"]
```

**CRITICAL invariant:** never import anything from `godoo.client._pydantic_transform` here. This module must stay stdlib-only.

---

### `client/_pydantic_transform.py` (NEW — sole pydantic-touching module)

**Analog (structural):** `packages/godoo-client/src/godoo/client/services/cdc/field_cache.py` — only other module-scoped private cache+helper module in the repo.

**Analog (style):** `packages/godoo-client/src/godoo/client/safety/__init__.py` for the "dataclass + module-level state + helpers" file layout. Note the underscore-prefixed `_default_safety_context: SafetyContext | None = None` at L51 of `safety/__init__.py` — same idiom for the partial-model cache.

**Imports pattern** (D-08: this is the ONE file allowed to import pydantic):
```python
"""Pydantic wire transforms — sole module that imports pydantic.

NEVER import this module at top of any other godoo.client submodule.
Always reach it via lazy `from godoo.client._pydantic_transform import ...`
inside a dispatch-branch function body (D-04, D-08).
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any, ClassVar

from pydantic import BaseModel, create_model, model_validator

from godoo.client.typed import Ref
```

**Module-private cache pattern** (mirror `safety/__init__.py:51`):
```python
_partial_model_cache: dict[tuple[int, frozenset[str]], type[BaseModel]] = {}
```

**Core class + helper** — full body specified in RESEARCH.md Pattern 3 (L361–401) and Pattern 4 (L426–456). Planner copies those verbatim with the helper predicates (`_annotation_mentions_ref`, `_annotation_is_date_like`, `_looks_iso_date`, `_looks_iso_datetime`) defined as module-private functions following the underscore-prefix convention used throughout the repo (e.g. `_categorize_error` at `transport.py:138`, `_guard` at `client.py:126`).

**Error/validation pattern** — mirror `client.py:295` (`OdooValidationError` on bad XML ID): `derive_partial_model` raises `ValueError` on unknown field name (per RESEARCH Pattern 4); planner may upgrade to `OdooValidationError` if it wants client-consistent exception types (Claude's discretion per Open Q3).

**No `__all__`** — D-08: this module is internal-only. Phase 7 codegen imports from it explicitly, never via barrel.

---

### `client/client.py` (MODIFIED — config field, init injection, two overload pairs)

**Analog:** self — extend existing patterns already present in this file.

#### Modification 1: `OdooClientConfig` dataclass extension (L77–84)

**Current code** (`client.py:77–84`):
```python
@dataclass
class OdooClientConfig:
    url: str
    database: str
    username: str
    password: str
    safety: SafetyContext | None = field(default=None)
    timeout: float | None = field(default=None)
```

**Add one field** (per D-07; RESEARCH Example A L547–566):
```python
    transport_factory: Callable[[OdooClientConfig], Transport] | None = field(default=None)
```

**Imports to add at top of file**:
```python
from collections.abc import Callable
# ...
if TYPE_CHECKING:
    from godoo.client.rpc.protocol import Transport
```

The forward-reference works because `from __future__ import annotations` is already L3. The `TYPE_CHECKING` guard mirrors the existing pattern at `client.py:21–31` (service-type imports). The `from collections.abc import Callable` is a runtime import — `Callable` is used inside the runtime dataclass field annotation… BUT under `from __future__ import annotations`, *all* annotations are strings, so `Callable` can also go under `TYPE_CHECKING`. Planner picks: keep `Callable` runtime-imported for symmetry with stdlib usage elsewhere (`safety/__init__.py:7` puts it under TYPE_CHECKING — planner may follow either; both are correct under PEP 563).

#### Modification 2: `OdooClient.__init__` transport injection (L90–97)

**Current code** (`client.py:90–97`):
```python
def __init__(self, config: OdooClientConfig) -> None:
    self._config = config
    self._transport = JsonRpcTransport(config.url, config.database, timeout=config.timeout)
    # _safety_context:
    #   _UNDEFINED  → use config.safety (which may be None)
    #   None        → explicitly disabled
    #   SafetyContext → explicitly set
    self._safety_context: SafetyContext | _UndefinedType | None = _UNDEFINED
```

**Replace single line** L92 (per D-07 + RESEARCH Example B L573–584):
```python
def __init__(self, config: OdooClientConfig) -> None:
    self._config = config
    if config.transport_factory is not None:
        self._transport: Transport = config.transport_factory(config)
    else:
        self._transport = JsonRpcTransport(config.url, config.database, timeout=config.timeout)
    self._safety_context: SafetyContext | _UndefinedType | None = _UNDEFINED
```

`JsonRpcTransport` is already imported at L13 (`from godoo.client.rpc import JsonRpcTransport, OdooSessionInfo`) — no new import needed, it remains stable per RESEARCH note at L584. The `Transport` annotation on `self._transport` needs the `TYPE_CHECKING` import already added above.

#### Modification 3: `@overload` pairs on `read` and `search_read`

**Analog (in-file precedent):** existing `create()` overload pair at `client.py:336–341`:
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
```

**Add to top of file** (TypeVar + import from stdlib-only `typed` module):
```python
from godoo.client.typed import OdooModel  # stdlib-only — safe at module load (D-05)
# ...
T = TypeVar("T", bound=OdooModel)
```

**Replace `read()` at `client.py:182–192`** — type[T] overload BEFORE str overload (D-03; mypy overlap):
```python
@overload
async def read(
    self,
    model: type[T],
    ids: int | list[int],
    fields: list[str] | None = None,
    **kwargs: Any,
) -> list[T]: ...

@overload
async def read(
    self,
    model: str,
    ids: int | list[int],
    fields: list[str] | None = None,
    **kwargs: Any,
) -> list[dict[str, Any]]: ...

async def read(
    self,
    model: str | type[T],
    ids: int | list[int],
    fields: list[str] | None = None,
    **kwargs: Any,
) -> list[dict[str, Any]] | list[T]:
    id_list = [ids] if isinstance(ids, int) else ids

    # Dispatch guard — duck-typed, never imports pydantic (D-04)
    if hasattr(model, "__odoo_model__"):
        # Lazy import — only loaded when typed branch fires (D-08)
        from godoo.client._pydantic_transform import (
            OdooBaseModel,
            derive_partial_model,
        )
        odoo_name: str = model.__odoo_model__  # type: ignore[union-attr]
        if fields is not None:
            kwargs["fields"] = fields
            target = derive_partial_model(model, fields)
        else:
            target = model
        raw = cast("list[dict[str, Any]]", await self.call(odoo_name, "read", [id_list], kwargs))
        return [target.model_validate(r) for r in raw]

    # str path — UNCHANGED from v1.0 (TYPED-04)
    if fields is not None:
        kwargs["fields"] = fields
    return cast("list[dict[str, Any]]", await self.call(model, "read", [id_list], kwargs))
```

**Replace `search_read()` at `client.py:194–213`** — same shape; `domain` positional, additional kwargs already handled. Planner mirrors the read dispatch but preserves the existing `*, fields=..., limit=..., offset=..., order=...` keyword-only signature on both overloads. The typed branch path: derive partial model when `fields` is set; on raw `dict[]` list returned from `self.call(..., "search_read", ...)`, `[target.model_validate(r) for r in raw]`.

**Error handling on missing pydantic** — per Open Q3 (RESEARCH L767–770): wrap the lazy import in try/except `ModuleNotFoundError` and re-raise as `OdooValidationError` with install hint `"Typed reads require 'pydantic'. Install with: pip install 'godoo-client[typed]'"`. Planner decides final exception class (could be new `OdooTypedNotInstalledError`).

---

### `pyproject.toml` (MODIFIED — add `[project.optional-dependencies]`)

**Current state** (`packages/godoo-client/pyproject.toml:1–17`):
```toml
[project]
name = "godoo-client"
version = "0.2.0"
description = "Async Python client for Odoo JSON-RPC"
readme = "README.md"
license = "LGPL-3.0-or-later"
requires-python = ">=3.14"
dependencies = ["httpx>=0.27"]
authors = [{ name = "Marc Fargas", email = "marc@marcfargas.com" }]
```

**Add new table** (anywhere after `dependencies =` line; per RESEARCH L111–115 + `<specifics>` of CONTEXT.md):
```toml
[project.optional-dependencies]
typed = ["pydantic>=2.13"]
```

**Lockfile-discipline rule (from user CLAUDE.md):** after editing `pyproject.toml`, run `uv sync` to regenerate `uv.lock`, and commit BOTH files in the same commit. Plan 06-03 must explicitly stage `pyproject.toml` AND `uv.lock` together.

---

### `tests/test_typed_isolation.py` (NEW — subprocess invariant guard)

**Analog:** `packages/godoo-client/tests/test_namespace.py` — full file (12 lines):
```python
from __future__ import annotations

import godoo


def test_godoo_is_namespace_package() -> None:
    """Assert godoo is a PEP 420 namespace package with no stray __init__.py."""
    assert godoo.__file__ is None, (
        "godoo.__file__ is not None — a stray __init__.py was introduced. "
        "This would break the namespace package layout and could prevent "
        "other packages from contributing to the godoo.* namespace."
    )
```

**Patterns to copy:**
- `from __future__ import annotations` first line
- Single function, descriptive name (`test_<invariant>_<verb>`)
- Multi-line failure-message assertion with reasoning (not just `assert x is None`)
- No fixtures, no parametrize — deterministic, runs in default suite

**Patterns to ADD** (per D-10 + RESEARCH Example E L666–702):
- `subprocess.run([sys.executable, "-c", script])` — spawns clean Python
- The inline script does `import godoo.client; import sys; assert 'pydantic' not in sys.modules`
- `capture_output=True, text=True, check=False` + manual `assert result.returncode == 0`
- Failure message includes `sorted(m for m in sys.modules if "pydantic" in m)` for debuggability

**Full body:** copy RESEARCH Example E (L666–702) verbatim.

---

### `tests/test_transport_protocol.py` (NEW — structural conformance)

**Analog:** `packages/godoo-client/tests/test_transport.py` for fixture style + import pattern.

**Imports pattern** (mirror `test_transport.py:1–17` minus respx/errors):
```python
"""mypy --strict on this file is the load-bearing assertion."""
from __future__ import annotations

from godoo.client.rpc.protocol import Transport
from godoo.client.rpc.transport import JsonRpcTransport
```

**Full body** — copy RESEARCH Example F (L706–730) verbatim:
```python
def test_jsonrpc_transport_satisfies_protocol() -> None:
    """Assert JsonRpcTransport satisfies the Transport Protocol structurally.

    The mypy --strict check on this file is the real assertion. The runtime
    test is belt-and-braces.
    """
    t: Transport = JsonRpcTransport("http://example", "db")
    assert hasattr(t, "authenticate")
    assert hasattr(t, "call")
    assert hasattr(t, "aclose")
    assert hasattr(t, "logout")
    assert hasattr(t, "session")
```

**No async, no fixtures, no respx** — the test is import-only.

---

### `tests/test_typed.py` (NEW — Ref dataclass + OdooModel marker)

**Analog:** `tests/test_namespace.py` style (single-purpose unit tests, no fixtures).

**Patterns to copy:** `from __future__ import annotations` first; simple `test_*` functions; no fixtures unless needed.

**Test cases to implement:**
- `Ref(id=1, name="X")` constructs; `Ref` is frozen (assigning `r.id = 2` raises `FrozenInstanceError`).
- `Ref(1, "X") == Ref(1, "X")` (dataclass equality).
- `Ref[SomeType]` is subscriptable at type-check time (Generic[T]).
- A class with `__odoo_model__: ClassVar[str] = "res.partner"` satisfies `isinstance(x, OdooModel)` IF `OdooModel` were runtime_checkable — since it's NOT (per Open Q1), assert via `hasattr(C, "__odoo_model__")` instead. This pins D-04's dispatch contract.

---

### `tests/test_pydantic_transform.py` (NEW — wire-transform unit tests)

**Analog:** `tests/test_transport.py` for `@pytest.mark.asyncio` / no respx pattern. But this test is synchronous (validators are sync).

**Imports pattern**:
```python
"""Wire transform behaviours: False→None, m2o→Ref, ISO strings→date/datetime, partial models."""
from __future__ import annotations

from datetime import date, datetime
from typing import ClassVar

import pytest
from pydantic import BaseModel

from godoo.client._pydantic_transform import OdooBaseModel, derive_partial_model
from godoo.client.typed import Ref
```

**Test cases (per D-01, D-02, TYPED-06):**
- Define a small `class _TestPartner(OdooBaseModel)` with `__odoo_model__: ClassVar[str] = "res.partner"`, plus a `name: str | None`, `is_company: bool`, `parent_id: Ref["_TestPartner"] | None`, `create_date: datetime | None`, `date_active: date | None`.
- False→None for non-bool: `_TestPartner.model_validate({"name": False})` → `.name is None`
- D-02 boolean preserved: `_TestPartner.model_validate({"is_company": False})` → `.is_company is False` (NOT None)
- m2o tuple → Ref: `model_validate({"parent_id": [3, "Acme"]})` → `.parent_id == Ref(3, "Acme")`
- ISO string → datetime: `model_validate({"create_date": "2026-01-15T12:00:00"})` → `.create_date == datetime(2026,1,15,12,0,0)`
- ISO string → date: `model_validate({"date_active": "2026-01-15"})` → `.date_active == date(2026,1,15)`
- `derive_partial_model(_TestPartner, ["name"])` returns a `type[BaseModel]` subclass; validating `{"name": "X", "is_company": True}` accepts only `name` (or extras-allow per planner decision); raises `ValueError` if `fields=["bogus"]`.
- Cache: `derive_partial_model(_TestPartner, ["name"]) is derive_partial_model(_TestPartner, ["name"])`.

---

### `tests/test_typed_dispatch.py` (NEW — overload runtime dispatch)

**Analog:** `packages/godoo-client/tests/test_client.py` (full respx + OdooClient pattern).

**Imports + fixtures pattern** — copy from `test_client.py:1–43` verbatim:
```python
from __future__ import annotations

import httpx
import pytest
import respx
from godoo.client.client import OdooClient, OdooClientConfig

BASE_URL = "http://odoo.test"
DB = "testdb"


def _jsonrpc_result(result):
    return {"jsonrpc": "2.0", "id": 1, "result": result}


def _make_config(**kwargs):
    defaults = dict(url=BASE_URL, database=DB, username="admin", password="admin")
    defaults.update(kwargs)
    return OdooClientConfig(**defaults)


@pytest.fixture
async def auth_client():
    c = OdooClient(_make_config())
    with respx.mock:
        respx.post(f"{BASE_URL}/jsonrpc").mock(return_value=httpx.Response(200, json=_jsonrpc_result(2)))
        await c.authenticate()
    yield c
```

**Test cases (per TYPED-03, TYPED-04, D-04):**
- `await auth_client.read("res.partner", [1])` returns `list[dict]` — str path UNCHANGED (TYPED-04 regression).
- Define a tiny `class TinyPartner(OdooBaseModel): __odoo_model__: ClassVar[str] = "res.partner"; name: str | None = None`. Mock the response as `[{"id": 1, "name": "Foo"}]`. `await auth_client.read(TinyPartner, [1])` returns `list[TinyPartner]`, validates name.
- Dispatch guard: define a non-pydantic class `class Marker: __odoo_model__ = "x.y"`. Confirm `await client.read(Marker, [1])` ALSO hits the typed branch (or fails on `model_validate` — pin which behaviour the planner chooses for non-BaseModel marker; D-04 mandates `hasattr` dispatch).
- search_read: same shape — str path returns list[dict], type[T] path returns list[T].

**Mock JSON-RPC pattern** — copy `test_client.py:50–88` style:
```python
@respx.mock
@pytest.mark.asyncio
async def test_typed_read_returns_models(auth_client):
    respx.post(f"{BASE_URL}/jsonrpc").mock(
        return_value=httpx.Response(200, json=_jsonrpc_result([{"id": 1, "name": "Foo"}]))
    )
    result = await auth_client.read(TinyPartner, [1])
    assert all(isinstance(r, TinyPartner) for r in result)
    assert result[0].name == "Foo"
```

---

## Shared Patterns

### Module file header (apply to all NEW .py files)

**Source:** `packages/godoo-client/src/godoo/client/rpc/types.py:1–3`
**Apply to:** every new source and test file in this phase
```python
"""<one-line module docstring>."""

from __future__ import annotations
```

This is the universally-applied opener in the codebase (verified in `transport.py:1–3`, `client.py:1–3`, `safety/__init__.py:1`, every test file). Non-negotiable.

### Lazy-import for circular/optional-dep avoidance

**Source:** `packages/godoo-client/src/godoo/client/client.py:381–384` (`@cached_property` body):
```python
@cached_property
def mail(self) -> MailService:
    from godoo.client.services.mail.service import MailService
    return MailService(self)
```

**Apply to:** the `from godoo.client._pydantic_transform import ...` inside `read()` / `search_read()` dispatch branches. Same idiom — local import inside a function body so the module-load graph stays clean. Per RESEARCH L300–303 + D-04: lazy imports look awkward but are mandatory for the [typed]-isolation invariant.

### TYPE_CHECKING import for type-only references

**Source:** `packages/godoo-client/src/godoo/client/client.py:21–31`:
```python
if TYPE_CHECKING:
    from collections.abc import AsyncIterator
    from godoo.client.services.accounting.service import AccountingService
    # ...
```

**Apply to:** importing `Transport` for the `transport_factory` annotation and `self._transport: Transport` declaration in `client.py`. Pure type annotation — no runtime cost, no circular-import risk.

### Cast for typed JSON-RPC returns

**Source:** `packages/godoo-client/src/godoo/client/client.py:180, 192, 213, 216`:
```python
return cast("list[int]", await self.call(model, "search", [domain or []], kwargs))
return cast("list[dict[str, Any]]", await self.call(model, "read", [id_list], kwargs))
```

**Apply to:** the str-path branch of new `read()` / `search_read()` bodies (unchanged — already uses this pattern). The typed branch does NOT use `cast` for the return; it returns `[target.model_validate(r) for r in raw]` which is naturally typed `list[BaseModel-subclass]`.

### Error class + clear remediation message

**Source:** `packages/godoo-client/src/godoo/client/client.py:294–295`:
```python
raise OdooValidationError(f"Invalid XML ID format (expected 'module.name'): {xml_id!r}")
```

**Apply to:** the lazy-import wrap in `read()`/`search_read()` when `ModuleNotFoundError: No module named 'pydantic'` fires:
```python
try:
    from godoo.client._pydantic_transform import OdooBaseModel, derive_partial_model
except ModuleNotFoundError as exc:
    raise OdooValidationError(
        "Typed reads require 'pydantic'. Install with: pip install 'godoo-client[typed]'"
    ) from exc
```

Mirrors the OdooMissingError raise at `client.py:303` for the "user passed something wrong, here's how to fix it" idiom.

### Module-private underscore prefix for internal symbols

**Source:** `packages/godoo-client/src/godoo/client/client.py:138` (`_categorize_error`), `client.py:126` (`_guard`), `safety/__init__.py:51` (`_default_safety_context`)

**Apply to:** helpers inside `_pydantic_transform.py` (`_annotation_mentions_ref`, `_partial_model_cache`, etc.). The module-name underscore prefix (`_pydantic_transform.py` itself) is the module-level signal; per-symbol underscores are the in-module signal.

### Dataclass-not-Pydantic for value types

**Source:** `packages/godoo-client/src/godoo/client/rpc/types.py:8–12`, `safety/__init__.py:33–44`, `client.py:77–84`

**Apply to:** `Ref` in `typed.py` — `@dataclass(frozen=True)`, not a Pydantic model. This is the documented project convention (CLAUDE.md L20: "Dataclasses for types, not Pydantic"). `OdooBaseModel` is the ONE deliberate exception per D-08, isolated behind `[typed]` extra.

## No Analog Found

All files have close analogs in the codebase. No file in this phase requires falling back to RESEARCH-only patterns.

## Metadata

**Analog search scope:**
- `packages/godoo-client/src/godoo/client/` (all subdirectories — `rpc/`, `safety/`, `services/`)
- `packages/godoo-client/tests/`
- `packages/godoo-client/pyproject.toml`

**Files scanned:** 45 source files + 15 test files + 1 pyproject (61 total)

**Files read in detail** (line-level pattern extraction):
- `packages/godoo-client/src/godoo/client/client.py` (full read — analog for overloads, init, config, lazy imports)
- `packages/godoo-client/src/godoo/client/rpc/transport.py` (full read — Protocol surface source)
- `packages/godoo-client/src/godoo/client/rpc/types.py` (full read — `Ref` analog)
- `packages/godoo-client/src/godoo/client/rpc/__init__.py` (barrel pattern)
- `packages/godoo-client/src/godoo/client/__init__.py` (public surface contract)
- `packages/godoo-client/src/godoo/client/safety/__init__.py` (partial — module-state idiom)
- `packages/godoo-client/tests/test_namespace.py` (full read — invariant guard analog)
- `packages/godoo-client/tests/test_client.py` (partial — respx fixture analog)
- `packages/godoo-client/tests/test_transport.py` (partial — transport test analog)
- `packages/godoo-client/pyproject.toml` (full read — extras target)

**Pattern extraction date:** 2026-05-28
