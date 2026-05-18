"""TimesheetsService — class wrapper."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from godoo.services.timesheets.functions import (
    get_running_timers,
    list_timesheets,
    log_time,
    start_timer,
    stop_timer,
)

if TYPE_CHECKING:
    from godoo.client import OdooClient
    from godoo.services.timesheets.types import (
        LogTimeOptions,
        TimerStartOptions,
        TimesheetListOptions,
    )


class TimesheetsService:
    """High-level timesheet service for Odoo."""

    def __init__(self, client: OdooClient) -> None:
        self._client = client

    async def start_timer(
        self,
        options: TimerStartOptions,
        employee_id: int | None = None,
    ) -> dict[str, Any]:
        return await start_timer(self._client, options, employee_id)

    async def stop_timer(self, timesheet_id: int) -> dict[str, Any]:
        return await stop_timer(self._client, timesheet_id)

    async def get_running_timers(self, employee_id: int | None = None) -> list[dict[str, Any]]:
        return await get_running_timers(self._client, employee_id)

    async def log_time(
        self,
        options: LogTimeOptions,
        employee_id: int | None = None,
    ) -> dict[str, Any]:
        return await log_time(self._client, options, employee_id)

    async def list_timesheets(self, options: TimesheetListOptions | None = None) -> list[dict[str, Any]]:
        return await list_timesheets(self._client, options)
