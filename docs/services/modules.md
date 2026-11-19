# Modules Service

Access via `client.modules`.  Manages Odoo module installation, upgrades, and
queries against `ir.module.module`.

## Methods

### install_module

Install a module by technical name.  If already installed, the call is a no-op:

```python
info = await client.modules.install_module("sale")
print(info["state"])  # "installed"
```

### uninstall_module

Dispatches the uninstall button even for an already-uninstalled visible match.
The server can affect dependent modules; returned metadata is read after dispatch.
Install, uninstall and detail lookup raise `RuntimeError` for no visible match.

<!-- atlas: base/modules-uninstall-lifecycle -->

```python
info = await client.modules.uninstall_module("sale")
```

### upgrade_module

Upgrade an already-installed module.  Raises `RuntimeError` if the module is not
currently installed:

```python
info = await client.modules.upgrade_module("sale")
```

### is_module_installed

Returns false if no visible installed match exists; invisible addons cannot be distinguished from absent ones:

<!-- atlas: base/modules-check-installed -->

```python
if await client.modules.is_module_installed("hr_timesheet"):
    print("Timesheets module is active")
```

### get_module_info

Fetch the first visible technical-name match. Missing visible matches raise `RuntimeError`:

<!-- atlas: base/modules-check-installed -->

```python
info = await client.modules.get_module_info("sale")
print(info["shortdesc"], info["installed_version"])
```

### list_modules

List visible module rows using keyword `state` and `application` equality filters,
plus `limit` and `offset` pagination. List and detail rows select identity, state,
descriptions, author, website, versions, license, application and category metadata:

<!-- atlas: base/modules-list-installed -->

```python
# All installed applications
apps = await client.modules.list_modules(state="installed", application=True)

# First 20 modules regardless of state
all_mods = await client.modules.list_modules(limit=20)
```

## ir_cron retry

<!-- atlas: base/modules-install-lifecycle -->

Module buttons can conflict with scheduled actions. The client allows **three
total attempts** (at most two delays). The constructor's `retry_delay` defaults
to **5 seconds**. Classification checks exception text and RPC data fields
`message`, `debug` and `name` for `ir_cron` or `scheduled action`, ignoring case.
Unclassified errors and the final failure propagate.

## Module states

Odoo modules flow through these states:

```
uninstalled → installed → to upgrade → installed
                        → to remove  → uninstalled
```

The `install_module` method skips the call entirely if the module is already in
the `installed` state.
