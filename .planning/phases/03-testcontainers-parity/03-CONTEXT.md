# Phase 3: Testcontainers Parity - Context

**Gathered:** 2026-05-21
**Status:** Ready for planning

<domain>
## Phase Boundary

Add the missing capabilities on top of the existing `OdooTestContainer` to reach
parity with `@godoo/testcontainers` — **scoped tightly to the bare minimum**.
The existing `OdooTestContainer` already handles Docker network, Postgres,
Odoo, seed image resolution, readiness wait, and module install. Phase 3
delivers, inside `packages/godoo-testcontainers/`:

- **TESTC-01** local snapshot cache (`pg_dump`/restore keyed by content hash)
- **TESTC-02** custom addons mount (`addons_path`)
- **TESTC-06** properties provisioner — `ir.config_parameter` k/v pairs
- **TESTC-07** `TestHarness` — thin async-cm wrapper composing the above + a
  ready `OdooClient`
- **TESTC-08** `py.typed` PEP 561 marker

**5 requirements** after the scope drop. Scope is fixed by REQUIREMENTS.md /
ROADMAP.md (with the Phase 3 amendments below) — discussion clarified HOW to
implement, never WHETHER to add capabilities.

**Removed from scope (hard-dropped this phase):**

- **TESTC-03** (partners provisioner) — D-Drop-1
- **TESTC-04** (projects provisioner) — D-Drop-1
- **TESTC-05** (users provisioner) — D-Drop-1

The owner decision: all record-seeding richness — partner categories, parent
companies, project stages, project tasks, task-property definitions, group
XML-IDs — is the natural surface of `godoo-stateman` (see `../godoo-stateman/`,
"Terraform for Odoo": a 7-stage reconciliation pipeline over jsonrpc with a
Python DSL for desired state). Testcontainers does the bare minimum
(container lifecycle + module install + `ir.config_parameter`); stateman
owns declarative seeding when it lands. A future phase will wire stateman
config application into `TestHarness` (`harness.apply_stateman(path)` or
equivalent); that hook is NOT in Phase 3.

</domain>

<decisions>
## Implementation Decisions

### Scope change — TESTC-03/04/05 dropped, snapshot path text amended

- **D-Drop-1:** TESTC-03 (partners), TESTC-04 (projects), TESTC-05 (users) are
  hard-dropped from v1 scope under the same protocol that retired CLIENT-09
  (Phase 1, D-01) and INTRO-05 (Phase 2, D-CLI-1). Charter amendments due:
  - `SEED.md` §2 (`godoo-testcontainers` block) — strike the partners, projects,
    and users bullets from the "Provisioners" list. The `TestHarness` bullet
    stays but its description must drop "composes the provisioners".
  - `.planning/REQUIREMENTS.md` — strike `TESTC-03`, `TESTC-04`, `TESTC-05`;
    update traceability table; update coverage count (29→26 v1 requirements
    after this drop — adjust both Phase 2's prior 30→29 footprint and this
    drop).
  - `.planning/ROADMAP.md` — Phase 3 `Requirements:` line drops TESTC-03/04/05;
    success criterion 3 rephrased from
    `"harness.partners.create(...), harness.projects.create(...), harness.users.create(...), and harness.properties.set(...) to seed test data without writing raw RPC calls"`
    to a properties+modules-only formulation (planner picks exact wording, e.g.
    `"harness.properties.set(...) and harness.modules.install(...) seed test state without writing raw RPC calls"`);
    success criterion 4 rephrased from
    `"single clean API composing all four provisioners"` to
    `"single clean API composing the snapshot cache, module install, and properties provisioner, and exposes a ready OdooClient"`.
  - `.planning/PROJECT.md` — drop the "Four resource provisioners (partners,
    projects, users, properties)" bullet from Active; replace with
    "Properties provisioner (ir.config_parameter)"; add a Key Decisions row.
  - Other TESTC IDs are NOT renumbered — gaps are self-documenting (same
    pattern as CLIENT-09→CLIENT-10 and INTRO-05).
- **D-Snap-3-amendment:** REQUIREMENTS TESTC-01 + ROADMAP success criterion 1
  path text changes from `~/.odoo-testcontainers/snapshots/` (user home) to
  `cwd/.odoo-testcontainers/snapshots/` (project-local). Folded into the same
  Phase 3 amendment batch.

### Scope philosophy — D-Scope-1

