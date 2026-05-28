"""mypy --strict on this file is the load-bearing assertion — runtime check is belt-and-braces."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from godoo.client.rpc.protocol import Transport

from godoo.client.rpc.transport import JsonRpcTransport


def test_jsonrpc_transport_satisfies_protocol() -> None:
    """Assert JsonRpcTransport satisfies the Transport Protocol structurally.

    The mypy --strict check on this file is the real assertion: the assignment
    ``t: Transport = JsonRpcTransport(...)`` is accepted by mypy only if
    JsonRpcTransport structurally conforms to every member of the Protocol.
    The runtime assertions are belt-and-braces.
    """
    t: Transport = JsonRpcTransport("http://example", "db")
    assert hasattr(t, "authenticate")
    assert hasattr(t, "call")
    assert hasattr(t, "aclose")
    assert hasattr(t, "logout")
    assert hasattr(t, "session")
