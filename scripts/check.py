#!/usr/bin/env -S uv run --script
# /// script
# requires-python = "==3.14.8"
# dependencies = []
# ///
"""Native checks. Evidence and immutable candidates are explicit external directories."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import tomllib
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGES = {"godoo-client", "godoo-introspection", "godoo-testcontainers", "godoo"}
MYPY = [f"packages/{name}/src" for name in sorted(PACKAGES - {"godoo"})]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_identity() -> dict:
    def git(*args: str) -> str:
        return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()

    files = git("ls-files", "--cached", "--others", "--exclude-standard", "-z").split("\0")
    tree = {name: sha(ROOT / name) if (ROOT / name).is_file() else None for name in sorted(set(files)) if name}
    patch = subprocess.check_output(["git", "diff", "HEAD", "--binary"], cwd=ROOT)
    return {
        "source_sha": git("rev-parse", "HEAD"),
        "tree_sha256": hashlib.sha256(json.dumps(tree, sort_keys=True).encode()).hexdigest(),
        "patch_sha256": hashlib.sha256(patch).hexdigest(),
        "dirty": bool(git("status", "--porcelain")),
        "lock_sha256": sha(ROOT / "uv.lock"),
        "python": sys.version,
        "uv": subprocess.check_output(["uv", "--version"], text=True).strip(),
        "github_sha": os.environ.get("GITHUB_SHA"),
        "pr_head": os.environ.get("PR_HEAD_SHA"),
        "pr_base": os.environ.get("PR_BASE_SHA"),
        "run_url": (
            f"{os.environ.get('GITHUB_SERVER_URL', 'https://github.com')}/"
            f"{os.environ.get('GITHUB_REPOSITORY')}/actions/runs/{os.environ['GITHUB_RUN_ID']}"
            if os.environ.get("GITHUB_RUN_ID")
            else None
        ),
    }


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def run(args: list[str], evidence: Path, label: str, *, cwd: Path = ROOT, env: dict | None = None) -> None:
    print(f"[{label}] {' '.join(map(str, args))}", flush=True)
    with (evidence / f"{label}.log").open("w") as output:
        result = subprocess.run(args, cwd=cwd, env=env, stdout=output, stderr=subprocess.STDOUT)
    write_json(evidence / f"{label}.json", {"command": args, "cwd": str(cwd), "exit": result.returncode})
    if result.returncode:
        print((evidence / f"{label}.log").read_text()[-12000:], file=sys.stderr)
        raise RuntimeError(f"{label} exited {result.returncode}; see {evidence}")


def check_junit(path: Path, *, integration: bool = False) -> None:
    cases = list(ET.parse(path).getroot().iter("testcase"))
    if not cases or any(c.find(tag) is not None for c in cases for tag in ("skipped", "failure", "error")):
        raise RuntimeError(f"empty, skipped or failed required suite: {path}")
    if integration:
        classes = [c.get("classname", "") for c in cases]
        expected = ("tests.integration.", "package_tests.godoo_testcontainers.", "package_tests.godoo_client.")
        if any(not any(suite in name for name in classes) for suite in expected):
            raise RuntimeError("root, testcontainers and client integration suites must all execute")


def verify_manifest(artifacts: Path, *, clean: bool = False) -> dict:
    manifest = json.loads((artifacts / "manifest.json").read_text())
    identity = source_identity()
    for key in ("source_sha", "tree_sha256", "patch_sha256", "lock_sha256"):
        if manifest["source"][key] != identity[key]:
            raise RuntimeError(f"candidate identity mismatch: {key}")
    if clean and (identity["dirty"] or manifest["source"]["dirty"]):
        raise RuntimeError("promotion requires a clean committed candidate")
    wheels = manifest["wheels"]
    if {w["name"] for w in wheels} != PACKAGES or len(wheels) != 4:
        raise RuntimeError("exactly four distributions required")
    if {p.name for p in artifacts.glob("*.whl")} != {w["filename"] for w in wheels}:
        raise RuntimeError("candidate wheel set mismatch")
    versions = {
        data["project"]["name"]: data["project"]["version"]
        for p in (ROOT / "packages").glob("*/pyproject.toml")
        if (data := tomllib.loads(p.read_text()))
    }
    if set(versions) != PACKAGES or len(set(versions.values())) != 1:
        raise RuntimeError("source distribution versions must remain coordinated")
    for w in wheels:
        if Path(w["filename"]).name != w["filename"] or sha(artifacts / w["filename"]) != w["sha256"]:
            raise RuntimeError("wheel hash mismatch")
        if w["version"] != versions[w["name"]]:
            raise RuntimeError("wheel version mismatch")
    if manifest["requirements_sha256"] != sha(artifacts / "requirements.txt"):
        raise RuntimeError("dependency export hash mismatch")
    return manifest


def consumer(artifacts: Path, scratch: Path, evidence: Path) -> Path:
    verify_manifest(artifacts)
    python = scratch / "venv/bin/python"
    run(["uv", "venv", "--python", "3.14.8", str(scratch / "venv")], evidence, "consumer-venv")
    run(
        [
            "uv",
            "pip",
            "sync",
            "--python",
            str(python),
            "--require-hashes",
            "--only-binary",
            ":all:",
            str(artifacts / "requirements.txt"),
        ],
        evidence,
        "consumer-dependencies",
    )
    wheel_requirements = scratch / "wheels.txt"
    wheel_requirements.write_text("".join(f"{p} --hash=sha256:{sha(p)}\n" for p in sorted(artifacts.glob("*.whl"))))
    run(
        [
            "uv",
            "pip",
            "install",
            "--python",
            str(python),
            "--no-deps",
            "--require-hashes",
            "-r",
            str(wheel_requirements),
        ],
        evidence,
        "consumer-wheels",
    )
    run(["uv", "pip", "check", "--python", str(python)], evidence, "consumer-consistency")
    return python


def package(artifacts: Path, evidence: Path, scratch: Path) -> None:
    artifacts.mkdir(parents=True, exist_ok=True)
    if any(artifacts.iterdir()):
        raise RuntimeError("build destination must be empty; never overwrite an immutable candidate")
    run(["uv", "sync", "--frozen", "--all-packages", "--all-extras"], evidence, "sync")
    run(
        [
            "uv",
            "export",
            "--frozen",
            "--all-packages",
            "--all-extras",
            "--no-emit-workspace",
            "--output-file",
            str(artifacts / "requirements.txt"),
        ],
        evidence,
        "export",
    )
    run(
        [
            "uv",
            "build",
            "--all-packages",
            "--wheel",
            "--no-build-isolation",
            "--python",
            str(ROOT / ".venv/bin/python"),
            "--out-dir",
            str(artifacts),
        ],
        evidence,
        "build",
    )
    import email
    import zipfile

    wheels = []
    for wheel in sorted(artifacts.glob("*.whl")):
        with zipfile.ZipFile(wheel) as z:
            metadata = email.message_from_bytes(
                z.read(next(n for n in z.namelist() if n.endswith(".dist-info/METADATA")))
            )
            name, version = metadata["Name"], metadata["Version"]
            if name == "godoo":
                assert not metadata.get_all("Requires-Dist")
                assert all(".dist-info/" in n for n in z.namelist()), z.namelist()
            else:
                assert f"godoo/{name.removeprefix('godoo-')}/py.typed" in z.namelist()
        wheels.append({"name": name, "version": version, "filename": wheel.name, "sha256": sha(wheel)})
    write_json(
        artifacts / "manifest.json",
        {
            "schema": 1,
            "source": source_identity(),
            "wheels": wheels,
            "requirements_sha256": sha(artifacts / "requirements.txt"),
            "publication": "unpublished-local-candidate",
        },
    )
    python = consumer(artifacts, scratch, evidence)
    shutil.copy(ROOT / "scripts/installed_consumer.py", scratch / "installed_consumer.py")
    run(
        [str(python), "-I", str(scratch / "installed_consumer.py"), str(artifacts / "manifest.json")],
        evidence,
        "installed-public-api",
        cwd=scratch,
    )
    run([str(scratch / "venv/bin/godoo-introspect"), "--help"], evidence, "installed-cli", cwd=scratch)


def odoo(major: int, artifacts: Path, evidence: Path, scratch: Path, baseline: Path | None) -> None:
    manifest = verify_manifest(artifacts)
    if os.environ.get("ODOO_VERSION", f"{major}.0") not in (str(major), f"{major}.0"):
        raise RuntimeError("explicit ODOO_VERSION differs from supported verification target")
    if major == 19:
        if baseline is None:
            raise RuntimeError("explicit Odoo19 requires same-candidate Odoo18 evidence")
        proof = json.loads((baseline / "result.json").read_text())
        if (
            proof["mode"] != "odoo18"
            or proof["passed"] is not True
            or proof["source"] != source_identity()
            or proof["manifest_sha256"] != sha(artifacts / "manifest.json")
        ):
            raise RuntimeError("Odoo19 baseline identity/result mismatch")
    run(["docker", "info"], evidence, "docker-readiness")
    python = consumer(artifacts, scratch, evidence)
    shutil.copytree(ROOT / "tests", scratch / "tests", ignore=shutil.ignore_patterns("__pycache__"))
    for tests in sorted((ROOT / "packages").glob("*/tests")):
        shutil.copytree(
            tests,
            scratch / "package_tests" / tests.parent.name.replace("-", "_"),
            ignore=shutil.ignore_patterns("__pycache__"),
        )
    shutil.copy(ROOT / "scripts/proof_plugin.py", scratch / "proof_plugin.py")
    (scratch / "pytest.ini").write_text(
        "[pytest]\nasyncio_mode = auto\nasyncio_default_fixture_loop_scope = session\n"
        "markers =\n    integration: disposable Odoo required\n"
    )
    env = {k: v for k, v in os.environ.items() if not k.startswith(("ODOO_", "PYTHONPATH"))}
    env.update(
        {
            "ODOO_VERSION": f"{major}.0",
            "GODOO_PROOF_MAJOR": str(major),
            "GODOO_PROOF_EVIDENCE": str(evidence),
            "PYTHONPATH": str(scratch),
            "TESTCONTAINERS_RYUK_DISABLED": "true",
        }
    )
    write_json(evidence / "candidate.json", manifest)
    run(
        [
            str(python),
            "-m",
            "pytest",
            "tests/integration",
            "package_tests",
            "--import-mode=importlib",
            "-p",
            "proof_plugin",
            "-m",
            "integration",
            "-v",
            "-s",
            "--junitxml",
            str(evidence / "integration.xml"),
        ],
        evidence,
        "integration",
        cwd=scratch,
        env=env,
    )
    check_junit(evidence / "integration.xml", integration=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["offline", "package", "odoo18", "odoo19", "manifest"])
    parser.add_argument("--artifacts", type=Path)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--baseline18", type=Path)
    args = parser.parse_args()
    evidence = args.evidence.resolve()
    if evidence == ROOT or ROOT in evidence.parents:
        parser.error("evidence must be outside the source checkout")
    artifacts = args.artifacts.resolve() if args.artifacts else None
    if artifacts and (artifacts == ROOT or ROOT in artifacts.parents):
        parser.error("artifacts must be outside the source checkout")
    evidence.mkdir(parents=True, exist_ok=True)
    before = source_identity()
    result = {"mode": args.mode, "source": before, "passed": False}
    scratch_root = Path.home() / ".cache/agent-work/godoo-py/verification"
    scratch_root.mkdir(parents=True, exist_ok=True)
    try:
        with tempfile.TemporaryDirectory(prefix=f"{args.mode}-", dir=scratch_root) as temp:
            scratch = Path(temp)
            if args.mode == "offline":
                run(["uv", "sync", "--frozen", "--all-packages", "--all-extras"], evidence, "sync")
                run(["uv", "run", "--frozen", "ruff", "check", "."], evidence, "ruff")
                run(["uv", "run", "--frozen", "ruff", "format", "--check", "."], evidence, "format")
                run(["uv", "run", "--frozen", "mypy", *MYPY], evidence, "mypy")
                run(
                    [
                        "uv",
                        "run",
                        "--frozen",
                        "pytest",
                        "packages",
                        "tests",
                        "--import-mode=importlib",
                        "-m",
                        "not integration",
                        "--junitxml",
                        str(evidence / "unit.xml"),
                    ],
                    evidence,
                    "unit",
                )
                check_junit(evidence / "unit.xml")
                run(
                    ["uv", "run", "--frozen", "mkdocs", "build", "--strict", "--site-dir", str(evidence / "site")],
                    evidence,
                    "docs",
                )
            elif artifacts is None:
                parser.error("this mode requires --artifacts")
            elif args.mode == "package":
                package(artifacts, evidence, scratch)
            elif args.mode == "manifest":
                verify_manifest(artifacts, clean=True)
            else:
                odoo(int(args.mode[-2:]), artifacts, evidence, scratch, args.baseline18)
            if before != source_identity():
                raise RuntimeError("source changed during verification")
            if artifacts:
                result["manifest_sha256"] = sha(artifacts / "manifest.json")
            result["passed"] = True
    finally:
        write_json(evidence / "result.json", result)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
