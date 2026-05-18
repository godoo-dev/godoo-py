# Accounting Service

Access via `client.accounting`.  Provides utilities for working with
`account.move`, `account.move.line`, and journal entries.

## Cash account discovery

### discover_cash_accounts

Finds cash and bank accounts by looking at journals with type `bank` or `cash`,
**not** by account code prefix.  This is more reliable across localisations:

```python
accounts = await client.accounting.discover_cash_accounts()
for a in accounts:
    print(a.name, a.code)
```

Returns a list of `CashAccount` dataclasses with `id`, `name`, `code`, and
`company_id`.

### get_cash_account_ids

Convenience wrapper that returns just the account IDs:

```python
ids = await client.accounting.get_cash_account_ids()
```

## Reconciliation

### trace_reconciliation

Follow the `full_reconcile_id` link across move lines to trace how a payment
was reconciled with invoices:

```python
trace = await client.accounting.trace_reconciliation(move_line_id=1042)
print(f"Reconcile group: {trace.full_reconcile_id}")
for line in trace.lines:
    print(f"  Move {line.move_id}: debit={line.debit} credit={line.credit}")
```

### resolve_partner_from_move

Find the partner on a bank statement entry.  The resolution order is:

1. Check the cash/bank line itself for a `partner_id`
2. Check counterpart lines in the reconciliation
3. Detect batch payments and resolve from there

```python
partner = await client.accounting.resolve_partner_from_move(move_id=500)
if partner:
    print(partner.name, partner.vat)
```

## Closing entries

### is_closing_entry

Detect year-end closing entries by checking for accounts in the 129x range:

```python
if await client.accounting.is_closing_entry(move_id=999):
    print("This is a closing entry, skip it")
```

## Days to pay

### calculate_days_to_pay

Calculate the number of days between invoice date and payment date by tracing
the reconciliation chain:

```python
result = await client.accounting.calculate_days_to_pay(move_id=450)
if result.days_to_pay is not None:
    print(f"Paid in {result.days_to_pay} days")
else:
    print("Not yet paid")
```

Returns a `DaysToPayResult` with `move_id`, `invoice_date`, `payment_date`,
and `days_to_pay`.

## Cash balance

### get_cash_balance

Sum posted balances for a journal up to the current date:

```python
balance = await client.accounting.get_cash_balance(journal_id=7)
print(f"Cash balance: {balance:.2f}")
```

## Move lines

### get_posted_move_lines

Convenience wrapper that adds `parent_state=posted` to any domain you provide:

```python
lines = await client.accounting.get_posted_move_lines(
    [("account_id", "=", 42)],
    limit=100,
    order="date desc",
)
```
