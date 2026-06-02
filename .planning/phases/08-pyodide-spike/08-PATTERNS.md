# Phase 8: Pyodide Spike - Pattern Map

**Mapped:** 2026-06-02
**Files analyzed:** 7 (new spike artifacts + docs)
**Analogs found:** 1 strong (transport prototype) / 7

> **Spike, not shipping code.** Per D-09 every artifact below is *non-shipping committed
> evidence* under `spikes/08-pyodide/` (or phase `artifacts/`) plus phase docs. Nothing
> enters a published package; nothing is added to any `pyproject.toml` (D-06). The single
> file with a real in-repo analog is the custom `pyfetch` `AsyncTransport` prototype —
> its analogs are the **shipped** Transport Protocol + `JsonRpcTransport`. Everything else
> is a genuinely new surface (browser HTML, Azure Bicep, ADR/docs) with no codebase
> precedent; those are called out plainly under "No Analog Found".

## File Classification

| New File | Role | Data Flow | Closest Analog | Match Quality |
|----------|------|-----------|----------------|---------------|
| `spikes/08-pyodide/transport_pyfetch.py` | transport (prototype) | request-response (JSON-RPC over fetch) | `packages/godoo-client/src/godoo/client/rpc/transport.py` (`JsonRpcTransport`) + `.../rpc/protocol.py` (`Transport` Protocol) | **role + data-flow match (strong)** — structural conformance to the shipped Protocol; same wire path, different HTTP primitive (`pyfetch` vs `httpx.AsyncClient`) |
| `spikes/08-pyodide/index.html` | test harness (browser page) | request-response (in-browser) | — | no analog — new surface |
| `spikes/08-pyodide/infra/main.bicep` | config / infra (ACA + Postgres + CORS ingress) | n/a (IaC) | — | no analog — new surface |
| `spikes/08-pyodide/infra/selfdestruct.bicep` | config / infra (UAMI + role assignment + Logic App TTL) | event-driven (timer → ARM DELETE) | — | no analog — new surface |
| `spikes/08-pyodide/infra/deploy.md` (or `deploy.sh`) | docs / ops | n/a | — | no analog — new surface |
| `spikes/08-pyodide/README.md` | docs | n/a | — | no analog — new surface |
| `.planning/phases/08-pyodide-spike/08-SPIKE.md` | docs (evidence) | n/a | — | no analog — phase artifact |
| `docs/adr/0001-pyodide-browser-go-no-go.md` | docs (ADR / decision) | n/a | — | no analog — establishes new convention (no `docs/adr/` exists) |

**Source-path correction (load-bearing):** CLAUDE.md documents the RPC layer at
`packages/godoo-client/src/godoo/rpc/`. That path is **stale**. The real location is
`packages/godoo-client/src/godoo/client/rpc/` — verified by filesystem scan. All excerpts
below cite the real paths.

---

## Pattern Assignments

### `spikes/08-pyodide/transport_pyfetch.py` (transport prototype, request-response)

**This is the key file.** It must structurally satisfy the shipped `Transport` Protocol
(5 members) and mirror the happy-path wire shape of `JsonRpcTransport`, but swap
`httpx.AsyncClient` for `pyodide.http.pyfetch` (Emscripten has no POSIX sockets, so
`httpx` cannot do raw socket I/O — that is exactly what the spike proves with strategy 1).

**Analog A — the Protocol it must satisfy:**
`packages/godoo-client/src/godoo/client/rpc/protocol.py` (lines 11-34)

```python
class Transport(Protocol):
    """Structural type for transports OdooClient drives.

    JsonRpcTransport satisfies this Protocol without modification (D-06).
    Alternative transports (e.g. a future Pyodide pyfetch-backed transport,
    or a Mock for tests) only need to expose these five members.
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

    def logout(self) -> None: ...          # NOTE: sync — the only non-async member

    async def aclose(self) -> None: ...
```

The prototype must expose **exactly these 5 members** with these signatures. Note
`session` is a `@property`, `logout` is **sync**, the other three are `async`. The
Protocol's own docstring already names "a future Pyodide pyfetch-backed transport" as the
intended implementer — this spike builds that.

**Analog B — the session type it returns:**
`packages/godoo-client/src/godoo/client/rpc/types.py` (lines 8-12)

```python
@dataclass
class OdooSessionInfo:
    uid: int
    session_id: str
    db: str
```

