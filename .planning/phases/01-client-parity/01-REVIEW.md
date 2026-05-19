---
phase: 01-client-parity
reviewed: 2026-05-19T00:00:00Z
depth: standard
files_reviewed: 7
files_reviewed_list:
  - packages/godoo/src/godoo/client.py
  - packages/godoo/src/godoo/rpc/transport.py
  - packages/godoo/src/godoo/services/cdc/service.py
  - packages/godoo/src/godoo/py.typed
  - packages/godoo/tests/test_client.py
  - packages/godoo/tests/test_transport.py
  - packages/godoo/tests/test_cdc.py
findings:
  critical: 2
  warning: 6
  info: 4
  total: 12
status: issues_found
---

# Phase 1: Code Review Report

**Reviewed:** 2026-05-19T00:00:00Z
**Depth:** standard
**Files Reviewed:** 7
**Status:** issues_found

## Summary

Phase 1 (Client Parity) adds configurable transport timeout + `OdooTimeoutError`,
the `CdcService.get_feed` async-generator fix, the `py.typed` marker, an async
context manager, `with_context()` ambient context, `iter_search_read()` keyset
pagination, and `fields_get`/`ref`/`execute_kw`/`read_binary`/overloaded bulk
`create`.

The implementation is broadly sound and the test coverage of the new surface is
good. However, two correctness defects must be fixed before this ships:

1. `iter_search_read()` has a keyset-pagination termination bug that **silently
   drops records** whenever `batch_size` exceeds a caller-supplied `limit` and the
   first page is full. The data-loss case is masked by the existing tests because
   none of them exercise `batch_size > limit` across a page boundary.
2. `read_binary()` passes `base64.b64decode()` a value that, for any real Odoo
   binary field, is a `str` containing newline-wrapped base64 — but it never sets
   `validate=False` and never guards against a non-`str`/non-`bytes` payload,
   producing a `binascii.Error` crash on legitimate data.

There are also several robustness gaps (`KeyError` on missing cursor field,
dead branch in `_effective_safety`, unbounded server-side trust in pagination).

## Critical Issues

### CR-01: `iter_search_read` drops records when `batch_size > limit`

**File:** `packages/godoo/src/godoo/client.py:232-258`
**Issue:**
The page loop computes `fetch_size = min(batch_size, remaining)` and then
terminates with `if len(batch) < fetch_size: break`. When the caller passes a
`limit` smaller than `batch_size`, `fetch_size` is clamped to `remaining`. The
generator yields up to `limit` records inside the `for` loop and `return`s
correctly (line 253-254), so the *limit* case happens to be safe.

The genuine defect is the **interaction of `fetch_size` clamping with the
break condition across pages**. Consider `batch_size=3`, `limit=5`:

- Page 1: `remaining=5`, `fetch_size=min(3,5)=3`. Server returns 3 records.
  `yielded` becomes 3. `len(batch)=3` is not `< fetch_size=3`, so the loop
  continues. `last_id` advances. Correct so far.
- Page 2: `remaining=5-3=2`, `fetch_size=min(3,2)=2`. Server returns 2 records.
  `yielded` reaches 5, `return` fires inside the `for`. Correct.

Now consider the data-loss case — `batch_size=3`, **no `limit`**, and the
collection has exactly 3 matching records on the last page, but the *server
caps the page at fewer rows than requested* (Odoo applies its own
`limit`/access-rule filtering and may legitimately return fewer rows than the
`limit` kwarg even when more records exist beyond the cursor — e.g. record
rules silently filter rows out of a page). The line `if len(batch) < fetch_size:
break` treats "server returned a short page" as "end of data" and terminates,
**skipping every record past the cursor**. Keyset pagination must terminate on
an *empty* page, not a *short* one, because per-page row counts are not a
reliable end-of-data signal once row-level filtering is in play.

The `not batch` check at line 245 already handles the only correct terminator.
The `len(batch) < fetch_size` short-circuit at line 256 is an unsound
optimization.

**Fix:**
```python
        # Do NOT break on a short page — Odoo record rules can filter rows
        # out of a page, so a short page is not a reliable end-of-data signal.
        # Terminate only on an empty page (handled by `if not batch: break`).
        last_id = batch[-1]["id"]
```
Remove lines 256-257 entirely. If a fast-path is desired, only break when the
page is short *and* no row-level filtering can apply — which the client cannot
know — so the safe choice is to always loop until an empty page.

### CR-02: `read_binary` crashes on real Odoo binary payloads

**File:** `packages/godoo/src/godoo/client.py:299-311`
**Issue:**
`base64.b64decode(raw)` is called on the raw field value with default
arguments. Two problems:

