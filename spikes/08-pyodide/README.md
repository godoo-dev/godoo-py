# Pyodide transport prototype

A non-shipping browser harness comparing three Odoo RPC transport strategies under
Pyodide 0.29.4. The [browser design](../../docs/browser.md) records the historical
feasibility result and current shipping prerequisites. Source remains experimental;
no browser extra or reusable cloud endpoint is promised.

| File | Purpose |
| --- | --- |
| `index.html` | Loads Pyodide and runs the three strategies, reporting results locally |
| `transport_pyfetch.py` | Custom `pyfetch` transport prototype through `transport_factory` |
| `infra/` | Experimental Azure Container Apps endpoint recipe |

## Serving the harness

Use a real HTTP(S) origin. Opening the file directly gives a `null` Origin, which
an endpoint CORS policy can reject before the transport runs. For local inspection:

```sh
cd spikes/08-pyodide
python -m http.server 8000
```

The endpoint CORS origin must match the page's scheme, host and port exactly.
Running an authenticated experiment requires an explicitly authorized disposable
endpoint. Historical deployment recipes do not authorize new cloud operations.
Do not assume resources mentioned in the recipe still exist.

The harness accepts `base_url`, `db`, `user` and `password` query parameters. This
exposes them in browser history and the URL: use only disposable test credentials,
never business credentials, and never commit filled values. Results can include
remote payloads and tracebacks. Retain necessary private evidence outside source
under `~/.share/agent-work/godoo-py/<task>/` and send work/acceptance results through
the shared tracker.

## Strategy boundaries

The historical spike reported success for stock httpx and the custom
`PyfetchTransport`; `pyodide-httpx==0.2.0` failed because it imported a missing
private httpx module. The custom transport is the selected design path. Stock
httpx's fetch routing still needs a stable public contract before being selected
as an alternative. Do not add `pyodide-httpx` to production dependencies.

The page installs experimental dependencies in-browser through micropip. This does
not prove the current Python >=3.14 distributions can be installed in its CPython
3.13 runtime, and does not change the normal client's httpx dependency. Recheck
runtime, dependency versions and endpoint compatibility for any new experiment.
