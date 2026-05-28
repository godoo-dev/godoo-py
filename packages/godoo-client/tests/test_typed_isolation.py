"""Load-bearing TYPED-05 isolation guard: `import godoo.client` must NOT load pydantic.

This test spawns a clean Python subprocess so the parent process's sys.modules
(which may contain pydantic from test_pydantic_transform.py or other test files)
cannot pollute the check. The subprocess is the only way to get a truly clean
module namespace.

This is the CI canary for the godoo[typed] isolation invariant: the default
install (httpx-only) must never trigger a pydantic import. If any future
contributor adds `from godoo.client._pydantic_transform import ...` at module
top, this test fails immediately.
"""

from __future__ import annotations

import subprocess
import sys


def test_pydantic_not_imported_by_default() -> None:
    """Subprocess guard: import godoo.client must not trigger import pydantic (TYPED-05).

    The subprocess spawns a clean Python process, imports godoo.client, then
    asserts pydantic is absent from sys.modules. This is the load-bearing CI
    guard — the default install promise (httpx-only runtime dependency) is
    enforced here. A failure message includes stdout and stderr so the
    regression source is immediately identifiable.
    """
    script = (
        "import godoo.client; "
        "import sys; "
        "assert 'pydantic' not in sys.modules, "
        "f'pydantic was imported by godoo.client (modules: {sorted(m for m in sys.modules if \"pydantic\" in m)})'; "
        "print('OK')"
    )
    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, (
        "godoo.client isolation check FAILED — pydantic was imported at module load time.\n"
        f"stdout: {result.stdout!r}\n"
        f"stderr: {result.stderr!r}\n"
        "Fix: ensure no top-level `from godoo.client._pydantic_transform import ...` "
        "exists in any godoo.client module."
    )
    assert result.stdout.strip() == "OK"
