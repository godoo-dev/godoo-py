#!/usr/bin/env -S uv run --script
# /// script
# requires-python = "==3.14.8"
# dependencies = []
# ///
"""Installed-wheel integration observer; exact owned resource tracking and cleanup."""

from __future__ import annotations

import contextlib
import json
import os
import sys
from pathlib import Path

import httpx
from docker.errors import NotFound
from godoo.testcontainers import OdooTestContainer
from testcontainers.core.container import DockerContainer
from testcontainers.core.network import Network

import docker

EVIDENCE = Path(os.environ["GODOO_PROOF_EVIDENCE"])
MAJOR = int(os.environ["GODOO_PROOF_MAJOR"])
RESOURCES = {"containers": [], "networks": []}
OBSERVATIONS = []


def save():
    (EVIDENCE / "resources.json").write_text(json.dumps(RESOURCES, indent=2))
    (EVIDENCE / "observed-odoo.json").write_text(json.dumps(OBSERVATIONS, indent=2))


def pytest_configure(config):
    assert MAJOR in (18, 19), "unsupported verification major before provisioning"
    import godoo.testcontainers

    assert Path(godoo.testcontainers.__file__).is_relative_to(Path(sys.prefix))
    original_container = DockerContainer.start
    original_network = Network.create
    original_start = OdooTestContainer.start

    def container_start(self):
        try:
            return original_container(self)
        finally:
            with contextlib.suppress(Exception):
                wrapped = self.get_wrapped_container()
                RESOURCES["containers"].append(wrapped.id)
                save()

    def network_create(self):
        try:
            return original_network(self)
        finally:
            with contextlib.suppress(Exception):
                RESOURCES["networks"].append(self.id)
                save()

    async def observed_start(self):
        started = await original_start(self)
        try:
            async with httpx.AsyncClient() as http:
                response = await http.post(
                    f"{started.url}/web/webclient/version_info",
                    json={
                        "jsonrpc": "2.0",
                        "method": "call",
                        "params": {},
                        "id": 1,
                    },
                )
                response.raise_for_status()
                version = response.json()["result"]
            containers = []
            for owned in (started.odoo_container, started.postgres_container):
                wrapped = owned.get_wrapped_container()
                containers.append(
                    {
                        "id": wrapped.id,
                        "image_id": wrapped.image.id,
                        "digests": wrapped.image.attrs.get("RepoDigests", []),
                    }
                )
            modules = sorted(m["name"] for m in await started.module_manager.list_modules(state="installed"))
            OBSERVATIONS.append(
                {
                    "requested_major": MAJOR,
                    "observed": version,
                    "containers": containers,
                    "modules": modules,
                    "url": started.url,
                }
            )
            save()
            assert version["server_version_info"][0] == MAJOR, version
            assert "base" in modules
        except BaseException:
            await started.cleanup()
            raise
        return started

    DockerContainer.start = container_start
    Network.create = network_create
    OdooTestContainer.start = observed_start
    save()


def pytest_sessionfinish(session, exitstatus):
    # Only the exact IDs observed from this process are eligible for rescue cleanup.
    client = docker.from_env()
    leaked = []
    errors = []
    for kind in ("containers", "networks"):
        for resource_id in RESOURCES[kind]:
            try:
                resource = getattr(client, kind).get(resource_id)
                leaked.append(resource_id)
                if kind == "containers":
                    (EVIDENCE / f"container-{resource_id[:12]}.log").write_bytes(resource.logs())
                    resource.remove(force=True, v=True)
                else:
                    resource.remove()
            except NotFound:
                pass
            except Exception as exc:
                errors.append(f"{resource_id}: {exc}")
    remaining = []
    for kind in ("containers", "networks"):
        for resource_id in RESOURCES[kind]:
            try:
                getattr(client, kind).get(resource_id)
                remaining.append(resource_id)
            except NotFound:
                pass
    client.close()
    (EVIDENCE / "cleanup.json").write_text(
        json.dumps({"rescued": leaked, "errors": errors, "remaining": remaining}, indent=2)
    )
    if errors or remaining or not OBSERVATIONS or leaked:
        session.exitstatus = 1


def pytest_collection_finish(session):
    (EVIDENCE / "collection.json").write_text(
        json.dumps(
            {
                "selected": [item.nodeid for item in session.items],
                "selected_count": len(session.items),
            },
            indent=2,
        )
    )
