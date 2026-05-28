# Phase 6: Transport Seam & Typed Models Core - Context

**Gathered:** 2026-05-28
**Status:** Ready for planning

<domain>
## Phase Boundary

Add a transport-injection seam on `OdooClientConfig` (BROWSER-01) and build the
stdlib-only `godoo.client.typed` module plus a private `_pydantic_transform`
module that owns all Pydantic usage. Implement wire transforms (False→None for
non-bool, m2o `[id, "Name"]`→`Ref(id, name)`, date/datetime strings→typed values).
Add `@overload` dispatch on `client.read` and `client.search_read` so that
`client.read(ResPartner, ids)` returns `list[ResPartner]` while
`client.read("res.partner", ids)` keeps returning `list[dict[str, Any]]`
unchanged. Enforce `godoo[typed]` extra: a default install with no Pydantic
installed must complete `import godoo.client` without `ImportError`, and no
Pydantic import occurs at module-load time anywhere in `godoo.client`.

**In scope:** Transport Protocol, `transport_factory` config field, `Transport`
structural conformance for `JsonRpcTransport`, `godoo.client.typed`
(`OdooModel` Protocol, `Ref[T]` dataclass — both stdlib-only),
`godoo.client._pydantic_transform` (`OdooBaseModel` + `@model_validator` wire
transforms + dynamic partial-fields model derivation), `@overload` dispatch on
both `read` and `search_read`, `[typed]` optional extra in
`packages/godoo-client/pyproject.toml`, subprocess-based isolation test.

**Out of scope:** Pydantic CLI generator (Phase 7); Pyodide browser execution
(Phase 8 — only the seam ships here); typed dispatch on any other CRUD method
(create/write/unlink/search); any code-generation tooling.

</domain>

<decisions>
## Implementation Decisions

### Open Decisions Resolved

- **D-01 (OD-1 partial-read strategy):** When the caller passes `fields=[...]`
  to the typed overload, the implementation derives a **subset model** of the
  target class containing only the requested fields and validates against that
  derived model. Preserves Odoo's partial-fetch semantics AND typed return.
  The plain `client.read(ResPartner, ids)` call (no `fields`) validates the
  full all-optional model. Research needed: confirm Pydantic
  `create_model()` is the right primitive (vs dataclass-based alternative),
  benchmark per-call subset-model creation cost, decide on a cache keyed by
  `(model, tuple(sorted(fields)))`. **Override of research recommendation —
  Marc rejected "fields=on type[T] is a TypeError" because partial reads are
  a real Odoo idiom that should stay typed.**

- **D-02 (OD-2 boolean False-coercion):** Generated boolean fields emit as
  plain `bool` (non-Optional, `default=False`). The `@model_validator(mode=
  "before")` in `OdooBaseModel` inspects `model_fields[name].annotation`; if
  the annotation is `bool`, leave the value untouched (so Odoo's real `False`
  is preserved). For all other field types, `False` is coerced to `None`.
  Decidable at validation time without a runtime FieldMeta lookup.

### Read/Search-Read Dispatch

- **D-03 (overload scope):** Phase 6 covers typed dispatch on **both**
  `client.read` AND `client.search_read`. Phase 7 codegen will consume both;
  shipping only one now would force a follow-up in Phase 7. The `type[T]`
  overload must come BEFORE the `str` overload in each pair to prevent mypy
  overlap errors (research P6 sub-issue a).

- **D-04 (overload runtime branching):** Dispatch guard is
  `hasattr(model, "__odoo_model__")` — NEVER `isinstance(BaseModel)` or
  `issubclass(BaseModel)`. This is what lets the dispatch run before
  `_pydantic_transform` is imported. The typed branch lazy-imports
  `_pydantic_transform` inside the function body; the `str` branch never
  touches it.

- **D-05 (typed dispatch in client.py):** The `@overload` declarations live in
  `client.py`. The `TypeVar` bound (`T` bound to `OdooModel`) imports
  `OdooModel` from `godoo.client.typed` (stdlib-only — safe at module load).
  The lazy `_pydantic_transform` import happens inside `read`/`search_read`
  bodies, gated on the `hasattr(model, "__odoo_model__")` branch.

### Transport Seam

- **D-06 (Transport Protocol surface — minimal):** `Transport` Protocol
  exposes exactly what `OdooClient` calls on `_transport`:
  - `authenticate(username: str, password: str) -> OdooSessionInfo`
  - `call(model: str, method: str, args: list, kwargs: dict) -> Any`
  - `aclose() -> None`
  - `logout() -> None`
  - `session: OdooSessionInfo | None` (property)

  Lives in `packages/godoo-client/src/godoo/client/rpc/protocol.py`. No
  modification to `JsonRpcTransport` — it satisfies the Protocol structurally.

- **D-07 (`transport_factory` signature):**
  `transport_factory: Callable[[OdooClientConfig], Transport] | None = None`
  on `OdooClientConfig`. Called once eagerly in `OdooClient.__init__` to
  replace the current hard-coded `JsonRpcTransport(...)` construction. When
  `None`, fall back to `JsonRpcTransport(config.url, config.database,
  timeout=config.timeout)`. Factory receives the full config so the caller
  doesn't duplicate values.

