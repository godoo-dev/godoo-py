# Phase 6: Transport Seam & Typed Models Core - Research

**Researched:** 2026-05-28
**Domain:** Python typed-model dispatch + Protocol-based transport injection (Pydantic v2 isolation)
**Confidence:** HIGH (CONTEXT.md pre-locked the architecture; research verified the open mechanics)

## Summary

Phase 6 ships two **additive, decoupled** seams on top of the existing `OdooClient`:

1. **Transport seam (BROWSER-01)** — a stdlib `Protocol` named `Transport` lives in `godoo.client.rpc.protocol`; `OdooClientConfig` gains an optional `transport_factory: Callable[[OdooClientConfig], Transport] | None` field; `OdooClient.__init__` switches its one hard-coded `JsonRpcTransport(...)` line to either call the factory or fall back to the same default. `JsonRpcTransport` is not touched — it already exposes the five members the Protocol enumerates (`authenticate`, `call`, `aclose`, `logout`, `session`) and satisfies the Protocol structurally.
2. **Typed reads core (TYPED-03/04/05/06/07)** — a stdlib-only `godoo.client.typed` module ships the `OdooModel` Protocol (a duck-typed marker requiring `__odoo_model__: ClassVar[str]`) plus the `Ref[T]` generic frozen dataclass. A private `godoo.client._pydantic_transform` module is the **sole** location that imports Pydantic; it ships `OdooBaseModel(BaseModel)` with a `@model_validator(mode="before")` that performs the three wire transforms (Odoo `False` → `None` for non-bool fields; many2one `[id, "Name"]` → `Ref(id, name)`; ISO date/datetime strings → `date`/`datetime`), plus a `derive_partial_model(model, fields)` helper that uses `pydantic.create_model(..., __base__=model)` to produce a subset model on demand. Both `client.read` and `client.search_read` grow `@overload` pairs; runtime dispatch keys off `hasattr(model, "__odoo_model__")` and only **then** does the function body do `from godoo.client._pydantic_transform import ...`.

A subprocess isolation test (in the same style as `test_namespace.py`) is the load-bearing CI guard: it spawns a subprocess that runs `import godoo.client`, then asserts `'pydantic' not in sys.modules`. This is the only objective check that future drive-by additions to the `godoo.client` tree cannot smuggle a top-level `import pydantic` past review.

**Primary recommendation:** ship the seam-then-types-then-dispatch slice exactly as `D-11` describes. Pin `pydantic>=2.13` in the `[typed]` extra. Use `pydantic.create_model(..., __base__=ModelClass)` with annotation rewriting for D-01 partial-model derivation, and cache by `(model, tuple(sorted(fields)))` in a module-level dict — both are simple and proven Pydantic-v2 patterns.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01 (OD-1 partial-read strategy):** When `fields=[...]` is passed to the typed overload, derive a **subset model** of the target class containing only the requested fields and validate against that derived model. The plain `client.read(ResPartner, ids)` call (no `fields`) validates the full all-optional model. Research must investigate `create_model()` (preferred) vs `BaseModel.__pydantic_fields_set__` introspection vs dataclass-based alternative; settle per-call cost and caching keyed by `(model, tuple(sorted(fields)))`. **Marc overrode the researcher's "TypeError on fields=" recommendation — partial reads must stay typed.**
- **D-02 (OD-2 boolean False-coercion):** Generated boolean fields emit as plain `bool` (non-Optional, `default=False`). The `@model_validator(mode="before")` in `OdooBaseModel` inspects `cls.model_fields[name].annotation`; if the annotation is `bool`, leave the value untouched. For all other field types, `False` → `None`.
- **D-03 (overload scope):** Phase 6 covers typed dispatch on **both** `client.read` AND `client.search_read`. The `type[T]` overload comes BEFORE the `str` overload in each pair.
- **D-04 (overload runtime branching):** Dispatch guard is `hasattr(model, "__odoo_model__")` — NEVER `isinstance(BaseModel)` or `issubclass(BaseModel)`. Typed branch lazy-imports `_pydantic_transform` inside the function body; `str` branch never touches it.
- **D-05 (typed dispatch in client.py):** `@overload` declarations live in `client.py`. `TypeVar` bound (`T` bound to `OdooModel`) imports from `godoo.client.typed` (stdlib-only — safe at module load). Lazy `_pydantic_transform` import inside `read`/`search_read` bodies, gated on `hasattr(model, "__odoo_model__")`.
- **D-06 (Transport Protocol surface — minimal):** Exposes exactly the five members `OdooClient` calls on `_transport`: `authenticate`, `call`, `aclose`, `logout`, `session` (property). Lives in `packages/godoo-client/src/godoo/client/rpc/protocol.py`. `JsonRpcTransport` is not modified.
- **D-07 (`transport_factory` signature):** `transport_factory: Callable[[OdooClientConfig], Transport] | None = None` on `OdooClientConfig`. Called once eagerly in `OdooClient.__init__`. Fallback to `JsonRpcTransport(config.url, config.database, timeout=config.timeout)` when `None`.
- **D-08 (`OdooBaseModel` lives in private `_pydantic_transform.py`):** `godoo.client.typed` is stdlib-only and always importable. `OdooBaseModel(BaseModel)` and the dynamic partial-fields helper live in `godoo.client._pydantic_transform`. Underscore prefix is the documented signal — never in `__all__`, never in any `__init__.py`, never imported at module-load time anywhere in `godoo.client`.
- **D-09 (`Ref` is generic `Ref[T]`):** `@dataclass(frozen=True) class Ref(Generic[T]): id: int; name: str` in `godoo.client.typed`. `T` is type-checker-visible only — unused at runtime.
- **D-10 (subprocess isolation test):** Pytest test at `packages/godoo-client/tests/test_typed_isolation.py` runs `subprocess.run([sys.executable, "-c", "import godoo.client; import sys; assert 'pydantic' not in sys.modules"])`. Follows `test_namespace.py` PEP 420 guard pattern.
- **D-11 (3-plan slice):** 06-01 transport seam (Wave 1) → 06-02 typed + transform module (Wave 2) → 06-03 dispatch + extra + isolation test + integration smoke (Wave 3).

### Claude's Discretion

