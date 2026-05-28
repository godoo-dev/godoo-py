---
status: partial
phase: 05-directory-rename
source: [05-VERIFICATION.md]
started: 2026-05-28
updated: 2026-05-28
---

## Current Test

[awaiting operator push and CI verification]

## Tests

### 1. CI green from `packages/godoo-client/` paths after push
expected: Operator pushes `develop` to `origin`; GitHub Actions `test.yml` workflow run completes with all jobs green (ruff, mypy, pytest, build). CI resolves all source paths from `packages/godoo-client/` without manual patching. The PEP 420 guard test (`packages/godoo-client/tests/test_namespace.py::test_godoo_is_namespace_package`) appears in the pytest output and passes.
result: [pending]

## Summary

total: 1
passed: 0
issues: 0
pending: 1
skipped: 0
blocked: 0

## Gaps
