from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

# Alias to avoid pytest PytestCollectionWarning — pytest tries to collect any
# name matching python_classes pattern (default: Test*), but TestHarness has an
# __init__ and is not a test class. Using the alias keeps the import out of the
# collection scan without affecting runtime behaviour.
from godoo_testcontainers.harness import TestHarness as Harness

if TYPE_CHECKING:
    from pathlib import Path


class TestTestHarnessDefaults:
    def test_default_modules(self) -> None:
        assert Harness()._modules == []

    def test_default_properties(self) -> None:
        assert Harness()._properties == {}

    def test_default_snapshot(self) -> None:
        assert Harness()._snapshot is True

    def test_default_database(self) -> None:
        assert Harness()._database == "test_odoo"

    def test_default_admin_password(self) -> None:
        assert Harness()._admin_password == "admin"

    def test_default_addons_path(self) -> None:
        assert Harness()._addons_path is None

    def test_default_cache_dir(self) -> None:
        assert Harness()._cache_dir is None

    def test_default_env(self) -> None:
        assert Harness()._env == {}

    def test_default_startup_timeout(self) -> None:
        assert Harness()._startup_timeout == 300

    def test_started_initially_none(self) -> None:
        assert Harness()._started is None


class TestTestHarnessCustomParams:
    def test_custom_modules(self) -> None:
        h = Harness(modules=["project"])
        assert h._modules == ["project"]

    def test_custom_properties(self) -> None:
        h = Harness(properties={"a": "1"})
        assert h._properties == {"a": "1"}

    def test_snapshot_disabled(self) -> None:
        h = Harness(snapshot=False)
        assert h._snapshot is False

    def test_addons_path_single(self, tmp_path: Path) -> None:
        h = Harness(addons_path=tmp_path)
        assert h._addons_path == tmp_path

    def test_addons_path_list(self, tmp_path: Path) -> None:
        paths = [tmp_path / "a", tmp_path / "b"]
        h = Harness(addons_path=paths)
        assert h._addons_path == paths

    def test_custom_database(self) -> None:
        h = Harness(database="mydb")
        assert h._database == "mydb"

    def test_custom_admin_password(self) -> None:
        h = Harness(admin_password="secret")
        assert h._admin_password == "secret"

    def test_custom_env(self) -> None:
        h = Harness(env={"LOG_LEVEL": "debug"})
        assert h._env == {"LOG_LEVEL": "debug"}

    def test_custom_startup_timeout(self) -> None:
        h = Harness(startup_timeout=60)
        assert h._startup_timeout == 60

    def test_none_modules_normalised_to_empty_list(self) -> None:
        h = Harness(modules=None)
        assert h._modules == []

    def test_none_properties_normalised_to_empty_dict(self) -> None:
        h = Harness(properties=None)
        assert h._properties == {}

    def test_none_env_normalised_to_empty_dict(self) -> None:
        h = Harness(env=None)
        assert h._env == {}


class TestTestHarnessPropertyAccessorsUnstarted:
    def test_client_raises_before_start(self) -> None:
        h = Harness()
        with pytest.raises(AssertionError):
            _ = h.client

    def test_url_raises_before_start(self) -> None:
        h = Harness()
        with pytest.raises(AssertionError):
            _ = h.url

    def test_modules_raises_before_start(self) -> None:
        h = Harness()
        with pytest.raises(AssertionError):
            _ = h.modules

    def test_properties_raises_before_start(self) -> None:
        h = Harness()
        with pytest.raises(AssertionError):
            _ = h.properties
