# Phase 3: Testcontainers Parity - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-21
**Phase:** 3-testcontainers-parity
**Areas discussed:** Properties provisioner semantics, Cross-cutting scope (mid-discussion redirect), Harness API style, Snapshot cache (key + opt-out + dir), Addons mount

---

## Gray-area selection

| Option | Description | Selected |
|--------|-------------|----------|
| Properties: ir.config_parameter or task-props? | Real divergence between REQUIREMENTS (ir.config_parameter) and TS reference (task properties on project). | ✓ |
| Harness API: imperative vs declarative | ROADMAP says harness.partners.create(...); TS uses declarative TestHarness.start({...}). | ✓ |
| Snapshot cache: key + opt-out | What inputs hash; default-on; env override; cache dir. | ✓ |
| Addons mount shape | Single path str vs list of mounts; default ro; container target. | ✓ |

**User's choice:** All four selected.

---

## Properties provisioner semantics

| Option | Description | Selected |
|--------|-------------|----------|
| ir.config_parameter (Recommended) | Match REQUIREMENTS TESTC-06 verbatim. Provisioner sets system k/v pairs. | ✓ |
| Task properties (TS-faithful) | Mirror TS — provision task property definitions on project.task_properties_definition. | |
| Both — keep them as distinct sub-provisioners | harness.properties for system params AND a separate task_properties facility. | |

**User's choice:** ir.config_parameter — locked as D-Props-1.

### Follow-up: ir.config_parameter write API

| Option | Description | Selected |
|--------|-------------|----------|
| Single-key set + bulk dict (Recommended) | .set(key, value) for one; .set_many({...}) for bulk. Idempotent via Odoo set_param upsert. | ✓ |
| Bulk dict only | .set({...}) overloaded — bulk-only entry point. | |
| Declarative-config-only | No imperative .set; only via TestHarness.start(properties={...}). | |

**User's choice:** Single-key + bulk — locked as D-Props-2.

---

## Cross-cutting redirect (mid-discussion)

**Free-text user input:** *"We have a parallel godoo-stateman project, I think
testcontainers should do the bare minimum and we later add support for applying
state manager scripts; avoid duplication of work and leverages what stateman
will do, see ../godoo-stateman/"*

Claude read `../godoo-stateman/SEED.md` to ground the redirect, identified that
stateman is a Terraform-for-Odoo CLI with a 7-stage reconciliation pipeline and
Python DSL for desired state, and reframed Phase 3 as "container lifecycle +
module install + ir.config_parameter only" with all record seeding deferred to
stateman.

### Cross-cutting scope confirmation

| Option | Description | Selected |
|--------|-------------|----------|
| Strict minimum (Recommended) | Each provisioner does only core record creation with primitive fields; no categories/parents/stages/tasks/groups. | ✓ |
| Strict minimum + named-reference lookups | Same but with refs= dict for ergonomic group/parent resolution. | |
| Match TS reference exactly | Re-grow categories, parents-by-name, stages, tasks, group XML-IDs. | |

**User's choice:** Strict minimum — locked as D-Scope-1.

### Cross-cutting scope: drop confirmation (Harness API turn)

When asked about TestHarness imperative-vs-declarative API, user picked Other
with the freeform: *"None of those, all that should go to the stateman. At most
TestHarness provides raw entities (ie, to set ir.config_parameter) and install
module."*

This converted D-Scope-1 (strict minimum) into D-Drop-1 (full requirement
drop). Claude flagged the charter-amendment protocol (CLIENT-09 / INTRO-05)
and asked for explicit confirmation.

| Option | Description | Selected |
|--------|-------------|----------|
| Drop TESTC-03/04/05; keep TESTC-06 + module install (Recommended) | Charter amendment under CLIENT-09/INTRO-05 protocol; ROADMAP criterion 3/4 rephrased; coverage 29→26. | ✓ |
| Drop TESTC-03/04/05/06 — only module install + raw setter | Even stronger; drops properties provisioner too. | |
| Keep them in REQUIREMENTS, just thin (walk back) | Imperative .create methods on each provisioner stay; just minimum fields. | |

**User's choice:** Drop TESTC-03/04/05; keep TESTC-06 — locked as D-Drop-1.

---

## Harness API style (post-redirect)

The original "imperative vs declarative" choice for TestHarness was moot after
D-Drop-1. Re-asked as: what does the trimmed TestHarness expose?

| Option | Description | Selected |
|--------|-------------|----------|
| Thin wrapper class with async context manager (Recommended) | async with TestHarness(modules, properties, addons_path, snapshot) as h: h.client / h.modules.install / h.properties.set | ✓ |
| Just promote StartedOdooContainer to be 'the harness' | No new class — add .properties to StartedOdooContainer; pytest fixture yields it. | |
| Start/stop methods only, no async-cm | harness = await TestHarness.start(...); ...; await harness.stop(). TS-faithful but less Pythonic. | |