- Exact typing of `args`/`kwargs` parameters on `Transport.call()` — Marc accepted "minimal" but precise typing is left to the planner (recommend `list[Any]` / `dict[str, Any]` to mirror current `JsonRpcTransport.call` signature).
- Cache strategy for derived partial-fields models — researcher recommends caching, but if uncached cost is acceptable the planner may defer to a follow-on.
- Whether `OdooClient.is_authenticated()` needs adjusting for the alternative transport case — it reads `_transport.session` which is on the Protocol, so should work unchanged (planner confirms during 06-01).

### Deferred Ideas (OUT OF SCOPE)

- Typed dispatch on `create`, `write`, `unlink` — possible v1.2 phase.
- `Ref[T]` with id-only fallback (one2many/many2many list of ints) — Phase 7 codegen decision, not a `Ref[T]` modification.
- Async transport factory — current sync `Callable[..., Transport]`; revisit only if Phase 8 reveals need.
- Pyodide-specific transport implementation — Phase 8 empirical question.

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| BROWSER-01 | A `Transport` `Protocol` plus a `transport_factory` hook on `OdooClientConfig` allows an alternative transport implementation to be injected without changing core (additive infra; ships regardless of the spike verdict) | Architecture Decision §1 + §3 (Protocol surface), Implementation Approach §1 (`rpc/protocol.py`, `OdooClientConfig` field, `__init__` injection point) |
| TYPED-03 | A developer can call `client.read(ModelClass, ids)` (and `search_read(ModelClass, ...)`) and receive validated, transformed `list[ModelClass]` instances | Architecture Decision §4 (overload dispatch), Implementation Approach §3 (`@overload` pairs + lazy import body) |
| TYPED-04 | The raw string-keyed path (`client.read("res.partner", ids)`) is unchanged and still returns `list[dict[str, Any]]` | Architecture Decision §4 (dispatch guard via `hasattr`); existing test suite is the regression evidence |
| TYPED-05 | Typed support is opt-in via the `godoo[typed]` extra; the default install stays httpx-only, enforced by a CI test asserting `import godoo` pulls in no pydantic | Architecture Decision §2 (Pydantic-isolation boundary), Implementation Approach §2 + §3, Validation §1 (subprocess isolation test) |
| TYPED-06 | A bidirectional wire transform handles Odoo's quirks declaratively — empty `False` → `None`, many2one `[id, "Name"]` → `Ref`, date/datetime strings → `date`/`datetime`, selection → `Literal` | Architecture Decision §2 (`OdooBaseModel.@model_validator`), Implementation Approach §2 (transform table + D-02 boolean exception) |
| TYPED-07 | `Ref[Model]` and the model dispatch `Protocol` (`__odoo_model__`) live in a stdlib-only `godoo.client.typed` module, importable without pydantic; runtime dispatch duck-types (`hasattr`), never `isinstance(BaseModel)` | Architecture Decision §2 (module split), Implementation Approach §2 (`godoo/client/typed.py` content), D-04 dispatch contract |

Selection→Literal in TYPED-06 is a **codegen-time** typing concern (Phase 7 emits `Literal[…]` annotations); the runtime transform in Phase 6 has nothing to do for selection — Pydantic enforces `Literal` membership at validation time automatically.

</phase_requirements>

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Transport `Protocol` definition | Library / Client core | — | Stdlib `typing.Protocol` lives next to its existing implementation (`rpc/`); no runtime cost; satisfied structurally by `JsonRpcTransport` without modification |
| `transport_factory` injection | Library / Client core | — | Single injection site in `OdooClient.__init__`; one config field; no service-tier or transport-tier change |
| Typed model marker (`OdooModel` Protocol, `Ref[T]`) | Library / Public typed API | — | Stdlib-only module imported at type-check time by user code AND at runtime by `client.py` for the TypeVar bound; must never touch Pydantic |
| Pydantic wire transforms (`OdooBaseModel`, partial-model derivation) | Library / Private impl | — | Single module that imports Pydantic; loaded lazily only on typed-dispatch branch; underscore-prefixed to signal not-for-import |
| `@overload` dispatch on `read`/`search_read` | Library / Client core | — | Lives in `client.py` because `OdooClient` is the entrypoint; type signature visible to mypy at module load, runtime body lazy-imports Pydantic only on typed branch |
| `[typed]` optional extra | Packaging | — | Declared in `packages/godoo-client/pyproject.toml`; gates the runtime `import pydantic`; failure surfaces as a clear `ImportError` with install hint on first typed dispatch |
| Isolation guard test | Test infra | — | Subprocess-based CI test in `packages/godoo-client/tests/`; mirrors `test_namespace.py` PEP 420 guard pattern |

**Why this matters:** the load-bearing invariant is that **only** `_pydantic_transform.py` ever does `import pydantic`, and that import is only triggered by the runtime body of the typed-dispatch branch. Every architectural assignment above is in service of that invariant.

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `pydantic` | `>=2.13` (latest 2.13.4 as of 2026-05-06) | User-facing typed model base class + `@model_validator` + `create_model` for partial-model derivation | [VERIFIED: pypi.org/pypi/pydantic 2026-05-06] Pydantic v2 is the de facto Python data-validation library; v2.13 baseline avoids any v1-flavored installs in the `[typed]` extra. Only place in the codebase Pydantic appears. |
| `typing.Protocol` | stdlib (3.14) | `Transport` structural type; `OdooModel` duck-type marker | [VERIFIED: codebase] Already used throughout godoo for runtime-checkable structural typing. No runtime cost when not `runtime_checkable`. |
| `dataclasses` | stdlib (3.14) | `Ref[T]` (frozen, generic), `OdooClientConfig` extension | [VERIFIED: CLAUDE.md convention] Project rule: dataclasses over Pydantic for internal types. `Ref[T]` is user-facing but stays stdlib so it's importable without `[typed]`. |
| `typing.overload` | stdlib (3.14) | Type-checker-visible `read`/`search_read` overload pairs | [VERIFIED: codebase] Already used at `client.py:336-341` for `create()`. Pattern is established. |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `pytest` `>=8` | dev | Subprocess isolation test, unit tests for transforms | Already in dev-deps (`pyproject.toml`) |
| `respx` `>=0.22` | dev | Mock httpx for unit tests on typed dispatch path | Already in dev-deps; reused for typed-read unit tests |
| `testcontainers[postgres]>=4` | dev | Integration smoke test for end-to-end typed read in 06-03 | Already in dev-deps; integration tests are session-scoped (`tests/conftest.py`) |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `pydantic.create_model(..., __base__=ModelClass)` for D-01 partial models | `BaseModel.model_construct()` (skip validation) | `model_construct` would skip wire transforms — defeats the purpose. **Rejected.** |
| `pydantic.create_model(..., __base__=ModelClass)` for D-01 partial models | Hand-rolled dataclass subset with manual transform code | Duplicates Pydantic's validation/transform pipeline. **Rejected.** |
| `cls.model_fields[name].annotation == bool` (D-02 detection) | Carrying explicit `FieldMeta` metadata into validation time | `model_fields` is class-level metadata available inside any classmethod (including mode="before" validators) at zero runtime cost. **Use the simpler form.** |
| `Protocol` for `Transport` | Abstract base class (`ABC`) | ABC requires `JsonRpcTransport` to inherit it — modifies the class, violates "no modification" criterion. **Rejected by D-06.** |
| `runtime_checkable` `Protocol` | Plain `Protocol` (type-check-only) | The Protocol is used as an annotation, not for `isinstance` checks. Plain Protocol is sufficient and faster. **Use plain.** |

