from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def invoke(root: Path, *args: str, env: dict | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(["python", *args], cwd=root, env=env, text=True, capture_output=True)


@pytest.mark.parametrize("bad", ["failure", "skipped", "cancelled", "missing", "pending"])
def test_required_rejects_every_nonsuccess(bad: str) -> None:
    results = {k: {"result": "success"} for k in ("offline", "package", "odoo18")}
    if bad == "missing":
        del results["odoo18"]
    else:
        results["odoo18"]["result"] = bad
    run = invoke(ROOT, "scripts/gate.py", "required", env={**os.environ, "RESULTS": json.dumps(results)})
    assert run.returncode != 0
    assert "all mandatory jobs must succeed" in run.stderr


def test_required_accepts_only_complete_success() -> None:
    results = {k: {"result": "success"} for k in ("offline", "package", "odoo18")}
    assert (
        invoke(ROOT, "scripts/gate.py", "required", env={**os.environ, "RESULTS": json.dumps(results)}).returncode == 0
    )
    results["unexpected"] = {"result": "success"}
    assert (
        invoke(ROOT, "scripts/gate.py", "required", env={**os.environ, "RESULTS": json.dumps(results)}).returncode != 0
    )


@pytest.mark.parametrize("requested", [True, False])
@pytest.mark.parametrize("state", ["success", "failure", "cancelled", "skipped", "pending", "missing", None])
def test_requested_compatibility_contributes_to_required(requested: bool, state: str | None) -> None:
    results = {k: {"result": "success"} for k in ("offline", "package", "odoo18")}
    if state != "missing":
        results["odoo19"] = {"result": state}
    result = invoke(
        ROOT,
        "scripts/gate.py",
        "required",
        env={**os.environ, "RESULTS": json.dumps(results), "REQUESTED19": str(requested).lower()},
    )
    accepted = state == ("success" if requested else "skipped") or (not requested and state == "missing")
    assert (result.returncode == 0) == accepted, result.stderr


@pytest.fixture
def candidate(tmp_path: Path):
    """Local gate simulation, not hosted proof; no canonical Git refs are changed."""
    root = tmp_path / "checkout"
    (root / "scripts").mkdir(parents=True)
    for name in ("check.py", "gate.py"):
        shutil.copy(ROOT / "scripts" / name, root / "scripts" / name)
    for name in ("godoo", "godoo-client", "godoo-introspection", "godoo-testcontainers"):
        directory = root / "packages" / name
        directory.mkdir(parents=True)
        (directory / "pyproject.toml").write_text(f'[project]\nname="{name}"\nversion="0.2.0"\n')
    (root / "uv.lock").write_text("fixture lock")
    (root / ".gitignore").write_text("__pycache__/\n")
    for args in (
        ["init", "--initial-branch=main"],
        ["add", "."],
        ["-c", "user.name=Gate fixture", "-c", "user.email=fixture@example.invalid", "commit", "-m", "fixture"],
    ):
        subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    subprocess.run(["git", "update-ref", "refs/remotes/origin/main", commit], cwd=root, check=True)
    artifacts = tmp_path / "candidate"
    artifacts.mkdir()
    (artifacts / "requirements.txt").write_text("")
    identity = json.loads(
        invoke(
            root,
            "-c",
            "import sys,json;sys.path.insert(0,'scripts');"
            "from check import source_identity;print(json.dumps(source_identity()))",
        ).stdout
    )
    import hashlib

    def digest(p):
        return hashlib.sha256(p.read_bytes()).hexdigest()

    wheels = []
    for p in sorted((root / "packages").iterdir()):
        wheel = artifacts / f"{p.name.replace('-', '_')}-0.2.0-py3-none-any.whl"
        wheel.write_bytes(b"gate fixture bytes; not an installable wheel")
        wheels.append({"name": p.name, "version": "0.2.0", "filename": wheel.name, "sha256": digest(wheel)})
    manifest = {"source": identity, "wheels": wheels, "requirements_sha256": digest(artifacts / "requirements.txt")}
    (artifacts / "manifest.json").write_text(json.dumps(manifest))
    proof = tmp_path / "proof"
    for mode in ("offline", "package", "odoo18"):
        (proof / mode).mkdir(parents=True)
        (proof / mode / "result.json").write_text(
            json.dumps(
                {
                    "source": identity,
                    "passed": True,
                    "mode": mode,
                    "manifest_sha256": digest(artifacts / "manifest.json"),
                }
            )
        )
    return root, artifacts, proof, commit


def promotion(candidate):
    root, artifacts, proof, commit = candidate
    return invoke(
        root, "scripts/gate.py", "promote", "--candidate", commit, "--artifacts", str(artifacts), "--proof", str(proof)
    )


def test_promotion_accepts_matching_committed_main_candidate(candidate) -> None:
    result = promotion(candidate)
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("fault", ["artifact", "proof", "missing-proof", "version", "source", "dirty"])
def test_promotion_rejects_mismatched_candidate_or_proof(candidate, fault: str) -> None:
    root, artifacts, proof, _ = candidate
    if fault == "artifact":
        next(artifacts.glob("*.whl")).write_bytes(b"tampered")
    elif fault == "missing-proof":
        (proof / "odoo18/result.json").unlink()
    elif fault == "proof":
        p = proof / "odoo18/result.json"
        record = json.loads(p.read_text())
        record["manifest_sha256"] = "0" * 64
        p.write_text(json.dumps(record))
    elif fault in ("version", "source"):
        p = artifacts / "manifest.json"
        record = json.loads(p.read_text())
        if fault == "version":
            record["wheels"][0]["version"] = "9.0.0"
        else:
            record["source"]["source_sha"] = "0" * 40
        p.write_text(json.dumps(record))
    else:
        (root / "uv.lock").write_text("modified")
    assert promotion(candidate).returncode != 0


def test_release_rejects_moving_ref_and_commit_outside_main(candidate) -> None:
    root, _, _, _ = candidate
    moving = invoke(root, "scripts/gate.py", "resolve", "--candidate", "main")
    assert moving.returncode != 0 and "full immutable SHA" in moving.stderr
    (root / "unreviewed").write_text("not on main")
    subprocess.run(["git", "add", "."], cwd=root, check=True)
    subprocess.run(
        ["git", "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "-m", "outside main"],
        cwd=root,
        check=True,
        capture_output=True,
    )
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    assert invoke(root, "scripts/gate.py", "resolve", "--candidate", commit).returncode != 0


def test_later_major_requires_same_candidate18_before_docker(candidate, tmp_path: Path) -> None:
    root, artifacts, _, _ = candidate
    env = {k: v for k, v in os.environ.items() if not k.startswith("ODOO_")}
    result = invoke(
        root,
        "scripts/check.py",
        "odoo19",
        "--artifacts",
        str(artifacts),
        "--evidence",
        str(tmp_path / "later-proof"),
        env=env,
    )
    assert result.returncode != 0 and "requires same-candidate Odoo18 evidence" in result.stderr
    assert not (tmp_path / "later-proof/docker-readiness.log").exists()


def test_explicit17_rejected_before_docker(candidate, tmp_path: Path) -> None:
    root, artifacts, _, _ = candidate
    result = invoke(
        root,
        "scripts/check.py",
        "odoo18",
        "--artifacts",
        str(artifacts),
        "--evidence",
        str(tmp_path / "wrong-major"),
        env={**os.environ, "ODOO_VERSION": "17"},
    )
    assert result.returncode != 0 and "differs from supported verification target" in result.stderr
    assert not (tmp_path / "wrong-major/docker-readiness.log").exists()


@pytest.mark.parametrize(
    "body", ["", '<testcase name="skip"><skipped/></testcase>', '<testcase name="failure"><failure/></testcase>']
)
def test_required_test_proof_rejects_empty_or_skipped_or_failed(tmp_path: Path, body: str) -> None:
    spec = importlib.util.spec_from_file_location("native_check", ROOT / "scripts/check.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    report = tmp_path / "result.xml"
    report.write_text(f"<testsuites><testsuite>{body}</testsuite></testsuites>")
    with pytest.raises(RuntimeError, match="empty, skipped or failed"):
        module.check_junit(report)


def test_required_missing_docker_is_a_failure(candidate, tmp_path: Path) -> None:
    root, artifacts, _, _ = candidate
    env = {k: v for k, v in os.environ.items() if not k.startswith("ODOO_")}
    env["DOCKER_HOST"] = "unix:///nonexistent-godoo-verification-docker.sock"
    result = invoke(
        root,
        "scripts/check.py",
        "odoo18",
        "--artifacts",
        str(artifacts),
        "--evidence",
        str(tmp_path / "no-docker"),
        env=env,
    )
    assert result.returncode != 0 and "docker-readiness exited" in result.stderr
    assert not (tmp_path / "no-docker/integration.log").exists()


@pytest.mark.parametrize("passed", [False, "true", None])
def test_later_major_rejects_malformed18_success_before_docker(candidate, tmp_path: Path, passed) -> None:
    root, artifacts, proof, _ = candidate
    baseline = proof / "odoo18"
    record = json.loads((baseline / "result.json").read_text())
    record["passed"] = passed
    (baseline / "result.json").write_text(json.dumps(record))
    env = {k: v for k, v in os.environ.items() if not k.startswith("ODOO_")}
    result = invoke(
        root,
        "scripts/check.py",
        "odoo19",
        "--artifacts",
        str(artifacts),
        "--evidence",
        str(tmp_path / "later-proof"),
        "--baseline18",
        str(baseline),
        env=env,
    )
    assert result.returncode != 0 and "Odoo19 baseline identity/result mismatch" in result.stderr
    assert not (tmp_path / "later-proof/docker-readiness.log").exists()
