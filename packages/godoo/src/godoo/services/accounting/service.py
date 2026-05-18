"""AccountingService — class wrapper."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from godoo.services.accounting.functions import (
    calculate_days_to_pay,
    discover_cash_accounts,
    get_cash_account_ids,
    get_cash_balance,
    get_posted_move_lines,
    is_closing_entry,
    resolve_partner_from_move,
    trace_reconciliation,
)

if TYPE_CHECKING:
    from godoo.client import OdooClient
    from godoo.services.accounting.types import (
        CashAccount,
        DaysToPayResult,
        ReconciliationTrace,
        ResolvedPartner,
    )


class AccountingService:
    """High-level accounting service for Odoo."""

    def __init__(self, client: OdooClient) -> None:
        self._client = client

    async def discover_cash_accounts(self) -> list[CashAccount]:
        return await discover_cash_accounts(self._client)

    async def get_cash_account_ids(self) -> list[int]:
        return await get_cash_account_ids(self._client)

    async def trace_reconciliation(self, move_line_id: int) -> ReconciliationTrace:
        return await trace_reconciliation(self._client, move_line_id)

    async def resolve_partner_from_move(self, move_id: int) -> ResolvedPartner | None:
        return await resolve_partner_from_move(self._client, move_id)

    async def is_closing_entry(self, move_id: int) -> bool:
        return await is_closing_entry(self._client, move_id)

    async def calculate_days_to_pay(self, move_id: int) -> DaysToPayResult:
        return await calculate_days_to_pay(self._client, move_id)

    async def get_cash_balance(self, journal_id: int) -> float:
        return await get_cash_balance(self._client, journal_id)

    async def get_posted_move_lines(
        self,
        domain: list[Any] | None = None,
        *,
        limit: int | None = None,
        order: str | None = None,
    ) -> list[dict[str, Any]]:
        return await get_posted_move_lines(self._client, domain, limit=limit, order=order)
