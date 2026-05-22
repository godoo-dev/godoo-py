from __future__ import annotations

import asyncio
import contextlib
import hashlib
import json
import logging
import os
import secrets
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger("godoo.testcontainers.snapshot")

# Bump to invalidate all cached snapshots (e.g. when key algorithm changes).
SNAPSHOT_SCHEMA_VERSION = 1

# The bind-mount target path inside the Postgres container (rw — pg_dump writes here).
CACHE_CONTAINER_DIR = "/snapshot-cache"

# Standard path for Odoo core addons in official Odoo Debian Docker images (17-19).
# If a future Odoo version changes this layout, update this constant — it is the
# single edit point used both by key hashing and the --addons-path CLI arg builder.
ODOO_CORE_ADDONS_PATH = "/usr/lib/python3/dist-packages/odoo/addons"


@dataclass
class SnapshotConfig:
    """Configuration and path helpers for a single snapshot cache entry."""

    enabled: bool
    key: str  # 16-char hex prefix of sha256
    cache_dir: Path

    @property
    def host_path(self) -> Path:
        """Absolute path on the host where the dump file lives."""
        return self.cache_dir / f"{self.key}.dump"

    @property
    def container_path(self) -> str:
        """Path of the dump file as seen from inside the Postgres container."""
        return f"{CACHE_CONTAINER_DIR}/{self.key}.dump"


# ---------------------------------------------------------------------------
# Key computation
# ---------------------------------------------------------------------------


def _hash_addons_path(addons_path: Path | list[Path] | None) -> list[dict[str, Any]]:
    """Return a deterministic content-hash representation of every addons mount.

    Returns [] if addons_path is None. For each Path, walks the directory tree,
    collects (relative_path, sha256(file_bytes)) for every file, sorted by
    relative path, ignoring .git, node_modules, __pycache__, .pytest_cache entries.
    Returns one dict per mount: {source, target, mode, tree}.
    """
    if addons_path is None:
        return []

    paths = [addons_path] if isinstance(addons_path, Path) else list(addons_path)
    result: list[dict[str, Any]] = []

    for i, p in enumerate(paths):
        resolved = p.resolve()
        target = "/mnt/extra-addons" if len(paths) == 1 else f"/mnt/addons-{i}"

        tree: list[dict[str, str]] = []
        _IGNORE = {".git", "node_modules", "__pycache__", ".pytest_cache"}

        if resolved.is_dir():
            for root, dirs, files in os.walk(resolved):
                # Prune ignored directories in-place so os.walk skips them.
                dirs[:] = [d for d in sorted(dirs) if d not in _IGNORE]
                for fname in sorted(files):
                    full = Path(root) / fname
                    rel = full.relative_to(resolved)
                    digest = hashlib.sha256(full.read_bytes()).hexdigest()
                    tree.append({"path": str(rel), "digest": digest})

        result.append(
            {
                "source": str(resolved),
                "target": target,
                "mode": "ro",
                "tree": tree,
            }
        )

    return result


def _build_addons_cmd(
    addons_path: Path | list[Path] | None,
) -> tuple[list[tuple[str, str, str]], list[str]]:
    """Return (mounts, targets) for wiring addons into the Odoo container.

    mounts  — list of (host_src, container_target, mode) for with_volume_mapping.
    targets — list of container target paths to append to --addons-path.

    Returns ([], []) if addons_path is None.
    """
    if addons_path is None:
        return [], []

    paths = [addons_path] if isinstance(addons_path, Path) else list(addons_path)
    mounts: list[tuple[str, str, str]] = []
    targets: list[str] = []

    for i, p in enumerate(paths):
        target = "/mnt/extra-addons" if len(paths) == 1 else f"/mnt/addons-{i}"
        mounts.append((str(p.resolve()), target, "ro"))
        targets.append(target)

    return mounts, targets


def compute_snapshot_key(
    *,
    odoo_version: str,
    postgres_image: str,
    modules: list[str],
    addons_path: Path | list[Path] | None,
    database: str,
    admin_password: str,
    env: dict[str, str],
    properties: dict[str, str],
    user_key: str = "",
) -> str:
    """Compute a 16-char hex snapshot cache key.

    The key is deterministic: same inputs always produce the same key. A change in
    any input — including properties (D-Snap-1) — produces a different key, ensuring
    that snapshots are invalidated when provisioner inputs change.

    sort_keys=False is intentional: the payload dict is pre-sorted to match TS
    JSON.stringify() insertion-order behaviour.
    """
    payload: dict[str, Any] = {
        "schema": SNAPSHOT_SCHEMA_VERSION,
        "odooVersion": odoo_version,
        "postgresImage": postgres_image,
        "modules": sorted(set(modules)),
        "addons": _hash_addons_path(addons_path),
        "database": database,
        "adminPassword": admin_password,
        "env": dict(sorted(env.items())),
        "properties": dict(sorted(properties.items())),
        "userKey": user_key,
    }
    digest = hashlib.sha256(json.dumps(payload, sort_keys=False).encode()).hexdigest()
    return digest[:16]


