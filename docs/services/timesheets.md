# Timesheets Service

Access via `client.timesheets`.  Tracks time on projects via `account.analytic.line`.

## Timer workflow

The timer workflow mirrors Odoo's UI timer -- start a timer with zero hours,
then stop it to compute the elapsed duration automatically:

```python
from godoo.services.timesheets.types import TimerStartOptions

# Start a timer on a project
entry = await client.timesheets.start_timer(
    TimerStartOptions(project_id=3, task_id=12, description="Bug fix #451")
)
timesheet_id = entry["id"]

# ... do work ...

# Stop the timer -- hours are computed from elapsed time
result = await client.timesheets.stop_timer(timesheet_id)
print(f"Logged {result['unit_amount']:.2f} hours")
```

## Manual logging

For time already completed, use `log_time` with explicit hours:

```python
from godoo.services.timesheets.types import LogTimeOptions

entry = await client.timesheets.log_time(
    LogTimeOptions(
        project_id=3,
        task_id=12,
        hours=2.5,
        description="Code review",
        date="2026-03-24",
    )
)
```

## Methods

### start_timer

Create a timesheet entry with `unit_amount=0` and the timer flag set.
Returns the created record dict.

### stop_timer

Stop a running timer by timesheet ID.  Computes elapsed hours from
`timer_start` and writes `unit_amount`.  Returns the updated record dict.

### get_running_timers

List all currently running timers for an employee:

```python
timers = await client.timesheets.get_running_timers()
for t in timers:
    print(t["id"], t["name"], t["project_id"])
```

### log_time

Create a completed timesheet entry with explicit hours.  Returns the created
record dict.

### list_timesheets

List timesheet entries with optional filters:

```python
from godoo.services.timesheets.types import TimesheetListOptions

entries = await client.timesheets.list_timesheets(
    TimesheetListOptions(project_id=3, limit=20, order="date desc")
)
```

## Employee resolution

Like the attendance service, `start_timer`, `get_running_timers`, and `log_time`
accept an optional `employee_id`.  When omitted, the employee linked to the
authenticated user is resolved automatically.
