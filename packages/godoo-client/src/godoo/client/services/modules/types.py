from __future__ import annotations

from typing import Literal, TypedDict

ModuleState = Literal["uninstalled", "installed", "to install", "to upgrade", "to remove", "uninstallable"]


class _ModuleInfoRequired(TypedDict):
    id: int
    name: str
    state: ModuleState


class ModuleInfo(_ModuleInfoRequired, total=False):
    shortdesc: str
    summary: str
    description: str
    author: str
    website: str
    installed_version: str
    latest_version: str
    license: str
    application: bool
    category_id: list[int | str]
