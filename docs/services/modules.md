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

Quick boolean check:

```python
if await client.modules.is_module_installed("hr_timesheet"):
    print("Timesheets module is active")
```

### get_module_info

Fetch detailed info for a single module:

```python
info = await client.modules.get_module_info("sale")
print(info["shortdesc"], info["installed_version"])
```

### list_modules

List modules with optional filters:

```python
# All installed applications
apps = await client.modules.list_modules(state="installed", application=True)

# First 20 modules regardless of state
all_mods = await client.modules.list_modules(limit=20)
```

## ir_cron retry

Module install/uninstall/upgrade triggers Odoo server operations that sometimes
collide with scheduled actions (`ir.cron`).  When a lock error mentioning
`ir_cron` is detected, godoo retries up to **3 times** with a **5-second
delay** between attempts.

## Module states

Odoo modules flow through these states:

```
uninstalled → installed → to upgrade → installed
                        → to remove  → uninstalled
```

The `install_module` method skips the call entirely if the module is already in
the `installed` state.