The prototype mirrors this dataclass locally (it cannot `import godoo` under Pyodide's
CPython 3.13 — D-07; the package is `>=3.14`-gated). Keep field names/types identical so
it reads as godoo code and can seed BROWSER-F1 on a "go" verdict.

**Analog C — the wire path to replicate (happy path):**
`packages/godoo-client/src/godoo/client/rpc/transport.py`

`authenticate` (lines 49-64) — `common.authenticate`, builds `OdooSessionInfo` with a
`uuid4` session id, stashes the password:

```python
async def authenticate(self, username: str, password: str) -> OdooSessionInfo:
    """Authenticate against Odoo; returns OdooSessionInfo."""
    uid = await self.call_rpc(
        "common.authenticate",
        {
            "service": "common",
            "method": "authenticate",
            "args": [self._db, username, password, {}],
        },
    )
    if not uid:
        raise OdooAuthError("Authentication failed: invalid credentials or database")

    self._session = OdooSessionInfo(uid=uid, session_id=str(uuid.uuid4()), db=self._db)
    self._password = password
    return self._session
```

`call_rpc` (lines 66-96) — the POST-to-`/jsonrpc` envelope the prototype must mirror
(the prototype swaps `self._client.post(...)` for `await pyfetch(...)` and `response.json()`
for `await resp.json()` — `FetchResponse.json()` is itself awaitable):

```python
async def call_rpc(self, method: str, params: dict[str, Any]) -> Any:
    """Low-level JSON-RPC POST to /jsonrpc."""
    payload = {
        "jsonrpc": "2.0",
        "method": "call",
        "id": 1,
        "params": params,
    }
    logger.debug("JSON-RPC call: method=%s", method)
    try:
        response = await self._client.post(
            f"{self._base_url}/jsonrpc",
            json=payload,
        )
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise OdooNetworkError(...)
    except httpx.TimeoutException as exc:
        raise OdooTimeoutError(...)
    except httpx.RequestError as exc:
        raise OdooNetworkError(...)

    data: dict[str, Any] = response.json()

    if "error" in data:
        raise self._categorize_error(data["error"])

    return data["result"]
```

`call` (lines 98-123) — `object.execute_kw`, the args ordering the prototype must copy
verbatim:

```python
async def call(self, model, method, args, kwargs) -> Any:
    if self._session is None:
        raise OdooAuthError("Not authenticated")
    return await self.call_rpc(
        "object.execute_kw",
        {
            "service": "object",
            "method": "execute_kw",
            "args": [self._db, self._session.uid, self._password, model, method, args, kwargs],
        },
    )
```

`logout` / `aclose` (lines 125-132) — `logout` is sync (clears session + password);
`aclose` closes the client (the prototype's `aclose` is a no-op — `pyfetch` holds no
client to close):

```python
def logout(self) -> None:
    self._session = None
    self._password = None

async def aclose(self) -> None:
    await self._client.aclose()
```

**Construction seam — `transport_factory`:**
`packages/godoo-client/src/godoo/client/client.py` (lines 91, 97-102)

```python
# OdooClientConfig field (line 91):
transport_factory: Callable[[OdooClientConfig], Transport] | None = field(default=None)

# OdooClient.__init__ (lines 99-102) — called ONCE, synchronously:
if config.transport_factory is not None:
    self._transport: Transport = config.transport_factory(config)
else:
    self._transport = JsonRpcTransport(config.url, config.database, timeout=config.timeout)
```

**Critical structural constraint for the prototype:** the factory is a **synchronous**
`Callable[[OdooClientConfig], Transport]` invoked once in `__init__`. The prototype must
therefore be **constructible synchronously** — no `await` in `__init__`; all network work
happens inside the async `authenticate`/`call` methods. (Phase 6 deferred an async
transport factory; the spike confirms sync construction suffices.)

**Divergences from the analog the prototype is ALLOWED (D-09 / research §Strategy 3):**
- Swap `httpx.AsyncClient` → `pyodide.http.pyfetch`; remember the **second `await`** on
  `resp.json()` (the classic pyfetch bug — Pitfall 4).
- May simplify error categorization: full `_categorize_error` (transport.py lines 138-168)
  parity is **not required** for evidence. Mirroring the happy path + raising on
  `"error" in data` is sufficient (research §Strategy 3 wire path).
- Local `OdooSessionInfo` mirror instead of importing godoo (D-07).
- Need NOT target Python 3.14 / pass mypy-strict (it lives outside `src/`; D-09). It
  SHOULD still follow style conventions (`from __future__ import annotations` first line,
  ruff format) so it reads as godoo code.