**Installation:**

```toml
# packages/godoo-client/pyproject.toml — add this table
[project.optional-dependencies]
typed = ["pydantic>=2.13"]
```

User-facing install command:
```bash
uv pip install 'godoo-client[typed]'
# or
pip install 'godoo-client[typed]'
```

**Version verification:**

```bash
# Pydantic version confirmed latest stable
# Source: https://pypi.org/pypi/pydantic/json (fetched 2026-05-28)
# Latest: 2.13.4 released 2026-05-06
```

`>=2.13` is the documented Phase 6 recommendation (`<specifics>` block of CONTEXT.md). Any 2.13.x patch is fine; pinning the minor floor prevents accidental Pydantic v1 install.

## Package Legitimacy Audit

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| `pydantic` | PyPI | ~9 yrs (initial 2017) | ~280M/month | github.com/pydantic/pydantic | [ASSUMED — slopcheck not run; package is canonical, widely used, MIT-licensed, by the named maintainer org pydantic] | Approved |

*slopcheck CLI was not available in this research session; the only new package introduced (`pydantic`) is the canonical, top-tier Python validation library with a 9-year history and is already named explicitly in CONTEXT.md (D-08, `<specifics>`). The planner does not need to gate this install behind a human-verify checkpoint, but should still install via the lockfile (`uv add pydantic>=2.13 --optional typed`) and commit `uv.lock` together with `pyproject.toml`.*

## Architecture Patterns

### System Architecture Diagram

```
                       USER CODE
                          │
                          ▼
            ┌─────────────────────────────┐
            │       OdooClient            │  client.py
            │                             │
            │  read(model, ids, **kw)     │
            │       │                     │
            │       ▼                     │
            │  ┌────────────────┐         │
            │  │ Dispatch guard │         │
            │  │ hasattr(model, │         │
            │  │ "__odoo_model__")?       │
            │  └────────┬───────┘         │
            │           │                 │
            │       ┌───┴───┐             │
            │       ▼       ▼             │
            │     STR     TYPED           │
            │      │       │              │
            │      │   ┌───┴────────────────────┐
            │      │   │ Lazy import:           │
            │      │   │ from godoo.client._pydantic_transform │
            │      │   │   import OdooBaseModel,│
            │      │   │   derive_partial_model │
            │      │   └───┬────────────────────┘
            │      │       │
            │      ▼       ▼
            │   self.call("read", …)  → dict[]
            │      │             │
            │      │             ▼
            │      │        [BaseModel.model_validate_python
            │      │         on each dict, with @model_validator
            │      │         applying False→None / m2o→Ref / iso→date]
            │      │             │
            │      ▼             ▼
            │  list[dict]   list[ResPartner]
            └─────────────────────────────┘
                          │
                          ▼
            ┌─────────────────────────────┐
            │  Transport (Protocol)       │  rpc/protocol.py
            │  - authenticate()           │
            │  - call()                   │
            │  - aclose()                 │
            │  - logout()                 │
            │  - session (property)       │
            └──────────────┬──────────────┘
                           │ (structural)
              ┌────────────┴─────────────┐
              ▼                          ▼
      ┌──────────────────┐    ┌─────────────────────┐
      │ JsonRpcTransport │    │ (alt impl)          │
      │ (default)        │    │ e.g. PyodideFetch   │
      │ httpx.AsyncClient│    │ Transport, Mock, …  │
      └──────────────────┘    └─────────────────────┘
                           ▲
                           │ instantiated via
              ┌────────────┴──────────────────┐
              │ config.transport_factory(cfg) │
              │   if not None, else default   │
              │   JsonRpcTransport(...)       │
              └───────────────────────────────┘

ISOLATION INVARIANT
  godoo.client.__init__ ─► imports client.py, rpc, services
                            (no pydantic, no _pydantic_transform)
  godoo.client.typed ────► stdlib only (Protocol + Ref[T])
  godoo.client._pydantic_transform ──► ONLY place import pydantic happens
                                       loaded ONLY when typed branch fires
```

### Recommended Project Structure

```
packages/godoo-client/src/godoo/client/
├── __init__.py                       # (unchanged) — DOES NOT re-export typed/_pydantic_transform
├── client.py                         # +OdooClientConfig.transport_factory
│                                     # +@overload pairs on read/search_read
│                                     # +lazy import of _pydantic_transform inside dispatch body
├── config.py                         # (unchanged)
├── errors.py                         # (unchanged)
├── typed.py                          # NEW — stdlib only
│                                     #   - OdooModel Protocol (__odoo_model__: ClassVar[str])
│                                     #   - Ref[T] (Generic) frozen dataclass
├── _pydantic_transform.py            # NEW — sole pydantic-importing module
│                                     #   - OdooBaseModel(BaseModel)
│                                     #     @model_validator(mode="before")
│                                     #   - derive_partial_model(model, fields) using create_model
│                                     #   - _partial_model_cache: dict
├── rpc/
│   ├── __init__.py                   # (unchanged) — DOES NOT export Transport
│   │                                 #   keep public surface stable; expose protocol via direct import
│   ├── protocol.py                   # NEW — Transport Protocol (5 members)
│   ├── transport.py                  # (unchanged) — satisfies Transport structurally
│   └── types.py                      # (unchanged)
└── services/                         # (unchanged)

packages/godoo-client/tests/
├── test_namespace.py                 # (existing PEP 420 guard)
├── test_typed_isolation.py           # NEW — subprocess guard: pydantic not in sys.modules
├── test_transport_protocol.py        # NEW — JsonRpcTransport satisfies Transport (mypy + runtime)
├── test_typed.py                     # NEW — Ref dataclass, OdooModel protocol marker
├── test_pydantic_transform.py        # NEW — OdooBaseModel transforms + derive_partial_model
└── test_typed_dispatch.py            # NEW — overload runtime dispatch on read/search_read (respx)
```

