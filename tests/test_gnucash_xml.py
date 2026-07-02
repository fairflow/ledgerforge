import gzip
from datetime import date
from decimal import Decimal

from ledgerforge.gnucash_xml import GnuCashBook, _parse_fraction

SAMPLE_XML = """<?xml version="1.0" encoding="utf-8"?>
<gnc-v2
  xmlns:gnc="http://www.gnucash.org/XML/gnc"
  xmlns:act="http://www.gnucash.org/XML/act"
  xmlns:trn="http://www.gnucash.org/XML/trn"
  xmlns:split="http://www.gnucash.org/XML/split"
  xmlns:ts="http://www.gnucash.org/XML/ts">
  <gnc:book version="2.0.0">
    <gnc:account version="2.0.0">
      <act:name>Root Account</act:name>
      <act:id type="guid">rootguid</act:id>
      <act:type>ROOT</act:type>
    </gnc:account>
    <gnc:account version="2.0.0">
      <act:name>Bank</act:name>
      <act:id type="guid">bankguid</act:id>
      <act:type>BANK</act:type>
      <act:parent type="guid">rootguid</act:parent>
    </gnc:account>
    <gnc:account version="2.0.0">
      <act:name>Sales</act:name>
      <act:id type="guid">salesguid</act:id>
      <act:type>INCOME</act:type>
      <act:parent type="guid">rootguid</act:parent>
    </gnc:account>
    <gnc:transaction version="2.0.0">
      <trn:description>Test sale</trn:description>
      <trn:date-posted><ts:date>2025-01-15 00:00:00 +0000</ts:date></trn:date-posted>
      <trn:splits>
        <trn:split>
          <split:value>10000/100</split:value>
          <split:account type="guid">bankguid</split:account>
        </trn:split>
        <trn:split>
          <split:value>-10000/100</split:value>
          <split:account type="guid">salesguid</split:account>
        </trn:split>
      </trn:splits>
    </gnc:transaction>
  </gnc:book>
</gnc-v2>
"""


def test_parse_fraction():
    assert _parse_fraction("27090/100") == Decimal("270.90")
    assert _parse_fraction("150") == Decimal("150")
    assert _parse_fraction("-15000/100") == Decimal("-150.00")
    assert _parse_fraction("1/100") == Decimal("0.01")


def _write_plain(tmp_path):
    p = tmp_path / "book.gnucash"
    p.write_text(SAMPLE_XML, encoding="utf-8")
    return p


def test_open_plain_xml(tmp_path):
    book = GnuCashBook.open(_write_plain(tmp_path))
    assert len(book.accounts) == 3
    bank = book.account_by_fullname("Bank")
    assert bank is not None and bank.is_asset()
    sales = book.account_by_fullname("Sales")
    assert sales is not None and sales.is_income()
    assert len(book.transactions) == 1
    txn = book.transactions[0]
    assert txn.txn_date == date(2025, 1, 15)
    assert sum(s.amount for s in txn.splits) == Decimal("0")  # double-entry balances


def test_open_gzip_xml(tmp_path):
    p = tmp_path / "book.gnucash"
    with gzip.open(p, "wb") as fh:
        fh.write(SAMPLE_XML.encode("utf-8"))
    book = GnuCashBook.open(p)
    assert len(book.accounts) == 3
    assert len(book.transactions) == 1


def test_fullname_omits_root(tmp_path):
    book = GnuCashBook.open(_write_plain(tmp_path))
    assert book.account_by_fullname("Root Account:Bank") is None  # root prefix stripped
    assert book.account_by_fullname("Bank") is not None


def test_splits_in_period(tmp_path):
    book = GnuCashBook.open(_write_plain(tmp_path))
    inside = list(book.splits_in_period(date(2025, 1, 1), date(2025, 1, 31)))
    assert len(inside) == 2
    outside = list(book.splits_in_period(date(2025, 2, 1), date(2025, 2, 28)))
    assert outside == []
    excluded = list(book.splits_in_period(date(2025, 1, 1), date(2025, 1, 31),
                                          exclude_desc_keywords=["test sale"]))
    assert excluded == []


def test_account_balance(tmp_path):
    book = GnuCashBook.open(_write_plain(tmp_path))
    assert book.account_balance("Bank", date(2025, 1, 31)) == Decimal("100.00")
    assert book.account_balance("Bank", date(2024, 12, 31)) == Decimal("0")  # before the txn
