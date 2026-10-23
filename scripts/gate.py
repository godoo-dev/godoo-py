#!/usr/bin/env -S uv run --script
# /// script
# requires-python = "==3.14.8"
# dependencies = []
# ///
"""Fail-closed CI aggregation and immutable main-line candidate promotion checks."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from pathlib import Path

from check import ROOT, sha, source_identity, verify_manifest

MANDATORY = {"offline", "package", "odoo18"}


def required(results: dict, requested19: bool = False) -> None:
    expected = MANDATORY | ({"odoo19"} if requested19 or "odoo19" in results else set())
    if set(results) != expected or any(
        not isinstance(results[k], dict) or results[k].get("result") != "success" for k in MANDATORY
    ):
        raise RuntimeError(f"all mandatory jobs must succeed: {results}")
    if "odoo19" in expected and (
        not isinstance(results["odoo19"], dict)
        or results["odoo19"].get("result") != ("success" if requested19 else "skipped")
    ):
        raise RuntimeError(f"requested compatibility result must match selection: {results}")


def eligible(candidate: str) -> str:
    if not re.fullmatch(r"[0-9a-f]{40}", candidate):
        raise RuntimeError("candidate must be a full immutable SHA")
    subprocess.run(["git", "cat-file", "-e", f"{candidate}^{{commit}}"], cwd=ROOT, check=True)
    subprocess.run(["git", "merge-base", "--is-ancestor", candidate, "refs/remotes/origin/main"], cwd=ROOT, check=True)
    return candidate


def promote(artifacts: Path, proof: Path, candidate: str) -> None:
    eligible(candidate)
    manifest = verify_manifest(artifacts, clean=True)
    current = source_identity()
    if candidate != current["source_sha"]:
        raise RuntimeError("promotion checkout differs from selected SHA")
    for mode in sorted(MANDATORY):
        result = json.loads((proof / mode / "result.json").read_text())
        if result["mode"] != mode or result["passed"] is not True:
            raise RuntimeError(f"missing successful {mode} proof")
        for key in ("source_sha", "tree_sha256", "patch_sha256", "lock_sha256"):
            if result["source"][key] != manifest["source"][key]:
                raise RuntimeError(f"{mode} proof is for another candidate")
        if result["source"]["dirty"]:
            raise RuntimeError("release proof must be from a clean commit")
        if mode != "offline" and result["manifest_sha256"] != sha(artifacts / "manifest.json"):
            raise RuntimeError(f"{mode} proof is for another wheel set")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["required", "resolve", "promote"])
    parser.add_argument("--candidate")
    parser.add_argument("--artifacts", type=Path)
    parser.add_argument("--proof", type=Path)
    args = parser.parse_args()
    if args.mode == "required":
        requested = os.environ.get("REQUESTED19", "false")
        if requested not in {"true", "false"}:
            raise RuntimeError("REQUESTED19 must be true or false")
        required(json.loads(os.environ["RESULTS"]), requested == "true")
    elif args.mode == "resolve":
        print(eligible(args.candidate))
    elif args.artifacts and args.proof and args.candidate:
        promote(args.artifacts.resolve(), args.proof.resolve(), args.candidate)
    else:
        parser.error("promotion requires candidate, artifacts and proof")


if __name__ == "__main__":
    main()
