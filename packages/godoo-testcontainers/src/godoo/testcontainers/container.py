from __future__ import annotations

import asyncio
import contextlib
import logging
import os
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path

import httpx
from godoo.client import OdooClient, OdooClientConfig
from godoo.client.errors import OdooNetworkError, OdooTimeoutError
from godoo.client.services.modules import ModuleManager
from godoo.testcontainers.seed_resolver import SeedInfo, normalise_odoo_version, resolve_seed_info
from godoo.testcontainers.snapshot import (
    ODOO_CORE_ADDONS_PATH,
    SnapshotConfig,
    _build_addons_cmd,
    has_snapshot,
    make_snapshot_config,
    restore_snapshot,
    save_snapshot,
)

from testcontainers.core.container import DockerContainer
from testcontainers.core.network import Network
from testcontainers.core.waiting_utils import wait_for_logs
from testcontainers.postgres import PostgresContainer

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
        with contextlib.suppress(Exception):
            self.client.logout()
        # CR-02: logout() only clears the in-memory session; aclose() releases the
        # underlying httpx.AsyncClient pool. OdooClient exposes no __aexit__, so the
        # harness is the only place that can close it — otherwise sockets/fds leak.
        with contextlib.suppress(Exception):
            await self.client.aclose()
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
        addons_path: Path | list[Path] | None = None,
        snapshot: bool = True,
        cache_dir: Path | None = None,
        env: dict[str, str] | None = None,
        properties: dict[str, str],
    ) -> None:
        self._modules = modules if modules is not None else []
        self._database = database
        self._admin_password = admin_password
        self._startup_timeout = startup_timeout
        self._addons_path = addons_path
        self._snapshot_enabled = snapshot
        self._cache_dir = cache_dir
        self._env = env if env is not None else {}
        # Stored for snapshot key accuracy only — the container does NOT call set_param.
        # TestHarness passes its properties dict here so different properties produce
        # a different snapshot key (D-Snap-1), ensuring correct cache invalidation.
        #
        # WR-03: `properties` is a KEY-ONLY input. It influences the snapshot key but is
        # NOT seeded into the database by `start()`, so a saved dump does NOT contain the
        # advertised ir.config_parameter rows. TestHarness reconciles this by calling
        # `properties.set_many()` after `start()` returns on every entry (including cache
        # hits). Direct `OdooTestContainer` users who pass `properties` therefore get a
        # snapshot keyed on properties they must seed themselves — the container will not
        # apply them. Use TestHarness if you want properties seeded automatically.
        #
        # Required keyword arg (no default) so callers are explicit about their snapshot
        # key inputs (DEBT-04 breaking change). Pass properties={} if your setup has no
        # ir.config_parameter entries.
        self._properties_for_key: dict[str, str] = properties

    async def start(self) -> StartedOdooContainer:
        odoo_ver = normalise_odoo_version(os.environ.get("ODOO_VERSION"))
        seed_info = resolve_seed_info(self._modules, odoo_ver)

        # Snapshot caching applies to the cold postgres:15-alpine path only.
        # When seed_info is resolved, the seed image acts as its own fast path
        # and snapshot caching is skipped (see 03-RESEARCH.md Open Question 4).
        snapshot_enabled = self._snapshot_enabled and (seed_info is None)

        network = Network()
        await asyncio.to_thread(network.create)

        pg: Any = None
        odoo: DockerContainer | None = None
        client: OdooClient | None = None
        try:
            # TESTC-01: build snapshot config before pg starts so we can bind-mount
            # the cache dir into the Postgres container (rw — pg_dump writes there).
            snapshot_cfg = await self._snapshot_config(odoo_ver) if snapshot_enabled else None

            # Postgres: assign before start() so the cleanup below owns it on failure.
            pg, pg_user, pg_password = self._postgres_builder(seed_info, network, snapshot_cfg)
            await asyncio.to_thread(pg.start)
            if seed_info:
                await asyncio.to_thread(wait_for_logs, pg, "PostgreSQL init process complete; ready for start up.", 90)

            # TESTC-01: restore snapshot after postgres is up but BEFORE odoo starts.
            snapshot_hit = False
            if snapshot_enabled and snapshot_cfg is not None and has_snapshot(snapshot_cfg):
                logger.info("Snapshot hit — restoring from %s", snapshot_cfg.host_path)
                await restore_snapshot(pg, snapshot_cfg, self._database, pg_user)
                snapshot_hit = True

            # Odoo. Skip --init base when snapshot hit — DB already has base installed.
            # Also skip when seed_info is set (seed image provides the pre-init DB).
            odoo = self._odoo_builder(
                odoo_ver, network, pg_user, pg_password, init_base=not seed_info and not snapshot_hit
            )
            await asyncio.to_thread(odoo.start)

            host = odoo.get_container_host_ip()
            port = odoo.get_exposed_port(8069)
            url = f"http://{host}:{port}"

            # WR-01: derive the readiness attempt budget from startup_timeout (the
            # readiness poll sleeps 2s between attempts), so raising startup_timeout
            # for slow CI actually extends the wait.
            ready_attempts = max(1, self._startup_timeout // 2)
            await self._wait_ready_or_log(odoo, url, ready_attempts)

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
            await self._install_modules(client, mm, to_install, url, ready_attempts)

            # TESTC-01: save snapshot after module install completes (snapshot miss path).
            if snapshot_cfg is not None and snapshot_cfg.enabled and not snapshot_hit:
                await self._save_snapshot(pg, snapshot_cfg, pg_user)

            return StartedOdooContainer(
                odoo_container=odoo,
                postgres_container=pg,
                client=client,
                module_manager=mm,
                url=url,
                database=self._database,
                _network=network,
            )
        except BaseException:
            if client is not None:
                with contextlib.suppress(Exception):
                    await client.aclose()
            for owned in (odoo, pg):
                if owned is not None:
                    with contextlib.suppress(Exception):
                        await asyncio.to_thread(owned.stop)
            with contextlib.suppress(Exception):
                await asyncio.to_thread(network.remove)
            raise

    async def _snapshot_config(self, odoo_ver: str) -> SnapshotConfig:
        # WR-04: _hash_addons_path walks the filesystem synchronously, so
        # build the config off the event loop.
        snapshot_cfg = await asyncio.to_thread(
            make_snapshot_config,
            snapshot_enabled=True,
            cache_dir=self._cache_dir,
            odoo_version=odoo_ver,
            postgres_image="postgres:15-alpine",
            modules=self._modules,
            addons_path=self._addons_path,
            database=self._database,
            admin_password=self._admin_password,
            env=self._env,
            properties=self._properties_for_key,
        )
        # CR-01: gate every snapshot side effect on the resolved cfg.enabled,
        # not the local snapshot_enabled flag — make_snapshot_config honours
        # ODOO_TESTCONTAINERS_SNAPSHOT=disabled, which the local flag misses.
        if snapshot_cfg.enabled:
            # Cache dir must exist BEFORE pg.start() — Docker volume mapping
            # does not create the host dir on Windows (and creates root-owned
            # dirs on Linux), so we create it explicitly.
            snapshot_cfg.cache_dir.mkdir(parents=True, exist_ok=True)
        return snapshot_cfg

    def _postgres_builder(
        self, seed_info: SeedInfo | None, network: Network, snapshot_cfg: SnapshotConfig | None
    ) -> tuple[Any, str, str]:
        """Return the unstarted Postgres container and its credentials."""
        if seed_info:
            seeded = (
                DockerContainer(seed_info.seed_image)
                .with_env("SEED_DB_NAME", self._database)
                .with_exposed_ports(5432)
                .with_network(network)
                .with_network_aliases("db")
            )
            return seeded, "admin", "admin"
        pg_builder = (
            PostgresContainer(
                "postgres:15-alpine",
                username="odoo",
                password="odoo",
                dbname=self._database,
            )
            .with_network(network)
            .with_network_aliases("db")
        )
        if snapshot_cfg is not None and snapshot_cfg.enabled:
            pg_builder = pg_builder.with_volume_mapping(str(snapshot_cfg.cache_dir), "/snapshot-cache", "rw")
        return pg_builder, "odoo", "odoo"

    def _odoo_builder(
        self, odoo_ver: str, network: Network, pg_user: str, pg_password: str, *, init_base: bool
    ) -> DockerContainer:
        """Return the unstarted Odoo container."""
        cmd_parts = ["--database", self._database, "--without-demo", "all", "--max-cron-threads", "0"]
        if init_base:
            cmd_parts[2:2] = ["--init", "base"]

        # TESTC-02: addons mount — add volume mappings and extend --addons-path.
        # cmd_parts must be fully built before with_command() is called, so we
        # extend it here before constructing the DockerContainer builder.
        mounts, addon_targets = _build_addons_cmd(self._addons_path)
        if addon_targets:
            # --addons-path replaces odoo.conf setting entirely, so always include
            # the core Odoo addons path to avoid "Module 'base' not found" errors.
            cmd_parts.extend(["--addons-path", ",".join([ODOO_CORE_ADDONS_PATH, *addon_targets])])

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
        for host_src, container_target, mode in mounts:
            odoo = odoo.with_volume_mapping(host_src, container_target, mode)
        return odoo

    async def _wait_ready_or_log(self, odoo: DockerContainer, url: str, ready_attempts: int) -> None:
        try:
            await self._wait_for_odoo_ready(url, self._database, max_attempts=ready_attempts)
        except TimeoutError:
            # Dump Odoo container logs for debugging
            try:
                raw = await asyncio.to_thread(lambda: odoo.get_wrapped_container().logs())
                logs = raw.decode("utf-8", errors="replace")
                logger.error("Odoo container logs:\n%s", logs[-3000:])
            except Exception as log_err:
                logger.error("Failed to get container logs: %s", log_err)
            raise

    async def _install_modules(
        self, client: OdooClient, mm: ModuleManager, to_install: list[str], url: str, ready_attempts: int
    ) -> None:
        for mod in to_install:
            if await mm.is_module_installed(mod):
                continue
            logger.info("Installing module: %s", mod)
            try:
                await mm.install_module(mod)
            except (OdooNetworkError, OdooTimeoutError) as exc:
                # WR-02: only restart-shaped errors (network drop / timeout) are
                # retried — a genuine install failure (bad module, ACL/dependency
                # error) is a different exception type and propagates immediately
                # instead of being swallowed and retried after a long delay.
                # The original error is logged/chained so failures are not opaque.
                logger.info("Module install interrupted (server may have restarted): %s", exc)
                # WR-01: budget the post-install readiness wait off startup_timeout.
                await self._wait_for_odoo_ready(url, self._database, max_attempts=ready_attempts)
                await client.authenticate()
                await mm.install_module(mod)

    async def _save_snapshot(self, pg: Any, snapshot_cfg: SnapshotConfig, pg_user: str) -> None:
        # Save failure is non-fatal — tests continue without snapshot benefit.
        logger.info("Snapshot miss — saving to %s", snapshot_cfg.host_path)
        try:
            await save_snapshot(pg, snapshot_cfg, self._database, pg_user)
        except Exception as exc:
            logger.warning("Snapshot save failed (non-fatal): %s", exc)

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
