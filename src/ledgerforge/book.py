"""Generic GnuCash (piecash) helpers shared by every consumer: read balances, set FX prices.

Deliberately small. The book-building logic that knows an entity's chart, contra routing, and
opening balances lives in that entity's consumer, not here.
"""
from __future__ import annotations

from datetime import date as _date
from decimal import Decimal

import piecash


def read_balances(book_path) -> dict:
    """{fullname: (type, commodity_mnemonic, balance)} for every account, read-only."""
    b = piecash.open_book(str(book_path), readonly=True, open_if_lock=True)
    try:
        return {a.fullname: (a.type, a.commodity.mnemonic, a.get_balance()) for a in b.accounts}
    finally:
        b.close()


def set_fx_prices(book, fx_to_base: dict, base: str = "GBP", on=None):
    """Record a fixed price per foreign currency against the base, so a reader can translate.
    `fx_to_base` maps a currency mnemonic to a rate (anything Decimal() accepts). Unknown
    currencies are skipped. piecash requires a `date` (not datetime)."""
    on = on or _date.today()
    base_ccy = book.currencies(mnemonic=base)
    for sym, rate in fx_to_base.items():
        try:
            com = book.currencies(mnemonic=sym)
        except Exception:
            continue
        piecash.Price(commodity=com, currency=base_ccy, date=on,
                      value=Decimal(str(rate)), source="user:fixed")