**User's choice:** Async-cm thin wrapper — locked as D-Harness-1.

---

## Snapshot cache — key composition

| Option | Description | Selected |
|--------|-------------|----------|
| TS-faithful + properties dict (Recommended) | TS inputs + sorted ir.config_parameter map. Properties added to key because they're applied post-restore. | ✓ |
| TS-faithful, properties OUT | Match TS exactly; re-apply properties on every run regardless of cache hit. | |
| Minimal key | Only schema_version + odoo_version + modules + addons + properties. Drop postgres image / db / admin pw / env. | |

**User's choice:** TS-faithful + properties dict — locked as D-Snap-1.

## Snapshot cache — enablement + opt-out

| Option | Description | Selected |
|--------|-------------|----------|
| TS-faithful (Recommended) | Default ON. Disable via env or kwarg. Override dir via env or kwarg. Caller user_key for manual invalidation. | ✓ |
| Default ON, env only | No constructor kwarg; env-var control only. | |
| Default OFF, opt-in | Off unless explicitly snapshot=True. | |

**User's choice:** TS-faithful — locked as D-Snap-2.

## Snapshot cache — default dir

Claude flagged: REQUIREMENTS TESTC-01 + ROADMAP criterion 1 say
`~/.odoo-testcontainers/snapshots/`; TS-faithful would be
`cwd/.odoo-testcontainers/snapshots/`. Real divergence; asked for the
preferred default.

| Option | Description | Selected |
|--------|-------------|----------|
| ~/.odoo-testcontainers/snapshots/ (Recommended) | Match REQUIREMENTS + ROADMAP verbatim. Shared across projects on same machine. No charter amendment needed. | |
| cwd/.odoo-testcontainers/snapshots/ (TS-faithful) | Per-project local cache; mirrors TS. Charter amendment to path text. | ✓ |
| User-home default + per-call override | ~/ default but cache_dir= kwarg/env override remain. Best-of-both. | |

**User's choice:** cwd-local (TS-faithful) — locked as D-Snap-3 + D-Snap-3-amendment.

---

## Addons mount — shape

| Option | Description | Selected |
|--------|-------------|----------|
| Path \| list[Path] union (Recommended) | Single Path → /mnt/extra-addons; list → /mnt/addons-0/1/.... Always ro. | ✓ |
| Single Path only | One directory, /mnt/extra-addons, ro. Matches REQUIREMENTS/ROADMAP verbatim. | |
| Full TS union: Path \| list[AddonsMount] | Per-mount target/mode customisation. Most flexible; v1-overkill. | |

**User's choice:** Path | list[Path] union — locked as D-Addons-1.

## Addons mount — interaction with modules=

| Option | Description | Selected |
|--------|-------------|----------|
| Orthogonal (Recommended, TS-faithful) | addons_path mounts only; user passes modules=[...] separately to install. | ✓ |
| Auto-install all modules found under addons_path | Scan __manifest__.py files, install all discovered modules. Magic; risky. | |
| Add a separate auto_install kwarg | Opt-in manifest-scan via auto_install_addons=True. | |

**User's choice:** Orthogonal — locked as D-Addons-2.

---

## Claude's Discretion (planner)

- ConfigParameterService location — testcontainers-internal helper vs godoo
  core service quad. Default lean: testcontainers-internal for v1.
- `asyncio.to_thread` boundaries for every new sync call.
- Concurrency rule for snapshot writes (temp + atomic rename + skip-if-exists).
- pytest fixture pattern in docs (session-scoped vs function-scoped).
- Snapshot vs seed-image interaction (default: snapshot caching applies on
  the non-seed path; seed image acts as its own fast path).
- `schema_version` constant starts at 1; bump policy documented.
- Typing of `properties.set(value)` — str only for v1; coercion overloads
  deferred.

## Deferred Ideas

- `harness.apply_stateman(config_path)` hook — future phase.
- Partner / project / user / task-property provisioners (full TS-reference
  surface) — deferred to stateman.
- Full `AddonsMount` dataclass union (per-mount target/mode) — v2.
- Convenience overloads on `properties.set` (int/bool/float → str coercion).
- General-purpose `ConfigParameterService` on godoo core client.
- `get_param` / `delete_param` on the properties helper.
- Multi-version Odoo snapshot sharing.
- Pre-existing v2 deferrals untouched (COMPAT-01, CLIENT-V2-01, PERF-01/02).
