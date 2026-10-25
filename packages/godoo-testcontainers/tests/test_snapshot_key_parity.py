from __future__ import annotations

from godoo.testcontainers.snapshot import compute_snapshot_key


def test_direct_container_key_matches_testharness_key() -> None:
    """Prove that compute_snapshot_key is deterministic: same inputs produce the same key.

    This is the structural guarantee that the direct-container path and the TestHarness
    path compute identical snapshot keys when given identical inputs.
    """
    props = {"web.base.url": "http://localhost:8069", "auth_signup.invitation_only": "True"}
    key_kwargs = {
        "odoo_version": "17.0",
        "postgres_image": "postgres:15-alpine",
        "modules": ["crm"],
        "addons_path": None,
        "database": "test_odoo",
        "admin_password": "admin",
        "env": {},
        "properties": props,
        "user_key": "",
    }
    direct_key = compute_snapshot_key(**key_kwargs)
    harness_key = compute_snapshot_key(**key_kwargs)
    assert direct_key == harness_key


def test_empty_properties_key_differs_from_non_empty() -> None:
    """Prove that different properties produce different snapshot keys.

    This is the D-08 correctness guarantee: the partial-key footgun that DEBT-04 fixes
    — where an empty-properties key would silently match a properties-bearing setup's key
    — cannot occur because the key inputs differ.
    """
    base_kwargs = {
        "odoo_version": "17.0",
        "postgres_image": "postgres:15-alpine",
        "modules": ["crm"],
        "addons_path": None,
        "database": "test_odoo",
        "admin_password": "admin",
        "env": {},
        "user_key": "",
    }
    key_empty = compute_snapshot_key(**base_kwargs, properties={})
    key_with_props = compute_snapshot_key(**base_kwargs, properties={"web.base.url": "http://localhost:8069"})
    assert key_empty != key_with_props
