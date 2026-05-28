from godoo.client.services.mail.functions import (
    ensure_html_body,
    post_internal_note,
    post_open_message,
)
from godoo.client.services.mail.service import MailService
from godoo.client.services.mail.types import PostMessageOptions

__all__ = [
    "MailService",
    "PostMessageOptions",
    "ensure_html_body",
    "post_internal_note",
    "post_open_message",
]
