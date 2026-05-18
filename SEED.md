# godoo-py — Project Seed

> The Python monorepo for the godoo library family — closes parity gaps against the TS core-3 libraries and builds godoo-introspection from scratch as a zero-to-working Python implementation.

**Seed written:** 2026-05-18
**Status:** Pre-charter. This document is the input to a `/gsd:new-project` pass.

---

## 0. Orientation — read this first

If you have just cloned this repo cold, start here.

### The godoo / Odoo Atlas initiative

This repo is one project under the **`godoo-dev` umbrella** — the **godoo / Odoo
Atlas initiative**, a multi-repo effort to build a coherent family of Odoo tooling
across languages, coordinated from a single vantage point (the `godoo-hq` *spine*).

**The godoo library family** is the core of that initiative: the TypeScript and
Python library monorepos plus the state manager — `godoo-ts` (TS), `godoo-py`
(Python), and `godoo-stateman`. `godoo-py` is the Python member of that family.

### What this document is — an adoption brief

This `SEED.md` is an **adoption brief**: a self-orienting charter document that seeds
this repo. It is committed as `godoo-py`'s first commit and is consumed as the
`/gsd:new-project` input that bootstraps `godoo-py`'s own Layer-1 GSD project. It
states what this satellite is for, what it must deliver, and what success looks like
— enough that a `/gsd:new-project` operator who picks up this repo cold can plan its
work.

### Where godoo-py starts from, and what the job is

`godoo-py` is **not greenfield, and not a code-transfer adoption.** Its starting point
is the **existing Python monorepo at `C:\dev\godoo-py`** — real, working code: a
functional async `godoo` client with eight domain services, a working
`godoo-testcontainers` package, and a placeholder `godoo-introspection` package. The
satellite **incorporates that codebase as its base** and evolves it in place.

The job of this charter is therefore *not* to transfer or re-implement code from
elsewhere. It is to **implement the parity gaps listed in §2 inside that existing
code** — completing the `godoo` client and `godoo-testcontainers` so the Python family
member matches what the TS monorepo already ships — and to **build out
`godoo-introspection`**, which currently has no implementation, into a working package.

Because godoo-py's code is already its own, the `godoo-adoption` branch protocol —
which moves code *from* a separate source repo *into* a satellite — does **not** govern
this satellite. There is no separate source repo being shed. See §3 for detail.

### Umbrella context

This brief assumes the shared umbrella context and does not restate it. Load it:

```
@../godoo-hq/UMBRELLA_CLAUDE.md
```

That file is the canonical "what every umbrella project must know" context — the
initiative overview, the three-layer architecture, the topology map, the coordination
model, and the load-bearing rules. It lives once in the private `godoo-hq` spine and
is `@`-imported (never copied) by every umbrella project.

---

## 1. Vision — what this satellite holds

`godoo-py` is the Python monorepo for the `@godoo`-equivalent libraries. It starts from
the existing `C:\dev\godoo-py` codebase and holds three packages, in three different
states:

- **`godoo`** — the Python async Odoo client (parity with `@godoo/client`). **Already
  functional**: the existing repo ships a working async client built on `httpx` with
  eight domain services (mail, modules, attendance, timesheets, accounting, urls,
  properties, cdc), an RPC transport layer, and opt-in safety guards. The work here is
  to *close the parity gaps in §2 against this existing code*, not to rebuild it.
- **`godoo-introspection`** — the Python introspection library. **A from-scratch
  build**: the package exists as a workspace member but ships no implementation (an
  empty module, "Pre-Alpha" classifier). It must be built from zero — see §2.
- **`godoo-testcontainers`** — the Python testcontainers library (parity with
  `@godoo/testcontainers`). **Already functional in part**: the existing repo ships
  Docker-based Odoo container support and a seed resolver. The work here is to *add
  the missing capabilities in §2* (snapshot cache, addons mount, provisioner
  subsystem).