1. Odoo returns binary fields as base64 **strings that frequently contain
   embedded newlines** (`\n` every 76 chars for attachments stored via the
   filestore, and `\r\n` for some transports). `base64.b64decode()` with
   `validate=False` (the default) tolerates ASCII whitespace, so newlines are
   fine — but any other non-alphabet character (which Odoo can emit when the
   field is a *computed* binary returning a Python `bytes` repr, or when the
   value is a data-URI-prefixed string) raises `binascii.Error`. The function
   advertises "return decoded bytes" with no documented failure mode for
   malformed input, so an unhandled `binascii.Error` escapes as a non-`OdooError`
   exception, breaking the typed-exception contract described in CLAUDE.md.
2. If `raw` is neither `False`/`None` nor a valid base64 `str` — e.g. Odoo
   returns an `int` or a list for a mis-typed field — `b64decode` raises
   `TypeError`/`binascii.Error` with a confusing message instead of a typed
   `OdooValidationError`.

The test suite only exercises `base64.b64encode(b"hello")` (clean, no newlines)
and the `False` case, so neither real-world failure is covered.

**Fix:**
```python
    raw = records[0].get(field)
    if raw is False or raw is None:
        return b""
    if not isinstance(raw, str | bytes):
        raise OdooValidationError(
            f"Field {field!r} on {model}:{record_id} is not a binary value "
            f"(got {type(raw).__name__})"
        )
    try:
        return base64.b64decode(raw)
    except (binascii.Error, ValueError) as exc:
        raise OdooValidationError(
            f"Field {field!r} on {model}:{record_id} is not valid base64"
        ) from exc
```
Add `import binascii` at the top of the module.

## Warnings

### WR-01: `iter_search_read` raises `KeyError` if server omits `id`

**File:** `packages/godoo/src/godoo/client.py:258`
**Issue:**
`last_id = batch[-1]["id"]` assumes every returned record contains an `id` key.
The code injects `id` into `fetch_fields` (line 230), but if the Odoo server
silently drops it (some custom models, or `fields_get`-restricted access), this
raises a bare `KeyError` mid-iteration with no context. The same bare-subscript
risk exists at line 258 for cursor advancement.

**Fix:**
```python
        next_id = batch[-1].get("id")
        if next_id is None:
            raise OdooValidationError(
                f"iter_search_read on {model!r}: server did not return 'id' "
                f"in records; keyset pagination cannot advance"
            )
        last_id = next_id
```

### WR-02: Dead/redundant branch in `_effective_safety`

**File:** `packages/godoo/src/godoo/client.py:105-111`
**Issue:**
The `else` branch passes
`self._safety_context if self._safety_context is not _UNDEFINED else None`.
But this branch is only reachable when `self._safety_context is not _UNDEFINED`
(the `if` at line 106 already returned for the `_UNDEFINED` case). Therefore the
inner ternary's `else None` arm is **unreachable dead code** — `self._safety_context`
is always the non-`_UNDEFINED` value here. This obscures intent and will confuse
future maintainers into thinking `None` is a distinct path.

**Fix:**
```python
    def _effective_safety(self) -> SafetyContext | None:
        if self._safety_context is _UNDEFINED:
            return resolve_safety_context(self._config.safety, undefined=False)
        # Explicitly set by set_safety_context() — may be a SafetyContext or None
        return resolve_safety_context(self._safety_context, undefined=False)
```

### WR-03: `_safety_context` typed as `Any` defeats `mypy --strict`

**File:** `packages/godoo/src/godoo/client.py:83`
**Issue:**
`self._safety_context: Any = _UNDEFINED`. CLAUDE.md mandates `mypy --strict`
and "no `any`". Typing the attribute as `Any` silently disables type checking
on every read/write of the safety context — `set_safety_context` could be
passed a wrong type and mypy would not catch it. The sentinel pattern can be
expressed without `Any`.

**Fix:** Use a typed sentinel union:
```python
from typing import Final

class _Undefined:
    pass

_UNDEFINED: Final = _Undefined()

# in __init__:
self._safety_context: SafetyContext | None | _Undefined = _UNDEFINED
```

### WR-04: `__aexit__` swallows transport-close errors masking the real exception

**File:** `packages/godoo/src/godoo/client.py:420-427`
**Issue:**
`__aexit__` calls `await self.aclose()` unconditionally. If `aclose()` itself
raises (e.g. httpx transport error during shutdown) while the `async with` body
also raised, the `aclose()` exception **replaces** the original body exception,
hiding the real failure. Conversely, an `aclose()` failure on a clean exit
surfaces as-is, which is fine. The asymmetric risk is the masking case.

**Fix:** Guard the close so a shutdown error never masks the body exception:
```python
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        try:
            await self.aclose()
        except Exception:
            if exc_val is None:
                raise
            logger.warning("aclose() failed during __aexit__", exc_info=True)
```

### WR-05: `with_context` ContextVar layer leaks across `await` boundaries in same task

