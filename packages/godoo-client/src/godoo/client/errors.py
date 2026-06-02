from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from godoo.client.safety import OperationInfo

# -- Path-stripping patterns (D-03, D-15) ------------------------------------
_POSIX_PATH_RE = re.compile(r'File "(/[^"]+)"')
_WIN_PATH_RE = re.compile(r'File "([A-Za-z]:[^"]+)"')


def _strip_paths(text: str) -> str:
    """Replace filesystem paths embedded in Python traceback format strings."""
    text = _POSIX_PATH_RE.sub('File "<server-path>"', text)
    text = _WIN_PATH_RE.sub('File "<server-path>"', text)
    return text


def _extract_human_message(data: dict[str, Any] | None) -> str | None:
    """Return clean human-readable message from fault data, path-stripped as defense-in-depth."""
    if not data:
        return None
    msg: str | None = data.get("message") or None
    if not msg:
        args = data.get("arguments")
        msg = args[0] if args else None
    if msg:
        msg = _strip_paths(msg)
    return msg or None


def _extract_model_name(data: dict[str, Any] | None) -> str | None:
    """Extract Odoo model technical name from fault context dict (e.g. 'res.partner').

    Standard Odoo 17/18/19 exceptions have context={} — returns None in the common case.
    """
    if not data:
        return None
    ctx = data.get("context") or {}
    return ctx.get("odoo_model") or ctx.get("model") or None


def _extract_field_name(data: dict[str, Any] | None) -> str | None:
    """Extract field technical name from fault context dict (e.g. 'email')."""
    if not data:
        return None
    ctx = data.get("context") or {}
    return ctx.get("field") or ctx.get("field_name") or None


def _extract_constraint_name(data: dict[str, Any] | None) -> str | None:
    """Extract SQL constraint name from fault context dict (e.g. 'res_partner_name_uniq')."""
    if not data:
        return None
    ctx = data.get("context") or {}
    return ctx.get("constraint") or ctx.get("constraint_name") or None


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
        data: dict[str, Any] | None = None,  # kwarg name PRESERVED for transport.py compat (D-06)
        cause: Exception | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.raw: dict[str, Any] | None = data  # RENAMED from self.data (D-05)
        self.human_message: str | None = _extract_human_message(data)
        self.model_name: str | None = _extract_model_name(data)
        self.field_name: str | None = _extract_field_name(data)
        self.constraint_name: str | None = _extract_constraint_name(data)
        if cause is not None:
            self.__cause__ = cause

    def __str__(self) -> str:
        return self.human_message or self.args[0]  # D-13: never exposes data.debug

    def to_json(self) -> dict[str, Any]:
        return {
            "error": "RPC_ERROR",
            "message": str(self),
            "model_name": self.model_name,
            "field_name": self.field_name,
            "constraint_name": self.constraint_name,
            "human_message": self.human_message,
            # NO "details" key (removed — was leaking raw payload)
            # NO "raw" key (security gate D-09 — .raw is attribute-only)
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
