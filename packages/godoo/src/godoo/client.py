"""OdooClient — high-level async client with safety guard."""

from __future__ import annotations

import base64
import contextvars
import logging
from dataclasses import dataclass, field
from functools import cached_property
from typing import TYPE_CHECKING, Any, cast, overload

from godoo.errors import OdooAuthError, OdooMissingError, OdooSafetyError, OdooValidationError
from godoo.rpc import JsonRpcTransport, OdooSessionInfo
from godoo.safety import (
    OperationInfo,
    SafetyContext,
    infer_safety_level,
    resolve_safety_context,
)

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

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

# Module-level ContextVar for ambient RPC context — task-safe (each asyncio task gets its own copy).
# Default is None (not {} — mutable defaults are disallowed by B039); callers treat None as empty.
_ambient_context: contextvars.ContextVar[dict[str, Any] | None] = contextvars.ContextVar(
    "_ambient_context", default=None
)


class _OdooContextScope:
    """Sync context manager that threads ambient RPC context for the duration of a with block."""

    def __init__(self, layer: dict[str, Any]) -> None:
        self._layer = layer
        self._token: contextvars.Token[dict[str, Any] | None] | None = None

    def __enter__(self) -> _OdooContextScope:
        current = _ambient_context.get() or {}
        self._token = _ambient_context.set({**current, **self._layer})
        return self

    def __exit__(self, *_: object) -> None:
        if self._token is not None:
            _ambient_context.reset(self._token)
            self._token = None


@dataclass
class OdooClientConfig:
    url: str
    database: str
    username: str
    password: str
    safety: SafetyContext | None = field(default=None)
    timeout: float | None = field(default=None)


class OdooClient:
    """Async Odoo client wrapping JsonRpcTransport with safety checks."""

    def __init__(self, config: OdooClientConfig) -> None:
        self._config = config
        self._transport = JsonRpcTransport(config.url, config.database, timeout=config.timeout)
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
        # Merge ambient context (from with_context block) with explicit per-call context (explicit wins)
        ambient = _ambient_context.get() or {}
        if ambient or "context" in kwargs:
            merged_ctx = {**ambient, **kwargs.get("context", {})}
            if merged_ctx:
                kwargs = {**kwargs, "context": merged_ctx}
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

    def with_context(self, **kwargs: Any) -> _OdooContextScope:
        """Return a sync context manager that merges kwargs into every RPC call in its block."""
        return _OdooContextScope(kwargs)

    async def iter_search_read(
        self,
        model: str,
        domain: list[Any] | None = None,
        *,
        fields: list[str] | None = None,
        batch_size: int = 500,
        limit: int | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[dict[str, Any]]:
        """Async generator yielding records via keyset (id-cursor) pagination.

        Always orders by id ascending; does not accept a custom order parameter.
        Injects 'id' into fetched fields internally for cursor advancement;
        strips it from yielded records if the caller did not request it.
        """
        base_domain = list(domain or [])
        last_id = 0
        yielded = 0
        # Always fetch id for cursor advancement; strip later if not requested by caller
        caller_requested_id = fields is None or "id" in fields
        fetch_fields = fields if fields is None else list(dict.fromkeys(["id", *list(fields)]))

        while True:
            page_domain = [*base_domain, ("id", ">", last_id)]
            remaining = (limit - yielded) if limit is not None else None
            fetch_size = min(batch_size, remaining) if remaining is not None else batch_size

            batch = await self.search_read(
                model,
                page_domain,
                fields=fetch_fields,
                limit=fetch_size,
                order="id",
                **kwargs,
            )
            if not batch:
                break

            for record in batch:
                if not caller_requested_id:
                    record = {k: v for k, v in record.items() if k != "id"}
                yield record
                yielded += 1
                if limit is not None and yielded >= limit:
                    return

            if len(batch) < fetch_size:
                break
            last_id = batch[-1]["id"]

    async def fields_get(self, model: str, attributes: list[str] | None = None) -> dict[str, Any]:
        """Return field metadata dict keyed by field name (Odoo's native fields_get shape)."""
        kw: dict[str, Any] = {}
        if attributes is not None:
            kw["attributes"] = attributes
        return cast("dict[str, Any]", await self.call(model, "fields_get", [], kw))

    async def ref(self, xml_id: str) -> int:
        """Resolve an external ID (module.name) to a numeric record id.

        Raises OdooValidationError for malformed xml_id.
        Raises OdooMissingError when the xml_id is not found.
        """
        parts = xml_id.split(".", 1)
        if len(parts) != 2:
            raise OdooValidationError(f"Invalid XML ID format (expected 'module.name'): {xml_id!r}")
        module, name = parts
        records = await self.search_read(
            "ir.model.data",
            [("module", "=", module), ("name", "=", name)],
            fields=["res_id"],
        )
        if not records:
            raise OdooMissingError(f"XML ID not found: {xml_id!r}")
        return cast("int", records[0]["res_id"])

    async def execute_kw(
        self,
        model: str,
        method: str,
        args: list[Any],
        kwargs: dict[str, Any] | None = None,
    ) -> Any:
        """Raw RPC passthrough for non-standard Odoo methods.

        Routes through call() so the safety guard still classifies and gates it.
        """
        return await self.call(model, method, args, kwargs or {})

    async def read_binary(self, model: str, record_id: int, field: str) -> bytes:
        """Fetch a binary field and return decoded bytes.

        Returns b"" when the field is unset (Odoo returns False for empty binary fields).
        Raises OdooMissingError when the record does not exist.
        """
        records = await self.read(model, record_id, fields=[field])
        if not records:
            raise OdooMissingError(f"Record {model}:{record_id} not found")
        raw = records[0].get(field)
        if raw is False or raw is None:
            return b""
        try:
            return base64.b64decode(raw)
        except (ValueError, TypeError) as exc:
            raise OdooValidationError(
                f"Binary field {field!r} on {model}:{record_id} is not valid base64"
            ) from exc

    @overload
    async def create(self, model: str, values: dict[str, Any], **kwargs: Any) -> int: ...

    @overload
    async def create(self, model: str, values: list[dict[str, Any]], **kwargs: Any) -> list[int]: ...

    async def create(
        self,
        model: str,
        values: dict[str, Any] | list[dict[str, Any]],
        **kwargs: Any,
    ) -> int | list[int]:
        """Create one or more records.

        Pass a single dict to create one record (returns int id).
        Pass a list of dicts to create multiple records (returns list[int] ids).
        Raises OdooValidationError locally if the list is empty (no RPC call made).
        """
        if isinstance(values, list):
            if not values:
                raise OdooValidationError("Cannot create with empty list of values")
            return cast("list[int]", await self.call(model, "create", [values], kwargs))
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

    async def __aenter__(self) -> OdooClient:
        """Authenticate and return self — enables `async with OdooClient(config) as client:`."""
        await self.authenticate()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        """Close the transport on exit — always called regardless of exception."""
        await self.aclose()
