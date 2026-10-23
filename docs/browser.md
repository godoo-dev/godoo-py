# Browser and Pyodide support

Browser execution is a future interface, not an available install extra. All
current distributions require Python >=3.14. The chosen direction keeps that
floor and waits for a compatible Pyodide runtime rather than publishing a separate
lower-floor browser build. Docker/testcontainers remains outside browser scope.

A June 2, 2026 spike recorded a feasibility GO for a custom `PyfetchTransport`
through `OdooClientConfig.transport_factory`. It recorded cross-origin HTTPS
JSON-RPC authentication and a read using Pyodide 0.29.4 / CPython 3.13 in isolation;
that did not install the current >=3.14 distributions or prove a shipped browser
product. The prototype is retained at
[`spikes/08-pyodide/transport_pyfetch.py`](https://github.com/godoo-dev/godoo-py/blob/develop/spikes/08-pyodide/transport_pyfetch.py).
Tracked Git history retains the original decision and work records.

The custom path depends on Pyodide's built-in `pyfetch`. The spike also reported
stock httpx working, but its fetch-routing stability was not established as a
shipping contract. `pyodide-httpx` 0.2.0 failed against a private httpx module and
was rejected as a dependency. These are historical observations, not tests rerun
against current dependencies.

Shipping requires a selected compatible runtime, distribution/extra contract,
CORS and HTTPS configuration owned by the Odoo endpoint, transport/error tests and
an authenticated read in a browser. Revisit Odoo's JSON-RPC successor when choosing
the endpoint contract. Prototype infrastructure is disposable experimental setup;
its presence does not authorize deployment or reuse of old cloud resources.
