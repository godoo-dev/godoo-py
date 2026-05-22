from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from godoo.testcontainers.container import OdooTestContainer, StartedOdooContainer
from godoo.testcontainers.properties import ConfigParameterHelper

if TYPE_CHECKING:
    from pathlib import Path

    from godoo.client import OdooClient
    from godoo.client.services.modules import ModuleManager

logger = logging.getLogger("godoo.testcontainers.harness")


class TestHarness:
    """Thin async context manager composing OdooTestContainer with module install and properties seeding."""

    def __init__(
        self,
        *,
        modules: list[str] | None = None,
        properties: dict[str, str] | None = None,
        addons_path: Path | list[Path] | None = None,
        snapshot: bool = True,
        cache_dir: Path | None = None,
        database: str = "test_odoo",
        admin_password: str = "admin",
        startup_timeout: int = 300,
        env: dict[str, str] | None = None,
    ) -> None:
        self._modules = modules if modules is not None else []
        self._properties = properties if properties is not None else {}
        self._addons_path = addons_path
        self._snapshot = snapshot
        self._cache_dir = cache_dir
        self._database = database
        self._admin_password = admin_password
        self._startup_timeout = startup_timeout
        self._env = env if env is not None else {}
        self._started: StartedOdooContainer | None = None

    async def __aenter__(self) -> TestHarness:
        container = OdooTestContainer(
            modules=self._modules,
            properties=self._properties,
            addons_path=self._addons_path,
            snapshot=self._snapshot,
            cache_dir=self._cache_dir,
            database=self._database,
            admin_password=self._admin_password,
            startup_timeout=self._startup_timeout,
            env=self._env,
        )
        self._started = await container.start()
        if self._properties:
            logger.info("Applying %d ir.config_parameter entries", len(self._properties))
            await self.properties.set_many(self._properties)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        if self._started is not None:
            await self._started.cleanup()

    @property
    def client(self) -> OdooClient:
        assert self._started is not None, "TestHarness not started — use 'async with TestHarness(...) as h:'"
        return self._started.client

    @property
    def url(self) -> str:
        assert self._started is not None, "TestHarness not started — use 'async with TestHarness(...) as h:'"
        return self._started.url

    @property
    def modules(self) -> ModuleManager:
        assert self._started is not None, "TestHarness not started — use 'async with TestHarness(...) as h:'"
        return self._started.module_manager

    @property
    def properties(self) -> ConfigParameterHelper:
        assert self._started is not None, "TestHarness not started — use 'async with TestHarness(...) as h:'"
        return ConfigParameterHelper(self._started.client)
