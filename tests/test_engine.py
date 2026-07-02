from datetime import date
from decimal import Decimal

from ledgerforge import overrides, parsers, rules, transfers


def test_parse_ofx_basic():
    ofx = ("<STMTTRN><TRNTYPE>DEBIT<DTPOSTED>20260115<TRNAMT>-12.50"
           "<NAME>TESCO STORES<MEMO>TOTNES<FITID>1</STMTTRN>"
           "<LEDGERBAL><BALAMT>100.00</LEDGERBAL>")
    txns, opening = parsers.parse_ofx(ofx)
    assert len(txns) == 1
    assert txns[0]["amount"] == Decimal("-12.50")
    assert txns[0]["date"] == date(2026, 1, 15)
    assert "TESCO" in txns[0]["desc"]
    assert opening == Decimal("112.50")  # ledger 100 minus net -12.50


def test_categorise_most_specific():
    rs = [
        {"account": "Expenses:Groceries", "match": ["MORRISON"]},
        {"account": "Expenses:Auto:Fuel", "match": ["MORRISONS PETROL"]},
    ]
    assert rules.categorise("MORRISONS PETROL TOTNES", rs) == "Expenses:Auto:Fuel"
    assert rules.categorise("WM MORRISON STORE", rs) == "Expenses:Groceries"
    assert rules.categorise("UNKNOWN PAYEE", rs) is None


def test_categorise_amp_decode():
    rs = [{"account": "Expenses:DIY", "match": ["B & Q"]}]
    assert rules.categorise("B &AMP; Q TOTNES", rs) == "Expenses:DIY"


def test_is_transfer():
    m = ["JANE DOE", "12345678"]
    assert transfers.is_transfer("PAYMENT TO JANE DOE", m)
    assert transfers.is_transfer("REF 12345678 XFER", m)
    assert not transfers.is_transfer("TESCO STORES", m)


def test_load_account_markers_missing_dirs_ok():
    assert transfers.load_account_markers(["/no/such/dir", ""]) == []


def test_override_window():
    ov = [{"_from": date(2026, 1, 1), "_to": date(2026, 1, 31),
           "account": "Expenses:Holiday", "currency": "EUR"}]
    hit = {"date": date(2026, 1, 15), "amount": Decimal("-5")}
    assert overrides.override_account(hit, "EUR", ov) == "Expenses:Holiday"
    assert overrides.override_account({"date": date(2026, 2, 1), "amount": Decimal("-5")}, "EUR", ov) is None
    assert overrides.override_account(hit, "GBP", ov) is None  # currency filter
