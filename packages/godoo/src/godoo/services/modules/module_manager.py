"""ModuleManager — high-level service for managing Odoo modules."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from godoo.client import OdooClient

logger = logging.getLogger("godoo.client.modules")

_MODULE_FIELDS = [
    "id",
    "name",
    "state",
    "shortdesc",
    "summary",
    "description",
    "author",
    "website",
    "installed_version",
    "latest_version",
    "license",
    "application",
    "category_id",
]

_MODEL = "ir.module.module"
_MAX_RETRIES = 3


def _is_ir_cron_error(exc: Exception) -> bool:
    """Return True if the exception (or its RPC data) mentions ir_cron or scheduled action."""
    msg = str(exc).lower()
    if "ir_cron" in msg or "scheduled action" in msg:
        return True
    # Also check the structured RPC data payload (data.message / data.debug)
    data = getattr(exc, "data", None)
    if isinstance(data, dict):
        for key in ("message", "debug", "name"):
            val = (data.get(key) or "").lower()
            if "ir_cron" in val or "scheduled action" in val:
                return True
    return False


class ModuleManager:
    """High-level service for managing Odoo modules."""

    def __init__(self, client: OdooClient, *, retry_delay: float = 5.0) -> None:
        self._client = client
        self._retry_delay = retry_delay

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def install_module(self, module_name: str) -> dict[str, Any]:
        """Install a module by name.

        Returns updated module info dict.
        Raises RuntimeError if module not found.
        """
        module = await self._find_module(module_name)
        if module["state"] == "installed":
            logger.debug("Module %r already installed, skipping.", module_name)
            return module

        logger.info("Installing module %r (id=%s).", module_name, module["id"])
        await self._call_with_ir_cron_retry(module["id"], "button_immediate_install", module_name)
        return await self._fetch_module_info(module_name)

    async def uninstall_module(self, module_name: str) -> dict[str, Any]:
        """Uninstall a module by name.

        Returns updated module info dict.
        Raises RuntimeError if module not found.
        """
        module = await self._find_module(module_name)
        logger.info("Uninstalling module %r (id=%s).", module_name, module["id"])
        await self._call_with_ir_cron_retry(module["id"], "button_immediate_uninstall", module_name)
        return await self._fetch_module_info(module_name)

    async def upgrade_module(self, module_name: str) -> dict[str, Any]:
        """Upgrade a module by name. Module must be installed.

        Returns updated module info dict.
        Raises RuntimeError if module not found or not installed.
        """
        module = await self._find_module(module_name)
        if module["state"] != "installed":
            raise RuntimeError(f"Module {module_name!r} is not installed (state={module['state']!r}); cannot upgrade.")
        logger.info("Upgrading module %r (id=%s).", module_name, module["id"])
        await self._call_with_ir_cron_retry(module["id"], "button_immediate_upgrade", module_name)
        return await self._fetch_module_info(module_name)

    async def list_modules(
        self,
        *,
        state: str | None = None,
        application: bool | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[dict[str, Any]]:
        """List modules with optional filters."""
        domain: list[Any] = []
        if state is not None:
            domain.append(("state", "=", state))
        if application is not None:
            domain.append(("application", "=", application))

        kwargs: dict[str, Any] = {"fields": _MODULE_FIELDS}
        if limit is not None:
            kwargs["limit"] = limit
        if offset is not None:
            kwargs["offset"] = offset

        return await self._client.search_read(_MODEL, domain, **kwargs)

    async def get_module_info(self, module_name: str) -> dict[str, Any]:
        """Return detailed info for a single module.

        Raises RuntimeError if module not found.
        """
        return await self._find_module(module_name)

    async def is_module_installed(self, module_name: str) -> bool:
        """Return True if the named module is installed."""
        ids = await self._client.search(
            _MODEL,
            [("name", "=", module_name), ("state", "=", "installed")],
        )
        return bool(ids)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _find_module(self, module_name: str) -> dict[str, Any]:
        """Search for a module by name and return its info dict.

        Raises RuntimeError if not found.
        """
        results = await self._client.search_read(
            _MODEL,
            [("name", "=", module_name)],
            fields=_MODULE_FIELDS,
        )
        if not results:
            raise RuntimeError(f"Module {module_name!r} not found in ir.module.module")
        return results[0]

    async def _fetch_module_info(self, module_name: str) -> dict[str, Any]:
        """Fetch the current info for a module after an operation."""
        return await self._find_module(module_name)

    async def _call_with_ir_cron_retry(
        self,
        module_id: int,
        method: str,
        module_name: str,
    ) -> Any:
        """Call a module button method, retrying up to _MAX_RETRIES on ir_cron errors."""
        last_exc: Exception | None = None
        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                return await self._client.call(
                    _MODEL,
                    method,
                    [[module_id]],
                    {},
                )
            except Exception as exc:
                if _is_ir_cron_error(exc) and attempt < _MAX_RETRIES:
                    logger.warning(
                        "ir_cron lock detected on attempt %d/%d for %r.%s, retrying in %.2fs …",
                        attempt,
                        _MAX_RETRIES,
                        module_name,
                        method,
                        self._retry_delay,
                    )
                    last_exc = exc
                    await asyncio.sleep(self._retry_delay)
                else:
                    raise
        # Should be unreachable but satisfies type checker
        raise RuntimeError(f"All {_MAX_RETRIES} attempts failed for {module_name!r}.{method}") from last_exc
