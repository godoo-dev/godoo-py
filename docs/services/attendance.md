# Attendance Service

Access via `client.attendance`.  Manages clock-in/clock-out operations against
Odoo's `hr.attendance` model.

## Employee resolution

All methods accept an optional `employee_id`.  When omitted, the service
resolves the employee linked to the authenticated user via `hr.employee`.  This
means the most common case (clocking yourself in) requires no extra arguments.

## Methods

### clock_in

```python
record = await client.attendance.clock_in()
print(record.check_in)  # "2026-03-24 08:30:00"
```

With an explicit employee:

```python
record = await client.attendance.clock_in(employee_id=7)
```

### clock_out

```python
record = await client.attendance.clock_out()
print(record.check_out)  # "2026-03-24 17:00:00"
```

### get_status

Check whether an employee is currently clocked in:

```python
status = await client.attendance.get_status()
if status.is_clocked_in:
    print(f"Clocked in since {status.last_check_in}")
```

### list_attendances

List attendance records with filtering options:

```python
from godoo.services.attendance.types import AttendanceListOptions

records = await client.attendance.list_attendances(
    AttendanceListOptions(limit=10, order="check_in desc")
)
for r in records:
    print(r.check_in, r.check_out)
```

## Validation

- **Clock in twice** -- raises an error if the employee already has an open
  attendance (no `check_out`).
- **Clock out without being clocked in** -- raises an error if no open
  attendance exists.

## Full example

```python
from godoo import create_client

client = await create_client()

# Clock in
await client.attendance.clock_in()

# Check status
status = await client.attendance.get_status()
assert status.is_clocked_in

# Clock out
record = await client.attendance.clock_out()
print(f"Worked from {record.check_in} to {record.check_out}")

await client.aclose()
```
