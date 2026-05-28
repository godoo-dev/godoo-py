# Phase 6: Transport Seam & Typed Models Core - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-28
**Phase:** 6-Transport Seam & Typed Models Core
**Areas discussed:** OD-1/OD-2 + overload scope, Transport seam shape, Module layout + import isolation, Plan slicing

---

## OD-1: Partial-read strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Reject fields on type[T] (research-recommended) | type[T] overload omits `fields` kwarg entirely; mypy rejects; runtime TypeError. All-Optional generated fields means full-fetch always validates. | |
| Accept fields, validate anyway | Caller passes fields=..., missing ones validate to None via All-Optional. Less footgun but bypasses architectural intent. | |
| Accept fields, use model_construct | If fields= is passed, call BaseModel.model_construct() to skip validation. Loses wire transforms. | |
| **Derive subset model (Marc's free-text)** | **If fields=, create a derived subset model of ResPartner with those fields; keeps Odoo partial-fetch semantics + typed return. Pydantic create_model() or dataclass-based — needs research.** | **✓** |

**User's choice:** Derive a subset model of the target class on the fly when `fields=[...]` is passed.
**Notes:** Override of research recommendation. Marc wants partial reads to remain a first-class typed idiom because they're a normal Odoo pattern. Researcher must investigate `create_model()` vs alternatives, per-call cost, caching strategy keyed by `(model, tuple(sorted(fields)))`.

---

## OD-2: Boolean False-coercion

| Option | Description | Selected |
|--------|-------------|----------|
| Plain bool, skip in validator (Recommended) | Generated booleans emit as `name: bool = False` (non-Optional). @model_validator inspects model_fields[name].annotation; if bool, leave False untouched. Other fields: False → None. | ✓ |
| Optional[bool] uniformly | All fields including bool are Optional[T]=None. Odoo's False on a bool field gets coerced to None (loses signal). | |
| Annotation-based at codegen | Codegen emits `Annotated[bool, KeepFalse]` for boolean fields; @model_validator reads the marker. More explicit but adds a marker. | |

**User's choice:** Plain bool, skip in validator (research recommendation).
**Notes:** None — accepted as proposed.

---

## Read/search_read overload scope

| Option | Description | Selected |
|--------|-------------|----------|
| Both read + search_read | Both methods get type[T] overloads in Phase 6. search_read more complex but Phase 7 codegen wants both. | ✓ |
| Only read in Phase 6 | search_read typed dispatch slips to Phase 7. Smaller surface. | |
| Both, but search_read typed-output only | search_read typed return, no fields/limit kwargs on type[T] overload. | |

**User's choice:** Both read + search_read.
**Notes:** None — accepted as proposed. Phase 7 codegen will consume both; deferring search_read would force a follow-up.

---

## Transport Protocol surface

| Option | Description | Selected |
|--------|-------------|----------|
| Minimal (just what OdooClient uses) (Recommended) | authenticate / call / aclose / session / logout. Lowest-risk for additive infra. | ✓ |
| Full JsonRpcTransport parity | Also includes call_rpc, is_authenticated. More inspection helpers. | |
| Functional core (call/auth/aclose only) | Drop session and logout from Protocol; OdooClient owns session state. Requires refactoring is_authenticated() and logout() flow. | |

**User's choice:** Minimal.
**Notes:** None — accepted as proposed.

---

## transport_factory signature

| Option | Description | Selected |
|--------|-------------|----------|
| Callable[[OdooClientConfig], Transport], eager (Recommended) | Factory receives full config, called once in __init__. Default: JsonRpcTransport fallback. | ✓ |
| Callable[[], Transport], eager | Factory ignores config; caller closes over their own state. | |
| Pre-built transport: Transport \| None | Skip factory; caller builds Transport before constructing OdooClient. | |

**User's choice:** Callable[[OdooClientConfig], Transport], eager.
**Notes:** None — accepted as proposed.

---

## OdooBaseModel home

| Option | Description | Selected |
|--------|-------------|----------|
| Private _pydantic_transform.py (Recommended) | typed.py = Protocol + Ref dataclass (stdlib only). _pydantic_transform = OdooBaseModel + @model_validator. Generated files import the underscore module. | ✓ |
| Public godoo.client.pydantic_support | Public module so generated files import a non-underscore name. Locks path as semver-visible. | |
| Conditional in typed.py (try/except) | Single module with try/except ImportError fallback. Harder mypy reasoning. | |

**User's choice:** Private _pydantic_transform.py.
**Notes:** None — accepted as proposed.

---

## Ref shape

| Option | Description | Selected |
|--------|-------------|----------|
| Ref[T] generic (Recommended) | @dataclass(frozen=True) class Ref(Generic[T]): id: int; name: str. T mypy-visible only. Phase 7 codegen emits Ref[ResPartner]. | ✓ |
| Plain Ref(id, name) | No Generic machinery; codegen emits Ref without target-type hint. | |

**User's choice:** Ref[T] generic.
**Notes:** None — accepted as proposed. Matches REQUIREMENTS.md TYPED-07 explicit "Ref[Model]".

---

## Import-isolation enforcement

| Option | Description | Selected |
|--------|-------------|----------|
| Subprocess test in pytest (Recommended) | subprocess.run with `import godoo.client; assert 'pydantic' not in sys.modules`. Deterministic, immune to test order. | ✓ |
| CI matrix job without [typed] | uv sync --no-extra typed && python -c 'import godoo.client'. Strongest guarantee, requires CI workflow edit. | |
| Both — subprocess test + CI matrix | Belt and braces. ~2x maintenance. | |
| In-process sys.modules check | Fast but fragile if any prior fixture imports pydantic. | |

**User's choice:** Subprocess test in pytest.
**Notes:** None — accepted as proposed. Follows test_namespace.py pattern.

---

## Plan slicing

| Option | Description | Selected |
|--------|-------------|----------|
| 3 plans (Recommended) | 06-01 transport seam / 06-02 typed module + transforms / 06-03 overloads + dispatch + isolation test. Cleanest bisect surface. | ✓ |
| 2 plans | 06-01 seam + typed.py + Ref + Protocol / 06-02 _pydantic_transform + overloads + dispatch + extra + isolation test. Dense 06-02. | |
| 4 plans | Split out 06-04 for wire-transform unit tests + integration smoke. Over-sliced. | |

**User's choice:** 3 plans.
**Notes:** None — accepted as proposed.

---

## Claude's Discretion

- Exact typing of `args`/`kwargs` parameters on Transport.call() (likely list[Any] / dict[str, Any]) — left to planner.
- Cache strategy for derived partial-fields models — researcher recommends, planner decides.
- Whether OdooClient.is_authenticated() needs any change for alternative transport (likely none — reads _transport.session, which is on the Protocol).

## Deferred Ideas

- Typed dispatch on create/write/unlink — possible v1.2 phase.
- Ref[T] with id-only fallback — not needed; Odoo m2o always returns [id, "Name"].
- Async transport factory — revisit if Phase 8 Pyodide spike reveals a need.
- Pyodide-specific transport implementation — Phase 8 empirical question, not 6.