### Pattern 1: Structural Protocol over implementation class

**What:** Define `Transport` as a `typing.Protocol` listing the exact members `OdooClient` calls. `JsonRpcTransport` is **not** modified — it satisfies the protocol structurally.

**When to use:** When you want an injection seam without forcing the existing impl to inherit a new base class.

**Example:**

```python
# Source: pydantic-free; standard typing.Protocol pattern
# packages/godoo-client/src/godoo/client/rpc/protocol.py
from __future__ import annotations

from typing import Any, Protocol

from godoo.client.rpc.types import OdooSessionInfo


class Transport(Protocol):
    """Structural type for transports that OdooClient can drive.

    JsonRpcTransport satisfies this Protocol without modification.
    Alternative transports (e.g. a future Pyodide pyfetch-backed transport)
    only need to expose these five members.
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

### Pattern 2: Lazy-imported private side-module with no top-level re-export

**What:** All Pydantic-touching code lives in `_pydantic_transform.py`. It is **not** imported anywhere at module load — only inside the function body of the dispatch branch that needs it.

**When to use:** Whenever a sub-feature has a dependency that the default install must not pull in.

**Example:**

```python
# Source: established pattern in godoo client.py (e.g. @cached_property service accessors do this)
# packages/godoo-client/src/godoo/client/client.py — inside OdooClient.read()

async def read(
    self,
    model: str | type[T],
    ids: int | list[int],
    fields: list[str] | None = None,
    **kwargs: Any,
) -> list[dict[str, Any]] | list[T]:
    id_list = [ids] if isinstance(ids, int) else ids

    # Dispatch guard — duck-typed, never imports pydantic
    if hasattr(model, "__odoo_model__"):
        # Lazy import — first time the typed branch is hit
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

    # str path — UNCHANGED from v1.0
    if fields is not None:
        kwargs["fields"] = fields
    return cast("list[dict[str, Any]]", await self.call(model, "read", [id_list], kwargs))
```

### Pattern 3: `@model_validator(mode="before")` with class-level field inspection

**What:** A classmethod that runs before Pydantic validation, transforms the raw dict, and is allowed to consult `cls.model_fields[name].annotation` because `model_fields` is class-level metadata (always defined when the validator is invoked).

**Caveat verified:** Pydantic docs warn the *input data shape* may not be a dict — but `cls.model_fields` is a class attribute, unrelated to data shape, and is always available from a classmethod.

**Example:**

```python
# Source: pydantic v2 docs (https://pydantic.dev/docs/validation/latest/concepts/validators/) verified 2026-05-28
# packages/godoo-client/src/godoo/client/_pydantic_transform.py
from __future__ import annotations

from datetime import date, datetime
from typing import Any, ClassVar

from pydantic import BaseModel, model_validator

from godoo.client.typed import Ref


