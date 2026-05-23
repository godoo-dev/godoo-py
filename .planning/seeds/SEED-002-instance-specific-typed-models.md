---
id: SEED-002
status: dormant
planted: 2026-05-23
planted_during: v1.0 — after milestone completion (next-milestone capture)
trigger_when: next milestone scoping; whenever godoo-introspection or core read/search API is touched
scope: large
---

# SEED-002: Instance-specific typed models — Pydantic codegen + polymorphic typed reads

## Why This Matters

Today every read is stringly-typed and returns untyped dicts:

```python
contact = await client.read("res.partner", [1])   # -> list[dict], IDE knows nothing
```

The IDE understands nothing about `contact` — no field autocomplete, no type checking,
and none of Odoo's wire quirks are handled. The goal is Pythonic ergonomics where the
returned record is something the IDE genuinely understands, with types derived from the
**user's actual Odoo instance** (custom fields, installed modules, selection values and
all), not a generic guess.

## The Converged Direction

Decided during exploration (2026-05-23):

- **`godoo-introspection` ships a CLI generator.** It reads the live schema (`fields_get`)
  and emits a **Pydantic-model package to a user-chosen output path**. Where that output
  lives (committed vs gitignored) is the *consuming project's* choice, not godoo's.
- **Core `godoo` gains the transform/validation layer** behind an **optional extra**
  (`godoo[typed]` → pydantic). Default install stays **httpx-only** — the established
  "sole runtime dep" constraint holds.
- **No separate `client.typed`.** The existing `read` / `search_read` / etc. **dispatch on
  the first argument**: a `str` (`"res.partner"`) → today's raw-dict path, unchanged;
  a generated model class → typed path with validation + transform. Types cleanly via
  `@overload`:

  ```python
  @overload
  async def read(self, model: str, ids, *, fields=...) -> list[dict[str, Any]]: ...
  @overload
  async def read(self, model: type[T], ids, *, fields=...) -> list[T]: ...

  contact = await client.read(ResPartner, [1])     # -> list[ResPartner], validated
  raw     = await client.read("res.partner", [1])  # -> list[dict], unchanged
  ```

- Each generated model carries its Odoo name (e.g. `__odoo_model__ = "res.partner"`) so the
  class alone tells the client both the wire model and the target type.
- **Dispatch must duck-type** (`hasattr(model, "__odoo_model__")` or a tiny `Protocol`),
  **never `isinstance(x, BaseModel)`** — so core never imports pydantic at runtime unless
  the typed path is actually exercised.

## Why Pydantic (not dataclasses, for this layer)

The core convention is "dataclasses, not Pydantic" — that still holds for core types. This
typed layer is the deliberate exception because the value is the **bidirectional transform**
that Odoo's wire format demands, declaratively:

- empty fields come back as `False` (not `None`/`""`) → coerce to `None`
- many2one is `[id, "Display Name"]` → parse into a typed ref
- date/datetime are strings → `date` / `datetime`
- selection fields → `Literal` / `Enum`

A dataclass can't do this without hand-written `__post_init__` glue per model. Pydantic does
it declaratively, which is exactly what generated code wants.

## Why Static Codegen (not LSP / mypy-plugin / runtime-dynamic)

Explored and rejected for the headline goal:

- **"IDE understands `contact`" is fundamentally static** — editors light up from what a type
  checker resolves ahead of time.
- **Runtime dynamic synthesis** (`pydantic.create_model()` from live schema) gives great
  validation but is **statically invisible** → no editor autocomplete. Fails the headline goal
  on its own.
- **mypy plugin** could synthesize types from a schema descriptor, but **pyright/Pylance — the
  VS Code default — has no third-party plugin API**, so most users get no editor autocomplete.
- **Dedicated LSP** is the most "live" option but is a whole product to build/maintain, and
  retyping the *return value* of `read(...)` is much harder than offering completions.
- **Static generated models** = universal editor + checker support, predictable, offline after
  generation. The common, proven choice — hence the CLI generator.

(Static codegen and runtime validation are not mutually exclusive; the generated Pydantic
models serve both — static for the editor, runtime for the transform.)

## Open Questions (settle when this milestone is scoped)

1. **Partial reads.** Passing a model class implies "give me the model's fields." If the caller
   *also* passes `fields=[...]`, the result is partial and strict Pydantic validation would fail.
   Strategy options: fetch-all-when-class-given · `model_construct` (skip validation) ·
   all-Optional models. This is the precision-vs-ergonomics line — precise per-field-selection
   typing likely stays on the raw path.
2. **Relational fields.** How does `parent_id` (m2o `[id, "name"]`) or `child_ids` (o2m) type?
   Nested model · a typed `Ref[Model]` · or just the id. Big scope lever — nesting balloons
   codegen and fetch semantics.
3. **Selection fields.** Emit `Literal[...]` / `Enum` from the instance's selection values — and
   how to keep those fresh as the instance changes (re-generation cadence).

## Breadcrumbs

- `packages/godoo-introspection/` — placeholder package; this is where the CLI generator lands.
  Its stated purpose is already "schema discovery + typed code generation."
- `packages/godoo/src/godoo/client.py` — `read`/`search_read`/CRUD helpers; the `@overload` +
  duck-typed dispatch goes here.
- `packages/godoo/pyproject.toml` — where the `[typed]` optional-extra (pydantic) is declared.
- `packages/godoo/src/godoo/rpc/transport.py` — `fields_get` lives at this layer; the generator
  consumes the schema it exposes.

## Notes

Captured via `/gsd:explore` on 2026-05-23. Premise from Marc: "improve user ergonomics by
providing typing hints based on the user's Odoo instance." TS twin's approach deemed irrelevant —
Python gets a Pythonic design, not a port.
