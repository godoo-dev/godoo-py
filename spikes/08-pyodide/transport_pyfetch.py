from __future__ import annotations

# NON-SHIPPING spike artifact — lives in spikes/08-pyodide/, not packages/*/src/.
# Exempt from the requires-python >=3.14 gate (D-09); runs under Pyodide CPython 3.13.
# Seeds BROWSER-F1 on a "go" verdict.  Never import godoo here (D-07).

import json
import uuid
from dataclasses import dataclass
from typing import Any

from pyodide.http import pyfetch  # bundled with Pyodide; unavailable on CPython host

# ---------------------------------------------------------------------------
# Local mirror of godoo.client.rpc.types.OdooSessionInfo
# Cannot `import godoo` under Pyodide (requires-python >=3.14 gate, D-07).
# Field names/types are kept identical so this can seed BROWSER-F1 unchanged.
# ---------------------------------------------------------------------------


@dataclass
class OdooSessionInfo:
    """Minimal mirror of godoo.client.rpc.types.OdooSessionInfo."""

    uid: int
    session_id: str
    db: str


# ---------------------------------------------------------------------------
# PyfetchTransport
# Structurally satisfies the 5-member Transport Protocol
# (packages/godoo-client/src/godoo/client/rpc/protocol.py).
# Mirrors the JsonRpcTransport happy-path wire shape but swaps
# httpx.AsyncClient.post for await pyfetch(...) (Emscripten has no POSIX sockets).
# Full _categorize_error parity is NOT required (research §Strategy 3);
# happy-path + raise-on-error is sufficient for spike evidence.
# ---------------------------------------------------------------------------


class PyfetchTransport:
    """Custom pyfetch-backed transport — strategy 3 (D-06) spike prototype.

    Construction is synchronous (no await in __init__) because transport_factory
    is a plain Callable[[OdooClientConfig], Transport] invoked once in
    OdooClient.__init__.  All network I/O lives in the async methods.

    Usage (standalone, no `import godoo`):
        t = PyfetchTransport("https://odoo.example.azurecontainerapps.io", "odoo")
        session = await t.authenticate("admin", "admin")
        result = await t.call("res.users", "read", [[session.uid]], {"fields": ["login", "name"]})
        t.logout()
        await t.aclose()

    Inject via transport_factory in a real godoo config (3.14 host only):
        OdooClientConfig(..., transport_factory=lambda cfg: PyfetchTransport(cfg.url, cfg.database))
    """

    def __init__(self, base_url: str, db: str) -> None:
        self._base = base_url.rstrip("/")
        self._db = db
        self._session: OdooSessionInfo | None = None
        self._password: str | None = None

    # ------------------------------------------------------------------
    # Transport Protocol — property
    # ------------------------------------------------------------------

    @property
    def session(self) -> OdooSessionInfo | None:
        """Return the current session, or None if not authenticated."""
        return self._session

    # ------------------------------------------------------------------
    # Transport Protocol — async methods
    # ------------------------------------------------------------------

    async def _rpc(self, params: dict[str, Any]) -> Any:
        """Low-level JSON-RPC POST via pyfetch.

        Mirrors JsonRpcTransport.call_rpc but swaps httpx.AsyncClient for pyfetch.
        NOTE: FetchResponse.json() is itself a coroutine — the double-await is
        mandatory (Pitfall 4 from research).
        """
        payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "id": 1,
            "params": params,
        }
        resp = await pyfetch(
            f"{self._base}/jsonrpc",
            method="POST",
            headers={"Content-Type": "application/json"},
            body=json.dumps(payload),
            # Do NOT set credentials='include' — godoo auth is in the body, not
            # cookies.  Keeps ACA corsPolicy allowCredentials=false valid (D-04).
        )
        data: dict[str, Any] = await resp.json()  # second await is mandatory
        if "error" in data:
            raise RuntimeError(data["error"])
        return data["result"]

    async def authenticate(self, username: str, password: str) -> OdooSessionInfo:
        """Authenticate against Odoo common.authenticate; returns OdooSessionInfo.

        Mirrors JsonRpcTransport.authenticate (transport.py lines 49-64).
        """
        uid = await self._rpc(
            {
                "service": "common",
                "method": "authenticate",
                "args": [self._db, username, password, {}],
            }
        )
        if not uid:
            raise RuntimeError("Authentication failed: invalid credentials or database")
        self._session = OdooSessionInfo(uid=uid, session_id=str(uuid.uuid4()), db=self._db)
        self._password = password
        return self._session

    async def call(self, model: str, method: str, args: list[Any], kwargs: dict[str, Any]) -> Any:
        """Call object.execute_kw.

        Mirrors JsonRpcTransport.call (transport.py lines 98-123).
        args ordering: [db, uid, password, model, method, args, kwargs].
        """
        if self._session is None:
            raise RuntimeError("Not authenticated — call authenticate() first")
        return await self._rpc(
            {
                "service": "object",
                "method": "execute_kw",
                "args": [
                    self._db,
                    self._session.uid,
                    self._password,
                    model,
                    method,
                    args,
                    kwargs,
                ],
            }
        )

    async def aclose(self) -> None:
        """No-op — pyfetch holds no persistent client to close."""
        return None

    # ------------------------------------------------------------------
    # Transport Protocol — sync method
    # ------------------------------------------------------------------

    def logout(self) -> None:
        """Clear session and stashed password synchronously.

        NOTE: logout() is the only *sync* member of the Transport Protocol.
        Mirrors JsonRpcTransport.logout (transport.py lines 125-127).
        """
        self._session = None
        self._password = None