- **D-Scope-1:** Strict minimum. Testcontainers does **container lifecycle**
  (already done) plus **two narrow seeding primitives** (module install,
  already done; `ir.config_parameter` k/v, this phase). Any seeding richer
  than that — records, relations, idempotency, xmlid identity, declarative
  desired state — is `godoo-stateman`'s surface, not testcontainers'.
  Avoid duplicating what stateman will own.

### Properties provisioner — TESTC-06

- **D-Props-1:** The properties provisioner sets **`ir.config_parameter`** k/v
  pairs (Odoo system parameters). It does NOT touch the
  `project.task_properties_definition` field — the TS reference's
  `properties.ts` (task-property definitions on projects) is out of scope
  for v1. Wording matches REQUIREMENTS TESTC-06 + SEED §2 verbatim.
- **D-Props-2:** Public API on `TestHarness`:
  - `await h.properties.set(key: str, value: str) -> None` — set one key.
  - `await h.properties.set_many(values: Mapping[str, str]) -> None` — bulk
    set; iterates `set_param` per key (Odoo's `ir.config_parameter.set_param`
    is upsert by design — idempotent without local pre-checks).
- **Planner discretion:** the exact transport — whether to call
  `client.execute_kw("ir.config_parameter", "set_param", [key, value])` per
  key, or write directly via `client.create`/`client.write` on the model
  after a `client.search`. Convention-wise, `set_param` is idiomatic;
  researcher should confirm it's exposed on the Odoo 17/18/19 JSON-RPC
  surface (it is in 17 CE — confirmed via SEED §2 wording and Odoo's public
  `ir.config_parameter.set_param` method).
- **Planner discretion:** typing of `value` — `str` is the wire shape;
  whether to add convenience overloads accepting `int`/`bool`/`float` and
  coerce to `str` before write is open. Default to `str` only for v1 to
  avoid silent coercion bugs.

### TestHarness shape — TESTC-07

- **D-Harness-1:** `TestHarness` is a **thin wrapper class with an async
  context manager**:

  ```python
  async with TestHarness(
      modules=[...],
      properties={...},          # ir.config_parameter k/v, applied post-start
      addons_path=Path(...),     # or list[Path]
      snapshot=True,             # bool — also accept env override
      cache_dir=Path(...),       # snapshot cache dir override
      database="test_odoo",
      admin_password="admin",
      startup_timeout=300,
      env={...},
  ) as h:
      h.client                   # OdooClient (authenticated)
      h.url                      # str
      await h.modules.install("project")
      await h.properties.set("mail.catchall.domain", "example.com")
      await h.properties.set_many({"a": "1", "b": "2"})
  ```

  Mirrors the Phase 1 D-14 client async-cm shape (`__aenter__` calls start +
  authenticate + post-start provisioning, `__aexit__` calls cleanup).
- **Planner discretion:** whether `TestHarness` is implemented as
  `OdooTestContainer` + a wrapping class, or as a refactor that adds
  `__aenter__`/`__aexit__` to `StartedOdooContainer` directly with
  `TestHarness` as a thin factory. Either is acceptable provided
  `async with TestHarness(...) as h:` is the public entry point. Existing
  `OdooTestContainer.start()` / `StartedOdooContainer.cleanup()` stay
  callable for advanced use (consistent with the codebase's
  "functions-first + class wrapper" pattern).
- **Planner discretion:** where `ir.config_parameter` write logic lives.
  Options:
  - (a) a small `ConfigParameterService` inside
    `packages/godoo-testcontainers/src/godoo_testcontainers/properties.py`
    (test-only — not a general godoo client service);
  - (b) a new service quad in `packages/godoo/src/godoo/services/config_parameters/`
    (general client surface, re-used by harness).
  Default lean: (a) — keeps the godoo core client surface frozen for v1
  (no new services), and the testcontainers-internal helper is sufficient
  for the harness use case. Planner may flip to (b) if researcher finds
  that the state manager or other downstream consumers want the same
  surface on the plain client.

### Snapshot cache — TESTC-01

