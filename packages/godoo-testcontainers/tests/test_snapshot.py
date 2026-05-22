from __future__ import annotations

from typing import TYPE_CHECKING

from godoo_testcontainers.snapshot import (
    SnapshotConfig,
    _build_addons_cmd,
    compute_snapshot_key,
    make_snapshot_config,
)

if TYPE_CHECKING:
    from pathlib import Path

    import pytest


def _base_key_kwargs() -> dict[str, object]:
    """Return a minimal set of valid keyword arguments for compute_snapshot_key."""
    return {
        "odoo_version": "17.0",
        "postgres_image": "postgres:15-alpine",
        "modules": ["base"],
        "addons_path": None,
        "database": "test_odoo",
        "admin_password": "admin",
        "env": {},
        "properties": {},
        "user_key": "",
    }


class TestComputeSnapshotKey:
    def test_identical_inputs_same_key(self) -> None:
        kwargs = _base_key_kwargs()
        key1 = compute_snapshot_key(**kwargs)  # type: ignore[arg-type]
        key2 = compute_snapshot_key(**kwargs)  # type: ignore[arg-type]
        assert key1 == key2

    def test_different_modules_different_key(self) -> None:
        kwargs = _base_key_kwargs()
        key1 = compute_snapshot_key(**kwargs)  # type: ignore[arg-type]
        kwargs["modules"] = ["base", "crm"]
        key2 = compute_snapshot_key(**kwargs)  # type: ignore[arg-type]
        assert key1 != key2

    def test_modules_order_independent(self) -> None:
        """["crm", "project"] and ["project", "crm"] must produce the same key (sorted dedup)."""
        kwargs = _base_key_kwargs()
        kwargs["modules"] = ["crm", "project"]
        key1 = compute_snapshot_key(**kwargs)  # type: ignore[arg-type]
        kwargs["modules"] = ["project", "crm"]
        key2 = compute_snapshot_key(**kwargs)  # type: ignore[arg-type]
        assert key1 == key2

    def test_properties_included_in_key(self) -> None:
        """D-Snap-1: properties dict must affect the snapshot key."""
        kwargs = _base_key_kwargs()
        kwargs["properties"] = {"a": "1"}
        key1 = compute_snapshot_key(**kwargs)  # type: ignore[arg-type]
        kwargs["properties"] = {"a": "2"}
        key2 = compute_snapshot_key(**kwargs)  # type: ignore[arg-type]
        assert key1 != key2

    def test_properties_order_independent(self) -> None:
        """Properties dict is sorted before hashing — insertion order must not matter."""
        kwargs = _base_key_kwargs()
        kwargs["properties"] = {"b": "2", "a": "1"}
        key1 = compute_snapshot_key(**kwargs)  # type: ignore[arg-type]
        kwargs["properties"] = {"a": "1", "b": "2"}
        key2 = compute_snapshot_key(**kwargs)  # type: ignore[arg-type]
        assert key1 == key2

    def test_key_is_16_hex_chars(self) -> None:
        key = compute_snapshot_key(**_base_key_kwargs())  # type: ignore[arg-type]
        assert len(key) == 16
        assert all(c in "0123456789abcdef" for c in key)

    def test_user_key_changes_key(self) -> None:
        kwargs = _base_key_kwargs()
        key1 = compute_snapshot_key(**kwargs)  # type: ignore[arg-type]
        kwargs["user_key"] = "my-invalidation-token"
        key2 = compute_snapshot_key(**kwargs)  # type: ignore[arg-type]
        assert key1 != key2

    def test_env_order_independent(self) -> None:
        kwargs = _base_key_kwargs()
        kwargs["env"] = {"Z": "last", "A": "first"}
        key1 = compute_snapshot_key(**kwargs)  # type: ignore[arg-type]
        kwargs["env"] = {"A": "first", "Z": "last"}
        key2 = compute_snapshot_key(**kwargs)  # type: ignore[arg-type]
        assert key1 == key2


