import warnings
from datetime import date
from decimal import Decimal

warnings.filterwarnings("ignore")
import piecash  # noqa: E402

from ledgerforge.report import accounts_html  # noqa: E402


def _tiny_book(path):
    book = piecash.create_book(sqlite_file=str(path), currency="GBP", overwrite=True)
    gbp = book.default_currency
    root = book.root_account
    assets = piecash.Account(name="Assets", type="ASSET", commodity=gbp, parent=root, placeholder=True)
    bank = piecash.Account(name="Bank", type="BANK", commodity=gbp, parent=assets)
    opening = piecash.Account(name="Opening Balances", type="EQUITY", commodity=gbp, parent=root)
    book.save()
    piecash.Transaction(
        currency=gbp, post_date=date(2026, 1, 1), description="open",
        splits=[piecash.Split(account=bank, value=Decimal("1000")),
                piecash.Split(account=opening, value=Decimal("-1000"))])
    book.save()
    book.close()


def test_accounts_html_renders_balances(tmp_path):
    p = tmp_path / "b.gnucash"
    _tiny_book(p)
    html = accounts_html(p, title="Test Ledger", built=" · x")
    assert "<title>Test Ledger</title>" in html
    assert "£1,000.00" in html          # net-worth card + the Bank leaf
    assert "Bank" in html
    assert "as at 01 Jan 2026" in html  # date pulled from the posted transaction
