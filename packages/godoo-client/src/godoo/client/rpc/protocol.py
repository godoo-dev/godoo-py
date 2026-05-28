"""Structural transport contract — Protocol that JsonRpcTransport satisfies."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from godoo.client.rpc.types import OdooSessionInfo


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

    def logout(self) -> None: ...

    async def aclose(self) -> None: ...
