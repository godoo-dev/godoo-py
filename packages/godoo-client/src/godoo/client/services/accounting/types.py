from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class CashAccount:
    """A cash/bank journal account."""

    id: int
    name: str
    code: str
    company_id: int


@dataclass
class ReconciliationLine:
    """A single line participating in a reconciliation."""

    id: int
    move_id: int
    account_id: int
    debit: float
    credit: float
    date: str
    name: str = ""


@dataclass
class ReconciliationTrace:
    """Full reconciliation trace for a payment/invoice."""

    full_reconcile_id: int | None
    lines: list[ReconciliationLine] = field(default_factory=list)


@dataclass
class ResolvedPartner:
    """Partner resolved from an account.move."""

    id: int
    name: str
    vat: str | None = None


@dataclass
class DaysToPayResult:
    """Result of days-to-pay calculation."""

    move_id: int
    invoice_date: str
    payment_date: str | None
    days_to_pay: int | None
