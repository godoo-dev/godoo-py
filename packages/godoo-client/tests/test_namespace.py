from __future__ import annotations

import godoo


def test_godoo_is_namespace_package() -> None:
    """Assert godoo is a PEP 420 namespace package with no stray __init__.py."""
    assert godoo.__file__ is None, (
        "godoo.__file__ is not None — a stray __init__.py was introduced. "
        "This would break the namespace package layout and could prevent "
        "other packages from contributing to the godoo.* namespace."
    )
