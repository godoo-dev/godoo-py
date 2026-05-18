from godoo.services.mail.functions import (
    ensure_html_body,
    post_internal_note,
    post_open_message,
)
from godoo.services.mail.service import MailService
from godoo.services.mail.types import PostMessageOptions

__all__ = [
    "MailService",
    "PostMessageOptions",
    "ensure_html_body",
    "post_internal_note",
    "post_open_message",
]
