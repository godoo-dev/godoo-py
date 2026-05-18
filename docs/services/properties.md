# Properties Service

Access via `client.properties`.  Handles Odoo's properties fields safely using
a read-merge-write pattern.

## Why read-merge-write?

Odoo properties use **full replacement semantics**.  When you write a properties
field, you must send the **complete** set of property values.  If you only send
the property you want to change, all other properties on the record are erased.

The properties service solves this by:

1. Reading the current properties from the record
2. Converting them to write format
3. Merging your updates into the full set
4. Writing the merged result back

## Methods

### update_safely

Update one or more properties on a single record:

```python
await client.properties.update_safely(
    "sale.order",
    42,
    "x_properties",  # the properties field name
    {"priority": "high", "reviewed": True},
)
```

This reads the current value of `x_properties` on record 42, merges in
`priority` and `reviewed`, and writes the full set back.

### update_safely_batch

Same operation but for multiple records in parallel using `asyncio.gather`:

```python
await client.properties.update_safely_batch(
    "sale.order",
    [42, 43, 44],
    "x_properties",
    {"priority": "high"},
)
```

Each record is processed independently -- a failure on one record does not
prevent the others from being updated.

### properties_to_write_format

Static utility that converts the read format (list of property dicts) into the
write format (flat key-value dict):

```python
# Read format from Odoo:
props = [
    {"name": "priority", "value": "high", "type": "char"},
    {"name": "reviewed", "value": True, "type": "boolean"},
]

# Convert to write format:
write_vals = PropertiesService.properties_to_write_format(props)
# {"priority": "high", "reviewed": True}
```

This conversion is done automatically inside `update_safely` -- you only need
this method if you are building custom write logic.
