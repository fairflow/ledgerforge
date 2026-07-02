"""Date/currency-scoped account overrides that BEAT the payee rules (e.g. a holiday window).

Each override is a dict with `_from`/`_to` (date objects), an `account`, and optional `currency`
and `debits_only` filters. The consumer prepares the date objects when it loads its config.
"""
from __future__ import annotations

from decimal import Decimal


def override_account(txn: dict, currency: str, overrides) -> str | None:
    """Return the overriding account for this txn, or None. Callers must check is_transfer() first;
    transfers are never overridden."""
    d = txn.get("date")
    if d is None:
        return None
    amt = txn.get("amount", Decimal(0))
    for o in overrides:
        if o.get("currency") and currency != o["currency"]:
            continue
        if o.get("debits_only") and amt >= 0:
            continue
        if o["_from"] <= d <= o["_to"]:
            return o["account"]
    return None
