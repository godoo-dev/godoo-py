# Plan 04-03 — Spike Findings (Task 1)

Resolved the three RESEARCH.md open questions for the `godoo` placeholder distribution.

## Open Question 1 — hatchling metadata-only wheel config

**Answer:** A plain `pyproject.toml` does **not** build — hatchling errors with
"At least one file selection option must be defined in the
`tool.hatch.build.targets.wheel` table". The documented `only-include = []` also fails
(an empty list still counts as "no selection option defined").

**Confirmed fix:** add to `packages/godoo-meta/pyproject.toml`:

```toml
[tool.hatch.build.targets.wheel]
bypass-selection = true
```

This is hatchling's canonical option for a code-free, metadata-only distribution. With
it, both the editable build (`uv sync`) and the wheel/sdist build succeed.

## Open Question 2 — `uv build --package godoo` resolves by project.name

**Answer:** Confirmed. `uv build --package godoo` builds successfully even though the
directory is named `godoo-meta` — uv resolves `--package` by `project.name`, not by
directory name. **Directory name is irrelevant.** No fallback needed.

## Open Question 3 — `uv sync` auto-discovery via `members = ["packages/*"]`

**Answer:** Confirmed. `uv sync` discovers `packages/godoo-meta/` automatically; it
installed `godoo==0.1.1` as a workspace member. No manual member entry required.

## Confirmed working build invocation (no branching)

```
uv build --package godoo
```

## Wheel verification

`dist/godoo-0.1.1-py3-none-any.whl` contains only:
`godoo-0.1.1.dist-info/{METADATA,WHEEL,RECORD}` — zero `.py` files, no
`godoo/__init__`. Namespace invariant (`find packages/ -path "*/src/godoo/__init__.py"`)
still returns zero results.

## Final state of packages/godoo-meta/pyproject.toml

`[project]` name=godoo, version=0.1.1, empty dependencies, readme=README.md;
`[build-system]` hatchling; `[tool.hatch.build.targets.wheel] bypass-selection = true`.
No `src/` tree.
