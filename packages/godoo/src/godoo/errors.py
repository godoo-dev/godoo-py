from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from godoo.safety import OperationInfo


class OdooError(Exception):
    """Base class for all Odoo client errors."""

    def to_json(self) -> dict[str, Any]:
        return {
            "error": "ODOO_ERROR",
            "message": str(self),
            "details": None,
        }


class OdooRpcError(OdooError):
    """Generic RPC error returned by the Odoo server."""

    def __init__(
        self,
        message: str,
        *,
        code: int | None = None,
        data: dict[str, Any] | None = None,
        cause: Exception | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.data = data
        if cause is not None:
            self.__cause__ = cause

    def to_json(self) -> dict[str, Any]:
        return {
            "error": "RPC_ERROR",
            "message": str(self),
            "details": self.data,
        }


class OdooAuthError(OdooRpcError):
    """Authentication / AccessDenied error."""

    def __init__(
        self,
        message: str = "Authentication failed",
        *,
        code: int | None = None,
        data: dict[str, Any] | None = None,
        cause: Exception | None = None,
    ) -> None:
        super().__init__(message, code=code, data=data, cause=cause)

    def to_json(self) -> dict[str, Any]:
        result = super().to_json()
        result["error"] = "AUTH_ERROR"
        return result


class OdooNetworkError(OdooRpcError):
    """Network / connection error."""

    def to_json(self) -> dict[str, Any]:
        result = super().to_json()
        result["error"] = "NETWORK_ERROR"
        return result


class OdooTimeoutError(OdooNetworkError):
    """Request timeout."""

    def to_json(self) -> dict[str, Any]:
        result = super().to_json()
        result["error"] = "TIMEOUT_ERROR"
        return result


class OdooValidationError(OdooRpcError):
    """ValidationError or UserError from Odoo."""

    def to_json(self) -> dict[str, Any]:
        result = super().to_json()
        result["error"] = "VALIDATION_ERROR"
        return result


class OdooAccessError(OdooRpcError):
    """ACL violation."""

    def to_json(self) -> dict[str, Any]:
        result = super().to_json()
        result["error"] = "ACCESS_ERROR"
        return result


class OdooMissingError(OdooRpcError):
    """Record not found (MissingError)."""

    def to_json(self) -> dict[str, Any]:
        result = super().to_json()
        result["error"] = "MISSING_ERROR"
        return result


class OdooSafetyError(OdooError):
    """Local safety guard blocked the operation — NOT an RPC error."""

    def __init__(self, message: str, *, operation: OperationInfo) -> None:
        super().__init__(message)
        self.operation = operation

    def to_json(self) -> dict[str, Any]:
        op = self.operation
        return {
            "error": "SAFETY_BLOCKED",
            "message": str(self),
            "details": {
                "name": op.name,
                "level": op.level,
                "model": op.model,
                "description": op.description,
                "target": op.target,
                "details": op.details,
            },
        }
