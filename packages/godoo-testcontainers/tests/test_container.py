from __future__ import annotations

from typing import TYPE_CHECKING

from godoo.testcontainers.container import OdooTestContainer

if TYPE_CHECKING:
    from pathlib import Path


class TestOdooTestContainerDefaults:
    def test_default_options(self) -> None:
        c = OdooTestContainer(properties={})
        assert c._modules == []
        assert c._database == "test_odoo"
        assert c._admin_password == "admin"
        assert c._startup_timeout == 300

    def test_default_env_is_empty(self) -> None:
        c = OdooTestContainer(properties={})
        assert c._env == {}

    def test_custom_options(self) -> None:
        c = OdooTestContainer(
            modules=["crm", "sale"],
            database="mydb",
            admin_password="secret",
            startup_timeout=120,
            properties={},
        )
        assert c._modules == ["crm", "sale"]
        assert c._database == "mydb"
        assert c._admin_password == "secret"
        assert c._startup_timeout == 120

    def test_custom_env(self) -> None:
        c = OdooTestContainer(env={"LOG_LEVEL": "debug"}, properties={})
        assert c._env == {"LOG_LEVEL": "debug"}

    def test_modules_default_is_independent(self) -> None:
        c1 = OdooTestContainer(properties={})
        c2 = OdooTestContainer(properties={})
        c1._modules.append("crm")
        assert c2._modules == []


class TestOdooTestContainerNewParams:
    def test_addons_path_default_none(self) -> None:
        c = OdooTestContainer(properties={})
        assert c._addons_path is None

    def test_snapshot_default_true(self) -> None:
        c = OdooTestContainer(properties={})
        assert c._snapshot_enabled is True

    def test_snapshot_false(self) -> None:
        c = OdooTestContainer(snapshot=False, properties={})
        assert c._snapshot_enabled is False

    def test_cache_dir_default_none(self) -> None:
        c = OdooTestContainer(properties={})
        assert c._cache_dir is None

    def test_addons_path_single(self, tmp_path: Path) -> None:
        c = OdooTestContainer(addons_path=tmp_path, properties={})
        assert c._addons_path == tmp_path

    def test_addons_path_list(self, tmp_path: Path) -> None:
        paths = [tmp_path / "a", tmp_path / "b"]
        c = OdooTestContainer(addons_path=paths, properties={})
        assert c._addons_path == paths

    def test_cache_dir_custom(self, tmp_path: Path) -> None:
        c = OdooTestContainer(cache_dir=tmp_path, properties={})
        assert c._cache_dir == tmp_path
