"""Introspector — queries ir.model / ir.model.fields for typed ModelSchema objects."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from godoo.client.errors import OdooMissingError, OdooValidationError

from godoo.introspection.types import FieldSchema, ModelSchema

if TYPE_CHECKING:
    from godoo.client.client import OdooClient

# ------------------------------------------------------------------
# Column projection for ir.model.fields search_read
# ------------------------------------------------------------------
_IR_FIELDS: list[str] = [
    "name",
    "ttype",
    "field_description",
    "relation",
    "relation_field",
    "required",
    "readonly",
    "store",
    "index",
    "copied",
    "translate",
    "help",
    "compute",
    "depends",
    "modules",
    "on_delete",
    "size",
    "selection_ids",
]

_IR_MODEL_FIELDS: list[str] = ["name", "model", "transient"]


def _str_to_tuple(value: Any) -> tuple[str, ...]:
    """Convert a comma-separated string or falsy value to tuple[str, ...]."""
    if not value or not isinstance(value, str):
        return ()
    return tuple(part.strip() for part in value.split(",") if part.strip())


def _parse_digits(value: Any) -> tuple[int, int] | None:
    """Parse digits field from ir.model.fields into tuple[int, int] | None.

    Odoo may return digits as a string like "(16, 2)", a list [16, 2], or False/None.
    """
    if not value:
        return None
    if isinstance(value, (list, tuple)) and len(value) == 2:
        try:
            return (int(value[0]), int(value[1]))
        except TypeError, ValueError:
            return None
    if isinstance(value, str):
        cleaned = value.strip("() ")
        parts = [p.strip() for p in cleaned.split(",")]
        if len(parts) == 2:
            try:
                return (int(parts[0]), int(parts[1]))
            except TypeError, ValueError:
                return None
    return None


def _coerce_str_or_none(value: Any) -> str | None:
    """Return value as str if truthy, else None."""
    if not value or not isinstance(value, str):
        return None
    return str(value)


def _coerce_int_or_none(value: Any) -> int | None:
    """Return value as int if truthy, else None."""
    if not value:
        return None
    try:
        return int(value)
    except TypeError, ValueError:
        return None


# ------------------------------------------------------------------
# IntrospectionCache
# ------------------------------------------------------------------


class IntrospectionCache:
    """Per-instance dict cache keyed by model name.

    Per-instance (not module-global) to avoid test isolation failures and
    correctly support multiple Introspector instances pointing to different
    Odoo instances.
    """

    def __init__(self) -> None:
        self._cache: dict[str, ModelSchema] = {}

    def get(self, name: str) -> ModelSchema | None:
        """Return the cached ModelSchema for name, or None if not cached."""
        return self._cache.get(name)

    def set(self, name: str, schema: ModelSchema) -> None:
        """Store a ModelSchema in the cache."""
        self._cache[name] = schema

    def invalidate(self, name: str) -> None:
        """Remove a model from the cache (no-op if not cached)."""
        self._cache.pop(name, None)

    def clear(self) -> None:
        """Clear all cached entries."""
        self._cache.clear()


# ------------------------------------------------------------------
# Introspector
# ------------------------------------------------------------------


class Introspector:
    """Queries ir.model / ir.model.fields to retrieve typed ModelSchema objects.

    Usage:
        introspector = Introspector(client)
        schema = await introspector.get_schema("res.partner")
    """

    def __init__(self, client: OdooClient) -> None:
        self._client = client
        self._cache = IntrospectionCache()

    async def get_schema(self, name: str, *, bypass_cache: bool = False) -> ModelSchema:
        """Return the schema for a single model.

        Raises OdooMissingError if the model is not found in ir.model.
        Raises OdooValidationError if name is empty.
        Uses cache unless bypass_cache=True.
        """
        if not bypass_cache:
            cached = self._cache.get(name)
            if cached is not None:
                return cached
        schemas = await self.get_schemas([name], bypass_cache=bypass_cache)
        if name not in schemas:
            raise OdooMissingError(f"Model not found in ir.model: {name!r}")
        return schemas[name]

    async def get_schemas(self, names: list[str], *, bypass_cache: bool = False) -> dict[str, ModelSchema]:
        """Batch schema fetch. Issues one RPC for all requested models.

        Warms the per-instance cache for every model returned.
        Raises OdooValidationError for empty names list.
        Raises OdooValidationError if any name is an empty string.
        """
        # T-02-01: validate names non-empty
        if not names:
            raise OdooValidationError("get_schemas() called with empty names list")
        # T-02-02: validate each name is a non-empty string
        for n in names:
            if not isinstance(n, str) or not n:
                raise OdooValidationError(f"Invalid model name: {n!r} — must be a non-empty string")

        # Check cache first (unless bypassing)
        if not bypass_cache:
            cached_result: dict[str, ModelSchema] = {}
            missing: list[str] = []
            for n in names:
                hit = self._cache.get(n)
                if hit is not None:
                    cached_result[n] = hit
                else:
                    missing.append(n)
            if not missing:
                return cached_result
            names = missing

        # ------------------------------------------------------------------
        # RPC 1: ir.model metadata
        # ------------------------------------------------------------------
        model_records: list[dict[str, Any]] = await self._client.search_read(
            "ir.model",
            [("model", "in", names)],
            fields=_IR_MODEL_FIELDS,
        )
        # Build lookup: model_name -> record
        model_info: dict[str, dict[str, Any]] = {r["model"]: r for r in model_records}

        # ------------------------------------------------------------------
        # RPC 2: ir.model.fields for all requested models in one call
        # ------------------------------------------------------------------
        field_records: list[dict[str, Any]] = await self._client.search_read(
            "ir.model.fields",
            [("model", "in", names)],
            fields=_IR_FIELDS,
        )

        # ------------------------------------------------------------------
        # RPC 3 (conditional): selection values for all selection fields
        # ------------------------------------------------------------------
        selection_field_ids: list[int] = [
            r["id"] for r in field_records if r.get("ttype") == "selection" and r.get("selection_ids")
        ]
        selection_map: dict[int, list[tuple[str, str]]] = {}
        if selection_field_ids:
            sel_records: list[dict[str, Any]] = await self._client.search_read(
                "ir.model.fields.selection",
                [("field_id", "in", selection_field_ids)],
                fields=["field_id", "value", "name", "sequence"],
                order="sequence",
            )
            for sel in sel_records:
                raw_fid: Any = sel.get("field_id")
                fid = int(raw_fid[0]) if isinstance(raw_fid, (list, tuple)) else int(raw_fid)
                value = sel.get("value", "")
                label = sel.get("name", "")
                selection_map.setdefault(fid, []).append((str(value), str(label)))

        # ------------------------------------------------------------------
        # Build FieldSchema instances (defensive: use .get() with defaults)
        # ------------------------------------------------------------------
        # Group field records by model name
        fields_by_model: dict[str, list[dict[str, Any]]] = {}
        for fr in field_records:
            model_name = fr.get("model") or ""
            if not model_name:
                # Older Odoo may not return model — fall back to matching against names
                # Cannot reliably assign; skip
                continue
            fields_by_model.setdefault(model_name, []).append(fr)

        # If "model" column is not returned by search_read, try assigning by domain
        # (edge case: if only one model was queried and model key is missing)
        if not any(fields_by_model) and len(names) == 1:
            fields_by_model[names[0]] = field_records

        # ------------------------------------------------------------------
        # Build ModelSchema instances and warm cache
        # ------------------------------------------------------------------
        result: dict[str, ModelSchema] = {}
        for model_name in names:
            if model_name not in model_info:
                # Model not found in ir.model — skip (caller raises OdooMissingError)
                continue
            info = model_info[model_name]
            display_name = str(info.get("name") or "")
            transient = bool(info.get("transient", False))

            field_schemas: dict[str, FieldSchema] = {}
            for fr in fields_by_model.get(model_name, []):
                field_name = str(fr.get("name") or "")
                if not field_name:
                    continue
                field_id = int(fr.get("id", 0))
                ttype = str(fr.get("ttype") or "char")

                # Pitfall 3: "copied" vs "copy" column name
                copy_val = fr.get("copied")
                if copy_val is None:
                    copy_val = fr.get("copy", True)

                # depends: comma-separated Char field
                depends = _str_to_tuple(fr.get("depends"))
                # modules: comma-separated Char field
                modules = _str_to_tuple(fr.get("modules"))
                # digits: may be string, list, or None
                digits = _parse_digits(fr.get("digits") or fr.get("size"))
                size = _coerce_int_or_none(fr.get("size"))
                # relation: False in Odoo means None
                relation = _coerce_str_or_none(fr.get("relation"))
                relation_field = _coerce_str_or_none(fr.get("relation_field"))
                compute = _coerce_str_or_none(fr.get("compute"))
                on_delete = _coerce_str_or_none(fr.get("on_delete"))

                # Selection values
                selection: list[tuple[str, str]] = selection_map.get(field_id, [])

                field_schemas[field_name] = FieldSchema(
                    name=field_name,
                    ttype=ttype,
                    field_description=str(fr.get("field_description") or ""),
                    relation=relation,
                    relation_field=relation_field,
                    required=bool(fr.get("required", False)),
                    readonly=bool(fr.get("readonly", False)),
                    store=bool(fr.get("store", True)),
                    index=bool(fr.get("index", False)),
                    copy=bool(copy_val) if copy_val is not None else True,
                    translate=bool(fr.get("translate", False)),
                    help=str(fr.get("help") or ""),
                    compute=compute,
                    depends=depends,
                    modules=modules,
                    on_delete=on_delete,
                    size=size,
                    digits=digits,
                    selection=selection,
                )

            schema = ModelSchema(
                name=model_name,
                display_name=display_name,
                transient=transient,
                fields=field_schemas,
            )
            self._cache.set(model_name, schema)
            result[model_name] = schema

        return result
