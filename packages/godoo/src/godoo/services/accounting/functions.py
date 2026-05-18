"""Accounting service — standalone async functions."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from godoo.services.accounting.types import (
    CashAccount,
    DaysToPayResult,
    ReconciliationLine,
    ReconciliationTrace,
    ResolvedPartner,
)

if TYPE_CHECKING:
    from godoo.client import OdooClient


# ---------------------------------------------------------------------------
# Many2one helpers
# ---------------------------------------------------------------------------


def _m2o_id(value: Any) -> int | None:
    """Extract the integer ID from a many2one field value.

    Odoo returns many2one as ``[id, name]`` or ``False``.
    """
    if isinstance(value, list) and len(value) >= 1:
        return int(value[0])
    if isinstance(value, int) and value:
        return value
    return None


def _m2o_name(value: Any) -> str:
    """Extract the display name from a many2one field value."""
    if isinstance(value, list) and len(value) >= 2:
        return str(value[1])
    return ""


# ---------------------------------------------------------------------------
# Cash / bank accounts
# ---------------------------------------------------------------------------


async def discover_cash_accounts(client: OdooClient) -> list[CashAccount]:
    """Find all cash/bank journal accounts."""
    journals = await client.search_read(
        "account.journal",
        [("type", "in", ["cash", "bank"])],
        fields=["id", "name", "code", "company_id"],
    )
    return [
        CashAccount(
            id=j["id"],
            name=j["name"],
            code=j["code"],
            company_id=_m2o_id(j["company_id"]) or 0,
        )
        for j in journals
    ]


async def get_cash_account_ids(client: OdooClient) -> list[int]:
    """Return IDs of all cash/bank journals."""
    accounts = await discover_cash_accounts(client)
    return [a.id for a in accounts]


# ---------------------------------------------------------------------------
# Reconciliation tracing
# ---------------------------------------------------------------------------


async def trace_reconciliation(
    client: OdooClient,
    move_line_id: int,
) -> ReconciliationTrace:
    """Trace the full reconciliation for a given move line."""
    lines = await client.read(
        "account.move.line",
        move_line_id,
        fields=["id", "full_reconcile_id"],
    )
    if not lines:
        return ReconciliationTrace(full_reconcile_id=None)
    full_rec = lines[0].get("full_reconcile_id")
    full_rec_id = _m2o_id(full_rec)
    if full_rec_id is None:
        return ReconciliationTrace(full_reconcile_id=None)
    # Fetch all lines with the same full_reconcile_id
    rec_lines = await client.search_read(
        "account.move.line",
        [("full_reconcile_id", "=", full_rec_id)],
        fields=["id", "move_id", "account_id", "debit", "credit", "date", "name"],
    )
    parsed = [
        ReconciliationLine(
            id=r["id"],
            move_id=_m2o_id(r["move_id"]) or 0,
            account_id=_m2o_id(r["account_id"]) or 0,
            debit=float(r.get("debit", 0)),
            credit=float(r.get("credit", 0)),
            date=r.get("date", ""),
            name=r.get("name", ""),
        )
        for r in rec_lines
    ]
    return ReconciliationTrace(full_reconcile_id=full_rec_id, lines=parsed)


# ---------------------------------------------------------------------------
# Partner resolution
# ---------------------------------------------------------------------------


async def resolve_partner_from_move(
    client: OdooClient,
    move_id: int,
) -> ResolvedPartner | None:
    """Resolve the partner from an account.move."""
    moves = await client.read(
        "account.move",
        move_id,
        fields=["partner_id"],
    )
    if not moves:
        return None
    partner_id = _m2o_id(moves[0].get("partner_id"))
    if partner_id is None:
        return None
    partners = await client.read(
        "res.partner",
        partner_id,
        fields=["id", "name", "vat"],
    )
    if not partners:
        return None
    p = partners[0]
    return ResolvedPartner(
        id=p["id"],
        name=p.get("name", ""),
        vat=p.get("vat") or None,
    )


# ---------------------------------------------------------------------------
# Closing-entry detection
# ---------------------------------------------------------------------------


def is_closing_entry_from_lines(lines: list[dict[str, Any]]) -> bool:
    """Detect if a set of move lines looks like a year-end closing entry.

    Heuristic: all lines reference accounts starting with '1' (assets/liabilities)
    and they net to zero.
    """
    if not lines:
        return False
    total = sum(float(ln.get("debit", 0)) - float(ln.get("credit", 0)) for ln in lines)
    if abs(total) > 0.01:
        return False
    # Check if journal is of type 'situation' or name hints
    for line in lines:
        name = line.get("name", "").lower()
        if "closing" in name or "clôture" in name:
            return True
    return False


async def is_closing_entry(
    client: OdooClient,
    move_id: int,
) -> bool:
    """Check whether an account.move is a closing entry."""
    lines = await client.search_read(
        "account.move.line",
        [("move_id", "=", move_id)],
        fields=["id", "debit", "credit", "name", "account_id"],
    )
    return is_closing_entry_from_lines(lines)


# ---------------------------------------------------------------------------
# Days to pay
# ---------------------------------------------------------------------------


async def calculate_days_to_pay(
    client: OdooClient,
    move_id: int,
) -> DaysToPayResult:
    """Calculate days from invoice date to payment date."""
    moves = await client.read(
        "account.move",
        move_id,
        fields=["invoice_date", "invoice_date_due", "payment_state", "state"],
    )
    if not moves:
        return DaysToPayResult(move_id=move_id, invoice_date="", payment_date=None, days_to_pay=None)
    move = moves[0]
    inv_date_str = move.get("invoice_date") or ""
    if not inv_date_str:
        return DaysToPayResult(move_id=move_id, invoice_date="", payment_date=None, days_to_pay=None)

    # Find reconciled payment lines
    move_lines = await client.search_read(
        "account.move.line",
        [("move_id", "=", move_id), ("full_reconcile_id", "!=", False)],
        fields=["full_reconcile_id"],
        limit=1,
    )
    if not move_lines:
        return DaysToPayResult(
            move_id=move_id,
            invoice_date=inv_date_str,
            payment_date=None,
            days_to_pay=None,
        )
    full_rec_id = _m2o_id(move_lines[0]["full_reconcile_id"])
    if full_rec_id is None:
        return DaysToPayResult(
            move_id=move_id,
            invoice_date=inv_date_str,
            payment_date=None,
            days_to_pay=None,
        )
    # Get the payment side lines
    payment_lines = await client.search_read(
        "account.move.line",
        [("full_reconcile_id", "=", full_rec_id), ("move_id", "!=", move_id)],
        fields=["date"],
        order="date desc",
        limit=1,
    )
    if not payment_lines:
        return DaysToPayResult(
            move_id=move_id,
            invoice_date=inv_date_str,
            payment_date=None,
            days_to_pay=None,
        )
    pay_date_str = payment_lines[0]["date"]
    inv_date = datetime.strptime(inv_date_str, "%Y-%m-%d")
    pay_date = datetime.strptime(pay_date_str, "%Y-%m-%d")
    days = (pay_date - inv_date).days
    return DaysToPayResult(
        move_id=move_id,
        invoice_date=inv_date_str,
        payment_date=pay_date_str,
        days_to_pay=max(days, 0),
    )


# ---------------------------------------------------------------------------
# Cash balance & posted move lines
# ---------------------------------------------------------------------------


async def get_cash_balance(
    client: OdooClient,
    journal_id: int,
) -> float:
    """Get the current balance for a cash/bank journal."""
    lines = await client.search_read(
        "account.move.line",
        [
            ("journal_id", "=", journal_id),
            ("parent_state", "=", "posted"),
        ],
        fields=["debit", "credit"],
    )
    return sum(float(ln.get("debit", 0)) - float(ln.get("credit", 0)) for ln in lines)


async def get_posted_move_lines(
    client: OdooClient,
    domain: list[Any] | None = None,
    *,
    limit: int | None = None,
    order: str | None = None,
) -> list[dict[str, Any]]:
    """Fetch posted journal items with an extra filter."""
    base_domain: list[Any] = [("parent_state", "=", "posted")]
    if domain:
        base_domain.extend(domain)
    kwargs: dict[str, Any] = {
        "fields": ["id", "move_id", "account_id", "debit", "credit", "date", "name", "partner_id"],
    }
    if limit is not None:
        kwargs["limit"] = limit
    if order is not None:
        kwargs["order"] = order
    return await client.search_read("account.move.line", base_domain, **kwargs)
