---
name: godoo-py-verification
description: Verify godoo-py native checks, four installed wheels and disposable Odoo18 public behavior, or maintain this proof path after interface changes. Hosted policy, registry publication and deployment remain separate.
---

# Verify the Python libraries

Work in the explicitly selected godoo-py checkout. Read its AGENTS.md and
[contributing guide](../../../CONTRIBUTING.md). Establish HEAD, branch, dirty and
untracked state, checkout ownership and requested proof scope first. These
instructions grant no shared-state, publication or deployment authority.

## Prepare and choose the proof

Use uv 0.12.5, Python 3.14.8 and the committed `uv.lock`. The maintained
[check entrypoint](../../../scripts/check.py) works from any current directory:

```sh
/absolute/godoo-py/scripts/check.py --help
```

Choose external absolute paths for a new empty candidate directory and separate
proof directories. Respect owner-paths or explicit task destinations. Then run:

```sh
uv sync --frozen --all-packages --all-extras
./scripts/check.py offline --evidence /absolute/proof/offline
./scripts/check.py package --artifacts /absolute/candidate --evidence /absolute/proof/package
```

`offline` runs Ruff check/format, all three existing strict mypy roots, all
nonintegration tests under packages **and** tests, and a strict documentation
build. A test skip or empty collection fails this required invocation.

`package` builds all four wheels once with pinned Hatchling, exports hashed
locked dependencies and installs exact wheel files without dependencies or editable
links into an isolated consumer outside source. It checks all three namespaces'
import origins and `py.typed`, distribution versions and installed archive hashes and extracted file bytes,
metadata-only `godoo` with no dependencies, a public client `search_read` through
the supported transport factory, generated Pydantic output and the installed
`godoo-introspect --help`. The transport fixture proves the installed API and
codegen contract; it does not establish real server compatibility.

Keep the candidate immutable. `manifest.json` records source SHA, relevant tree
hash, dirty patch hash, lock/tools, versions and every wheel SHA256. A change to
source, scripts, tests, lock, docs or this skill invalidates reuse: rerun offline
and build into a new empty candidate directory. Never overwrite a tested set or
call a local wheel a published registry release.

## Exercise owned Odoo18

Docker must be available and owned disposable containers/networks permitted.
Inspect existing resources read-only; do not stop unrelated sessions. Run:

```sh
./scripts/check.py odoo18 --artifacts /absolute/candidate --evidence /absolute/proof/odoo18
```

The entrypoint checks Docker readiness, verifies candidate hashes/source, installs
those same wheels, copies root `tests/integration` and every package test directory (including
`godoo-testcontainers/tests/test_integration.py` and the client typed round trip) into the isolated consumer and
selects every integration-marked test. It overrides business connection/seed settings, disables shared Ryuk,
and owns only newly created containers, random networks, mapped ports, disposable
Postgres data and temporary snapshot/addon files. No external Odoo credentials are
used. Explicit wrong `ODOO_VERSION` values fail before provisioning.

The installed proof observer requests server version info after authentication,
asserts actual major 18 and records image IDs/digests, container/network IDs and
installed modules. Tests drive CRUD/readback/deletion, module queries, live
introspection/codegen, TestHarness property seeding, actual snapshot save/restore
and custom addon installation. These writes affect only disposable test databases.
Missing Docker, wrong major, empty selection, missing suite, any skip/failure or
unclean teardown fails. Read `integration.log`, JUnit, `observed-odoo.json`,
`resources.json` and `cleanup.json`; a listening container alone is insufficient.

On surprising failure, recheck Docker health and the observed server/image,
inspect retained logs, and distinguish missing readiness from a product defect.
The helper tracks exact run-owned IDs and attempts cleanup even after failure.
Confirm `cleanup.json` has no remaining IDs/errors/rescued leaks, and independently
query recorded IDs if execution was interrupted. Remove only recorded owned
resources; never prune Docker globally. Evidence lives outside temporary state
and survives the consumer and containers being removed.

Odoo17 is unsupported by these entrypoints. Odoo19 is optional and must use the
same candidate after successful18 with an explicit invocation:

```sh
./scripts/check.py odoo19 --artifacts /absolute/candidate --baseline18 /absolute/proof/odoo18 --evidence /absolute/proof/odoo19
```

A requested19 failure is a failed qualification; it is never a default18 claim.

## Consume proof and maintain the route

[Test](../../../.github/workflows/test.yml) runs offline, package and18 for PRs
and pushes to develop/main and manual validation, without path filters.
`required` runs always and requires each exact dependency to succeed.
[Release](../../../.github/workflows/release.yml) reuses that validation for an
immutable reviewed main SHA, checks all results against the wheel manifest, and
publishes only those tested bytes behind explicit `publish` and a protected
environment. Version preparation is a separate reviewable patch operation;
documentation remains an artifact. Local gate fixtures exercise rejection of
failed/skipped/cancelled/missing results and mismatched refs/artifacts/proof.
They do not establish GitHub branch protection or a configured trusted publisher.

Report actual command exits, test counts/skips, observed source/tree/wheel identity,
public behavior and checked cleanup. Separate local execution, hosted CI, remote
required-check enforcement, publication and user acceptance. Retain gaps through
the project's capture route (or return them to a parent who owns tracker writes).
No new tracker or evidence collection belongs in source.

For changed public interfaces, audit the affected instructions against source,
tests and delivery callers. Fix stale instructions or owned harness gaps and
rerun the affected public proof. Preserve expected behavior and failed evidence
for product regressions rather than relaxing assertions. Full skill authoring
uses the verification maker plus skill-creator; ordinary verification does not
change provenance, install plugins or start a schedule.
