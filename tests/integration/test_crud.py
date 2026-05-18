from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from godoo import OdooClient


@pytest.mark.integration
class TestCRUDIntegration:
    async def test_search_partners(self, client: OdooClient) -> None:
        ids = await client.search("res.partner", limit=5)
        assert isinstance(ids, list)
        assert len(ids) <= 5

    async def test_create_read_write_unlink(self, client: OdooClient) -> None:
        # Create
        partner_id = await client.create("res.partner", {"name": "Test CRUD Partner"})
        assert isinstance(partner_id, int)

        # Read
        records = await client.read("res.partner", partner_id, ["name"])
        assert records[0]["name"] == "Test CRUD Partner"

        # Write
        await client.write("res.partner", partner_id, {"name": "Updated Partner"})
        records = await client.read("res.partner", partner_id, ["name"])
        assert records[0]["name"] == "Updated Partner"

        # Unlink
        result = await client.unlink("res.partner", partner_id)
        assert result is True

    async def test_search_read(self, client: OdooClient) -> None:
        records = await client.search_read(
            "res.partner",
            [["is_company", "=", True]],
            fields=["name", "email"],
            limit=3,
        )
        assert isinstance(records, list)
        for rec in records:
            assert "name" in rec

    async def test_search_count(self, client: OdooClient) -> None:
        count = await client.search_count("res.partner")
        assert isinstance(count, int)
        assert count > 0