- **D-Snap-1:** Snapshot cache key is `sha256(stable_json(...))` truncated to
  the first 16 hex chars (TS-faithful). Hashed inputs:
  - `schema_version` (constant — bump to invalidate every cached snapshot at once)
  - `odoo_version` (from `ODOO_VERSION` env or constructor)
  - `postgres_image` (e.g. `postgres:15-alpine` — also covers the seeded
    `goborey/odoo-postgres:17.0` case)
  - `modules` — sorted, deduped
  - `addons` — content-tree hash: walk every file under each mount source,
    ignoring `.git`, `node_modules`, `__pycache__`, `.pytest_cache`; record
    `(relative_path, sha256(file_content))` sorted by relative path; per-mount
    {source(resolved), target, mode, tree}. Edits invalidate automatically.
  - `database`
  - `admin_password`
  - `env` — sorted dict
  - **`properties`** — sorted `ir.config_parameter` k/v dict applied by the
    harness post-start. This addition is **forced by the new flow**: params
    are applied after restore, so a different param set must invalidate the
    cached snapshot or restored runs will silently disagree with first runs.
  - optional caller-owned `user_key` for manual invalidation
- **D-Snap-2:** Enablement is TS-faithful:
  - Default **ON**.
  - Disable via env `ODOO_TESTCONTAINERS_SNAPSHOT=disabled` OR by passing
    `snapshot=False` to `TestHarness` / `OdooTestContainer`.
  - Override cache dir via env `ODOO_TESTCONTAINERS_SNAPSHOT_DIR` OR by passing
    `cache_dir=Path(...)`.
  - Caller-owned `user_key` for manual invalidation.
- **D-Snap-3:** Default cache dir is **`cwd/.odoo-testcontainers/snapshots/`**
  (TS-faithful), NOT `~/.odoo-testcontainers/snapshots/`. Requires the
  REQUIREMENTS/ROADMAP path text amendment in D-Drop-1.
- **Planner discretion:** save/restore mechanics — TS uses
  `postgres_container.exec(['pg_dump', '-U', ..., '-d', ..., '-Fc', '-f',
  containerPath])` for save and `dropdb / createdb / pg_restore` for
  restore, with a bind-mount of the cache dir to a container path. Python
  testcontainers' `PostgresContainer` exposes `.exec(cmd)` (sync) — wrap in
  `asyncio.to_thread`. Researcher confirms exact API surface. Concurrency
  (two pytest workers building the same key) is handled via the existing
  TS pattern: temp file (`.pid.timestamp.random.tmp`) + atomic rename +
  if-exists-skip; corruption falls back to fresh provision (best-effort
  cleanup on save failure).
- **Planner discretion:** when seed images are in play
  (`ODOO_SEED_IMAGE` / `resolve_seed_info`), the snapshot path interacts
  with the pre-seeded DB image. Researcher decides whether snapshot caching
  is disabled when a seed image provides the same fast-path, or whether
  the snapshot key incorporates the seed image identifier and replaces it.
  Current bias: snapshot caching applies on top of the non-seed path
  (postgres:15-alpine); when a seed image is used, the seed image IS the
  cache. Document the chosen rule in code comments.

### Addons mount — TESTC-02

- **D-Addons-1:** `addons_path: Path | list[Path] | None = None`.
  - `None` → no extra mount (current behavior).
  - Single `Path` → mounted read-only at container target `/mnt/extra-addons`.
  - `list[Path]` → mounted read-only at `/mnt/addons-0`, `/mnt/addons-1`, …
    (TS-faithful indexing).
  - Full TS union (`Path | list[AddonsMount]` with per-mount target/mode
    customisation) is **out of scope for v1** — deferred.
- **D-Addons-2:** `addons_path` and `modules` are **orthogonal**. Mounting
  a directory does NOT auto-install the modules found inside it. The user
  passes `modules=["my_custom_module"]` separately, and the existing
  `OdooTestContainer` install flow picks it up. Same mental model as
  installing system modules. (TS reference is the same.)
- **Planner discretion:** Odoo's `--addons-path` command-line argument
  must be extended to include the mounted directories so Odoo discovers
  them. Researcher confirms the correct invocation (likely
  `--addons-path=/mnt/extra-addons,/usr/lib/python3/dist-packages/odoo/addons`
  or the modern Odoo 17+ equivalent). The current
  `OdooTestContainer.with_command` build doesn't pass `--addons-path`;
  this is a code change inside the existing container.py.

### Claude's Discretion (Planner)

- **ConfigParameterService location** — see D-Harness-1 planner-discretion
  note above. Default to a testcontainers-internal helper for v1.
- **`asyncio.to_thread` boundaries** — every new sync `testcontainers` /
  filesystem call (snapshot save/restore, addons-tree hashing, bind-mounts)
  must be wrapped, per the existing pattern in `container.py`.
