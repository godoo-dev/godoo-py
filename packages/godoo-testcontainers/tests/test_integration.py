"""Docker-backed integration tests for the Phase 3 testcontainers-parity features.

These exercise the behaviors that unit tests cannot: a real Odoo+Postgres container
lifecycle via TestHarness (TESTC-07), ir.config_parameter seeding over JSON-RPC
(TESTC-06), the snapshot save/restore cache (TESTC-01), and custom addons mounting
with --addons-path discovery (TESTC-02).

Marked `integration` — require a Docker daemon. Run with:
    uv run pytest packages/godoo-testcontainers -m integration
Deselected from the default unit run (`-m "not integration"`).
"""

from __future__ import annotations

import os
import time
from typing import TYPE_CHECKING

import pytest
from godoo.errors import OdooValidationError
from godoo_testcontainers import TestHarness
from godoo_testcontainers.seed_resolver import normalise_odoo_version
from godoo_testcontainers.snapshot import has_snapshot, make_snapshot_config

if TYPE_CHECKING:
    from pathlib import Path

pytestmark = pytest.mark.integration


async def test_harness_lifecycle_and_properties() -> None:
    """TESTC-07 + TESTC-06: async-cm starts a ready client and seeds ir.config_parameter."""
    async with TestHarness(
        modules=["base"],
        properties={"godoo.test.seeded": "hello-world"},
        snapshot=False,
    ) as h:
        # Ready, authenticated client + url surface.
        assert isinstance(h.url, str) and h.url.startswith("http")
        user_count = await h.client.search_count("res.users")
        assert user_count >= 1

        # Property seeded on enter via set_many is readable back over RPC.
        seeded = await h.client.execute_kw("ir.config_parameter", "get_param", ["godoo.test.seeded"])
        assert seeded == "hello-world"

        # set() upserts a single key; set_many() applies a batch.
        await h.properties.set("godoo.test.single", "v1")
        await h.properties.set_many({"godoo.test.a": "1", "godoo.test.b": "2"})
        assert await h.client.execute_kw("ir.config_parameter", "get_param", ["godoo.test.single"]) == "v1"
        assert await h.client.execute_kw("ir.config_parameter", "get_param", ["godoo.test.a"]) == "1"
        assert await h.client.execute_kw("ir.config_parameter", "get_param", ["godoo.test.b"]) == "2"

        # Empty key is rejected locally before any RPC.
        with pytest.raises(OdooValidationError):
            await h.properties.set("", "nope")


async def test_snapshot_save_and_restore(tmp_path: Path) -> None:
    """TESTC-01: first run saves a pg_dump snapshot; an identical second run restores it."""
    cache_dir = tmp_path / "snapshots"
    odoo_ver = normalise_odoo_version(os.environ.get("ODOO_VERSION"))

    # The config the container computes internally for these exact inputs (D-Snap-1).
    cfg = make_snapshot_config(
        snapshot_enabled=True,
        cache_dir=cache_dir,
        odoo_version=odoo_ver,
        postgres_image="postgres:15-alpine",
        modules=["base"],
        addons_path=None,
        database="test_odoo",
        admin_password="admin",
        env={},
        properties={},
    )
    assert not has_snapshot(cfg), "cache must start cold"

    # First run: cold provision, snapshot saved on the way through.
    t0 = time.monotonic()
    async with TestHarness(modules=["base"], snapshot=True, cache_dir=cache_dir) as h:
        assert await h.client.search_count("res.users") >= 1
    first_run = time.monotonic() - t0

    # pg_dump actually executed and produced a restorable artifact.
    assert has_snapshot(cfg), "snapshot artifact should exist after the first run"

    # Second run with identical inputs hits the cache and restores cleanly.
    t1 = time.monotonic()
    async with TestHarness(modules=["base"], snapshot=True, cache_dir=cache_dir) as h:
        assert await h.client.search_count("res.users") >= 1
    second_run = time.monotonic() - t1

    # Restore should not be slower than a cold provision. Generous margin — absolute
    # timing is environment-dependent; the load-bearing assertion is the artifact above.
    assert second_run <= first_run * 1.5


async def test_custom_addons_mount(tmp_path: Path) -> None:
    """TESTC-02: a module in a mounted addons dir is discovered via --addons-path and installs."""
    addons_root = tmp_path / "addons"
    module_dir = addons_root / "godoo_test_addon"
    module_dir.mkdir(parents=True)
    (module_dir / "__init__.py").write_text("")
    (module_dir / "__manifest__.py").write_text(
        "{\n"
        "    'name': 'Godoo Test Addon',\n"
        "    'version': '1.0',\n"
        "    'depends': ['base'],\n"
        "    'installable': True,\n"
        "    'application': False,\n"
        "}\n"
    )

    async with TestHarness(
        modules=["godoo_test_addon"],
        addons_path=addons_root,
        snapshot=False,
    ) as h:
        assert await h.modules.is_module_installed("godoo_test_addon")