def make_snapshot_config(
    *,
    snapshot_enabled: bool,
    cache_dir: Path | None,
    **key_kwargs: Any,
) -> SnapshotConfig:
    """Build a SnapshotConfig from constructor-level params and env overrides.

    Env overrides (D-Snap-2):
      ODOO_TESTCONTAINERS_SNAPSHOT=disabled  → disables caching regardless of snapshot_enabled.
      ODOO_TESTCONTAINERS_SNAPSHOT_DIR       → overrides cache_dir.
    """
    enabled = (
        False
        if os.environ.get("ODOO_TESTCONTAINERS_SNAPSHOT", "").lower() == "disabled"
        else snapshot_enabled
    )

    env_dir = os.environ.get("ODOO_TESTCONTAINERS_SNAPSHOT_DIR", "")
    if env_dir:
        cache_dir_resolved = Path(env_dir)
    elif cache_dir is not None:
        cache_dir_resolved = cache_dir
    else:
        cache_dir_resolved = Path.cwd() / ".odoo-testcontainers" / "snapshots"

    key = compute_snapshot_key(**key_kwargs)
    return SnapshotConfig(enabled=enabled, key=key, cache_dir=cache_dir_resolved)


# ---------------------------------------------------------------------------
# Snapshot existence check
# ---------------------------------------------------------------------------


def has_snapshot(cfg: SnapshotConfig) -> bool:
    """Return True iff snapshot caching is enabled AND the dump file exists on the host."""
    return cfg.enabled and cfg.host_path.exists()


# ---------------------------------------------------------------------------
# Restore
# ---------------------------------------------------------------------------


async def restore_snapshot(pg: Any, cfg: SnapshotConfig, database: str, pg_user: str) -> None:
    """Restore a pg_dump snapshot into a running Postgres container.

    Three-step sequence: dropdb → createdb → pg_restore.
    Each step is wrapped in asyncio.to_thread because pg.exec() is a sync call.
    Raises RuntimeError with decoded output on any non-zero exit code.
    """
    logger.info("Restoring snapshot: dropdb %s", database)
    result = await asyncio.to_thread(pg.exec, ["dropdb", "-U", pg_user, database])
    if result.exit_code != 0:
        raise RuntimeError(f"dropdb failed: {result.output.decode(errors='replace')}")

    logger.info("Restoring snapshot: createdb %s", database)
    result = await asyncio.to_thread(pg.exec, ["createdb", "-U", pg_user, database])
    if result.exit_code != 0:
        raise RuntimeError(f"createdb failed: {result.output.decode(errors='replace')}")

    logger.info("Restoring snapshot: pg_restore into %s from %s", database, cfg.container_path)
    result = await asyncio.to_thread(
        pg.exec,
        [
            "pg_restore",
            "-U",
            pg_user,
            "-d",
            database,
            "--no-owner",
            "--role",
            pg_user,
            cfg.container_path,
        ],
    )
    if result.exit_code != 0:
        raise RuntimeError(f"pg_restore failed: {result.output.decode(errors='replace')}")

    logger.info("Snapshot restore complete: %s", cfg.host_path)


# ---------------------------------------------------------------------------
# Save
# ---------------------------------------------------------------------------


async def save_snapshot(pg: Any, cfg: SnapshotConfig, database: str, pg_user: str) -> None:
    """Save a pg_dump snapshot from a running Postgres container.

    Uses a temp file + atomic rename (os.replace) to be safe under concurrent pytest
    workers. If another worker saves the same key first, the fast-path skip at entry
    returns immediately; the second skip after dump discards the duplicate.
    """
    # Fast-path skip: another worker already saved this snapshot.
    if cfg.host_path.exists():
        logger.info("Snapshot already exists, skipping save: %s", cfg.host_path)
        return

    cfg.cache_dir.mkdir(parents=True, exist_ok=True)

    # Unique temp suffix to avoid collision between concurrent workers.
    suffix = f".{os.getpid()}.{int(time.monotonic_ns() // 1_000_000)}.{secrets.token_hex(4)}.tmp"
    tmp_host = cfg.host_path.with_suffix(cfg.host_path.suffix + suffix)
    tmp_container = cfg.container_path + suffix

    logger.info("Saving snapshot: pg_dump to %s", tmp_container)
    result = await asyncio.to_thread(
        pg.exec,
        ["pg_dump", "-U", pg_user, "-d", database, "-Fc", "-f", tmp_container],
    )
    if result.exit_code != 0:
        with contextlib.suppress(Exception):
            tmp_host.unlink(missing_ok=True)
        raise RuntimeError(f"pg_dump failed: {result.output.decode(errors='replace')}")

    # Post-dump skip: another worker saved while we were dumping.
    if cfg.host_path.exists():
        with contextlib.suppress(Exception):
            tmp_host.unlink(missing_ok=True)
        logger.info("Snapshot saved by another worker, discarding: %s", tmp_host)
        return

    # Atomic rename — same directory guarantees same filesystem.
    os.replace(tmp_host, cfg.host_path)
    logger.info("Snapshot saved: %s", cfg.host_path)
