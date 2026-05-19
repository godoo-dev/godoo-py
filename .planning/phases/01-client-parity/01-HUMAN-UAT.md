---
status: partial
phase: 01-client-parity
source: [01-VERIFICATION.md]
started: 2026-05-19T12:00:00Z
updated: 2026-05-19T12:00:00Z
---

## Current Test

[awaiting human testing]

## Tests

### 1. iter_search_read does not silently drop records on a short non-final page (CR-01)
expected: All records are yielded even when Odoo row-level rules cause a short non-final page; the `if len(batch) < fetch_size: break` termination should only fire on a genuinely empty last page. Needs a running Odoo instance with record rules that filter rows mid-page.
result: [pending]

### 2. read_binary handles real Odoo binary payloads and malformed fields (CR-02)
expected: `read_binary` returns correct bytes for attachments stored via the Odoo filestore (newline-wrapped base64), and raises a typed `OdooError` (not a raw `binascii.Error`) for corrupted fields. Needs a real Odoo attachment or a mocked payload with embedded newlines / invalid characters.
result: [pending]

## Summary

total: 2
passed: 0
issues: 0
pending: 2
skipped: 0
blocked: 0

## Gaps
