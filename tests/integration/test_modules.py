from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from godoo_testcontainers import StartedOdooContainer


@pytest.mark.integration
class TestModulesIntegration:
    async def test_list_installed_modules(self, odoo: StartedOdooContainer) -> None:
        installed = await odoo.module_manager.list_modules(state="installed")
        assert len(installed) > 0
        names = [m["name"] for m in installed]
        assert "base" in names

    async def test_is_module_installed(self, odoo: StartedOdooContainer) -> None:
        assert await odoo.module_manager.is_module_installed("base") is True
        assert await odoo.module_manager.is_module_installed("nonexistent_module_xyz") is False

    async def test_get_module_info(self, odoo: StartedOdooContainer) -> None:
        info = await odoo.module_manager.get_module_info("base")
        assert info["name"] == "base"
        assert info["state"] == "installed"