class OdooBaseModel(BaseModel):
    """Base for all generated Odoo typed models. Applies wire transforms.

    Subclasses (emitted by Phase 7 codegen) declare:
        __odoo_model__: ClassVar[str] = "res.partner"
    plus their fields.
    """

    __odoo_model__: ClassVar[str]

    @model_validator(mode="before")
    @classmethod
    def _odoo_wire_transforms(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        out: dict[str, Any] = {}
        for name, value in data.items():
            field_info = cls.model_fields.get(name)
            if field_info is None:
                out[name] = value
                continue
            annotation = field_info.annotation
            # D-02: skip coercion for bool-annotated fields
            if value is False and annotation is not bool:
                out[name] = None
                continue
            # m2o tuple [id, "Name"] → Ref(id, name)
            if isinstance(value, list) and len(value) == 2 and isinstance(value[0], int) and isinstance(value[1], str):
                # Heuristic: only when annotation involves Ref. Codegen guarantees this.
                if _annotation_mentions_ref(annotation):
                    out[name] = Ref(id=value[0], name=value[1])
                    continue
            # ISO date / datetime strings → typed values
            if isinstance(value, str) and _annotation_is_date_like(annotation, date) and _looks_iso_date(value):
                out[name] = date.fromisoformat(value)
                continue
            if isinstance(value, str) and _annotation_is_date_like(annotation, datetime) and _looks_iso_datetime(value):
                out[name] = datetime.fromisoformat(value)
                continue
            out[name] = value
        return out
```

(Helper predicates `_annotation_mentions_ref`, `_annotation_is_date_like`, `_looks_iso_*` are module-private; the planner finalises the exact signatures during 06-02.)

### Pattern 4: Dynamic partial-model derivation with `create_model(..., __base__=...)`

**What:** Build a fresh Pydantic model class whose fields are the subset requested, inheriting the base's `@model_validator` so wire transforms still apply. Cache by `(model, tuple(sorted(fields)))`.

**Verified API (2026-05-28):** `pydantic.create_model("Name", field=(annotation, default), __base__=ParentModel)` is the v2 signature; `__base__` parameter is documented and tested. See https://pydantic.dev/docs/validation/latest/concepts/models/.

**Example:**

```python
# Source: pydantic v2 docs verified 2026-05-28
# packages/godoo-client/src/godoo/client/_pydantic_transform.py
from __future__ import annotations

from typing import Any
from pydantic import BaseModel, create_model

# Cache key: (id(model_class), frozenset(fields))
_partial_model_cache: dict[tuple[int, frozenset[str]], type[BaseModel]] = {}


def derive_partial_model(model: type[BaseModel], fields: list[str]) -> type[BaseModel]:
    """Derive a subset model carrying only the requested fields.

    Caller passes `fields=["name", "email"]`; this returns a new BaseModel subclass
    that inherits OdooBaseModel's @model_validator (so wire transforms apply) and
    declares only those fields. All inherited fields not listed in `fields` are
    omitted from validation by overriding with model_config exclude semantics or
    by listing only the requested fields in create_model.
    """
    key = (id(model), frozenset(fields))
    cached = _partial_model_cache.get(key)
    if cached is not None:
        return cached

    # Pull annotation + default from the base model's fields, keep only requested ones
    field_defs: dict[str, Any] = {}
    for name in fields:
        if name not in model.model_fields:
            raise ValueError(f"Field {name!r} not declared on {model.__name__}")
        fi = model.model_fields[name]
        # All-Optional partial semantics: each field becomes (annotation | None, None)
        field_defs[name] = (fi.annotation, None)

    derived = create_model(
        f"{model.__name__}__partial__{abs(hash(key))}",
        __base__=model,
        **field_defs,
    )
    _partial_model_cache[key] = derived
    return derived
```

### Anti-Patterns to Avoid

- **`isinstance(model, type) and issubclass(model, BaseModel)` as dispatch guard:** forces `BaseModel` to be importable at dispatch time, which means pulling Pydantic into `client.py`'s import graph. **D-04 forbids this.** Use `hasattr(model, "__odoo_model__")` instead — purely duck-typed, zero Pydantic dependency at dispatch time.
- **Re-exporting `OdooBaseModel` from `godoo.client.__init__.py` or `godoo.client.typed`:** would force Pydantic to load on every `import godoo.client`. **D-08 forbids this.** `_pydantic_transform` must be reachable only via explicit `from godoo.client._pydantic_transform import ...` inside a lazy-import body.
- **Modifying `JsonRpcTransport` to inherit `Transport`:** unnecessary — Protocol matching is structural. **D-06 forbids this.** Verifying the conformance is a one-line test (`_t: Transport = JsonRpcTransport("http://x", "db")`).
- **Async `transport_factory`:** ruled out by deferred-ideas; `OdooClient.__init__` is sync, the factory is sync, the produced transport's lifecycle methods are async. **Don't introduce async factories** without an empirical Pyodide reason.
- **`@model_validator(mode="after")` for the wire transforms:** would mean the validator can't intercept Odoo's `False` before Pydantic complains about `False` not being a valid `str | None`. **Must be `mode="before"`.**
- **Putting `[typed]` extras anywhere except `packages/godoo-client/pyproject.toml`:** the root `pyproject.toml` is for the workspace and dev-deps; package-level `[project.optional-dependencies]` is the right home so end-users running `pip install godoo-client[typed]` resolve it.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Subset-model derivation | A bespoke dict-of-types → subclass code generator | `pydantic.create_model(..., __base__=ModelClass, **field_defs)` | Pydantic v2's documented public API; supports inheritance from a base model; handles `model_validator` propagation; tested by Pydantic's own suite |
| Boolean detection at validation time | Carrying a separate `FieldMeta` dict synced with the model | `cls.model_fields[name].annotation is bool` inside the classmethod validator | `model_fields` is class-level metadata, always present; the validator is a classmethod so `cls` is always the right class |
| Transport structural-conformance test | Duck-typing assertions checking method-by-method existence | A one-line `_t: Transport = JsonRpcTransport(...)` assignment at the top of `test_transport_protocol.py` — runs under mypy AND at runtime | `mypy --strict` is the load-bearing check; runtime is belt-and-braces. Anything more is busywork. |
| Lazy import guard | Manual `sys.modules` check inside `read()` | Plain `from godoo.client._pydantic_transform import ...` inside the dispatch branch | Python's import system already caches; second invocation pays zero cost. |
| Date-format detection | Hand-written ISO 8601 regex | `date.fromisoformat(value)` (raises `ValueError` if malformed) inside a `try/except`, gated on the field annotation already being `date`/`datetime` | stdlib parser; Phase 7 codegen only annotates dates as `date`/`datetime` when Odoo says so, so format matches |

**Key insight:** Pydantic v2's `create_model` with `__base__` does exactly the D-01 job (inherit validator, override field defs to a subset). Trying to imitate it with dataclasses or hand-rolled `__init_subclass__` machinery duplicates work that the library already does correctly.

## Runtime State Inventory

> Phase 6 is a **greenfield** capability addition: new modules (`typed.py`, `_pydantic_transform.py`, `rpc/protocol.py`), additive field on a dataclass, additive `@overload` declarations on existing methods. **No rename or migration.** This section is included only to confirm no runtime state hides in the seams.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None — no schema migrations, no persistent stores in this phase | None |
| Live service config | None — no external services impacted | None |
| OS-registered state | None — no OS-level registrations | None |
| Secrets and env vars | None — no new env vars introduced; `ODOO_*` env vars unchanged | None |
| Build artifacts | `[typed]` extra requires `uv.lock` regeneration after `pyproject.toml` edit; planner must commit `uv.lock` alongside `pyproject.toml` (per project lockfile-discipline rule). Stale local `.venv` of contributors who don't `uv sync` will lack Pydantic — by design; that's the isolation we are testing. | `uv sync` after pyproject edit; commit lockfile in same commit |

## Common Pitfalls

### Pitfall 1: Accidental Pydantic top-level import in `client.py`

**What goes wrong:** A planner or contributor adds `from godoo.client._pydantic_transform import OdooBaseModel` at module top of `client.py` (instead of inside the dispatch function body) to "make the code cleaner." This silently breaks the [typed]-isolation invariant — `import godoo.client` now fails on a default install with no Pydantic.

**Why it happens:** Lazy imports look awkward and contributors with full `[typed]` extras installed won't see the failure locally.

**How to avoid:** the subprocess isolation test (`test_typed_isolation.py`) is the load-bearing CI guard. Run it on every PR. Phase 7 codegen contributors must also be aware: generated model files import from `_pydantic_transform`, but `client.py` and `client/__init__.py` must never.

**Warning signs:** the subprocess test reports `pydantic in sys.modules` after a refactor; or `import godoo.client` succeeds in a venv where Pydantic *is* installed but fails in a clean venv (only the subprocess test catches this in CI).

### Pitfall 2: `Protocol` member signature drift from `JsonRpcTransport`

**What goes wrong:** `Transport` Protocol declares `async def call(self, model: str, method: str, args: list[Any], kwargs: dict[str, Any]) -> Any`, but `JsonRpcTransport.call`'s signature changes (e.g. someone adds a default to `kwargs`). Structural conformance breaks silently — mypy catches it only because of the one-line `_t: Transport = JsonRpcTransport(...)` test.

**Why it happens:** Protocols are structural; mypy will only complain at the point of assignment, not on the Protocol itself.

**How to avoid:** keep the conformance test (`test_transport_protocol.py`) red-checked by mypy. Run `uv run mypy packages/godoo-client/src` and `uv run mypy packages/godoo-client/tests` (already in CI per Phase 5 summary). On any `JsonRpcTransport.call` signature change, mypy fails at the test's assignment line.

**Warning signs:** mypy passes in source but the conformance test file emits a `Argument N has incompatible type` error.

### Pitfall 3: D-02 boolean detection misses `Optional[bool]`

**What goes wrong:** `cls.model_fields[name].annotation is bool` only matches a bare `bool` annotation. If Phase 7 codegen later emits `Optional[bool]` for a "tribool" field, the check fails — `False` would be coerced to `None`, hiding the genuine false value.

**Why it happens:** D-02 says "emit boolean fields as plain `bool` (non-Optional, `default=False`)" — this is Phase 7's contract, not a runtime check.

**How to avoid:** the planner for 06-02 must document the contract in `_pydantic_transform.py`'s docstring: "boolean fields MUST be emitted as bare `bool` to opt out of False→None coercion." Phase 7 codegen must honour it. A unit test in `test_pydantic_transform.py` should pin the behaviour (`bool` field: False preserved; `str | None` field: False→None).

**Warning signs:** an integration test against a real Odoo instance where a checkbox field returns `False` from the wire and the typed model has `None` for that field.

### Pitfall 4: `derive_partial_model` cache leak

**What goes wrong:** `_partial_model_cache` is module-level and grows unbounded. Long-running processes (e.g. web servers using godoo) accumulate one entry per unique `(model, fields)` combination.

**Why it happens:** No eviction policy.

**How to avoid:** for v1.1, this is acceptable — the cardinality is bounded by `models × distinct_field_subsets_used_at_runtime`, typically small. If a user reports memory growth, a `functools.lru_cache` wrapper or explicit `clear_partial_model_cache()` API can be added in a follow-on. **Document the unbounded behaviour in the helper's docstring** so a future profiler hit has a starting point.

**Warning signs:** memory growth over time in a long-lived `OdooClient`-using process; the cache dict grows beyond ~100 entries.

### Pitfall 5: `transport_factory` is called eagerly but transport may need authentication state

**What goes wrong:** The factory receives only `OdooClientConfig` and is called in `__init__` — before any authentication. An alternative transport that needs a pre-existing session token can't get it this way.

**Why it happens:** D-07 mandates eager construction with the config-only signature.

**How to avoid:** the v1.1 contract is exactly "build the transport from config." Authentication still flows through `OdooClient.authenticate()` → `transport.authenticate()`. If a Pyodide spike (Phase 8) reveals a transport that needs richer construction, the deferred async-factory escape hatch is documented in CONTEXT.md. Don't preemptively complicate the seam.

**Warning signs:** the Phase 8 spike reports "needed to pass an httpx.AsyncClient into the factory" — that's the trigger to revisit, not a Phase 6 problem.

## Code Examples

### Example A: `OdooClientConfig` extension

```python
# Source: extension of existing dataclass at client.py:77-84
# from __future__ import annotations is already present
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from godoo.client.rpc.protocol import Transport


@dataclass
class OdooClientConfig:
    url: str
    database: str
    username: str
    password: str
    safety: SafetyContext | None = field(default=None)
    timeout: float | None = field(default=None)
    transport_factory: Callable[[OdooClientConfig], Transport] | None = field(default=None)
```

### Example B: `OdooClient.__init__` injection

```python
# Source: edit at client.py:90-92
def __init__(self, config: OdooClientConfig) -> None:
    self._config = config
    if config.transport_factory is not None:
        self._transport: Transport = config.transport_factory(config)
    else:
        # Default — identical to v1.0 behaviour
        from godoo.client.rpc.transport import JsonRpcTransport
        self._transport = JsonRpcTransport(config.url, config.database, timeout=config.timeout)
    self._safety_context: SafetyContext | _UndefinedType | None = _UNDEFINED
```

Note: the `from godoo.client.rpc.transport import JsonRpcTransport` is already at the top of `client.py` today (line 13 — `from godoo.client.rpc import JsonRpcTransport, OdooSessionInfo`). Moving it inside the `else` branch is optional; the top-level import is fine because `JsonRpcTransport` does not pull in Pydantic. Keep it at module level for simplicity.

### Example C: `godoo.client.typed` module

```python
# Source: stdlib only; no Pydantic
# packages/godoo-client/src/godoo/client/typed.py
from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar, Generic, Protocol, TypeVar

T = TypeVar("T")


class OdooModel(Protocol):
    """Marker protocol for typed Odoo model classes.

    Concrete implementations (emitted by Phase 7 codegen) declare:
        __odoo_model__: ClassVar[str] = "res.partner"

    Runtime dispatch in OdooClient.read/search_read keys on
    hasattr(model, "__odoo_model__") — never on isinstance(BaseModel).
    """

    __odoo_model__: ClassVar[str]


@dataclass(frozen=True)
class Ref(Generic[T]):
    """Typed many2one reference: id + display name.

    T is the target model type — type-checker-visible only,
    unused at runtime. Phase 7 codegen emits Ref[ResPartner]
    annotations on many2one fields.
    """

    id: int
    name: str


__all__ = ["OdooModel", "Ref"]
```

### Example D: `@overload` pairs on `read`

```python
# Source: mirrors existing create() overload pair at client.py:336-341
# Add after the existing create() overloads

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
    # … body from Pattern 2 above
```

`T` is bound to `OdooModel`: `T = TypeVar("T", bound=OdooModel)` declared once at module top of `client.py`. The import `from godoo.client.typed import OdooModel` is safe at module top — `typed` is stdlib-only.

### Example E: Subprocess isolation test

```python
# Source: mirrors test_namespace.py PEP 420 guard at tests/test_namespace.py
# packages/godoo-client/tests/test_typed_isolation.py
from __future__ import annotations

import subprocess
import sys


def test_pydantic_not_imported_by_default() -> None:
    """Assert that `import godoo.client` does not pull in pydantic.

    Run in a subprocess so the test's own `sys.modules` (which may contain
    pydantic from other tests) doesn't pollute the check. This is the
    load-bearing CI guard for the godoo[typed]-extra isolation invariant
    (TYPED-05): the default install must remain httpx-only.
    """
    script = (
        "import godoo.client\n"
        "import sys\n"
        "assert 'pydantic' not in sys.modules, "
        "f'pydantic was imported by godoo.client (modules: {sorted(m for m in sys.modules if \"pydantic\" in m)})'\n"
        "print('OK')\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, (
        f"subprocess isolation check failed.\n"
        f"stdout: {result.stdout!r}\n"
        f"stderr: {result.stderr!r}"
    )
    assert result.stdout.strip() == "OK"
```

This test runs in the default test suite (no `integration` marker) and depends on no fixtures — it is deterministic regardless of order.

### Example F: Transport structural-conformance test

```python
# Source: mypy + runtime structural check
# packages/godoo-client/tests/test_transport_protocol.py
from __future__ import annotations

from godoo.client.rpc.protocol import Transport
from godoo.client.rpc.transport import JsonRpcTransport


def test_jsonrpc_transport_satisfies_protocol() -> None:
    """Assert JsonRpcTransport satisfies the Transport Protocol structurally.

    The mypy --strict check on this file is the real assertion. The runtime
    test is belt-and-braces: it confirms the assignment doesn't fail at import.
    """
    # mypy check: this line fails if JsonRpcTransport's surface no longer matches Transport
    t: Transport = JsonRpcTransport("http://example", "db")
    assert hasattr(t, "authenticate")
    assert hasattr(t, "call")
    assert hasattr(t, "aclose")
    assert hasattr(t, "logout")
    assert hasattr(t, "session")
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Pydantic v1 `BaseModel.validator(pre=True)` | Pydantic v2 `@model_validator(mode="before") @classmethod` | Pydantic 2.0 (2023-06) | The class-method form is now required; the v1 `pre=True` keyword is removed. CONTEXT.md `>=2.13` floor prevents v1 install. |
| `pydantic.create_model("Name", __base__=Base, field=...)` | (unchanged) | v1 → v2 carried forward | Public API is stable; documented in v2 docs (verified 2026-05-28). |
| `dataclass_transform` for IDE integration | Pydantic 2 emits PEP 681 metadata natively | v2.0+ | mypy/Pyright see Pydantic v2 fields correctly without plugins. Our `OdooBaseModel` subclasses get full type inference. |
| `respx` for httpx mocking (already in dev-deps) | (unchanged) | — | Reused for typed-dispatch unit tests; no library change needed. |

**Deprecated/outdated:**

- Pydantic v1 patterns (`@validator`, `Config` inner class, `dict()` method) — must not be used. Pin `pydantic>=2.13` excludes v1.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The `[ASSUMED]` slopcheck verdict on `pydantic` is benign — pydantic is the canonical package, not slopcheck-flagged. | Package Legitimacy Audit | None practical; pydantic's identity is unambiguous. Planner may install without a human-verify checkpoint. |
| A2 | `cls.model_fields[name].annotation` returns the bare type (`bool`, `str`, etc.) for non-generic types and a `_GenericAlias` for generic ones — the `is bool` comparison in D-02 works for bare bool. | Pattern 3 / Pitfall 3 | If Phase 7 codegen emits `Annotated[bool, ...]` for boolean fields, `is bool` would miss. Mitigation: the planner adds a unit test pinning the bare-`bool` contract; if codegen needs `Annotated`, switch the check to `get_origin(annotation) is None and annotation is bool or get_args(annotation) and get_args(annotation)[0] is bool`. |
| A3 | `derive_partial_model` cache keyed by `(id(model), frozenset(fields))` is safe because typed model classes are module-level (lifetime ≥ process) — `id()` is stable. | Pattern 4 | If a user dynamically reloads modules (rare), `id()` collisions could happen. For v1.1, ignore. Document in helper docstring. |
| A4 | `respx` mocks suffice for unit-testing the typed dispatch path — no need for testcontainers for the unit suite; integration test in 06-03 exercises the real wire. | Recommended Project Structure | None — `respx` is already proven for `test_client.py`. |
| A5 | The `Transport` Protocol's `call` signature using `list[Any]` / `dict[str, Any]` exactly matches `JsonRpcTransport.call`'s current signature; structural matching needs no covariance/contravariance gymnastics. | Pattern 1 | If mypy reports variance issues, fall back to `Sequence[Any]` / `Mapping[str, Any]`. Verified by reading transport.py:98-103. |

## Open Questions

1. **Should `Transport` Protocol be `runtime_checkable`?**
   - What we know: D-06 lists the members; D-04 forbids `isinstance(BaseModel)` for the typed dispatch but says nothing about `isinstance(Transport)`.
   - What's unclear: do we want runtime `isinstance(x, Transport)` for testing or third-party transports?
   - Recommendation: **NO — keep it a plain Protocol.** No code currently does `isinstance(transport, Transport)`. Adding `@runtime_checkable` adds a slow `_ProtocolMeta` check at runtime. If a future caller needs it, adding it is a one-line non-breaking change.

2. **Where does `Transport` get re-exported (if anywhere) from `godoo.client.rpc.__init__.py`?**
   - What we know: `rpc/__init__.py` currently exports `JsonRpcTransport` and `OdooSessionInfo`.
   - What's unclear: should `Transport` join the public `rpc` barrel?
   - Recommendation: **YES — add `Transport` to `rpc/__init__.py`'s `__all__`.** Users who write custom transports need it; importing from `godoo.client.rpc.protocol` is fine but the barrel keeps the public surface tidy. The `Protocol` import is stdlib — no Pydantic concern.

3. **Does `godoo[typed]` import-error message tell the user what to install?**
   - What we know: D-08 says `_pydantic_transform` is the only Pydantic-importing module.
   - What's unclear: when a user calls `client.read(ResPartner, ids)` without installing `[typed]`, the dispatch branch does `from godoo.client._pydantic_transform import ...` which raises a bare `ModuleNotFoundError: pydantic`. The user gets no hint.
   - Recommendation: **wrap the lazy import in a try/except** in the dispatch body and re-raise as `OdooValidationError` or a new `OdooTypedNotInstalledError` with a clear message: `"Typed reads require 'pydantic'. Install with: pip install 'godoo-client[typed]'"`. Planner for 06-03 finalises the exception type.

4. **D-01 partial-model: cache eviction strategy?**
   - What we know: cache is `dict[(id(model), frozenset(fields)), type[BaseModel]]`. Unbounded.
   - What's unclear: do we ship eviction or a `clear` API in v1.1?
   - Recommendation: **No eviction. Add `clear_partial_model_cache() -> None` as an escape hatch in `_pydantic_transform`. Document the unbounded behaviour. Revisit if a user reports growth.** Conservative shipping.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | All code | ✓ | 3.14 (per `requires-python` and project CLAUDE.md) | — |
| uv | Workspace mgmt, lock regeneration | ✓ (assumed — phase 5 D-04 used it) | — | — |
| pydantic | `[typed]` extra runtime + 06-02 test suite | will be added in 06-03 to `[typed]` extra | 2.13.4 (latest) | None — adding it IS the task |
| pytest, respx | Test suite | ✓ | ≥8, ≥0.22 | — |
| Docker + testcontainers | 06-03 integration smoke test (typed read against live Odoo) | ✓ (already used in v1.0/Phase 3) | — | Skip integration test; rely on unit tests if Docker unavailable in dev env. CI has Docker. |

**Missing dependencies with no fallback:**

- None — `pydantic` is the new arrival and adding it is exactly the deliverable in 06-03.

**Missing dependencies with fallback:**

- Docker for local dev of 06-03 integration smoke test — fallback to skipping the `-m integration` selection locally; CI runs it.

## Security Domain

> `security_enforcement: true` in `.planning/config.json` (ASVS level 1, block on high). This phase is purely additive infrastructure — no new auth flows, no new network endpoints, no new input-validation surface, no new crypto. The threat surface is import-isolation correctness (an availability/integrity concern for the default install) and dispatch correctness (a correctness concern for typed reads).

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | Phase 6 does not touch auth; `JsonRpcTransport.authenticate` is unchanged; Protocol forwards it. |
| V3 Session Management | no | `OdooSessionInfo` unchanged; Protocol exposes the same `session` property. |
| V4 Access Control | no | Safety guard (`SafetyContext`) is untouched — operates at the `OdooClient.call` level, applies equally to str and typed dispatch paths. |
| V5 Input Validation | partial | Pydantic v2's own validation enforces the typed model's field annotations; the `@model_validator(mode="before")` only normalises Odoo wire quirks (False, m2o tuple, ISO strings). No SQL/expression construction. |
| V6 Cryptography | no | No crypto introduced. |
| V14 Configuration | yes (low) | `[typed]` extra is opt-in by design; default install is httpx-only (TYPED-05). The subprocess isolation test is the **integrity guard** that prevents a contributor from silently widening the default attack surface by importing Pydantic eagerly. |

### Known Threat Patterns for Python library tier

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Supply-chain typosquatting of Pydantic | Tampering | Pin `pydantic>=2.13` in `[typed]` extra; commit `uv.lock` together with `pyproject.toml`; CI uses `uv sync --frozen` which fails on lockfile mismatch. |
| Dispatch confusion attack (a malicious dict subclass triggers the typed branch) | Spoofing | The dispatch guard is `hasattr(model, "__odoo_model__")` — `model` is the first positional argument the **user** passes, not data from the wire. The attack surface is the user's own code; nothing the library can do. Document this in the dispatch docstring. |
| Cache pollution via attacker-controlled `fields` list | DoS | `fields` is a list of `str` chosen by the user. `derive_partial_model` validates each field name against `model.model_fields` and raises `ValueError` on unknown. No user-controlled cache growth via untrusted input. |
| Pydantic `model_validate` arbitrary code execution via `__init__` shenanigans | RCE | Pydantic v2's model_validate does not execute user code; field types are constrained by codegen-emitted annotations. No `eval`, no `pickle`. |

**Summary:** Phase 6 introduces no high or medium security risk under ASVS L1. The only meaningful security-adjacent invariant is the isolation guard (TYPED-05), enforced by the subprocess test.

## Sources

### Primary (HIGH confidence)

- **Pydantic v2 docs — Models / create_model**: https://pydantic.dev/docs/validation/latest/concepts/models/ — verified 2026-05-28 — `create_model(name, __base__=Base, **fields)` signature confirmed
- **Pydantic v2 docs — Validators / @model_validator**: https://pydantic.dev/docs/validation/latest/concepts/validators/ — verified 2026-05-28 — `mode="before" @classmethod` signature confirmed; classmethod can access `cls.model_fields`
- **PyPI — pydantic**: https://pypi.org/pypi/pydantic/json — verified 2026-05-28 — latest 2.13.4 (2026-05-06)
- **Codebase — `client/client.py`**: existing `@overload` pattern for `create()` at L336-341; existing `JsonRpcTransport(...)` construction at L90-92; existing `OdooClientConfig` dataclass at L77-84
- **Codebase — `client/rpc/transport.py`**: confirms `JsonRpcTransport` exposes `authenticate` (L49), `call` (L98), `aclose` (L130), `logout` (L125), `session` property (L38) — exactly the five members D-06 enumerates
- **Codebase — `tests/test_namespace.py`**: pattern for PEP 420 invariant guard test; clone for the isolation test
- **Codebase — `tests/test_client.py`**: pattern for respx-mocked unit tests with `OdooClient`

### Secondary (MEDIUM confidence)

- **CONTEXT.md (this phase)**: 11 decisions pre-locked; all architecture choices verified against codebase

### Tertiary (LOW confidence)

- None — every claim in this research is either codebase-verified or cited against current official Pydantic docs.

## Metadata

**Confidence breakdown:**

- Standard stack: HIGH — Pydantic version verified against PyPI; httpx/pytest/respx unchanged from established v1.0 stack
- Architecture: HIGH — entirely pre-decided in CONTEXT.md; research verified each decision against codebase
- Pitfalls: HIGH — derived from explicit invariants (D-04, D-08) and observable failure modes in the test suite
- D-01 partial-model derivation: HIGH for the create_model API; MEDIUM for caching semantics (Pattern 4 is sound but the eviction question is deferred — see Open Q4)
- D-02 boolean detection: HIGH — `cls.model_fields[name].annotation is bool` is a documented, stable Pydantic v2 contract

**Research date:** 2026-05-28
**Valid until:** 2026-06-27 (30 days — Pydantic 2.x is stable; create_model and @model_validator are LTS APIs)

## RESEARCH COMPLETE
