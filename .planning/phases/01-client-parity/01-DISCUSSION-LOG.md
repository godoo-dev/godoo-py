# Phase 1: Client Parity - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-19
**Phase:** 1-Client Parity
**Areas discussed:** OAuthProxyClient architecture (→ dropped), with_context() mechanics, Bulk create API shape, iter_search_read pagination

---

## OAuthProxyClient architecture (CLIENT-09)

Selected for discussion, but during the first question the owner halted it:
*"Delete the OAuthProxyClient shit, that should have never landed in that codebase."*

Verified `OAuthProxyClient` had **no source code** — it existed only in planning
documents. Resolved via two follow-up questions:

| Question | Choice |
|----------|--------|
| How to remove CLIENT-09 from v1 scope? | **Hard-drop entirely** (not v2 backlog) |
| SEED.md (charter) names it in §2/§4 — how handled? | **Amend SEED.md too** (keep charter consistent with plan) |

**Outcome:** CLIENT-09 struck from `SEED.md`, `REQUIREMENTS.md`, `ROADMAP.md`,
`PROJECT.md`. See CONTEXT.md D-01. Area produced no implementation decisions.

---

## with_context() mechanics (CLIENT-03)

| Question | Options | Selected |
|----------|---------|----------|
| Return shape / lifetime | Reusable scoped client / One-shot proxy / Async context manager | **Other** |
| Chaining | Merge / Replace | **Merge** |
| Coverage | Whole surface (CRUD + services) / Core CRUD only | **Other** |
| Per-call `context=` precedence | Merges over / Fully replaces / You decide | **Merges over** |

**User's choice:** Overrode the menu — `with_context` should be a Python context
manager: `with client.with_context(lang='fr'): client.search(...)` — *"much more
Pythonic."* Calls go on the base client inside the block; whole surface inherits the
context. Nested blocks merge.

**Notes:** Raised that a plain instance attribute is unsafe under `asyncio`
concurrency. Owner: research the mechanism, with `contextvars.ContextVar` as the
current direction unless something better comes up.

---

## Bulk create API shape (CLIENT-08)

| Option | Description | Selected |
|--------|-------------|----------|
| Single `create`, `@overload`'d | One method; `@typing.overload` gives `dict→int`, `list[dict]→list[int]` | ✓ |
| Separate `create_many()` | Two precisely-typed methods | |
| Single `create`, runtime union | One method, `int \| list[int]` return | |

| Option | Description | Selected |
|--------|-------------|----------|
| Raise `OdooValidationError` locally | Reject empty list before any RPC | ✓ |
| Pass through to Odoo | Let Odoo return `[]` | |
| You decide | — | |

**User's choice:** Single `create` with `@typing.overload`; `create(model, [])` raises
`OdooValidationError` locally.
**Notes:** Overload chosen to keep strict-mypy call sites union-free.

---

## iter_search_read pagination (CLIENT-02)

| Question | Options | Selected |
|----------|---------|----------|
| Strategy | Id-cursor (keyset) / Offset-based | **Id-cursor (keyset)** |
| Custom `order`? | No, always id-asc / Yes, offset fallback / You decide | **No — always id-ascending** |
| Default batch size | 500 / 100 / 1000 | **500** |
| Total `limit`? | Yes, optional / No, full set / You decide | **Yes — optional limit** |

**User's choice:** Keyset paging on `id`, no custom order, `batch_size` default 500,
optional total `limit`.
**Notes:** Yields individual records — fixed by ROADMAP success criterion 2.

---

## Claude's Discretion

- Exact fix shape for FIXES-01/02 follows `CONCERNS.md` fix approaches.
- Remaining requirements (CLIENT-01/04/05/06/07/10, FIXES-03) were not separately
  discussed — sensible defaults were presented in a table and accepted as-is
  ("I'm ready for context"). See CONTEXT.md D-14–D-22.
- Un-specified ergonomics (parameter names, docstrings) at planner/executor discretion.

## Deferred Ideas

- None new — discussion stayed within phase scope.
- CLIENT-09 (`OAuthProxyClient`) was hard-dropped, not deferred.
