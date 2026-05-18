"""Mail service — standalone async functions."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

from godoo.errors import OdooValidationError
from godoo.services.mail.types import PostMessageOptions

if TYPE_CHECKING:
    from godoo.client import OdooClient

_HTML_TAG_RE = re.compile(r"<[^>]+>")


def ensure_html_body(body: str) -> str:
    """Validate and normalise a message body to HTML.

    - Empty / whitespace-only raises OdooValidationError.
    - Plain text is wrapped in ``<p>…</p>``.
    - Already-HTML content is returned as-is.
    """
    if not body or not body.strip():
        raise OdooValidationError("Message body must not be empty")
    if _HTML_TAG_RE.search(body):
        return body
    return f"<p>{body}</p>"


def _extract_id(result: Any) -> int:
    """Normalise the return value of message_post to a single int."""
    if isinstance(result, int):
        return result
    if isinstance(result, list) and len(result) > 0:
        return int(result[0])
    if isinstance(result, dict):
        return int(result.get("id", 0))
    return int(result)


async def post_internal_note(
    client: OdooClient,
    model: str,
    res_id: int,
    body: str,
    options: PostMessageOptions | None = None,
) -> int:
    """Post an internal note (not visible to portal users)."""
    opts = options or PostMessageOptions()
    html_body = ensure_html_body(body)
    kwargs: dict[str, Any] = {
        "body": html_body,
        "message_type": "comment",
        "subtype_xmlid": "mail.mt_note",
        "is_internal": True,
        "body_is_html": True,
        "partner_ids": opts.partner_ids,
        "attachment_ids": opts.attachment_ids,
    }
    result = await client.call(model, "message_post", [res_id], kwargs)
    return _extract_id(result)


async def post_open_message(
    client: OdooClient,
    model: str,
    res_id: int,
    body: str,
    options: PostMessageOptions | None = None,
) -> int:
    """Post an open message (visible to portal / followers)."""
    opts = options or PostMessageOptions()
    html_body = ensure_html_body(body)
    kwargs: dict[str, Any] = {
        "body": html_body,
        "message_type": "comment",
        "subtype_xmlid": "mail.mt_comment",
        "is_internal": False,
        "body_is_html": True,
        "partner_ids": opts.partner_ids,
        "attachment_ids": opts.attachment_ids,
    }
    result = await client.call(model, "message_post", [res_id], kwargs)
    return _extract_id(result)
