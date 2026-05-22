# godoo — Async Odoo SDK for Python

An async Odoo JSON-RPC SDK family for Python developers automating or testing Odoo
instances. This `godoo` distribution is a meta package — it ships no importable code and
exists to host the family README and reserve the namespace. Install the real
distributions below.

## Packages

### godoo-client

The async Odoo JSON-RPC client.

```bash
pip install godoo-client
```

```python
from godoo.client import OdooClient
```

### godoo-introspection

Live-schema discovery and typed code generation.

```bash
pip install godoo-introspection
```

```python
from godoo.introspection import Introspector
```

### godoo-testcontainers

Docker-based Odoo test infrastructure.

```bash
pip install godoo-testcontainers
```

```python
from godoo.testcontainers import OdooTestContainer
```

## License

LGPL-3.0-or-later
