"""Simple dict cache for ir.model.fields metadata."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from godoo.services.cdc.types import FieldMeta

if TYPE_CHECKING:
    from godoo.client import OdooClient

# Cache key: "model_name.field_name" -> FieldMeta
_cache: dict[str, FieldMeta] = {}


def cache_key(model: str, field_name: str) -> str:
    return f"{model}.{field_name}"


def get_cached(model: str, field_name: str) -> FieldMeta | None:
    return _cache.get(cache_key(model, field_name))


def set_cached(model: str, field_name: str, meta: FieldMeta) -> None:
    _cache[cache_key(model, field_name)] = meta


def clear_cache() -> None:
    _cache.clear()


async def fetch_field_meta(
    client: OdooClient,
    model: str,
    field_name: str,
) -> FieldMeta:
    """Fetch and cache field metadata from ir.model.fields."""
    cached = get_cached(model, field_name)
    if cached is not None:
        return cached
    records = await client.search_read(
        "ir.model.fields",
        [("model", "=", model), ("name", "=", field_name)],
        fields=["name", "ttype", "relation", "selection_ids"],
        limit=1,
    )
    if not records:
        meta = FieldMeta(name=field_name, field_type="char")
    else:
        rec = records[0]
        meta = FieldMeta(
            name=rec["name"],
            field_type=rec.get("ttype", "char"),
            relation=rec.get("relation") or None,
        )
    set_cached(model, field_name, meta)
    return meta


async def ensure_fields_cached(
    client: OdooClient,
    model: str,
    field_names: list[str],
) -> dict[str, FieldMeta]:
    """Ensure multiple fields are cached; return them all."""
    result: dict[str, FieldMeta] = {}
    missing: list[str] = []
    for fn in field_names:
        cached = get_cached(model, fn)
        if cached:
            result[fn] = cached
        else:
            missing.append(fn)
    if missing:
        records: list[dict[str, Any]] = await client.search_read(
            "ir.model.fields",
            [("model", "=", model), ("name", "in", missing)],
            fields=["name", "ttype", "relation"],
        )
        found_names = set()
        for rec in records:
            meta = FieldMeta(
                name=rec["name"],
                field_type=rec.get("ttype", "char"),
                relation=rec.get("relation") or None,
            )
            set_cached(model, rec["name"], meta)
            result[rec["name"]] = meta
            found_names.add(rec["name"])
        # Fill defaults for not-found fields
        for fn in missing:
            if fn not in found_names:
                meta = FieldMeta(name=fn, field_type="char")
                set_cached(model, fn, meta)
                result[fn] = meta
    return result
