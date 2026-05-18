from __future__ import annotations

import pytest_asyncio
from godoo_testcontainers import OdooTestContainer


@pytest_asyncio.fixture(scope="session")
async def odoo():
    """Session-scoped Odoo instance for all integration tests."""
    container = OdooTestContainer(
        modules=["crm", "sale", "project"],
    )
    started = await container.start()
    yield started
    await started.cleanup()


@pytest_asyncio.fixture
async def client(odoo):  # type: ignore[no-untyped-def]
    """Per-test authenticated client."""
    return odoo.client