- **Concurrency rule for snapshot writes** — TS uses temp + atomic rename
  + skip-if-exists; planner replicates with Python's
  `tempfile.NamedTemporaryFile` + `os.replace`.
- **pytest fixture pattern in docs** — show `@pytest_asyncio.fixture` with
  `async with TestHarness(...) as h: yield h`, session-scoped if snapshot
  caching is enabled, function-scoped otherwise. Planner picks the canonical
  example.
- **Snapshot vs seed-image interaction** — see D-Snap-3 planner-discretion
  note above. Default rule: snapshot caching applies on top of the non-seed
  path; seed image acts as its own fast path.
- **`schema_version` constant** — start at `1`. Bump invalidates everything;
  document the bump policy in the snapshot module's docstring.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Charter & requirements

- `SEED.md` §2 (`godoo-testcontainers` block) — defines the testcontainers
  parity surface. Amendment due 2026-05-21: strike the partners, projects,
  and users bullets from the "Provisioners" list (per D-Drop-1); soften the
  `TestHarness` bullet to drop "composes the provisioners". Stateman
  positioning (see `../godoo-stateman/SEED.md`) is the rationale.
- `.planning/REQUIREMENTS.md` — TESTC-01/02/06/07/08 are the in-scope
  requirements after D-Drop-1. TESTC-03/04/05 to be struck; traceability
  table + coverage count amended. TESTC-01 path text amended per
  D-Snap-3-amendment.
- `.planning/ROADMAP.md` — Phase 3 goal + success criteria. Requirements
  line drops TESTC-03/04/05. Success criteria 3 and 4 rephrased per
  D-Drop-1; success criterion 1 path text amended per D-Snap-3-amendment.
- `.planning/PROJECT.md` — Active block bullet rewrite + Key Decisions row
  per D-Drop-1.

### Sister project — the rationale for the scope drop

- `../godoo-stateman/SEED.md` — full charter for the Python state-manager
  satellite. Read §1 (Vision), §2 (What to salvage — the 7-stage
  reconciliation pipeline), and §1's authoring-surface bullets to
  understand why declarative record seeding belongs to stateman, not
  testcontainers. The future testcontainers↔stateman integration hook
  (e.g. `harness.apply_stateman(path)`) is a FUTURE phase, deferred from
  here.
- `../godoo-stateman/` (root) — repo state at time of writing: SEED.md
  only, no source yet. Confirms stateman is not blocking this phase but
  will land separately; the integration hook lands when stateman ships.

### Phase 1 & Phase 2 decisions (apply here)

- `.planning/phases/01-client-parity/01-CONTEXT.md` — especially:
  - **D-14** (`async with OdooClient(...)` shape) — `TestHarness` mirrors
    it (D-Harness-1).
  - **D-01** (CLIENT-09 scope-drop protocol) — D-Drop-1 follows the same
    procedure verbatim.
  - **D-20** (timeout on `OdooClientConfig`) — `TestHarness` may need to
    surface this so callers can override the container's startup vs
    request timeouts independently (planner discretion).
- `.planning/phases/02-introspection/02-CONTEXT.md` — especially:
  - **D-CLI-1** (INTRO-05 scope-drop protocol) — second precedent for the
    drop protocol applied here.

### Codebase (the patterns and integration points)

- `.planning/codebase/ARCHITECTURE.md` — layer model, `OdooClient` as the
  sole integration point; service pattern; the anti-pattern "use sync
  testcontainers calls in async tests" — directly applies to the new save/
  restore paths.
- `.planning/codebase/CONVENTIONS.md` — naming, typing, module conventions
  (snake_case modules, PascalCase classes, dataclasses-not-Pydantic,
  all-async, `from __future__ import annotations`, `TYPE_CHECKING` imports
  for `OdooClient`, `cast()` at `client.call()` boundary).
- `.planning/codebase/STRUCTURE.md` §`packages/godoo-testcontainers/` —
  current state of the package.
- `packages/godoo-testcontainers/src/godoo_testcontainers/container.py` —
  existing `OdooTestContainer` and `StartedOdooContainer` shapes; sync
  testcontainers wrapped in `asyncio.to_thread`; module install + retry on
  Odoo restart. The new code wraps/extends this; do NOT rewrite it.