**File:** `packages/godoo/src/godoo/client.py:45-60, 205-207`
**Issue:**
`_OdooContextScope` is a **synchronous** context manager (`__enter__`/`__exit__`)
backed by a `ContextVar`. Within a single task this is correct, and the
concurrency-isolation test (`test_with_context_concurrent_isolation`) passes
because each task gets its own context copy. However, a sync `with` block that
spans an `await` does not isolate the context from a *child task spawned inside
the block* via `asyncio.create_task()` — the child captures the context at
creation time and **keeps the ambient layer even after the parent's `with`
block exits**. That child task's later RPC calls will silently carry stale
`lang`/context values. This is a documented `contextvars` semantic, but the
`with_context` docstring ("merges kwargs into every RPC call in its block")
implies block-scoped containment that does not hold for spawned tasks.

**Fix:** Document the limitation explicitly in the `with_context` docstring, and
note that `asyncio.create_task()` inside a `with_context` block captures the
context. Consider providing an async variant or a warning. At minimum:
```python
    def with_context(self, **kwargs: Any) -> _OdooContextScope:
        """Return a sync context manager that merges kwargs into every RPC
        call made *in the current task* within its block.

        NOTE: tasks spawned via asyncio.create_task() inside the block inherit
        the ambient context and retain it even after the block exits.
        """
```

### WR-06: `execute_kw` read-like custom methods are over-gated as WRITE

**File:** `packages/godoo/src/godoo/client.py:286-297`; `safety/__init__.py:68-73`
**Issue:**
`execute_kw` routes through `call()`, which is correct for safety. But
`infer_safety_level` returns `"WRITE"` for any method not in `READ_METHODS`/
`DELETE_METHODS`. A custom read-only method invoked via `execute_kw`
(e.g. `get_report_values`, `name_get` on an older model alias, a computed
helper) is classified `WRITE` and will trigger the safety `confirm` callback,
prompting the user for confirmation on a pure read. This is conservative (no
data-loss risk) but degrades UX and is the kind of false positive that trains
users to blindly approve. The `execute_kw` docstring claims the guard
"classifies and gates it" without noting the classification is a coarse default.

**Fix:** Document the coarse classification in the `execute_kw` docstring, and
consider an optional `level: SafetyLevel | None = None` parameter so callers
can declare a known-read custom method as `"READ"`.

## Info

### IN-01: `py.typed` marker file is empty — verify it is packaged

**File:** `packages/godoo/src/godoo/py.typed`
**Issue:**
`py.typed` is correctly a zero-byte marker (PEP 561). However, an empty marker
only takes effect if `hatchling` actually includes it in the wheel. Confirm
`packages/godoo/pyproject.toml` does not exclude extension-less files and that
the built wheel contains `godoo/py.typed`. This is outside the reviewed file
set but is a required companion check for the marker to have any effect.

**Fix:** Add a packaging test or verify with
`python -m zipfile -l dist/godoo-*.whl | grep py.typed`.

### IN-02: `call()` re-injects `context` even when merged context is empty-equivalent

**File:** `packages/godoo/src/godoo/client.py:149-154`
**Issue:**
When `"context" in kwargs` is true but the explicit context is `{}` and there
is no ambient context, `merged_ctx` is `{}` and the `if merged_ctx:` guard
correctly skips re-injection — good. But if `kwargs` already had
`context={}` explicitly, the original empty `context` key survives in `kwargs`
and is sent to Odoo. Harmless, but inconsistent with the "strip empty context"
intent shown by the guard. Minor.

**Fix:** Optional — normalize by dropping an empty `context` key from `kwargs`.

### IN-03: `OperationInfo.details` typed as bare `dict` with `# type: ignore`

**File:** `packages/godoo/src/godoo/safety/__init__.py:39`
**Issue:**
`details: dict | None = None  # type: ignore[type-arg]`. Suppressing the
type-arg error rather than spelling `dict[str, Any]` is inconsistent with the
project's `mypy --strict` convention and the rest of the codebase. Not in the
primary changed-file set but adjacent to `client.py`'s safety usage.

**Fix:** `details: dict[str, Any] | None = None`.

### IN-04: Transport timeout test reaches into private `_client.timeout`

**File:** `packages/godoo/tests/test_transport.py:209-211`
**Issue:**
`test_transport_timeout_param_accepted` asserts on `t._client.timeout.read`,
coupling the test to httpx internals and `JsonRpcTransport` private state. If
httpx changes its `Timeout` representation the test breaks for reasons
unrelated to godoo. Acceptable for now, but a behavioral test (mock a slow
response, assert `OdooTimeoutError`) would be more robust — and the timeout
config path from `OdooClientConfig.timeout` → `JsonRpcTransport` is currently
**not** covered end-to-end by any test.

**Fix:** Add a test that constructs an `OdooClient` with
`OdooClientConfig(timeout=...)` and verifies the transport received it, plus a
behavioral timeout test.

---

_Reviewed: 2026-05-19T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
