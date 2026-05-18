"""Timesheets service — standalone async functions."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from godoo.errors import OdooValidationError
from godoo.services.attendance.functions import resolve_employee_id
from godoo.services.timesheets.types import (
    LogTimeOptions,
    TimerStartOptions,
    TimesheetListOptions,
)

if TYPE_CHECKING:
    from godoo.client import OdooClient

_MODEL = "account.analytic.line"

_TS_FIELDS = [
    "id",
    "employee_id",
    "project_id",
    "task_id",
    "name",
    "unit_amount",
    "date",
    "create_date",
]


async def start_timer(
    client: OdooClient,
    options: TimerStartOptions,
    employee_id: int | None = None,
) -> dict[str, Any]:
    """Start a timesheet timer (unit_amount=0, to be stopped later)."""
    eid = await resolve_employee_id(client, employee_id)
    today = datetime.now(UTC).strftime("%Y-%m-%d")
    values: dict[str, Any] = {
        "employee_id": eid,
        "project_id": options.project_id,
        "name": options.description or "/",
        "unit_amount": 0,
        "date": today,
    }
    if options.task_id is not None:
        values["task_id"] = options.task_id
    rec_id = await client.create(_MODEL, values)
    records = await client.read(_MODEL, rec_id, fields=_TS_FIELDS)
    return records[0]


async def stop_timer(
    client: OdooClient,
    timesheet_id: int,
) -> dict[str, Any]:
    """Stop a running timer — compute elapsed hours from create_date."""
    records = await client.read(_MODEL, timesheet_id, fields=_TS_FIELDS)
    if not records:
        raise OdooValidationError(f"Timesheet {timesheet_id} not found")
    rec = records[0]
    create_date_str = rec.get("create_date", "")
    if not create_date_str:
        raise OdooValidationError("Timesheet has no create_date")
    create_dt = datetime.strptime(create_date_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=UTC)
    now = datetime.now(UTC)
    elapsed_hours = max((now - create_dt).total_seconds() / 3600, 0.01)
    elapsed_hours = round(elapsed_hours, 2)
    await client.write(_MODEL, timesheet_id, {"unit_amount": elapsed_hours})
    rec["unit_amount"] = elapsed_hours
    return rec


async def get_running_timers(
    client: OdooClient,
    employee_id: int | None = None,
) -> list[dict[str, Any]]:
    """Return all timesheets with unit_amount == 0 (active timers)."""
    eid = await resolve_employee_id(client, employee_id)
    return await client.search_read(
        _MODEL,
        [("employee_id", "=", eid), ("unit_amount", "=", 0)],
        fields=_TS_FIELDS,
        order="create_date desc",
    )


async def log_time(
    client: OdooClient,
    options: LogTimeOptions,
    employee_id: int | None = None,
) -> dict[str, Any]:
    """Log a completed timesheet entry directly."""
    if options.hours <= 0:
        raise OdooValidationError("Hours must be positive")
    eid = await resolve_employee_id(client, employee_id)
    date = options.date or datetime.now(UTC).strftime("%Y-%m-%d")
    values: dict[str, Any] = {
        "employee_id": eid,
        "project_id": options.project_id,
        "name": options.description or "/",
        "unit_amount": options.hours,
        "date": date,
    }
    if options.task_id is not None:
        values["task_id"] = options.task_id
    rec_id = await client.create(_MODEL, values)
    records = await client.read(_MODEL, rec_id, fields=_TS_FIELDS)
    return records[0]


async def list_timesheets(
    client: OdooClient,
    options: TimesheetListOptions | None = None,
) -> list[dict[str, Any]]:
    """List timesheet entries with optional filters."""
    opts = options or TimesheetListOptions()
    domain: list[Any] = list(opts.domain)
    if opts.employee_id is not None:
        domain.append(("employee_id", "=", opts.employee_id))
    if opts.project_id is not None:
        domain.append(("project_id", "=", opts.project_id))

    kwargs: dict[str, Any] = {"fields": _TS_FIELDS}
    if opts.limit is not None:
        kwargs["limit"] = opts.limit
    if opts.offset is not None:
        kwargs["offset"] = opts.offset
    if opts.order is not None:
        kwargs["order"] = opts.order

    return await client.search_read(_MODEL, domain, **kwargs)
