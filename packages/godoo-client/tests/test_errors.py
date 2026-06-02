from __future__ import annotations

from typing import Any, ClassVar

from godoo.client.errors import (
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
from godoo.client.safety import OperationInfo

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
        assert err.raw is None
        assert not hasattr(err, "data")
        assert err.__cause__ is None

    def test_stores_code_and_data(self) -> None:
        data = {"debug": "traceback here"}
        err = OdooRpcError("rpc error", code=200, data=data)
        assert err.code == 200
        assert err.raw is data

    def test_cause_sets_dunder_cause(self) -> None:
        cause = ValueError("socket error")
        err = OdooRpcError("rpc error", cause=cause)
        assert err.__cause__ is cause

    def test_to_json(self) -> None:
        err = OdooRpcError("rpc message", code=100, data={"key": "val"})
        result = err.to_json()
        assert result["error"] == "RPC_ERROR"
        assert result["message"] == "rpc message"
        assert "details" not in result
        assert result["human_message"] is None
        assert result["model_name"] is None
        assert "raw" not in result

    def test_to_json_no_data(self) -> None:
        err = OdooRpcError("rpc message", code=100)
        result = err.to_json()
        assert "details" not in result
        assert result["human_message"] is None


# ---------------------------------------------------------------------------
# OdooRpcError — Phase 9 structured fields (ERR-01 … ERR-05)
# ---------------------------------------------------------------------------


class TestOdooRpcErrorStructuredFields:
    """Tests for Phase 9 structured error surface (ERR-01 ... ERR-05)."""

    _FAULT_DATA: ClassVar[dict[str, Any]] = {
        "name": "odoo.exceptions.ValidationError",
        "debug": 'Traceback (most recent call last):\n  File "/opt/odoo/addons/account/models.py", line 42',
        "message": "The field 'name' is required.",
        "arguments": ("The field 'name' is required.",),
        "context": {},
    }

    # ERR-01: structured field access
    def test_human_message_extracted(self) -> None:
        err = OdooValidationError("Odoo Server Error", data=self._FAULT_DATA)
        assert err.human_message == "The field 'name' is required."

    def test_model_name_none_for_empty_context(self) -> None:
        err = OdooValidationError("Odoo Server Error", data=self._FAULT_DATA)
        assert err.model_name is None

    def test_field_name_none_for_empty_context(self) -> None:
        err = OdooValidationError("Odoo Server Error", data=self._FAULT_DATA)
        assert err.field_name is None

    def test_constraint_name_none_for_empty_context(self) -> None:
        err = OdooValidationError("Odoo Server Error", data=self._FAULT_DATA)
        assert err.constraint_name is None

    # ERR-02: privacy gate — no paths/tracebacks in str() or to_json()
    def test_no_server_path_in_str(self) -> None:
        err = OdooValidationError("Odoo Server Error", data=self._FAULT_DATA)
        assert "/opt/odoo" not in str(err)

    def test_no_server_path_in_to_json(self) -> None:
        err = OdooValidationError("Odoo Server Error", data=self._FAULT_DATA)
        assert "/opt/odoo" not in str(err.to_json())

    def test_windows_path_stripped(self) -> None:
        win_data: dict[str, Any] = {
            "name": "odoo.exceptions.ValidationError",
            "debug": 'Traceback (most recent call last):\n  File "C:\\odoo\\addons\\x.py", line 1',
            "message": 'Error in File "C:\\odoo\\addons\\x.py", line 1',
            "arguments": ('Error in File "C:\\odoo\\addons\\x.py", line 1',),
            "context": {},
        }
        err = OdooValidationError("Odoo Server Error", data=win_data)
        assert "C:\\odoo" not in str(err)
        assert "C:\\odoo" not in str(err.to_json())

    # ERR-03: .raw holds full original dict including data.debug
    def test_raw_holds_full_dict(self) -> None:
        err = OdooRpcError("msg", data=self._FAULT_DATA)
        assert err.raw is self._FAULT_DATA
        assert err.raw is not None
        assert "debug" in err.raw

    # ERR-04: to_json() never emits "raw" key
    def test_to_json_no_raw_key(self) -> None:
        for cls in [
            OdooRpcError,
            OdooAuthError,
            OdooValidationError,
            OdooAccessError,
            OdooMissingError,
            OdooNetworkError,
            OdooTimeoutError,
        ]:
            err = cls("test", data=self._FAULT_DATA)
            assert "raw" not in err.to_json()

    # ERR-05: .data removed; data= kwarg still accepted; .raw is the new name
    def test_data_attribute_removed(self) -> None:
        err = OdooRpcError("msg", data={"name": "x"})
        assert not hasattr(err, "data")
        assert err.raw == {"name": "x"}

    # D-13: __str__ fallback when no data
    def test_str_fallback_no_data(self) -> None:
        err = OdooAuthError("Not authenticated")
        assert str(err) == "Not authenticated"

    # D-13: __str__ returns human_message when present
    def test_str_returns_human_message(self) -> None:
        err = OdooRpcError("Odoo Server Error", data=self._FAULT_DATA)
        assert str(err) == "The field 'name' is required."

    # ERR-04: to_json() flat structured keys present; no "details" key
    def test_to_json_flat_keys(self) -> None:
        err = OdooValidationError("Odoo Server Error", data=self._FAULT_DATA)
        result = err.to_json()
        assert result["error"] == "VALIDATION_ERROR"
        assert "message" in result
        assert "model_name" in result
        assert "field_name" in result
        assert "constraint_name" in result
        assert "human_message" in result
        assert "details" not in result
        assert "raw" not in result


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
