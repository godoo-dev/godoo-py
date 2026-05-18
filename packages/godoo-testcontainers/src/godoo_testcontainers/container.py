from __future__ import annotations

import asyncio
import contextlib
import logging
import os
from dataclasses import dataclass, field
from typing import Any

import httpx
from godoo import OdooClient, OdooClientConfig
from godoo.services.modules import ModuleManager
from testcontainers.core.container import DockerContainer
from testcontainers.core.network import Network
from testcontainers.core.waiting_utils import wait_for_logs
from testcontainers.postgres import PostgresContainer

from godoo_testcontainers.seed_resolver import normalise_odoo_version, resolve_seed_info

logger = logging.getLogger("godoo.testcontainers")


@dataclass
class StartedOdooContainer:
    odoo_container: DockerContainer
    postgres_container: Any  # PostgresContainer or DockerContainer
    client: OdooClient
    module_manager: ModuleManager
    url: str
    database: str
    _network: Network | None = field(default=None, repr=False)

    async def cleanup(self) -> None:
        logger.info("Cleaning up...")
        self.client.logout()
        for c in [self.odoo_container, self.postgres_container]:
            with contextlib.suppress(Exception):
                await asyncio.to_thread(c.stop)
        if self._network:
            with contextlib.suppress(Exception):
                await asyncio.to_thread(self._network.remove)


class OdooTestContainer:
    def __init__(
        self,
        *,
        modules: list[str] | None = None,
        database: str = "test_odoo",
        admin_password: str = "admin",
        startup_timeout: int = 300,
        env: dict[str, str] | None = None,
    ) -> None:
        self._modules = modules if modules is not None else []
        self._database = database
        self._admin_password = admin_password
        self._startup_timeout = startup_timeout
        self._env = env if env is not None else {}

    async def start(self) -> StartedOdooContainer:
        odoo_ver = normalise_odoo_version(os.environ.get("ODOO_VERSION"))
        seed_info = resolve_seed_info(self._modules, odoo_ver)

        network = Network()
        await asyncio.to_thread(network.create)

        try:
            # Postgres
            if seed_info:
                pg: Any = (
                    DockerContainer(seed_info.seed_image)
                    .with_env("SEED_DB_NAME", self._database)
                    .with_exposed_ports(5432)
                    .with_network(network)
                    .with_network_aliases("db")
                )
                await asyncio.to_thread(pg.start)
                await asyncio.to_thread(wait_for_logs, pg, "PostgreSQL init process complete; ready for start up.", 90)
                pg_user, pg_password = "admin", "admin"
            else:
                pg = (
                    PostgresContainer(
                        "postgres:15-alpine",
                        username="odoo",
                        password="odoo",
                        dbname=self._database,
                    )
                    .with_network(network)
                    .with_network_aliases("db")
                )
                await asyncio.to_thread(pg.start)
                pg_user, pg_password = "odoo", "odoo"

            # Odoo
            cmd_parts = ["--database", self._database, "--without-demo", "all", "--max-cron-threads", "0"]
            if not seed_info:
                cmd_parts[2:2] = ["--init", "base"]

            odoo = (
                DockerContainer(f"odoo:{odoo_ver}")
                .with_env("HOST", "db")  # network alias
                .with_env("PORT", "5432")
                .with_env("USER", pg_user)
                .with_env("PASSWORD", pg_password)
                .with_exposed_ports(8069)
                .with_command(" ".join(cmd_parts))
                .with_network(network)
            )
            for k, v in self._env.items():
                odoo = odoo.with_env(k, v)

            await asyncio.to_thread(odoo.start)

            host = odoo.get_container_host_ip()
            port = odoo.get_exposed_port(8069)
            url = f"http://{host}:{port}"

            try:
                await self._wait_for_odoo_ready(url, self._database)
            except TimeoutError:
                # Dump Odoo container logs for debugging
                try:
                    raw = await asyncio.to_thread(lambda: odoo.get_wrapped_container().logs())
                    logs = raw.decode("utf-8", errors="replace")
                    logger.error("Odoo container logs:\n%s", logs[-3000:])
                except Exception as log_err:
                    logger.error("Failed to get container logs: %s", log_err)
                raise

            client = OdooClient(
                OdooClientConfig(
                    url=url,
                    database=self._database,
                    username="admin",
                    password=self._admin_password,
                )
            )
            await client.authenticate()

            mm = ModuleManager(client)
            to_install = [m for m in self._modules if m not in seed_info.seed_modules] if seed_info else self._modules
            for mod in to_install:
                if not await mm.is_module_installed(mod):
                    logger.info("Installing module: %s", mod)
                    try:
                        await mm.install_module(mod)
                    except Exception:
                        # Module install can restart Odoo — wait for it to come back and retry
                        logger.info("Module install failed (server may have restarted), waiting...")
                        await self._wait_for_odoo_ready(url, self._database, max_attempts=60)
                        await client.authenticate()
                        await mm.install_module(mod)

            return StartedOdooContainer(
                odoo_container=odoo,
                postgres_container=pg,
                client=client,
                module_manager=mm,
                url=url,
                database=self._database,
                _network=network,
            )
        except Exception:
            with contextlib.suppress(Exception):
                await asyncio.to_thread(network.remove)
            raise

    async def _wait_for_odoo_ready(self, url: str, database: str, max_attempts: int = 120) -> None:
        payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {"db": database, "login": "admin", "password": self._admin_password},
        }
        async with httpx.AsyncClient() as http:
            for i in range(max_attempts):
                with contextlib.suppress(httpx.HTTPError):
                    resp = await http.post(f"{url}/web/session/authenticate", json=payload)
                    if resp.status_code == 200:
                        data = resp.json()
                        uid = data.get("result", {}).get("uid")
                        if uid:
                            logger.info("Odoo ready (attempt %d)", i + 1)
                            return
                await asyncio.sleep(2)
        raise TimeoutError("Odoo session handler did not become ready")
