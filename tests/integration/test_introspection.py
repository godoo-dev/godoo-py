from __future__ import annotations

import importlib.util
import sys
from typing import TYPE_CHECKING

import pytest
from godoo.introspection import CodeGenerator, Introspector

if TYPE_CHECKING:
    from pathlib import Path

    from godoo.client import OdooClient


@pytest.mark.integration
async def test_live_schema_and_generated_model(client: OdooClient, tmp_path: Path) -> None:
    introspector = Introspector(client)
    schema = await introspector.get_schema("res.partner")
    assert schema.name == "res.partner"
    assert schema.fields["name"].ttype == "char"
    # Generate only a bounded real projection; the full model includes relations
    # whose dependent models the consumer has not elected to generate.
    schema.fields = {name: field for name, field in schema.fields.items() if name in ("id", "name")}
    CodeGenerator(introspector).write([schema], tmp_path)
    spec = importlib.util.spec_from_file_location("live_partner", tmp_path / "res_partner.py")
    assert spec and spec.loader
    generated = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = generated
    spec.loader.exec_module(generated)
    rows = await client.search_read("res.partner", [], fields=["name"], limit=1)
    assert rows
    partner = generated.ResPartner.model_validate(rows[0])
    assert partner.id == rows[0]["id"] and partner.name == rows[0]["name"]
