# Python library targets and language boundaries

These are development targets for godoo-py's client, introspection and disposable
test environments. They preserve the library intent consolidated on 22–27 October
2026; they are not a release matrix. The [usage guides](index.md) describe the
available interfaces. The [organization overview](https://github.com/godoo-dev/.github/blob/main/profile/README.md)
provides family orientation; normal use and checks require no online overview fetch.

## Baseline and useful outcomes

Odoo 18 is the default and required first integration target. Odoo 17 is not an
active support target. Later-major qualification follows the same candidate
passing Odoo 18 and retains version-specific limits. Disposable server proof does
not establish customer-instance or business acceptance.

The Python and [TypeScript libraries](https://github.com/godoo-dev/godoo-ts) aim for
equivalent useful outcomes with explicit differences, through idiomatic APIs.
Matching method names, implementations or every capability is not required.

- **Client:** authenticate and execute supported RPCs with clear transport and
  structured errors; provide ergonomic domains, context, pagination, relations
  and safety guards. Preserve dynamic/custom-model access alongside optional
  instance-derived typing, and make permission/unsupported-operation limits visible.
- **Introspection:** discover actual model/field metadata and generate useful
  native models, selections and relation information. Make cache freshness and
  explicit refresh clear; after addon changes obtain fresh metadata before
  validating dependent resources. See [typed models](guides/typed-models.md).
- **Testcontainers:** start disposable Odoo/PostgreSQL, wait for ORM readiness,
  install selected modules and reliably clean up owned resources. Support custom
  addons/configuration, a composable harness, ordinary seeding and snapshots with
  explicit restore/invalidation semantics. See [testing](testing.md).

Python uses the PEP 420 `godoo.*` namespaces, dataclass core types, optional
Pydantic generated models, async services and lazy service accessors. The `godoo`
distribution is metadata-only. [Development](development.md) owns these boundaries.
[Browser execution](browser.md) remains a future interface gated on a compatible
Python >=3.14 Pyodide runtime; the June spike is historical feasibility evidence.

## Explicit capability differences

TypeScript's `getServerInfo()`, `modules.inspectPrerequisites()` and structural
`inspectModulePrerequisites` contracts belong to its
[client guide](https://github.com/godoo-dev/godoo-ts/blob/develop/packages/client/README.md).
Its published client 0.7.0 account includes read-only dependency inspection,
install/upgrade postconditions and bounded classified lock retries. Those contracts
are not Python API promises. Python's current
[module service](services/modules.md) has its own methods and cron-lock retry
behavior; equivalent hardening would require scoped Python design and verification.

Useful generic future capabilities include read-only server/version discovery,
addon dependency inspection with explicit access-denied/incomplete states, and
verified install/upgrade/uninstall postconditions. Remote inspection cannot prove
addon source, catalog freshness or external system/Python prerequisite availability.
Keep read-only inspection separate from module refresh/install. Preserve relational
commands, context and safety-error propagation. Adoption, ownership and resource
ordering belong to Stateman rather than the client.

## Chatter and declarative state

The Python mail body-format extension `body_is_html` defaults to true for existing
HTML callers; explicit false requests Odoo's native literal-text escaping. As of
27 October 2026 this is an uncommitted local contribution, not part of the committed
release baseline. Preserve its pending integration/verification status. Clients do
not interpret Markdown; conversion belongs to the caller. The
[MCP server](https://github.com/godoo-dev/godoo-mcp-server) owns its separate
Markdown/HTML/text tool contract. Odoo retains permission and sanitization rules;
formatting does not change recipients or authorize retrying uncertain writes.

[Stateman](https://github.com/godoo-dev/godoo-stateman) owns the declarative state
engine and its [fixture/seeding interface](https://github.com/godoo-dev/godoo-stateman/blob/develop/docs/fixtures.md).
Python consumers invoke the installed CLI with bounded rendered JSON files and
checked subprocess status after readiness. No second Python Stateman engine is
promised, and testcontainers does not depend on Stateman. Container startup and
cleanup remain with the testcontainer owner.

Source, local checks, immutable installed wheels, publication and consumer
acceptance are separate evidence. Historical recovered correctness/capability
findings belong in project issues as re-triage leads, not confirmed defects or a
blanket parity commitment.
