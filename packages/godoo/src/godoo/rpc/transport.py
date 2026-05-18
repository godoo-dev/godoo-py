"""JSON-RPC transport over httpx."""

from __future__ import annotations

import logging
import uuid
from typing import Any

import httpx

from godoo.errors import (
    OdooAccessError,
    OdooAuthError,
    OdooMissingError,
    OdooNetworkError,
    OdooRpcError,
    OdooValidationError,
)
from godoo.rpc.types import OdooSessionInfo

logger = logging.getLogger("godoo.client.rpc")


class JsonRpcTransport:
    """Async JSON-RPC transport backed by httpx.AsyncClient."""

    def __init__(self, base_url: str, db: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._db = db
        self._client = httpx.AsyncClient()
        self._session: OdooSessionInfo | None = None
        self._password: str | None = None

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def session(self) -> OdooSessionInfo | None:
        return self._session

    def is_authenticated(self) -> bool:
        return self._session is not None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

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
            raise OdooNetworkError(
                f"HTTP error {exc.response.status_code}: {exc.response.text}",
                cause=exc,
            ) from exc
        except httpx.RequestError as exc:
            raise OdooNetworkError(f"Connection error: {exc}", cause=exc) from exc

        data: dict[str, Any] = response.json()

        if "error" in data:
            raise self._categorize_error(data["error"])

        return data["result"]

    async def call(
        self,
        model: str,
        method: str,
        args: list[Any],
        kwargs: dict[str, Any],
    ) -> Any:
        """Call execute_kw on the Odoo object endpoint."""
        if self._session is None:
            raise OdooAuthError("Not authenticated")
        return await self.call_rpc(
            "object.execute_kw",
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
            },
        )

    def logout(self) -> None:
        """Clear session and password."""
        self._session = None
        self._password = None

    async def aclose(self) -> None:
        """Close the underlying httpx client."""
        await self._client.aclose()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _categorize_error(self, error_dict: dict[str, Any]) -> OdooRpcError:
        """Map a JSON-RPC error dict to a specific OdooRpcError subclass."""
        code: int | None = error_dict.get("code")
        message: str = error_dict.get("message", "Unknown RPC error")
        data: dict[str, Any] = error_dict.get("data") or {}

        exception_type: str = (data.get("exception_type") or "").lower()
        name: str = data.get("name") or ""

        # Check exception_type first
        if exception_type in ("access_denied",):
            return OdooAuthError(message, code=code, data=data)
        if exception_type in ("access_error",):
            return OdooAccessError(message, code=code, data=data)
        if exception_type in ("validation_error", "user_error"):
            return OdooValidationError(message, code=code, data=data)
        if exception_type in ("missing_error",):
            return OdooMissingError(message, code=code, data=data)

        # Fall back to data.name
        name_lower = name.lower()
        if "accessdenied" in name_lower:
            return OdooAuthError(message, code=code, data=data)
        if "accesserror" in name_lower:
            return OdooAccessError(message, code=code, data=data)
        if "validationerror" in name_lower or "usererror" in name_lower:
            return OdooValidationError(message, code=code, data=data)
        if "missingerror" in name_lower:
            return OdooMissingError(message, code=code, data=data)

        return OdooRpcError(message, code=code, data=data)
