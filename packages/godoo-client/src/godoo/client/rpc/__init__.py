"""RPC package — transport and types."""

from godoo.client.rpc.protocol import Transport
from godoo.client.rpc.transport import JsonRpcTransport
from godoo.client.rpc.types import OdooSessionInfo

__all__ = ["JsonRpcTransport", "OdooSessionInfo", "Transport"]
