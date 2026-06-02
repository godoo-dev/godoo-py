"""OdooClient — high-level async client with safety guard."""

from __future__ import annotations

import base64
import contextvars
import logging
from dataclasses import dataclass, field
from functools import cached_property
from typing import TYPE_CHECKING, Any, Final, TypeVar, cast, overload

from godoo.client.errors import OdooAuthError, OdooMissingError, OdooSafetyError, OdooValidationError
from godoo.client.rpc import JsonRpcTransport, OdooSessionInfo
from godoo.client.safety import (
    OperationInfo,
    SafetyContext,
    infer_safety_level,
    resolve_safety_context,
)
from godoo.client.typed import OdooModel, Ref

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Callable

    from godoo.client.rpc.protocol import Transport
    from godoo.client.services.accounting.service import AccountingService
    from godoo.client.services.attendance.service import AttendanceService
    from godoo.client.services.cdc.service import CdcService
    from godoo.client.services.mail.service import MailService
    from godoo.client.services.modules.module_manager import ModuleManager
    from godoo.client.services.properties.service import PropertiesService
    from godoo.client.services.timesheets.service import TimesheetsService
    from godoo.client.services.urls.service import UrlService

logger = logging.getLogger("godoo.client")

# TypeVar bound to OdooModel Protocol — used for typed read/search_read overloads (D-05).
# OdooModel is imported from the stdlib-only typed module, safe at module load time.
T = TypeVar("T", bound=OdooModel)

# Sentinel — means "no safety context was explicitly set by the caller"


class _UndefinedType:
    """Sentinel type for _UNDEFINED — indicates that no safety context override was set.

    When _safety_context holds this value the client falls back to the config's safety default.
    """


_UNDEFINED: Final = _UndefinedType()

# Module-level ContextVar for ambient RPC context — task-safe (each asyncio task gets its own copy).
# Default is None (not {} — mutable defaults are disallowed by B039); callers treat None as empty.
_ambient_context: contextvars.ContextVar[dict[str, Any] | None] = contextvars.ContextVar(
    "_ambient_context", default=None
)


class _OdooContextScope:
    """Sync context manager that sets ambient RPC context for the current task within its block.

    Uses a ``contextvars.ContextVar``, so each asyncio task gets its own copy of the context.
    Tasks spawned via ``asyncio.create_task()`` inside the block inherit the ambient context at
    creation time and retain that copy independently — it is not reset when the block exits.
    """

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
    transport_factory: Callable[[OdooClientConfig], Transport] | None = field(default=None)


