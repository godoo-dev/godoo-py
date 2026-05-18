"""AttendanceService — class wrapper."""

from __future__ import annotations

from typing import TYPE_CHECKING

from godoo.services.attendance.functions import (
    clock_in,
    clock_out,
    get_status,
    list_attendances,
    resolve_employee_id,
)

if TYPE_CHECKING:
    from godoo.client import OdooClient
    from godoo.services.attendance.types import (
        AttendanceListOptions,
        AttendanceRecord,
        AttendanceStatus,
    )


class AttendanceService:
    """High-level attendance service for Odoo HR."""

    def __init__(self, client: OdooClient) -> None:
        self._client = client

    async def resolve_employee_id(self, employee_id: int | None = None) -> int:
        return await resolve_employee_id(self._client, employee_id)

    async def clock_in(self, employee_id: int | None = None) -> AttendanceRecord:
        return await clock_in(self._client, employee_id)

    async def clock_out(self, employee_id: int | None = None) -> AttendanceRecord:
        return await clock_out(self._client, employee_id)

    async def get_status(self, employee_id: int | None = None) -> AttendanceStatus:
        return await get_status(self._client, employee_id)

    async def list_attendances(self, options: AttendanceListOptions | None = None) -> list[AttendanceRecord]:
        return await list_attendances(self._client, options)
