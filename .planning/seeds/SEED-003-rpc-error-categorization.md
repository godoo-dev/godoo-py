---
id: SEED-003
status: dormant
planted: 2026-06-02
planted_during: v1.1 — Typed Models & Browser Reach
trigger_when: when relevant
scope: unknown
---

# SEED-003: Improve RPC error reporting — categorize errors, strip sensitive traceback data

## Why This Matters

_To be filled in. Run `/gsd:capture --seed --enrich SEED-003` to add context._

## When to Surface

**Trigger:** when relevant

This seed will surface during `/gsd:new-milestone` when the milestone scope matches.

## Scope Estimate

**Unknown** — run `/gsd:capture --seed --enrich SEED-003` to estimate effort.

## Breadcrumbs

- `packages/godoo-client/src/godoo/client/rpc/transport.py:138` — `_categorize_error()` maps `exception_type` / `data.name` to typed `OdooRpcError` subclasses; currently handles `access_denied`, `access_error`, `validation_error`, `user_error`, `missing_error`
- `packages/godoo-client/src/godoo/client/rpc/transport.py:94` — call site: `raise self._categorize_error(data["error"])`
- `packages/godoo-client/src/godoo/client/rpc/transport.py:140-145` — raw `data` dict passed through to error unchanged (includes `debug`, `traceback`, `arguments`, internal paths)
- `packages/godoo-client/src/godoo/client/errors.py:20-43` — `OdooRpcError` stores full `data` dict as `self.data`; exposed via `to_json()` as `"details"`
- `packages/godoo-client/src/godoo/client/errors.py:9-129` — full error tree: `OdooError` → `OdooRpcError` → `OdooAuthError`, `OdooNetworkError`/`OdooTimeoutError`, `OdooValidationError`, `OdooAccessError`, `OdooMissingError`; plus `OdooSafetyError` (local, non-RPC)
- `packages/godoo-client/src/godoo/client/errors.py:12` — `OdooError.to_json()` base; each subclass overrides `"error"` key but none strip or parse traceback fields

## Notes

Original idea: Odoo RPC bubbles exceptions with tracebacks that include internal paths. Categorize errors (e.g. `invalid_domain`, `unknown_field`, `access_denied`, `validation_error`) PLUS the offending model/field/constraint, surfacing a clean human-readable Odoo message. Strip Python tracebacks, internal file paths, and any credential/session data from the user-facing error — while preserving the original raw error data somewhere (e.g. a `.raw` / `.to_json()` field) for debugging.

_Captured via one-shot seed capture. Enrich with trigger, why, and scope at your convenience._