class OdooClient:
    """Async Odoo client wrapping JsonRpcTransport with safety checks."""

    def __init__(self, config: OdooClientConfig) -> None:
        self._config = config
        if config.transport_factory is not None:
            self._transport: Transport = config.transport_factory(config)
        else:
            self._transport = JsonRpcTransport(config.url, config.database, timeout=config.timeout)
        # _safety_context:
        #   _UNDEFINED  → use config.safety (which may be None)
        #   None        → explicitly disabled
        #   SafetyContext → explicitly set
        self._safety_context: SafetyContext | _UndefinedType | None = _UNDEFINED

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
        # Explicitly set by set_safety_context() — _UndefinedType branch already returned above
        assert not isinstance(self._safety_context, _UndefinedType)
        return resolve_safety_context(self._safety_context, undefined=False)

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

    @overload
    async def read(self, ref: Ref[T]) -> T: ...

    @overload
    async def read(self, refs: list[Ref[T]]) -> list[T]: ...

    @overload
    async def read(
        self,
        model: type[T],
        ids: int | list[int],
        fields: list[str] | None = None,
        **kwargs: Any,
    ) -> list[T]: ...

    @overload
    async def read(
        self,
        model: str,
        ids: int | list[int],
        fields: list[str] | None = None,
        **kwargs: Any,
    ) -> list[dict[str, Any]]: ...

    async def read(  # type: ignore[misc]
        self,
        model: Any,
        ids: int | list[int] | None = None,
        fields: list[str] | None = None,
        **kwargs: Any,
    ) -> Any:
        # Empty list is unambiguously the list[Ref] case → resolve to empty result (WR-01).
        if isinstance(model, list) and not model:
            return []
        # Ref / list[Ref] dispatch — D-01, D-02, D-03
        if isinstance(model, Ref) or (isinstance(model, list) and model and isinstance(model[0], Ref)):
            # Collect refs, validate all up front (D-03)
            refs: list[Ref[Any]] = [model] if isinstance(model, Ref) else list(model)
            bad = [r for r in refs if r._target_cls is None]
            if bad:
                raise OdooValidationError(
                    f"Cannot resolve Ref(id={bad[0].id}): no target model known"
                    " — it came from an untyped many2one field."
                )
            # Group by target class, preserving insertion order within each group (D-02)
            from collections import defaultdict

            groups: dict[type[Any], list[int]] = defaultdict(list)
            for r in refs:
                assert r._target_cls is not None
                if r.id not in groups[r._target_cls]:
                    groups[r._target_cls].append(r.id)
            # Fire one read() per distinct target model (batched)
            fetched: dict[tuple[type[Any], int], Any] = {}
            for target_cls, target_ids in groups.items():
                results = await self.read(target_cls, target_ids)
                for record in results:
                    fetched[(target_cls, record.id)] = record
            # Stitch back in input order
            ordered = [fetched[(r._target_cls, r.id)] for r in refs]  # type: ignore[index]
            if isinstance(model, Ref):
                return ordered[0]
            return ordered

        id_list = [ids] if isinstance(ids, int) else (ids or [])

        # Typed dispatch — duck-typed guard; never imports pydantic at module level (D-04)
        if hasattr(model, "__odoo_model__"):
            try:
                from godoo.client._pydantic_transform import derive_partial_model
            except ModuleNotFoundError as exc:
                raise OdooValidationError(
                    "Typed reads require 'pydantic'. Install with: pip install 'godoo-client[typed]'"
                ) from exc
            typed_model = cast("type[Any]", model)
            odoo_name: str = typed_model.__odoo_model__
            if fields is not None:
                # read() always returns id from Odoo regardless of fields — no injection needed.
                kwargs["fields"] = fields
                try:
                    target: type[Any] = derive_partial_model(typed_model, fields)
                except ValueError as exc:
                    raise OdooValidationError(str(exc)) from exc
            else:
                target = typed_model
            raw = cast("list[dict[str, Any]]", await self.call(odoo_name, "read", [id_list], kwargs))
            return [target.model_validate(r) for r in raw]

        # str path — UNCHANGED from v1.0 (TYPED-04 regression invariant)
        if fields is not None:
            kwargs["fields"] = fields
        return cast("list[dict[str, Any]]", await self.call(model, "read", [id_list], kwargs))

    @overload
    async def search_read(
        self,
        model: type[T],
        domain: list[Any] | None = None,
        *,
        fields: list[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        order: str | None = None,
        **kwargs: Any,
    ) -> list[T]: ...

    @overload
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
    ) -> list[dict[str, Any]]: ...

    async def search_read(
        self,
        model: str | type[T],
        domain: list[Any] | None = None,
        *,
        fields: list[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        order: str | None = None,
        **kwargs: Any,
    ) -> list[dict[str, Any]] | list[T]:
        if fields is not None:
            kwargs["fields"] = fields
        if limit is not None:
            kwargs["limit"] = limit
        if offset is not None:
            kwargs["offset"] = offset
        if order is not None:
            kwargs["order"] = order

        # Typed dispatch — duck-typed guard; never imports pydantic at module level (D-04)
        if hasattr(model, "__odoo_model__"):
            try:
                from godoo.client._pydantic_transform import derive_partial_model
            except ModuleNotFoundError as exc:
                raise OdooValidationError(
                    "Typed reads require 'pydantic'. Install with: pip install 'godoo-client[typed]'"
                ) from exc
            typed_model = cast("type[Any]", model)
            odoo_name: str = typed_model.__odoo_model__
            if fields is not None:
                # Inject 'id' into the fields sent to Odoo — search_read does NOT auto-include id.
                # Use dict.fromkeys to deduplicate while preserving order (id first).
                effective_fields = list(dict.fromkeys(["id", *fields]))
                kwargs["fields"] = effective_fields
                try:
                    target: type[Any] = derive_partial_model(typed_model, effective_fields)
                except ValueError as exc:
                    raise OdooValidationError(str(exc)) from exc
            else:
                target = typed_model
            raw = cast("list[dict[str, Any]]", await self.call(odoo_name, "search_read", [domain or []], kwargs))
            return cast("list[T]", [target.model_validate(r) for r in raw])

        # str path — UNCHANGED from v1.0 (TYPED-04 regression invariant)
        return cast("list[dict[str, Any]]", await self.call(model, "search_read", [domain or []], kwargs))

    async def search_count(self, model: str, domain: list[Any] | None = None, **kwargs: Any) -> int:
        return cast("int", await self.call(model, "search_count", [domain or []], kwargs))

    def with_context(self, **kwargs: Any) -> _OdooContextScope:
        """Return a sync context manager that merges kwargs into every RPC call made in the
        current task within its block.

        The ambient context is stored in a ``contextvars.ContextVar``.  Tasks created via
        ``asyncio.create_task()`` inside the block inherit a copy of the ambient context per
        standard ``ContextVar`` semantics — that copy is independent of the block and is not
        reset when the block exits.
        """
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
            raise OdooValidationError(f"Binary field {field!r} on {model}:{record_id} is not valid base64") from exc

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
        from godoo.client.services.mail.service import MailService

        return MailService(self)

    @cached_property
    def modules(self) -> ModuleManager:
        from godoo.client.services.modules.module_manager import ModuleManager

        return ModuleManager(self)

    @cached_property
    def attendance(self) -> AttendanceService:
        from godoo.client.services.attendance.service import AttendanceService

        return AttendanceService(self)

    @cached_property
    def timesheets(self) -> TimesheetsService:
        from godoo.client.services.timesheets.service import TimesheetsService

        return TimesheetsService(self)

    @cached_property
    def accounting(self) -> AccountingService:
        from godoo.client.services.accounting.service import AccountingService

        return AccountingService(self)

    @cached_property
    def urls(self) -> UrlService:
        from godoo.client.services.urls.service import UrlService

        return UrlService(self)

    @cached_property
    def properties(self) -> PropertiesService:
        from godoo.client.services.properties.service import PropertiesService

        return PropertiesService(self)

    @cached_property
    def cdc(self) -> CdcService:
        from godoo.client.services.cdc.service import CdcService

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
        """Close the transport on exit — always called regardless of exception.

        If aclose() raises and the block body also raised, the body exception is preserved:
        the close failure is logged as a warning rather than propagated over the original error.
        If aclose() raises on a clean exit (no body exception), it is re-raised as normal.
        """
        try:
            await self.aclose()
        except Exception:
            if exc_val is None:
                raise
            logger.warning("aclose() failed during __aexit__; preserving the original exception", exc_info=True)
