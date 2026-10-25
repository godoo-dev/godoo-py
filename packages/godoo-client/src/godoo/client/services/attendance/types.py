from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AttendanceRecord:
    """A single hr.attendance record."""

    id: int
    employee_id: int
    check_in: str
    check_out: str | None = None


@dataclass
class AttendanceListOptions:
    """Filtering options for listing attendance records."""

    employee_id: int | None = None
    limit: int | None = None
    offset: int | None = None
    order: str | None = None
    domain: list[Any] = field(default_factory=list)


@dataclass
class AttendanceStatus:
    """Current clock-in/out status for an employee."""

    employee_id: int
    is_clocked_in: bool
    last_attendance_id: int | None = None
    last_check_in: str | None = None
