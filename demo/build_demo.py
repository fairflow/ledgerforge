"""Build the ledgerforge demo: fictional statements -> categorised GnuCash book -> the full toolkit.

End to end with entirely fictional data, exercising the real engine:
  parse (ledgerforge.parsers) -> categorise (ledgerforge.rules) -> build a piecash book
  (multi-currency, credit card, FX prices via ledgerforge.book) -> generate the four toolkit
  pages (home, accounts & balances, rules editor, unspecified assigner) into demo/site/.

Run:  python demo/build_demo.py
Then serve demo/site/ — e.g. `ddev start` here, or:
  python -c "from ledgerforge.serve import run; run('demo/site', 'demo/pending')"
"""
from __future__ import annotations

import json
import warnings
from datetime import date
from decimal import Decimal
from pathlib import Path

warnings.filterwarnings("ignore")
import piecash  # noqa: E402

from ledgerforge.book import set_fx_prices  # noqa: E402
from ledgerforge.parsers import parse_ofx  # noqa: E402
from ledgerforge.rules import categorise  # noqa: E402

HERE = Path(__file__).parent
DATA = HERE / "data"
BUILD = HERE / "build"
SITE = HERE / "site"
BOOK = BUILD / "demo.gnucash"

FX_TO_GBP = {"EUR": "0.855"}

CHART = [  # (full account name, GnuCash type, placeholder?, code, currency)
    ("Assets", "ASSET", True, "1000", "GBP"),
    ("Assets:Bank", "ASSET", True, "1100", "GBP"),
    ("Assets:Bank:Current", "BANK", False, "1110", "GBP"),
    ("Assets:Bank:Savings", "BANK", False, "1120", "GBP"),
    ("Assets:Bank:Euro Account", "BANK", False, "1130", "EUR"),
    ("Assets:Cash", "CASH", False, "1200", "GBP"),
    ("Liabilities", "LIABILITY", True, "2000", "GBP"),
    ("Liabilities:Credit Card", "CREDIT", False, "2100", "GBP"),
    ("Equity", "EQUITY", True, "3000", "GBP"),
    ("Equity:Opening Balances", "EQUITY", False, "3100", "GBP"),
    ("Equity:Opening Balances EUR", "EQUITY", False, "3110", "EUR"),
    ("Income", "INCOME", True, "4000", "GBP"),
    ("Income:Salary", "INCOME", False, "4100", "GBP"),
    ("Income:Interest", "INCOME", False, "4200", "GBP"),
    ("Expenses", "EXPENSE", True, "5000", "GBP"),
    ("Expenses:Groceries", "EXPENSE", False, "5100", "GBP"),
    ("Expenses:Dining", "EXPENSE", False, "5200", "GBP"),
    ("Expenses:Utilities", "EXPENSE", False, "5300", "GBP"),
    ("Expenses:Transport", "EXPENSE", False, "5400", "GBP"),
    ("Expenses:Holiday EUR", "EXPENSE", False, "5500", "EUR"),
    ("Expenses:Unspecified", "EXPENSE", False, "5900", "GBP"),
]

# (target account, statement file, all-spend contra override or None -> categorise by rules)
STATEMENTS = [
    ("Assets:Bank:Current", DATA / "statements/current.ofx", None),
    ("Assets:Bank:Savings", DATA / "statements/savings.ofx", None),
    ("Liabilities:Credit Card", DATA / "statements/card.ofx", None),
    # single-currency posting: EUR spend goes to the EUR expense account, per-currency reporting
    ("Assets:Bank:Euro Account", DATA / "statements/euro.ofx", "Expenses:Holiday EUR"),
]
CASH_OPENING = Decimal("150.00")


def build() -> None:
    BUILD.mkdir(exist_ok=True)
    if BOOK.exists():
        BOOK.unlink()
    rules = json.loads((DATA / "rules.json").read_text())["rules"]
    book = piecash.create_book(sqlite_file=str(BOOK), currency="GBP", overwrite=True)
    gbp = book.default_currency
    eur = book.currencies(mnemonic="EUR")
    ccy = {"GBP": gbp, "EUR": eur}

    by = {}
    for full, typ, ph, code, cur in CHART:
        parent = by[full.rsplit(":", 1)[0]] if ":" in full else book.root_account
        by[full] = piecash.Account(name=full.split(":")[-1], type=typ, commodity=ccy[cur],
                                   parent=parent, placeholder=ph, code=code)
    book.save()
    unspec = by["Expenses:Unspecified"]

    def tx(d, desc, pairs, cur="GBP"):
        piecash.Transaction(currency=ccy[cur], post_date=d, description=desc,
                            splits=[piecash.Split(account=a, value=v) for a, v in pairs])

    matched = unmatched = 0
    for full, ofx, override in STATEMENTS:
        target = by[full]
        cur = target.commodity.mnemonic
        equity = by["Equity:Opening Balances" + (" EUR" if cur == "EUR" else "")]
        txns, opening = parse_ofx(ofx.read_text())
        tx(date(2026, 1, 1), f"Opening balance — {full}", [(target, opening), (equity, -opening)], cur)
        for t in txns:
            if override:
                contra = by[override]
                matched += 1
            else:
                acct = categorise(t["desc"], rules)
                contra = by.get(acct, unspec)
                if acct and acct in by:
                    matched += 1
                else:
                    unmatched += 1
            tx(t["date"], t["desc"], [(target, t["amount"]), (contra, -t["amount"])], cur)
    tx(date(2026, 1, 1), "Opening balance — Assets:Cash",
       [(by["Assets:Cash"], CASH_OPENING), (by["Equity:Opening Balances"], -CASH_OPENING)])

    book.save()
    set_fx_prices(book, FX_TO_GBP, base="GBP", on=date(2026, 1, 31))
    book.save()
    book.close()
    print(f"Built {BOOK}  ({matched} categorised, {unmatched} -> Unspecified)")


def render() -> None:
    SITE.mkdir(exist_ok=True)
    (SITE / ".htaccess").write_text("DirectoryIndex index.html\nOptions +Indexes\n", encoding="utf-8")
    import make_accounts
    import make_editor
    import make_home
    import make_unspec
    make_accounts.main()
    make_editor.main()
    make_unspec.main()
    make_home.main()  # last: it links only the pages that exist


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(HERE))
    build()
    render()
