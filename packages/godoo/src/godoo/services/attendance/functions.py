"""Attendance service — standalone async functions."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from godoo.errors import OdooValidationError
from godoo.services.attendance.types import (
    AttendanceListOptions,
    AttendanceRecord,
    AttendanceStatus,
)

if TYPE_CHECKING:
    from godoo.client import OdooClient

_MODEL = "hr.attendance"
_EMPLOYEE_MODEL = "hr.employee"


async def resolve_employee_id(
    client: OdooClient,
    employee_id: int | None = None,
) -> int:
    """Resolve an employee ID, falling back to the current session user."""
    if employee_id is not None:
        return employee_id
    session = client.get_session()
    if session is None:
        raise OdooValidationError("Not authenticated — cannot resolve employee")
    ids = await client.search(_EMPLOYEE_MODEL, [("user_id", "=", session.uid)], limit=1)
    if not ids:
        raise OdooValidationError(f"No hr.employee found for uid {session.uid}")
    return ids[0]


async def get_status(
    client: OdooClient,
    employee_id: int | None = None,
) -> AttendanceStatus:
    """Return the current attendance status for an employee."""
    eid = await resolve_employee_id(client, employee_id)
    records = await client.search_read(
        _MODEL,
        [("employee_id", "=", eid)],
        fields=["id", "employee_id", "check_in", "check_out"],
        order="check_in desc",
        limit=1,
    )
    if not records:
        return AttendanceStatus(employee_id=eid, is_clocked_in=False)
    rec = records[0]
    return AttendanceStatus(
        employee_id=eid,
        is_clocked_in=not rec.get("check_out"),
        last_attendance_id=rec["id"],
        last_check_in=rec["check_in"],
    )


async def clock_in(
    client: OdooClient,
    employee_id: int | None = None,
) -> AttendanceRecord:
    """Clock in — create a new attendance record.  Raises if already clocked in."""
    eid = await resolve_employee_id(client, employee_id)
    status = await get_status(client, eid)
    if status.is_clocked_in:
        raise OdooValidationError("Employee is already clocked in")
    now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")
    rec_id = await client.create(_MODEL, {"employee_id": eid, "check_in": now})
    return AttendanceRecord(id=rec_id, employee_id=eid, check_in=now)


async def clock_out(
    client: OdooClient,
    employee_id: int | None = None,
) -> AttendanceRecord:
    """Clock out — set check_out on the current open attendance."""
    eid = await resolve_employee_id(client, employee_id)
    status = await get_status(client, eid)
    if not status.is_clocked_in or status.last_attendance_id is None:
        raise OdooValidationError("Employee is not clocked in")
    now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")
    await client.write(_MODEL, status.last_attendance_id, {"check_out": now})
    return AttendanceRecord(
        id=status.last_attendance_id,
        employee_id=eid,
        check_in=status.last_check_in or "",
        check_out=now,
    )


async def list_attendances(
    client: OdooClient,
    options: AttendanceListOptions | None = None,
) -> list[AttendanceRecord]:
    """List attendance records with optional filters."""
    opts = options or AttendanceListOptions()
    domain: list[Any] = list(opts.domain)
    if opts.employee_id is not None:
        domain.append(("employee_id", "=", opts.employee_id))

    kwargs: dict[str, Any] = {"fields": ["id", "employee_id", "check_in", "check_out"]}
    if opts.limit is not None:
        kwargs["limit"] = opts.limit
    if opts.offset is not None:
        kwargs["offset"] = opts.offset
    if opts.order is not None:
        kwargs["order"] = opts.order

    records = await client.search_read(_MODEL, domain, **kwargs)
    result: list[AttendanceRecord] = []
    for rec in records:
        emp = rec["employee_id"]
        emp_id = emp[0] if isinstance(emp, list) else int(emp)
        result.append(
            AttendanceRecord(
                id=rec["id"],
                employee_id=emp_id,
                check_in=rec["check_in"],
                check_out=rec.get("check_out") or None,
            )
        )
    return result
