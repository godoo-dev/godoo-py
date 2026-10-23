# Developing the Python libraries

This is a uv workspace of four distributions under `packages/`. Source packages
share the PEP 420 `godoo` namespace; do not add a top-level `godoo/__init__.py` or
teach users to import the metadata-only `godoo` distribution. Each wheel includes
only its own namespace subtree. Package manifests own names, Python requirements,
extras and entrypoints.

## Client, services and transport

`packages/godoo-client/src/godoo/client/client.py` owns CRUD, typed dispatch,
authentication and lazy service accessors. `config.py` reads connection variables
and builds authenticated clients. Always close an authenticated client with
`aclose()` or use the client's async context-manager interface.

`rpc/protocol.py` defines the transport interface and `rpc/transport.py` supplies
the httpx JSON-RPC implementation. `OdooClientConfig.transport_factory` is the
extension point for alternate transports; service code uses the client rather
than calling a transport directly. The keep-alive pooling fix in this transport
is deliberate; do not restore pooling without reproducing the original failure.

Services under `client/services/{name}/` contain input/output dataclasses,
standalone async functions with client first, and thin service classes. Accessors
use lazy imports/`cached_property`; use `TYPE_CHECKING` for annotation-only client
imports to avoid cycles. Core types remain dataclasses. Generated typed models
are the optional Pydantic exception; see [typed models](guides/typed-models.md).

Errors expose a structured caller surface and retain raw server faults for explicit
debugging. Treat `.raw` as sensitive. Changing error sanitization requires checking
both `str(exc)` and `to_json()`, not merely the exception class hierarchy.

## Introspection and containers

`godoo-introspection` discovers the actual instance schema and emits static model
files for editors/typecheckers. Generated output location and whether to commit it
are consumer choices. Invalidate stale schema after addon changes.

`godoo-testcontainers` supplies `OdooTestContainer`, `TestHarness` and snapshot
helpers. testcontainers-python is synchronous: container lifecycle work belongs
inside `asyncio.to_thread()`. Preserve cleanup on failure and keep seed/snapshot
keys sensitive to their configuration; a cache hit must describe the requested
Odoo state. Docker facilities do not run in a browser.

Use [contributing](https://github.com/godoo-dev/godoo-py/blob/develop/CONTRIBUTING.md) for offline checks and explicit integration
commands. CI requires Odoo18; optional19 qualification follows successful18 for the same
immutable wheels. Historical check output
and current acceptance are separate evidence. [Browser support](browser.md) is a
future packaging/interface decision, not a current install extra.