- `packages/godoo-testcontainers/src/godoo_testcontainers/seed_resolver.py`
  — `normalise_odoo_version`, `resolve_seed_info`, and the seed-image
  fast path. Snapshot caching interacts with this — see D-Snap planner
  discretion.
- `packages/godoo/src/godoo/client.py` — `OdooClient` surface; new properties
  helper uses `execute_kw('ir.config_parameter', 'set_param', [k, v])` or
  the equivalent CRUD primitives.
- `packages/godoo/src/godoo/services/modules/` — existing `ModuleManager` /
  `modules` service used by the harness for install.

### Reference — TS implementation to MIRROR (key parts) and IGNORE (record-seeding parts)

- `../godoo-ts/packages/testcontainers/src/snapshot-cache.ts` — **MIRROR.**
  Source of truth for the snapshot cache key composition (D-Snap-1), the
  enablement defaults (D-Snap-2), and the temp-file + atomic-rename save
  protocol. Python implementation closely follows; differences documented
  in code comments.
- `../godoo-ts/packages/testcontainers/src/odoo-container.ts` — **MIRROR
  the addons mount logic and `--addons-path` plumbing only.** Most of the
  rest (provisioners) does not apply.
- `../godoo-ts/packages/testcontainers/src/provisioners/` — **IGNORE for v1.**
  partners.ts, projects.ts, properties.ts (task properties), users.ts,
  harness.ts (declarative `TestHarness.start(config)`) — none of these
  apply after D-Drop-1. They are reference for the FUTURE stateman
  integration phase only.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- **`OdooTestContainer.start()`** (`packages/godoo-testcontainers/src/godoo_testcontainers/container.py:60`)
  — full container lifecycle. The new `TestHarness` composes this rather
  than reimplementing; addons mount and snapshot restore/save plug into
  the same flow.
- **`StartedOdooContainer.cleanup()`** (same file, `:33`) — already async,
  already wraps sync `container.stop()` calls in `asyncio.to_thread`. New
  `TestHarness.__aexit__` delegates to this.
- **`ModuleManager.install_module` / `is_module_installed`** (already used
  in `container.py:140-152`) — reused as-is by `h.modules.install(...)`.
- **`normalise_odoo_version` / `resolve_seed_info`** (`seed_resolver.py`)
  — keep; the snapshot key uses the normalised odoo version (D-Snap-1).
- **`SafetyContext`-free path** — `OdooTestContainer` builds an
  `OdooClient` without safety; this stays. Testcontainers is for tests,
  not prod safety guard exercises.
- **`asyncio.to_thread` wrapping pattern** — every new sync call (file IO,
  `subprocess`, `tempfile.replace`, `pg_dump` via `container.exec`) follows
  the same idiom already used in `container.py:65,77,91,...`.

### Established Patterns

- `from __future__ import annotations` at the top of every module.
- `TYPE_CHECKING` for `OdooClient` (if a new ConfigParameterService is
  created — see D-Harness-1 planner discretion).
- `cast()` at the `client.call()` / `search_read()` boundary to absorb
  `dict[str, Any]` returns when the new properties helper reads back
  values (if needed).
- One module quad per service: `types.py` (dataclasses) / `functions.py`
  (standalone async functions) / `service.py` (class wrapper) /
  `__init__.py` (barrel). Optional for the testcontainers-internal
  helper; mandatory if the helper lands in the godoo core client (planner
  discretion).
- Local-precondition-validation raising `OdooValidationError` BEFORE the
  RPC — applies to `h.properties.set("", value)` (empty key) and similar.
- Dataclasses-not-Pydantic for all new types (snapshot cache config,
  addons mount records, properties dict).
- Sync testcontainers + asyncio anti-pattern is the primary failure mode
  to avoid (called out in ARCHITECTURE.md anti-patterns).

### Integration Points

- `TestHarness` uses an authenticated `OdooClient` (from
  `OdooTestContainer.start()`) and a `ModuleManager` (already attached).
  No new client surface required.
- New addons mount: wires into the existing
  `DockerContainer(...).with_command(...)` builder in
  `OdooTestContainer.start()` — adds `--addons-path=...` to the command
  parts and adds `.with_volume_mapping(source, target, mode='ro')` for
  each mount.
