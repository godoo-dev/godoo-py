from __future__ import annotations

from godoo.errors import (
    OdooAccessError,
    OdooAuthError,
    OdooError,
    OdooMissingError,
    OdooNetworkError,
    OdooRpcError,
    OdooSafetyError,
    OdooTimeoutError,
    OdooValidationError,
)
from godoo.safety import OperationInfo

# ---------------------------------------------------------------------------
# OdooError (base)
# ---------------------------------------------------------------------------


class TestOdooError:
    def test_is_exception(self) -> None:
        err = OdooError("something went wrong")
        assert isinstance(err, Exception)

    def test_to_json_shape(self) -> None:
        err = OdooError("base message")
        result = err.to_json()
        assert result["error"] == "ODOO_ERROR"
        assert result["message"] == "base message"
        assert result["details"] is None

    def test_to_json_returns_dict(self) -> None:
        err = OdooError("x")
        assert isinstance(err.to_json(), dict)


# ---------------------------------------------------------------------------
# OdooRpcError
# ---------------------------------------------------------------------------


class TestOdooRpcError:
    def test_inherits_odoo_error(self) -> None:
        err = OdooRpcError("rpc failed")
        assert isinstance(err, OdooError)

    def test_defaults(self) -> None:
        err = OdooRpcError("rpc failed")
        assert err.code is None
        assert err.data is None
        assert err.__cause__ is None

    def test_stores_code_and_data(self) -> None:
        data = {"debug": "traceback here"}
        err = OdooRpcError("rpc error", code=200, data=data)
        assert err.code == 200
        assert err.data == data

    def test_cause_sets_dunder_cause(self) -> None:
        cause = ValueError("socket error")
        err = OdooRpcError("rpc error", cause=cause)
        assert err.__cause__ is cause

    def test_to_json(self) -> None:
        err = OdooRpcError("rpc message", code=100, data={"key": "val"})
        result = err.to_json()
        assert result["error"] == "RPC_ERROR"
        assert result["message"] == "rpc message"
        assert result["details"] == {"key": "val"}

    def test_to_json_no_data(self) -> None:
        err = OdooRpcError("rpc message", code=100)
        result = err.to_json()
        assert result["details"] is None


# ---------------------------------------------------------------------------
# OdooAuthError
# ---------------------------------------------------------------------------


class TestOdooAuthError:
    def test_inherits_rpc_error(self) -> None:
        err = OdooAuthError()
        assert isinstance(err, OdooRpcError)
        assert isinstance(err, OdooError)

    def test_default_message(self) -> None:
        err = OdooAuthError()
        assert str(err) == "Authentication failed"

    def test_custom_message(self) -> None:
        err = OdooAuthError("bad credentials")
        assert str(err) == "bad credentials"

    def test_to_json_error_code(self) -> None:
        err = OdooAuthError()
        assert err.to_json()["error"] == "AUTH_ERROR"


# ---------------------------------------------------------------------------
# OdooNetworkError
# ---------------------------------------------------------------------------


class TestOdooNetworkError:
    def test_inherits_rpc_error(self) -> None:
        cause = ConnectionRefusedError("refused")
        err = OdooNetworkError("network down", cause=cause)
        assert isinstance(err, OdooRpcError)

    def test_sets_cause(self) -> None:
        cause = OSError("timed out")
        err = OdooNetworkError("conn failed", cause=cause)
        assert err.__cause__ is cause

    def test_to_json_error_code(self) -> None:
        err = OdooNetworkError("net error", cause=OSError())
        assert err.to_json()["error"] == "NETWORK_ERROR"


# ---------------------------------------------------------------------------
# OdooTimeoutError
# ---------------------------------------------------------------------------


class TestOdooTimeoutError:
    def test_inherits_network_error(self) -> None:
        err = OdooTimeoutError("timed out", cause=TimeoutError())
        assert isinstance(err, OdooNetworkError)
        assert isinstance(err, OdooRpcError)

    def test_to_json_error_code(self) -> None:
        err = OdooTimeoutError("timed out", cause=TimeoutError())
        assert err.to_json()["error"] == "TIMEOUT_ERROR"


# ---------------------------------------------------------------------------
# OdooValidationError
# ---------------------------------------------------------------------------


class TestOdooValidationError:
    def test_inherits_rpc_error(self) -> None:
        err = OdooValidationError("invalid value")
        assert isinstance(err, OdooRpcError)

    def test_to_json_error_code(self) -> None:
        err = OdooValidationError("invalid")
        assert err.to_json()["error"] == "VALIDATION_ERROR"


# ---------------------------------------------------------------------------
# OdooAccessError
# ---------------------------------------------------------------------------


class TestOdooAccessError:
    def test_inherits_rpc_error(self) -> None:
        err = OdooAccessError("access denied")
        assert isinstance(err, OdooRpcError)

    def test_to_json_error_code(self) -> None:
        err = OdooAccessError("denied")
        assert err.to_json()["error"] == "ACCESS_ERROR"


# ---------------------------------------------------------------------------
# OdooMissingError
# ---------------------------------------------------------------------------


class TestOdooMissingError:
    def test_inherits_rpc_error(self) -> None:
        err = OdooMissingError("record not found")
        assert isinstance(err, OdooRpcError)

    def test_to_json_error_code(self) -> None:
        err = OdooMissingError("not found")
        assert err.to_json()["error"] == "MISSING_ERROR"


# ---------------------------------------------------------------------------
# OdooSafetyError
# ---------------------------------------------------------------------------


class TestOdooSafetyError:
    def _make_op(self) -> OperationInfo:
        return OperationInfo(
            name="unlink",
            level="DELETE",
            model="res.partner",
            description="Delete partner records",
        )

    def test_inherits_odoo_error(self) -> None:
        err = OdooSafetyError("blocked", operation=self._make_op())
        assert isinstance(err, OdooError)

    def test_does_not_inherit_rpc_error(self) -> None:
        err = OdooSafetyError("blocked", operation=self._make_op())
        assert not isinstance(err, OdooRpcError)

    def test_stores_operation(self) -> None:
        op = self._make_op()
        err = OdooSafetyError("blocked", operation=op)
        assert err.operation is op

    def test_to_json_error_code(self) -> None:
        err = OdooSafetyError("blocked", operation=self._make_op())
        result = err.to_json()
        assert result["error"] == "SAFETY_BLOCKED"
        assert result["message"] == "blocked"

    def test_to_json_details_has_operation_info(self) -> None:
        op = self._make_op()
        err = OdooSafetyError("blocked", operation=op)
        result = err.to_json()
        assert result["details"] is not None
        details = result["details"]
        assert details["name"] == "unlink"
        assert details["level"] == "DELETE"
        assert details["model"] == "res.partner"
