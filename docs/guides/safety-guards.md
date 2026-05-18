# Safety Guards

godoo includes an optional safety system that intercepts write and delete
operations before they reach the Odoo server.  This is useful for CLI tools,
scripts, and multi-environment setups where accidental mutations must be
prevented.

## Off by default

Safety guards are **disabled** by default for backwards compatibility.  You
opt in by providing a `SafetyContext`.

## SafetyContext

A `SafetyContext` holds a single async `confirm` callback.  Before any
non-read operation, godoo calls this function with an `OperationInfo`
describing what is about to happen.  If the callback returns `False`, the
operation is blocked locally and `OdooSafetyError` is raised.

```python
from godoo import SafetyContext, OperationInfo

async def confirm_handler(op: OperationInfo) -> bool:
    print(f"About to {op.level} on {op.model}: {op.description}")
    answer = input("Allow? [y/N] ")
    return answer.lower() == "y"

safety = SafetyContext(confirm=confirm_handler)
```

## Safety levels

| Level | When | Blocked? |
|---|---|---|
| `READ` | `search`, `read`, `search_read`, `search_count`, etc. | Never |
| `WRITE` | `create`, `write`, `message_post`, and any unknown method | If `confirm` returns `False` |
| `DELETE` | `unlink` | If `confirm` returns `False` |

The level is inferred from the RPC method name via `infer_safety_level`.

## Per-client safety

Pass the context when creating the config:

```python
from godoo import OdooClient, OdooClientConfig

config = OdooClientConfig(
    url="https://prod.mycompany.com",
    database="production",
    username="admin",
    password="secret",
    safety=safety,
)
client = OdooClient(config)
```

Or set it after creation:

```python
client.set_safety_context(safety)
```

## Global default

Set a default for all clients that do not have an explicit safety context:

```python
from godoo.safety import set_default_safety_context

set_default_safety_context(safety)
```

Clients with an explicit context (even `None` for "disabled") ignore the global
default.

## OdooSafetyError

When an operation is blocked, `OdooSafetyError` is raised.  This is a **local
error** -- no RPC call is made.  It includes the `OperationInfo` that was
rejected:

```python
from godoo import OdooSafetyError

try:
    await client.unlink("res.partner", [1])
except OdooSafetyError as e:
    print(e.operation.model)  # "res.partner"
    print(e.operation.level)  # "DELETE"
```

## Auto-approve reads pattern

A common pattern is to auto-approve reads and prompt only for writes/deletes:

```python
async def interactive_confirm(op: OperationInfo) -> bool:
    if op.level == "READ":
        return True  # never reached, but defensive
    return input(f"Allow {op.level} on {op.model}? [y/N] ").lower() == "y"
```

Note that `READ` operations are **never** sent to the confirm callback -- they
are short-circuited internally.