- New snapshot save/restore: bind-mounts the cache dir into the postgres
  container, then calls `pg_dump` (save) or `dropdb && createdb &&
  pg_restore` (restore) via `pg.exec([...])` wrapped in
  `asyncio.to_thread`. Hooks into `OdooTestContainer.start()` AFTER
  postgres is up but BEFORE Odoo init/`--init base`: if the snapshot
  exists, skip the Odoo init phase entirely (the DB is already populated)
  and just start Odoo against the restored DB. Researcher confirms exact
  ordering.
- `py.typed` (TESTC-08): mechanical empty file at
  `packages/godoo-testcontainers/src/godoo_testcontainers/py.typed`,
  exactly like CLIENT-10 (D-19) and INTRO-07 in Phase 2.

</code_context>

<specifics>
## Specific Ideas

- **Owner's framing for the scope cut:** *"We have a parallel godoo-stateman
  project, I think testcontainers should do the bare minimum and we later
  add support for applying state manager scripts; avoid duplication of work
  and leverages what stateman will do."* This overturned the original
  ROADMAP success criterion 3 (`harness.partners.create / harness.projects.create
  / harness.users.create`) and the four-provisioner surface from SEED §2.
  The cut is deliberate: testcontainers becomes a thin container+module+param
  layer; richer seeding belongs to stateman's declarative Python DSL +
  7-stage reconcile pipeline.
- **Future testcontainers↔stateman integration is a separate phase.** Once
  `godoo-stateman` ships, a follow-on phase (post-v1 or v1.1) will add
  a hook on `TestHarness` to apply a stateman config inside the started
  container (e.g. `await h.apply_stateman(Path("test-state.py"))`). That
  phase is NOT in this milestone; the deferral is captured below.
- **TS reference is half-applicable.** Snapshot cache + addons mount in
  `../godoo-ts/packages/testcontainers/src/{snapshot-cache,odoo-container}.ts`
  are the design source-of-truth for those parts. The TS `provisioners/`
  directory is intentionally NOT a reference for this phase — that surface
  is stateman's.
- **`ir.config_parameter` is the entire "properties" surface.** No
  per-project task-property definitions, no JSON-typed columns, no
  multi-record relations. Just `set_param(key, value)` upsert and (if a
  consumer ever asks) `get_param(key)`.

</specifics>

<deferred>
## Deferred Ideas

- **`harness.apply_stateman(config_path)` hook** — apply a `godoo-stateman`
  config file inside the started container. Belongs in a post-v1
  integration phase, after `godoo-stateman` ships its first usable
  `apply` command. Captured here so it isn't lost; NOT this phase.
- **Partner / project / user / task-property provisioners (full TS-reference
  surface)** — partner categories, parent-by-name resolution, project
  stages, project tasks, group XML-IDs, task properties on
  `project.task_properties_definition`. All deferred to stateman; users
  who need them today use raw `client.create(...)` or wait for the
  stateman integration hook.
- **Full `AddonsMount` dataclass union** (per-mount target/mode
  customisation, rw mode for live-edit workflows) — out of scope for v1
  (D-Addons-1 planner-discretion note). Revisit when a real consumer
  asks.
- **Convenience overloads on `properties.set`** (int/bool/float → str
  coercion) — keep typing tight in v1 (str only); revisit if a consumer
  hits friction.
- **General-purpose `ConfigParameterService` on the godoo core client**
  — D-Harness-1 planner discretion leans testcontainers-internal for v1;
  promotion to a real godoo service can land later if state manager or
  another consumer needs it. No charter blocker.
- **`get_param` / `delete_param` on the properties helper** — only `set` /
  `set_many` requested in REQUIREMENTS TESTC-06; read/delete deferred
  until a consumer asks.
- **Snapshot save/restore via host-side `pg_dump`** (i.e. install pg_dump
  on the host and call it against the exposed port) — rejected in favour
  of TS-style `container.exec(['pg_dump', ...])` to avoid the host
  dependency. Not deferred so much as out of scope by design.
- **Multi-version Odoo snapshot sharing** — when seed images and live
  init coexist, the snapshot cache could share entries across compatible
  versions. Out of scope: snapshot key includes the exact odoo version
  (D-Snap-1) so each version gets its own snapshot.
- Pre-existing deferrals on record in REQUIREMENTS.md (v2 section) —
  COMPAT-01 (Python floor), CLIENT-V2-01 (auto re-auth), PERF-01/02 —
  remain untouched.

</deferred>

---

*Phase: 3-Testcontainers Parity*
*Context gathered: 2026-05-21*
