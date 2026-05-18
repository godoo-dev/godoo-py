from __future__ import annotations

import json
from typing import TYPE_CHECKING

from godoo_testcontainers.seed_resolver import (
    SeedInfo,
    normalise_odoo_version,
    read_seed_config,
    resolve_seed_info,
)

if TYPE_CHECKING:
    from pathlib import Path

    import pytest


class TestNormaliseOdooVersion:
    def test_none_returns_17_0(self) -> None:
        assert normalise_odoo_version(None) == "17.0"

    def test_empty_string_returns_17_0(self) -> None:
        assert normalise_odoo_version("") == "17.0"

    def test_already_dotted_passthrough(self) -> None:
        assert normalise_odoo_version("18.0") == "18.0"

    def test_already_dotted_17(self) -> None:
        assert normalise_odoo_version("17.0") == "17.0"

    def test_bare_integer_17(self) -> None:
        assert normalise_odoo_version("17") == "17.0"

    def test_bare_integer_19(self) -> None:
        assert normalise_odoo_version("19") == "19.0"


class TestReadSeedConfig:
    def test_found_in_docker_subdir(self, tmp_path: Path) -> None:
        docker_dir = tmp_path / "docker"
        docker_dir.mkdir()
        config = {"versions": {"17.0": {"modules": ["base", "crm"]}}}
        (docker_dir / "seed-config.json").write_text(json.dumps(config))

        result = read_seed_config(str(tmp_path))
        assert result == config

    def test_not_found_returns_none(self, tmp_path: Path) -> None:
        result = read_seed_config(str(tmp_path))
        assert result is None

    def test_invalid_json_returns_none(self, tmp_path: Path) -> None:
        docker_dir = tmp_path / "docker"
        docker_dir.mkdir()
        (docker_dir / "seed-config.json").write_text("{ invalid json }")

        result = read_seed_config(str(tmp_path))
        assert result is None

    def test_found_two_levels_up(self, tmp_path: Path) -> None:
        # Create config two levels up from a nested cwd
        docker_dir = tmp_path / "docker"
        docker_dir.mkdir()
        config = {"versions": {"17.0": {"modules": ["base"]}}}
        (docker_dir / "seed-config.json").write_text(json.dumps(config))

        # cwd is tmp_path/a/b — two levels up is tmp_path
        nested = tmp_path / "a" / "b"
        nested.mkdir(parents=True)

        result = read_seed_config(str(nested))
        assert result == config


class TestResolveSeedInfo:
    def _write_config(self, tmp_path: Path, config: dict) -> None:
        docker_dir = tmp_path / "docker"
        docker_dir.mkdir(exist_ok=True)
        (docker_dir / "seed-config.json").write_text(json.dumps(config))

    def test_no_env_var_returns_none(self, tmp_path: Path) -> None:
        result = resolve_seed_info(
            ["base"],
            "17.0",
            seed_image_env=None,
            cwd=str(tmp_path),
        )
        assert result is None

    def test_no_config_file_returns_none(self, tmp_path: Path) -> None:
        result = resolve_seed_info(
            ["base"],
            "17.0",
            seed_image_env="myregistry/odoo-seed:17.0",
            cwd=str(tmp_path),
        )
        assert result is None

    def test_seed_covers_all_modules(self, tmp_path: Path) -> None:
        config = {"versions": {"17.0": {"modules": ["base", "crm", "sale"]}}}
        self._write_config(tmp_path, config)

        result = resolve_seed_info(
            ["base", "crm"],
            "17.0",
            seed_image_env="myregistry/odoo-seed:17.0",
            cwd=str(tmp_path),
        )
        assert result is not None
        assert result.seed_image == "myregistry/odoo-seed:17.0"
        assert result.seed_modules == ["base", "crm", "sale"]

    def test_seed_missing_modules_returns_none(self, tmp_path: Path) -> None:
        config = {"versions": {"17.0": {"modules": ["base"]}}}
        self._write_config(tmp_path, config)

        result = resolve_seed_info(
            ["base", "crm"],
            "17.0",
            seed_image_env="myregistry/odoo-seed:17.0",
            cwd=str(tmp_path),
        )
        assert result is None

    def test_version_not_in_config_returns_none(self, tmp_path: Path) -> None:
        config = {"versions": {"18.0": {"modules": ["base", "crm"]}}}
        self._write_config(tmp_path, config)

        result = resolve_seed_info(
            ["base"],
            "17.0",
            seed_image_env="myregistry/odoo-seed:17.0",
            cwd=str(tmp_path),
        )
        assert result is None

    def test_empty_requested_modules_is_covered(self, tmp_path: Path) -> None:
        config = {"versions": {"17.0": {"modules": ["base", "crm"]}}}
        self._write_config(tmp_path, config)

        result = resolve_seed_info(
            [],
            "17.0",
            seed_image_env="myregistry/odoo-seed:17.0",
            cwd=str(tmp_path),
        )
        assert result is not None
        assert isinstance(result, SeedInfo)

    def test_reads_env_var_from_environment(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        config = {"versions": {"17.0": {"modules": ["base"]}}}
        self._write_config(tmp_path, config)
        monkeypatch.setenv("ODOO_SEED_IMAGE", "env-registry/seed:17.0")

        result = resolve_seed_info(["base"], "17.0", cwd=str(tmp_path))
        assert result is not None
        assert result.seed_image == "env-registry/seed:17.0"

    def test_explicit_none_env_overrides_environment(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        config = {"versions": {"17.0": {"modules": ["base"]}}}
        self._write_config(tmp_path, config)
        monkeypatch.setenv("ODOO_SEED_IMAGE", "should-be-ignored")

        # seed_image_env=None means "check os.environ"
        result = resolve_seed_info(["base"], "17.0", seed_image_env=None, cwd=str(tmp_path))
        assert result is not None
        assert result.seed_image == "should-be-ignored"
