"""URL service — standalone async functions."""

from __future__ import annotations

from typing import TYPE_CHECKING

from godoo.client.services.urls.types import PortalUrlOptions, PortalUrlResult

if TYPE_CHECKING:
    from godoo.client.client import OdooClient

# Cache: client id() -> base_url
_base_url_cache: dict[int, str] = {}


async def get_base_url(client: OdooClient, *, force_refresh: bool = False) -> str:
    """Read the base URL from ir.config_parameter (web.base.url).

    See atlas:base/url-base-url.
    Results are cached per client instance; force_refresh bypasses the cache.
    Trailing slashes are trimmed. An absent parameter returns an empty string.
    """
    cid = id(client)
    if not force_refresh and cid in _base_url_cache:
        return _base_url_cache[cid]
    records = await client.search_read(
        "ir.config_parameter",
        [("key", "=", "web.base.url")],
        fields=["value"],
        limit=1,
    )
    base_url = records[0]["value"].rstrip("/") if records else ""
    _base_url_cache[cid] = base_url
    return base_url


async def get_record_url(client: OdooClient, model: str, res_id: int) -> str:
    """Interpolate model and res_id into a mail redirect URL without query encoding.

    Resolution depends on installed controllers, model routes and access rights.
    See atlas:base/url-record-basic.
    """
    base = await get_base_url(client)
    return f"{base}/mail/view?model={model}&res_id={res_id}"


async def get_portal_url(
    client: OdooClient,
    model: str,
    res_id: int,
    options: PortalUrlOptions | None = None,
) -> PortalUrlResult:
    """Read access_url and, when enabled, an existing access_token; never create one.

    Token access depends on the model's portal policy.
    See atlas:base/url-portal-mixin.
    Missing rows or access_url fall back to the mail redirect URL. Missing or
    disabled tokens return None; RPC access errors propagate.
    See atlas:base/url-record-basic.
    """
    opts = options or PortalUrlOptions()
    fields = ["access_url"]
    if opts.access_token:
        fields.append("access_token")
    records = await client.read(model, res_id, fields=fields)
    if not records:
        base = await get_base_url(client)
        return PortalUrlResult(url=f"{base}/mail/view?model={model}&res_id={res_id}")
    rec = records[0]
    base = await get_base_url(client)
    access_url = rec.get("access_url", "")
    url = f"{base}{access_url}" if access_url else f"{base}/mail/view?model={model}&res_id={res_id}"
    token = rec.get("access_token") or None if opts.access_token else None
    if token:
        separator = "&" if "?" in url else "?"
        url = f"{url}{separator}access_token={token}"
    return PortalUrlResult(url=url, access_token=token)
