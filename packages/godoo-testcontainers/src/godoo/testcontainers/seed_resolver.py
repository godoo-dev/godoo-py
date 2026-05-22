from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class SeedInfo:
    seed_image: str
    seed_modules: list[str]


def normalise_odoo_version(raw: str | None) -> str:
    """Normalise ODOO_VERSION into dotted form. None/'17' → '17.0'."""
    if not raw:
        return "17.0"
    if "." in raw:
        return raw
    return f"{raw}.0"


def read_seed_config(cwd: str) -> dict[str, Any] | None:
    """Read docker/seed-config.json from cwd or two levels up."""
    candidates = [
        Path(cwd) / "docker" / "seed-config.json",
        Path(cwd).parent.parent / "docker" / "seed-config.json",
    ]
    for p in candidates:
        try:
            result: dict[str, Any] = json.loads(p.read_text())
            return result
        except FileNotFoundError, json.JSONDecodeError:
            continue
    return None


def resolve_seed_info(
    requested_modules: list[str],
    odoo_version: str,
    *,
    seed_image_env: str | None = None,
    cwd: str = ".",
) -> SeedInfo | None:
    """Check if seed image covers requested modules. Returns None for cold start."""
    if seed_image_env is None:
        seed_image_env = os.environ.get("ODOO_SEED_IMAGE")
    if not seed_image_env:
        return None
    config = read_seed_config(cwd)
    if config is None:
        return None
    version_config = config.get("versions", {}).get(odoo_version)
    if not version_config or "modules" not in version_config:
        return None
    seed_modules: list[str] = version_config["modules"]
    uncovered = [m for m in requested_modules if m not in seed_modules]
    if uncovered:
        return None
    return SeedInfo(seed_image=seed_image_env, seed_modules=seed_modules)