### Module Layout & Isolation

- **D-08 (`OdooBaseModel` lives in private `_pydantic_transform.py`):**
  `godoo.client.typed` (Protocol + `Ref[T]` dataclass) is stdlib-only,
  **always importable**, never imports Pydantic. `OdooBaseModel(BaseModel)`
  with the `@model_validator` and dynamic partial-fields helper lives in
  `godoo.client._pydantic_transform`. Generated files in Phase 7 will
  `from godoo.client._pydantic_transform import OdooBaseModel`. The
  underscore prefix is the documented signal that it's an internal
  implementation contract — not user-facing API. Never in `__all__`, never
  in any `__init__.py`, never imported at module-load time anywhere in
  `godoo.client`.

- **D-09 (`Ref` is generic `Ref[T]`):** `@dataclass(frozen=True)
  class Ref(Generic[T]): id: int; name: str` in `godoo.client.typed`. `T` is
  type-checker-visible only — unused at runtime. Phase 7 codegen emits
  `Ref[ResPartner]` annotations so mypy sees the relational type. Matches
  REQUIREMENTS.md TYPED-07 ("`Ref[Model]`").

- **D-10 (subprocess isolation test):** A pytest test in
  `packages/godoo-client/tests/test_typed_isolation.py` runs
  `subprocess.run([sys.executable, "-c", "import godoo.client; import sys;
  assert 'pydantic' not in sys.modules"])` and asserts a clean exit. Lives
  in the normal test suite, runs deterministically regardless of fixture
  order. Follows the pattern of `test_namespace.py` PEP 420 guard.

### Plan Slicing

- **D-11 (3-plan slice):**
  - **06-01** — Transport seam: `rpc/protocol.py` Protocol, `transport_factory`
    field on `OdooClientConfig`, wire factory into `OdooClient.__init__`,
    structural-conformance test verifying `JsonRpcTransport` satisfies
    `Transport` without modification.
  - **06-02** — `godoo.client.typed` module (`OdooModel` Protocol, `Ref[T]`
    dataclass) + `godoo.client._pydantic_transform` (`OdooBaseModel` with
    `@model_validator(mode="before")` doing False→None / m2o→Ref /
    date-string→datetime transforms + dynamic partial-fields model derivation
    helper). Unit tests for each transform.
  - **06-03** — `@overload` pairs on `read` and `search_read`, runtime
    dispatch with lazy `_pydantic_transform` import, `[typed]` optional
    extra in `packages/godoo-client/pyproject.toml` (`pydantic>=2.13`),
    subprocess isolation test, end-to-end smoke test (integration test
    against testcontainers exercising the typed path).
  - Wave 1: 06-01. Wave 2: 06-02 (depends on 06-01 only for type imports).
    Wave 3: 06-03 (depends on 06-02).

### Claude's Discretion

- Exact field names in the `Transport` Protocol — Marc accepted "minimal" but
  the precise typing of `args`/`kwargs` parameters on `call()` is left to the
  planner (likely `list[Any]` / `dict[str, Any]` matching current
  `JsonRpcTransport.call` signature at `client/rpc/transport.py`).
- Cache strategy for derived partial-fields models — researcher recommends, but
  if uncached cost is acceptable (likely is), the planner can defer caching to
  a follow-on.
- Whether `OdooClient.is_authenticated()` needs adjusting for the alternative
  transport case (it reads `_transport.session`, which is on the Protocol, so
  should be fine without changes — planner confirms).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Roadmap & Requirements

- `.planning/ROADMAP.md` §"Phase 6: Transport Seam & Typed Models Core" —
  goal, success criteria, requirement IDs.
- `.planning/REQUIREMENTS.md` — full text of BROWSER-01, TYPED-03, TYPED-04,
  TYPED-05, TYPED-06, TYPED-07.
- `.planning/PROJECT.md` — `godoo.*` namespace immutability invariant,
  dataclasses-not-Pydantic convention, httpx-as-sole-runtime-dep constraint.
- `.planning/STATE.md` — current open-decisions list (OD-1, OD-2, OD-3) and
  v1.1 phase order.

### Research

- `.planning/research/SUMMARY.md` — Phase 6 build order (transport seam +
  typed core as Steps 2+3), import-isolation invariants, dispatch guard
  contract (`hasattr(model, "__odoo_model__")`).
- Researcher MUST produce/update a research note on Pydantic dynamic-model
  creation (`create_model()` / `BaseModel` introspection alternatives /
  dataclass-based fallback) for D-01 partial-fields derivation strategy
  before 06-02 is planned.

### Current Code (read before modifying)

- `packages/godoo-client/src/godoo/client/client.py` — `OdooClient`,
  `OdooClientConfig`, `read` (L182), `search_read` (L194), existing `create`
  `@overload` pattern (L336–341), hard-coded `JsonRpcTransport(...)`
  construction in `__init__` (L91–92), `is_authenticated()`.
