---
name: godoo-py-verification
description: Check a godoo-py change — the offline check command, the installed-wheel package tier and disposable Odoo 18/19 integration — and maintain that check path when interfaces change. Publication and deployment are separate operations.
---

# Verify godoo-py

Work in the selected godoo-py checkout. uv's version is pinned by
`required-version` in `pyproject.toml` and Python's by `.python-version`. setup-uv and
setup-python read them in CI, uv enforces its pin, and the scripts use Python from
`.python-version`. Install the workspace once:

```sh
uv sync --frozen --all-packages --all-extras
```

## Check command

The default check is:

```sh
./scripts/check.py offline --evidence /tmp/godoo-py-offline
```

It runs Ruff lint (including complexity), Ruff format, strict mypy on the three
source packages, every non-integration test under `packages/` and `tests/`, and a
strict mkdocs build. An empty or skipped suite fails. Its exit status is the
result. `--evidence` must be outside the checkout; it holds the tool logs.

For iteration, run the focused tools:

```sh
uv run --frozen ruff check . && uv run --frozen ruff format --check .
uv run --frozen mypy packages/godoo-client/src packages/godoo-testcontainers/src packages/godoo-introspection/src
uv run --frozen pytest packages/ tests/ --import-mode=importlib -m "not integration" -k NAME
```

CI ([test.yml](../../../.github/workflows/test.yml), GitHub-hosted
`ubuntu-latest`) runs `offline`, `package` and `odoo18` on every PR to `main`
and every push to `main`. The `required` job requires all three. A newer push to
the same PR cancels the older run. Run the offline check before pushing, but
leave the `package` and Odoo tiers to the PR's CI unless the change needs them
earlier.

## Complexity

Ruff `C901` blocks at `max-complexity = 10` (`pyproject.toml`). Refactor a new
violation without changing behaviour, adding characterization tests where
coverage is missing. If a function cannot be fixed safely, report it to the
owner with its complexity and the reason. An approved exception is a
`# noqa: C901` on that function with its reason and "owner-approved".

## Slow tiers

Run these when the owner asks or when the change touches what the tier covers.
CI runs `package` and `odoo18` on every PR anyway.

- **Package:** use it for packaging, entrypoints, namespaces, dependencies or
  the public API seen from an installed wheel.

  ```sh
  ./scripts/check.py package --artifacts /tmp/godoo-py-candidate --evidence /tmp/godoo-py-package
  ```

  `--artifacts` must be a new or empty directory outside the checkout. It
  builds the four wheels there, installs them without
  editable links into an isolated consumer, and drives the public client,
  dynamic-property and code-generation APIs through an in-process transport. It
  does not contact a real Odoo server.

- **Odoo 18:** use it for RPC behaviour, services, introspection against a live
  schema, testcontainers, the harness or snapshots. It needs Docker.

  ```sh
  ./scripts/check.py odoo18 --artifacts /tmp/godoo-py-candidate --evidence /tmp/godoo-py-odoo18
  ```

  It installs the same wheels, runs every integration-marked test from
  `tests/integration` and the package test directories against disposable Odoo
  and Postgres containers, and checks that the server reports major version 18.

- **Odoo 19:** this tier is optional. Run it only on request and after Odoo 18
  passes for the same candidate. In CI it runs through manual dispatch with
  `qualify19`.

  ```sh
  ./scripts/check.py odoo19 --artifacts /tmp/godoo-py-candidate --baseline18 /tmp/godoo-py-odoo18 --evidence /tmp/godoo-py-odoo19
  ```

Each Odoo tier creates its own containers, a random network, mapped ports and
temporary Postgres data, and removes them on exit, even after a failure. If a
run is interrupted, find what it left with `docker ps -a` and
`docker network ls`, and remove only those resources. Never prune Docker
globally or stop containers that another session owns. Odoo 17 is unsupported.

## Release path

[release.yml](../../../.github/workflows/release.yml) is manual. It reruns
`test.yml` for a reviewed SHA on `main`. `scripts/gate.py` then checks the
results and the wheel `manifest.json`, and the job publishes those exact wheels
only when `publish` is selected. That release gate is the consumer of the
manifest and proof artifacts that `check.py` writes. Version preparation
(`prepare-version.yml`) is a separate reviewable change.

## Maintain this path

When a public interface changes, update the affected commands here, in
`CONTRIBUTING.md` and in `scripts/check.py`. Keep failing assertions that
protect real behaviour rather than relaxing them. Hosted branch protection and
PyPI trusted publishing are configured outside this repository.