class TestSnapshotEnablement:
    def test_enabled_by_default(self) -> None:
        cfg = make_snapshot_config(
            snapshot_enabled=True,
            cache_dir=None,
            **_base_key_kwargs(),  # type: ignore[arg-type]
        )
        assert cfg.enabled is True

    def test_disabled_by_param(self) -> None:
        cfg = make_snapshot_config(
            snapshot_enabled=False,
            cache_dir=None,
            **_base_key_kwargs(),  # type: ignore[arg-type]
        )
        assert cfg.enabled is False

    def test_disabled_by_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """D-Snap-2: ODOO_TESTCONTAINERS_SNAPSHOT=disabled overrides snapshot_enabled=True."""
        monkeypatch.setenv("ODOO_TESTCONTAINERS_SNAPSHOT", "disabled")
        cfg = make_snapshot_config(
            snapshot_enabled=True,
            cache_dir=None,
            **_base_key_kwargs(),  # type: ignore[arg-type]
        )
        assert cfg.enabled is False

    def test_disabled_by_env_case_insensitive(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ODOO_TESTCONTAINERS_SNAPSHOT", "DISABLED")
        cfg = make_snapshot_config(
            snapshot_enabled=True,
            cache_dir=None,
            **_base_key_kwargs(),  # type: ignore[arg-type]
        )
        assert cfg.enabled is False

    def test_cache_dir_default_is_cwd_local(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """D-Snap-3: default cache dir is cwd/.odoo-testcontainers/snapshots/."""
        monkeypatch.chdir(tmp_path)
        # Unset env var in case it is set in the test environment.
        monkeypatch.delenv("ODOO_TESTCONTAINERS_SNAPSHOT_DIR", raising=False)
        cfg = make_snapshot_config(
            snapshot_enabled=True,
            cache_dir=None,
            **_base_key_kwargs(),  # type: ignore[arg-type]
        )
        assert ".odoo-testcontainers" in str(cfg.cache_dir)
        assert "snapshots" in str(cfg.cache_dir)

    def test_cache_dir_override_via_param(self, tmp_path: Path) -> None:
        cfg = make_snapshot_config(
            snapshot_enabled=True,
            cache_dir=tmp_path,
            **_base_key_kwargs(),  # type: ignore[arg-type]
        )
        assert cfg.cache_dir == tmp_path

    def test_cache_dir_override_via_env(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """D-Snap-2: ODOO_TESTCONTAINERS_SNAPSHOT_DIR overrides cache_dir param."""
        monkeypatch.setenv("ODOO_TESTCONTAINERS_SNAPSHOT_DIR", str(tmp_path))
        cfg = make_snapshot_config(
            snapshot_enabled=True,
            cache_dir=None,
            **_base_key_kwargs(),  # type: ignore[arg-type]
        )
        assert cfg.cache_dir == tmp_path


class TestBuildAddonsCmd:
    def test_none_returns_empty(self) -> None:
        mounts, targets = _build_addons_cmd(None)
        assert mounts == []
        assert targets == []

    def test_single_path(self, tmp_path: Path) -> None:
        """D-Addons-1: single Path → target /mnt/extra-addons."""
        mounts, targets = _build_addons_cmd(tmp_path)
        assert len(mounts) == 1
        assert targets == ["/mnt/extra-addons"]

    def test_list_of_paths(self, tmp_path: Path) -> None:
        """D-Addons-1: list of Paths → targets /mnt/addons-0, /mnt/addons-1, ..."""
        paths = [tmp_path / "a", tmp_path / "b"]
        mounts, targets = _build_addons_cmd(paths)
        assert targets == ["/mnt/addons-0", "/mnt/addons-1"]
        assert len(mounts) == 2

    def test_single_path_mode_is_ro(self, tmp_path: Path) -> None:
        """Addons directories are always mounted read-only."""
        mounts, _ = _build_addons_cmd(tmp_path)
        assert mounts[0][2] == "ro"

    def test_list_path_modes_are_ro(self, tmp_path: Path) -> None:
        paths = [tmp_path / "a", tmp_path / "b"]
        mounts, _ = _build_addons_cmd(paths)
        assert all(m[2] == "ro" for m in mounts)

    def test_single_path_host_src_is_resolved(self, tmp_path: Path) -> None:
        """T-03-02-01: resolved path prevents relative traversal."""
        mounts, _ = _build_addons_cmd(tmp_path)
        # resolved path is absolute
        from pathlib import Path as P

        assert P(mounts[0][0]).is_absolute()


class TestSnapshotConfigPaths:
    def test_host_path(self) -> None:
        from pathlib import Path as P

        cfg = SnapshotConfig(enabled=True, key="abc123def456789a", cache_dir=P("/tmp/snap"))
        assert cfg.host_path == P("/tmp/snap/abc123def456789a.dump")

    def test_container_path(self) -> None:
        from pathlib import Path as P

        cfg = SnapshotConfig(enabled=True, key="abc123def456789a", cache_dir=P("/tmp/snap"))
        assert cfg.container_path == "/snapshot-cache/abc123def456789a.dump"

    def test_host_path_uses_key(self) -> None:
        from pathlib import Path as P

        key = "0123456789abcdef"
        cfg = SnapshotConfig(enabled=True, key=key, cache_dir=P("/cache"))
        assert cfg.host_path.name == f"{key}.dump"

    def test_container_path_uses_key(self) -> None:
        from pathlib import Path as P

        key = "0123456789abcdef"
        cfg = SnapshotConfig(enabled=True, key=key, cache_dir=P("/cache"))
        assert cfg.container_path.endswith(f"{key}.dump")
