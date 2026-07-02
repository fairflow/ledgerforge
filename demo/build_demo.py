"""Build the ledgerforge demo: fictional statements -> categorised GnuCash book -> accounts page.

End to end with entirely fictional data, exercising the real engine:
  parse (ledgerforge.parsers) -> categorise (ledgerforge.rules) -> build a piecash book ->
  render a balance-sheet page (ledgerforge.report).

Run:  python demo/build_demo.py
Outputs:  demo/build/demo.gnucash  and  demo/site/index.html  (both git-ignored, regenerated).
"""
from __future__ import annotations

import json
import warnings
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

warnings.filterwarnings("ignore")
import piecash  # noqa: E402

from ledgerforge.parsers import parse_ofx  # noqa: E402
from ledgerforge.report import accounts_html  # noqa: E402
from ledgerforge.rules import categorise  # noqa: E402

HERE = Path(__file__).parent
DATA = HERE / "data"
BUILD = HERE / "build"
SITE = HERE / "site"
BOOK = BUILD / "demo.gnucash"

CHART = [  # (full account name, GnuCash type, placeholder?)
    ("Assets", "ASSET", True),
    ("Assets:Bank", "ASSET", True),
    ("Assets:Bank:Current", "BANK", False),
    ("Assets:Bank:Savings", "BANK", False),
    ("Assets:Cash", "CASH", False),
    ("Income", "INCOME", True),
    ("Income:Salary", "INCOME", False),
    ("Income:Interest", "INCOME", False),
    ("Expenses", "EXPENSE", True),
    ("Expenses:Groceries", "EXPENSE", False),
    ("Expenses:Dining", "EXPENSE", False),
    ("Expenses:Utilities", "EXPENSE", False),
    ("Expenses:Transport", "EXPENSE", False),
    ("Equity", "EQUITY", True),
    ("Equity:Opening Balances", "EQUITY", False),
    ("Unspecified", "EXPENSE", False),
]

STATEMENTS = [
    ("Assets:Bank:Current", DATA / "statements/current.ofx"),
    ("Assets:Bank:Savings", DATA / "statements/savings.ofx"),
]
CASH_OPENING = Decimal("150.00")


def build() -> None:
    BUILD.mkdir(exist_ok=True)
    if BOOK.exists():
        BOOK.unlink()
    rules = json.loads((DATA / "rules.json").read_text())["rules"]
    book = piecash.create_book(sqlite_file=str(BOOK), currency="GBP", overwrite=True)
    gbp = book.default_currency

    by = {"": book.root_account}
    for full, typ, ph in CHART:
        parent = by[full.rsplit(":", 1)[0]] if ":" in full else book.root_account
        by[full] = piecash.Account(name=full.split(":")[-1], type=typ, commodity=gbp,
                                   parent=parent, placeholder=ph)
    book.save()
    equity, unspec = by["Equity:Opening Balances"], by["Unspecified"]

    def tx(d, desc, pairs):
        piecash.Transaction(currency=gbp, post_date=d, description=desc,
                            splits=[piecash.Split(account=a, value=v) for a, v in pairs])

    matched = 0
    for full, ofx in STATEMENTS:
        target = by[full]
        txns, opening = parse_ofx(ofx.read_text())
        tx(date(2026, 1, 1), f"Opening balance — {full}", [(target, opening), (equity, -opening)])
        for t in txns:
            acct = categorise(t["desc"], rules)
            contra = by.get(acct, unspec)
            if acct and acct in by:
                matched += 1
            tx(t["date"], t["desc"], [(target, t["amount"]), (contra, -t["amount"])])
    tx(date(2026, 1, 1), "Opening balance — Assets:Cash",
       [(by["Assets:Cash"], CASH_OPENING), (equity, -CASH_OPENING)])

    book.save()
    book.close()
    print(f"Built {BOOK}  ({matched} transactions categorised by rules)")


def render() -> None:
    SITE.mkdir(exist_ok=True)
    built = f" &middot; built {datetime.now():%d %b %Y}"
    html = accounts_html(BOOK, title="ledgerforge demo — a fictional household", built=built)
    out = SITE / "index.html"
    out.write_text(html, encoding="utf-8")
    print(f"Wrote {out}  ({len(html):,} bytes)")


if __name__ == "__main__":
    build()
    render()