---

## Shared Patterns

### Async transport surface (the only cross-cutting code pattern)
**Source:** `packages/godoo-client/src/godoo/client/rpc/protocol.py` (Transport Protocol)
**Apply to:** `transport_pyfetch.py` only (it is the sole code artifact in this spike).
The 5-member structural contract above is the whole shared surface. There is no auth
middleware, validation layer, or error-wrapper pattern to propagate — the spike has
exactly one Python class.

### Project style conventions (from CLAUDE.md — apply to the prototype only)
- `from __future__ import annotations` as the first line.
- Dataclasses, not Pydantic (the local `OdooSessionInfo` mirror is a `@dataclass`).
- All network methods `async`; `logout` stays sync to match the Protocol.
- ruff line-length 120; `ruff format`. **Exception:** the prototype is non-shipping
  (D-09) — it lives outside `packages/*/src/`, so it is NOT in the mypy-strict set and
  need NOT satisfy `requires-python >=3.14`. Planner decides whether to lint `spikes/`.

---

## No Analog Found

These artifacts have no in-repo precedent. The planner should drive them from RESEARCH.md
(which carries concrete Bicep/CORS/Logic-App snippets and the ADR convention) rather than
from any codebase analog.

| File | Role | Data Flow | Reason — drive from RESEARCH.md section |
|------|------|-----------|------------------------------------------|
| `spikes/08-pyodide/index.html` | browser test harness | request-response | No HTML / browser surface exists anywhere in this Python monorepo. New surface. Use RESEARCH.md §"The Three Transport Strategies" + §Code Examples (`pyfetch` POST recipe) for the three-strategy runner. |
| `spikes/08-pyodide/infra/main.bicep` | infra (ACA + multi-container Postgres + CORS ingress) | IaC | No Azure / Bicep / IaC anywhere in repo. New surface. Use RESEARCH.md §"Azure Throwaway Endpoint" (verified `ingress.corsPolicy` block, multi-container pod topology, `minReplicas:1` reconciliation per Pitfall 1). |
| `spikes/08-pyodide/infra/selfdestruct.bicep` | infra (UAMI + RG-scoped Contributor + Logic App TTL) | event-driven (timer → ARM RG DELETE) | New surface. Use RESEARCH.md §"Self-destruct" (verified UAMI + `roleAssignments` Bicep with `principalType: 'ServicePrincipal'`, built-in Contributor GUID `b24988ac-…`, ARM DELETE REST recipe). Logic App preferred over ACA Job (D-05). |
| `spikes/08-pyodide/infra/deploy.md` | ops docs | n/a | New surface. `az` deploy + manual `az group delete` backstop (NOT GitHub Actions — D-05). |
| `spikes/08-pyodide/README.md` | docs | n/a | New surface. How to run the spike + where the verdict lives. |
| `.planning/phases/08-pyodide-spike/08-SPIKE.md` | evidence doc | n/a | Phase artifact. Structure from RESEARCH.md §"Validation Architecture" (per-strategy worked/failed 3-row table with verbatim tracebacks, Python-floor section, devtools Network evidence). |
| `docs/adr/0001-pyodide-browser-go-no-go.md` | ADR / decision | n/a | **No `docs/adr/` exists — confirmed by scan.** This phase ESTABLISHES the convention (MADR-style, add to `mkdocs.yml` nav). Assumption A1 — flag at plan/discuss. Holds the durable go/no-go (status `accepted`); references `08-SPIKE.md` for evidence (D-08 evidence/decision split). |

---

## Metadata

**Analog search scope:** `packages/godoo-client/src/godoo/client/rpc/` (protocol.py,
transport.py, types.py), `packages/godoo-client/src/godoo/client/client.py`; plus
existence scans of `docs/adr/` and `spikes/` (both absent).
**Files scanned:** 4 source files read in full + 2 directory existence checks.
**Key finding:** Only `transport_pyfetch.py` has a real analog (the shipped Transport
Protocol + `JsonRpcTransport`). The HTML, Bicep, and docs are new surfaces with no
codebase precedent — the planner draws those from RESEARCH.md's verified snippets.
**Path correction:** RPC layer is `godoo/client/rpc/`, NOT `godoo/rpc/` (CLAUDE.md stale).
**Pattern extraction date:** 2026-06-02
```