- `packages/godoo-client/src/godoo/client/rpc/transport.py` —
  `JsonRpcTransport` public surface (`authenticate`, `call_rpc`, `call`,
  `logout`, `aclose`, `session`, `is_authenticated`).
- `packages/godoo-client/src/godoo/client/rpc/types.py` —
  `OdooSessionInfo(uid, session_id, db)`.
- `packages/godoo-client/src/godoo/__init__.py` — current public exports.
- `packages/godoo-client/src/godoo/client/__init__.py` — current
  `godoo.client` namespace exports.
- `packages/godoo-client/pyproject.toml` — current dependencies
  (`httpx>=0.27` only), no optional extras yet.
- `packages/godoo-client/tests/test_namespace.py` — precedent for invariant
  guard tests (PEP 420 namespace check) — pattern to follow for isolation
  test.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- **`create()` `@overload` pair** at `client/client.py:336–341` — the
  precedent for overloading return type by input shape. Mirror this style
  for `read`/`search_read`.
- **`JsonRpcTransport`** at `client/rpc/transport.py:24` — already exposes
  all five methods the minimal `Transport` Protocol needs. No modification
  required; structural typing makes it conform automatically.
- **`OdooSessionInfo`** at `client/rpc/types.py:8` — already the return
  type of `authenticate`; reuse on the Protocol signature.
- **PEP 420 guard test** at `tests/test_namespace.py` — the pattern for
  invariant guards; clone its structure for the isolation test.

### Established Patterns

- `from __future__ import annotations` first line in every new file.
- `TYPE_CHECKING` for `OdooClient` imports in services — but the new
  `Transport` Protocol and `OdooModel` Protocol live OUTSIDE any service,
  in their own modules. They get TYPE_CHECKING treatment only for the
  reverse direction (when client.py annotates with them).
- Lazy imports inside `@cached_property` bodies — same pattern applies to
  the lazy `_pydantic_transform` import inside `read`/`search_read`.
- Dataclasses (not Pydantic) for core types — `Ref`, `OdooClientConfig`,
  `OdooSessionInfo` are all `@dataclass`. `OdooBaseModel` is the ONE
  deliberate exception, isolated behind `[typed]` extra.

### Integration Points

- **`OdooClient.__init__`** at `client/client.py:91–92` — single hard-coded
  `JsonRpcTransport(...)` construction. Replace with
  `config.transport_factory(config) if config.transport_factory else
  JsonRpcTransport(config.url, config.database, timeout=config.timeout)`.
  This is the ONE injection site.
- **`OdooClient.read` and `.search_read`** — add `@overload` pairs; runtime
  body grows a single dispatch branch.
- **`OdooClientConfig`** dataclass at `client/client.py:78–84` — add
  `transport_factory: Callable[[OdooClientConfig], Transport] | None = None`
  field (with `default=None`). Forward-referenced `Transport` is fine under
  `from __future__ import annotations`.
- **`packages/godoo-client/pyproject.toml`** — add
  `[project.optional-dependencies]` table with `typed = ["pydantic>=2.13"]`.

</code_context>

<specifics>
## Specific Ideas

- **D-01 partial-fields derived-model strategy (Marc's override of research):**
  Research recommended "type[T] overload doesn't accept fields kwarg, raise
  TypeError." Marc rejected: partial reads ARE a normal Odoo idiom and should
  stay typed. So the typed dispatch path, when called with `fields=[...]`,
  produces a dynamically-derived subset model of the target class and
  validates against that. Researcher must investigate Pydantic
  `create_model()` (preferred), `BaseModel.__pydantic_fields_set__`
  introspection, or a dataclass-based alternative — and report feasibility
  + per-call cost + caching strategy.
- **Generated model files (Phase 7 forward look):** each will inherit
  `OdooBaseModel` from `godoo.client._pydantic_transform` and carry
  `__odoo_model__: ClassVar[str]` (e.g. `"res.partner"`). Phase 7 codegen
  consumes the contract defined in Phase 6.
- **`pydantic>=2.13` pin** (not `>=2.0`) — research recommendation to prevent
  Pydantic v1 installs in the `[typed]` extra. Plan 06-03 must encode this.

</specifics>

<deferred>
## Deferred Ideas

- **Typed dispatch on `create`, `write`, `unlink`** — not in Phase 6 scope.
  Could be a v1.2 phase if Phase 7 codegen exposes the pattern usefully.
- **`Ref[T]` with id-only fallback** — currently Odoo m2o always returns
  `[id, "Name"]` on a normal read, so `Ref.name` is always populated. If
  Phase 7 codegen ever needs to handle a one2many/many2many list of ints
  (which it does), the `list[int]` typing decision is in Phase 7 — NOT a
  `Ref[T]` modification here.
- **Async transport factory** — current decision is sync `Callable[..., Transport]`.
  If Phase 8 Pyodide spike reveals an async-construction need, revisit then.
- **Pyodide-specific transport implementation** — that's Phase 8's empirical
  question; Phase 6 only ships the seam, not any browser transport.

</deferred>

---

*Phase: 6-Transport Seam & Typed Models Core*
*Context gathered: 2026-05-28*
