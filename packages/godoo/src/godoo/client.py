"""OdooClient — high-level async client with safety guard."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from functools import cached_property
from typing import TYPE_CHECKING, Any, cast

from godoo.errors import OdooAuthError, OdooSafetyError
from godoo.rpc import JsonRpcTransport, OdooSessionInfo
from godoo.safety import (
    OperationInfo,
    SafetyContext,
    infer_safety_level,
    resolve_safety_context,
)

if TYPE_CHECKING:
    from godoo.services.accounting.service import AccountingService
    from godoo.services.attendance.service import AttendanceService
    from godoo.services.cdc.service import CdcService
    from godoo.services.mail.service import MailService
    from godoo.services.modules.module_manager import ModuleManager
    from godoo.services.properties.service import PropertiesService
    from godoo.services.timesheets.service import TimesheetsService
    from godoo.services.urls.service import UrlService

logger = logging.getLogger("godoo.client")

# Sentinel — means "no safety context was explicitly set by the caller"
_UNDEFINED = object()


@dataclass
class OdooClientConfig:
    url: str
    database: str
    username: str
    password: str
    safety: SafetyContext | None = field(default=None)


class OdooClient:
    """Async Odoo client wrapping JsonRpcTransport with safety checks."""

    def __init__(self, config: OdooClientConfig) -> None:
        self._config = config
        self._transport = JsonRpcTransport(config.url, config.database)
        # _safety_context:
        #   _UNDEFINED  → use config.safety (which may be None)
        #   None        → explicitly disabled
        #   SafetyContext → explicitly set
        self._safety_context: Any = _UNDEFINED

    # ------------------------------------------------------------------
    # Auth
    # ------------------------------------------------------------------

    async def authenticate(self) -> OdooSessionInfo:
        return await self._transport.authenticate(self._config.username, self._config.password)

    def is_authenticated(self) -> bool:
        return self._transport.session is not None

    def get_session(self) -> OdooSessionInfo | None:
        return self._transport.session

    # ------------------------------------------------------------------
    # Safety
    # ------------------------------------------------------------------

    def set_safety_context(self, ctx: SafetyContext | None) -> None:
        self._safety_context = ctx

    def _effective_safety(self) -> SafetyContext | None:
        if self._safety_context is _UNDEFINED:
            return resolve_safety_context(self._config.safety, undefined=False)
        return resolve_safety_context(
            self._safety_context if self._safety_context is not _UNDEFINED else None,
            undefined=False,
        )

    async def _guard(self, op: OperationInfo) -> None:
        """Check safety; raise OdooSafetyError if denied."""
        if op.level == "READ":
            return
        ctx = self._effective_safety()
        if ctx is None:
            return
        allowed = await ctx.confirm(op)
        if not allowed:
            raise OdooSafetyError(
                f"Operation '{op.name}' on '{op.model}' was blocked by safety guard",
                operation=op,
            )

    # ------------------------------------------------------------------
    # Core call
    # ------------------------------------------------------------------

    async def call(
        self,
        model: str,
        method: str,
        args: list[Any],
        kwargs: dict[str, Any],
    ) -> Any:
        if not self.is_authenticated():
            raise OdooAuthError("Client not authenticated. Call authenticate() first.")

        level = infer_safety_level(method)
        op = OperationInfo(
            name=method,
            level=level,
            model=model,
            description=f"{model}.{method}",
        )
        await self._guard(op)
        return await self._transport.call(model, method, args, kwargs)

    # ------------------------------------------------------------------
    # CRUD helpers
    # ------------------------------------------------------------------

    async def search(
        self,
        model: str,
        domain: list[Any] | None = None,
        **kwargs: Any,
    ) -> list[int]:
        return cast("list[int]", await self.call(model, "search", [domain or []], kwargs))

    async def read(
        self,
        model: str,
        ids: int | list[int],
        fields: list[str] | None = None,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        id_list = [ids] if isinstance(ids, int) else ids
        if fields is not None:
            kwargs["fields"] = fields
        return cast("list[dict[str, Any]]", await self.call(model, "read", [id_list], kwargs))

    async def search_read(
        self,
        model: str,
        domain: list[Any] | None = None,
        *,
        fields: list[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        order: str | None = None,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        if fields is not None:
            kwargs["fields"] = fields
        if limit is not None:
            kwargs["limit"] = limit
        if offset is not None:
            kwargs["offset"] = offset
        if order is not None:
            kwargs["order"] = order
        return cast("list[dict[str, Any]]", await self.call(model, "search_read", [domain or []], kwargs))

    async def search_count(self, model: str, domain: list[Any] | None = None, **kwargs: Any) -> int:
        return cast("int", await self.call(model, "search_count", [domain or []], kwargs))

    async def create(self, model: str, values: dict[str, Any], **kwargs: Any) -> int:
        return cast("int", await self.call(model, "create", [values], kwargs))

    async def write(
        self,
        model: str,
        ids: int | list[int],
        values: dict[str, Any],
        **kwargs: Any,
    ) -> bool:
        if isinstance(ids, int):
            ids = [ids]
        return cast("bool", await self.call(model, "write", [ids, values], kwargs))

    async def unlink(self, model: str, ids: int | list[int], **kwargs: Any) -> bool:
        if isinstance(ids, int):
            ids = [ids]
        return cast("bool", await self.call(model, "unlink", [ids], kwargs))

    # ------------------------------------------------------------------
    # Service accessors (lazy, cached)
    # ------------------------------------------------------------------

    @cached_property
    def mail(self) -> MailService:
        from godoo.services.mail.service import MailService

        return MailService(self)

    @cached_property
    def modules(self) -> ModuleManager:
        from godoo.services.modules.module_manager import ModuleManager

        return ModuleManager(self)

    @cached_property
    def attendance(self) -> AttendanceService:
        from godoo.services.attendance.service import AttendanceService

        return AttendanceService(self)

    @cached_property
    def timesheets(self) -> TimesheetsService:
        from godoo.services.timesheets.service import TimesheetsService

        return TimesheetsService(self)

    @cached_property
    def accounting(self) -> AccountingService:
        from godoo.services.accounting.service import AccountingService

        return AccountingService(self)

    @cached_property
    def urls(self) -> UrlService:
        from godoo.services.urls.service import UrlService

        return UrlService(self)

    @cached_property
    def properties(self) -> PropertiesService:
        from godoo.services.properties.service import PropertiesService

        return PropertiesService(self)

    @cached_property
    def cdc(self) -> CdcService:
        from godoo.services.cdc.service import CdcService

        return CdcService(self)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def logout(self) -> None:
        self._transport.logout()

    async def aclose(self) -> None:
        await self._transport.aclose()