This charter defines what must be completed to reach parity with the TS core-3 and to
ship `godoo-introspection` as a functional, standalone package.

The satellite is a LGPL-3.0 public library — the existing `C:\dev\godoo-py` Python work
is incorporated as the satellite's base and published under the `godoo-dev` org once the
parity gaps are closed and the GitHub repo is created (§5).

---

## 2. Parity gaps to close

### `godoo` (Python client — parity with `@godoo/client`)

The existing client is functional but missing the following:

- Async context manager (`async with OdooClient(...) as c`) — proper `__aenter__` /
  `__aexit__` for session lifecycle management
- `iter_search_read()` — auto-paginated async generator for large result sets
- `with_context(lang=...)` — call modifier that threads a context dict into the
  subsequent RPC call (e.g. for language-aware field access)
- `fields_get()` method — introspects a model's field metadata via `fields_get` RPC
- `ref(xml_id)` — XML ID lookup shortcut (resolves an xmlid to a numeric `res_id`)
- `execute_kw()` — raw call passthrough for non-standard RPC methods
- `read_binary()` — fetches binary field data (e.g. attachments)
- Bulk `create` — pass a list of value dicts to create multiple records in one RPC call
- `OAuthProxyClient` — bearer-token transport variant for Odoo instances fronted by an
  OAuth proxy (passes a `Bearer` token in the `Authorization` header instead of a
  session cookie)
- `py.typed` PEP 561 marker — signals to type checkers that the package ships inline
  type information; required for downstream `mypy`/`pyright` integration

### `godoo-introspection` (build from scratch — zero existing implementation)

No Python implementation exists. The following must be built from scratch, replicating
the capability of `@godoo/introspection` for Python:

- `Introspector` class — queries `ir.model` and `ir.model.fields` on a live Odoo
  instance to retrieve the full schema for one or more models
- `IntrospectionCache` — dict-based cache keyed by model name; supports a bypass option
  for always-live queries
- `CodeGenerator` — takes introspection results and emits typed Python representations
  (class stubs, typed dicts, or similar) from the live schema
- Type mapper — translates Odoo field types (`char`, `many2one`, `selection`, etc.) to
  Python type hints (`str`, `int | None`, `Literal[...]`, etc.)
- CLI (`godoo-introspect`) — entry point:
  `godoo-introspect --url <odoo-url> --db <dbname> --output ./types`
- Selection fields as `Literal[...]` — selection fields must emit
  `Literal["value1", "value2", ...]` type hints rather than bare `str`, preserving the
  closed-set constraint in the generated types

### `godoo-testcontainers` (parity with `@godoo/testcontainers`)

The Python testcontainers package has basic container support but is missing:

- Local snapshot cache — `pg_dump`/restore workflow keyed by a content hash of the
  provisioned state, stored under `~/.odoo-testcontainers/snapshots/`. Avoids
  re-provisioning a fresh Odoo database on every test run when the provisioner inputs
  have not changed
- Custom addons mount (`addonsPath`) — mounts a local addons directory into the
  testcontainer so tests can exercise custom modules
- Provisioners:
  - Partners provisioner — seeds `res.partner` records into the test database
  - Projects provisioner — seeds `project.project` + `project.task.type` records
  - Users provisioner — seeds `res.users` records with configurable groups
  - Properties provisioner — sets `ir.config_parameter` key/value pairs
  - `TestHarness` — high-level fixture that composes the provisioners and exposes a
    clean test API
- `py.typed` marker — same PEP 561 requirement as the client

---

## 3. godoo-adoption protocol — applicability

The `godoo-adoption` protocol governs **code-transfer adoptions** — cases where existing
code moves from a separate source repo into a satellite via a paired `godoo-adoption`
branch on both sides (the way `odoo-toolbox` code is shed into `godoo-ts`).

