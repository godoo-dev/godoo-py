"""Environment-based configuration helpers."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from godoo.errors import OdooError

if TYPE_CHECKING:
    from godoo.client import OdooClient, OdooClientConfig


def config_from_env(prefix: str = "ODOO") -> OdooClientConfig:
    """Build OdooClientConfig from environment variables.

    Reads:
      {prefix}_URL
      {prefix}_DB  (alias: {prefix}_DATABASE)
      {prefix}_USER (alias: {prefix}_USERNAME)
      {prefix}_PASSWORD
    """
    from godoo.client import OdooClientConfig  # lazy import

    url = os.environ.get(f"{prefix}_URL")
    database = os.environ.get(f"{prefix}_DB") or os.environ.get(f"{prefix}_DATABASE")
    username = os.environ.get(f"{prefix}_USER") or os.environ.get(f"{prefix}_USERNAME")
    password = os.environ.get(f"{prefix}_PASSWORD")

    missing: list[str] = []
    if not url:
        missing.append(f"{prefix}_URL")
    if not database:
        missing.append(f"{prefix}_DB (or {prefix}_DATABASE)")
    if not username:
        missing.append(f"{prefix}_USER (or {prefix}_USERNAME)")
    if not password:
        missing.append(f"{prefix}_PASSWORD")

    if missing:
        raise OdooError(f"Missing required environment variables: {', '.join(missing)}")

    # At this point all values are guaranteed non-None/non-empty
    assert url is not None
    assert database is not None
    assert username is not None
    assert password is not None

    return OdooClientConfig(
        url=url,
        database=database,
        username=username,
        password=password,
    )


async def create_client(prefix: str = "ODOO") -> OdooClient:
    """Create and authenticate an OdooClient from environment variables."""
    from godoo.client import OdooClient  # lazy import

    config = config_from_env(prefix=prefix)
    client = OdooClient(config)
    await client.authenticate()
    return client
