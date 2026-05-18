from __future__ import annotations

from godoo.safety import (
    OperationInfo,
    SafetyContext,
    get_default_safety_context,
    infer_safety_level,
    resolve_safety_context,
    set_default_safety_context,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _dummy_confirm(op: OperationInfo) -> bool:
    return True


def _make_ctx() -> SafetyContext:
    return SafetyContext(confirm=_dummy_confirm)


# ---------------------------------------------------------------------------
# infer_safety_level
# ---------------------------------------------------------------------------


class TestInferSafetyLevel:
    def test_read_methods(self) -> None:
        read_methods = [
            "search",
            "read",
            "search_read",
            "search_count",
            "fields_get",
            "name_get",
            "name_search",
            "default_get",
            "onchange",
            "load_views",
            "check_access_rights",
            "check_access_rule",
            "read_group",
        ]
        for method in read_methods:
            assert infer_safety_level(method) == "READ", f"{method} should be READ"

    def test_delete_methods(self) -> None:
        assert infer_safety_level("unlink") == "DELETE"

    def test_write_methods(self) -> None:
        for method in ("write", "create", "copy", "action_confirm", "custom_method"):
            assert infer_safety_level(method) == "WRITE", f"{method} should be WRITE"

    def test_unknown_method_is_write(self) -> None:
        assert infer_safety_level("some_random_method") == "WRITE"


# ---------------------------------------------------------------------------
# OperationInfo
# ---------------------------------------------------------------------------


class TestOperationInfo:
    def test_required_fields(self) -> None:
        op = OperationInfo(
            name="write",
            level="WRITE",
            model="sale.order",
            description="Update sale order",
        )
        assert op.name == "write"
        assert op.level == "WRITE"
        assert op.model == "sale.order"
        assert op.description == "Update sale order"

    def test_optional_fields_default_to_none(self) -> None:
        op = OperationInfo(
            name="read",
            level="READ",
            model="res.partner",
            description="Read partners",
        )
        assert op.target is None
        assert op.details is None

    def test_optional_fields_can_be_set(self) -> None:
        op = OperationInfo(
            name="unlink",
            level="DELETE",
            model="res.partner",
            description="Delete records",
            target="id=42",
            details={"count": 1},
        )
        assert op.target == "id=42"
        assert op.details == {"count": 1}


# ---------------------------------------------------------------------------
# resolve_safety_context
# ---------------------------------------------------------------------------


class TestResolveSafetyContext:
    def setup_method(self) -> None:
        # always start clean
        set_default_safety_context(None)

    def teardown_method(self) -> None:
        set_default_safety_context(None)

    def test_client_context_wins_over_global(self) -> None:
        global_ctx = _make_ctx()
        client_ctx = _make_ctx()
        set_default_safety_context(global_ctx)
        result = resolve_safety_context(client_ctx)
        assert result is client_ctx

    def test_none_client_context_disables(self) -> None:
        global_ctx = _make_ctx()
        set_default_safety_context(global_ctx)
        result = resolve_safety_context(None)
        assert result is None

    def test_undefined_falls_back_to_global(self) -> None:
        global_ctx = _make_ctx()
        set_default_safety_context(global_ctx)
        result = resolve_safety_context(undefined=True)
        assert result is global_ctx

    def test_no_context_returns_none(self) -> None:
        result = resolve_safety_context(undefined=True)
        assert result is None

    def test_client_none_explicitly_disables_global(self) -> None:
        global_ctx = _make_ctx()
        set_default_safety_context(global_ctx)
        # Passing None as client_context explicitly disables safety
        result = resolve_safety_context(None)
        assert result is None


# ---------------------------------------------------------------------------
# set/get default safety context
# ---------------------------------------------------------------------------


class TestDefaultSafetyContext:
    def setup_method(self) -> None:
        set_default_safety_context(None)

    def teardown_method(self) -> None:
        set_default_safety_context(None)

    def test_default_is_none(self) -> None:
        assert get_default_safety_context() is None

    def test_round_trip(self) -> None:
        ctx = _make_ctx()
        set_default_safety_context(ctx)
        assert get_default_safety_context() is ctx

    def test_can_clear(self) -> None:
        ctx = _make_ctx()
        set_default_safety_context(ctx)
        set_default_safety_context(None)
        assert get_default_safety_context() is None

    def test_overwrite(self) -> None:
        ctx1 = _make_ctx()
        ctx2 = _make_ctx()
        set_default_safety_context(ctx1)
        set_default_safety_context(ctx2)
        assert get_default_safety_context() is ctx2