**`godoo-py` is NOT governed by this protocol** — but the reason is precise: godoo-py
has **no separate source repo to shed**. Its code already lives in `C:\dev\godoo-py`,
which the satellite incorporates as its own base and evolves in place (§0, §1). With no
source/destination pair, the protocol's branch machinery — paired `godoo-adoption`
branches, the source-side deprecation README, the cutover handshake — has nothing to
operate on. This is *not* because godoo-py is greenfield (it is not) and *not* because
no code exists (it does); it is simply that the code is already the satellite's own.
The protocol is referenced here for completeness only, so the satellite maintainer can
confirm it does not apply to this track. Full definition:
`../godoo-hq/.planning/notes/godoo-adoption-protocol.md`.

---

## 4. Report-back

When `godoo-py` has met **all** the success criteria below, it reports completion to the
spine: a single terminal entry appended (newest-first) to the spine's `dev-log.md`,
which the spine then verifies by direct query of this satellite repo. The mechanism
defines *how* to report; this section defines *what* `godoo-py` reports. Full mechanism:
`../godoo-hq/.planning/notes/report-back-mechanism.md`.

**At completion, godoo-py reports:**

- All named client parity gaps closed: async context manager, `iter_search_read()`,
  `with_context()`, `fields_get()`, `ref()`, `execute_kw()`, `read_binary()`, bulk
  `create`, `OAuthProxyClient`, and `py.typed` — each bullet from §2 verified and
  shipped
- `godoo-introspection` built from scratch and functional: all six components
  implemented (`Introspector`, `IntrospectionCache`, `CodeGenerator`, type mapper, CLI,
  and `Literal` selection fields)
- Testcontainers snapshot cache and provisioner subsystem implemented: local snapshot
  cache, custom addons mount, and all five provisioners (`TestHarness` + four resource
  provisioners) operational
- `py.typed` markers added across all packages (`godoo`, `godoo-introspection`,
  `godoo-testcontainers`)

---

## 5. Org bootstrap

Create the satellite repo under the `godoo-dev` org. The existing `C:\dev\godoo-py`
codebase is incorporated during the satellite's own project setup (the mechanics —
fork, re-remote, or clean copy — are a satellite decision, not a charter constraint).

```bash
gh repo create godoo-dev/godoo-py --public
```

Note: `godoo-py` is a library (LGPL-3.0 likely), so `--public` is the expected
visibility. Visibility is the satellite's final decision.

When `godoo-py` runs `/gsd:new-project`, the generated `CLAUDE.md` must `@`-import the
umbrella context so the repo stays umbrella-aware. Add this line to the generated
`CLAUDE.md`:

```
@../godoo-hq/UMBRELLA_CLAUDE.md
```

---

## 6. Open questions / discretion areas

The following are left to the satellite's own `/gsd:new-project` planning pass:

**(a) How to incorporate the existing `C:\dev\godoo-py` repo.** Options include forking
the existing repo and re-remoting it to `godoo-dev/godoo-py`, cloning and rewriting the
remote, or starting fresh and cherry-picking commits. The brief does not mandate the
mechanics — any approach that results in the satellite owning the full git history is
acceptable.

**(b) Whether package names stay as-is or align with the `godoo-{client,introspection,
testcontainers}` naming convention.** The existing packages in `godoo-py` may use
different PyPI names. Whether to rename on publish (e.g. `godoo-client` on PyPI) or
keep short names (`godoo`, `godoo-introspection`, `godoo-testcontainers`) is a satellite
decision, constrained by PyPI name availability and the publishing strategy.

**(c) Test framework choices.** `pytest` with `asyncio-mode = auto` is the natural fit
for an async Python library, but the exact `pytest` plugins, `asyncio` settings, and
whether `hypothesis` or property-based testing is used are satellite decisions.

---

*Seed authored 2026-05-18 as part of the godoo-hq Phase 3 — Adoption Briefs initiative.
This document is the spine's charter to `godoo-py`; the satellite's own
`/gsd:new-project` pass owns all implementation decisions not explicitly stated here.*
