---
id: SEED-003
status: dormant
planted: 2026-06-02
planted_during: v1.1 — Typed Models & Browser Reach
trigger_when: when relevant
scope: medium
---

# SEED-003: Improve RPC error reporting — categorize errors, strip sensitive traceback data

## Why This Matters

Two drivers, one security and one ergonomic:

- **Privacy / data leakage.** Odoo RPC faults bubble back the full server `data` dict —
  Python traceback, internal file paths, method `arguments` (which can include record
  values and, in some flows, credential/session data). Today that raw dict is passed
  through unchanged into the error and re-exposed verbatim via `to_json()` as
  `"details"` (`errors.py:20-43`). For a public library, that means a caller who logs or
  surfaces `to_json()` is silently leaking server internals — and potentially secrets —
  to logs, error trackers, or end users.
- **Developer experience.** A categorized error (`invalid_domain`, `unknown_field`,
  `access_denied`, `validation_error`, …) plus the *offending model / field /
  constraint* and a clean human-readable Odoo message lets consumers branch on error
  type programmatically and show users something meaningful — instead of regex-scraping
  a traceback string. This is also a parity concern with the godoo-ts error model.

The key constraint: **strip the sensitive data from the user-facing surface while
preserving the original raw error somewhere** (e.g. a `.raw` attribute) so debugging
isn't lost — opt-in, not on by default.

## When to Surface

**Trigger:** when relevant

This seed will surface during `/gsd:new-milestone` when the milestone scope matches.
Strongest fit is a DX / error-handling milestone or alongside introspection work — model
and field metadata make it possible to name the offending field/constraint cleanly.

## Scope Estimate

**Medium** — a phase or two. The error tree and `_categorize_error()` dispatch already
exist (`transport.py:138`), so this is not a rewrite. The work is: (1) design the
categorization taxonomy + structured fields (model/field/constraint/human-message),
(2) build a sanitizer that splits the clean user-facing payload from the raw `data`,
(3) decide where raw data lives and how it's opted into, (4) tests covering each Odoo
fault shape. Cross-cutting across `transport.py` + `errors.py`, hence a phase or two
rather than a quick task.

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
