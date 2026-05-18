from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class TimerStartOptions:
    """Options for starting a timesheet timer."""

    project_id: int
    task_id: int | None = None
    description: str = ""


@dataclass
class LogTimeOptions:
    """Options for logging a completed timesheet entry."""

    project_id: int
    hours: float
    task_id: int | None = None
    description: str = ""
    date: str | None = None  # YYYY-MM-DD, defaults to today


@dataclass
class TimesheetListOptions:
    """Filtering options for listing timesheets."""

    employee_id: int | None = None
    project_id: int | None = None
    limit: int | None = None
    offset: int | None = None
    order: str | None = None
    domain: list[Any] = field(default_factory=list)
