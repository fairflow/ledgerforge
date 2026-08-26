"""Convert the piecash (SQLite) demo book to a GnuCash **XML** book.

GnuCash stores books as either SQLite or XML (a File → Save-As option). piecash only writes
SQLite; this emits the equivalent uncompressed XML so the demo book can live in git as diffable
text and be opened/tested by anyone who clones the repo. GUIDs are derived deterministically from
content, so regenerating an unchanged book produces byte-identical XML (clean diffs).

Output validates by round-tripping through the engine's own GnuCash-XML reader
(`ledgerforge.gnucash_xml`), which parses real GnuCash XML books.

Run (needs the ledger venv):
  python demo/web/scripts/book_to_xml.py
"""
from __future__ import annotations

import hashlib
import warnings
from decimal import Decimal
from pathlib import Path
from xml.sax.saxutils import escape

warnings.filterwarnings("ignore")
import piecash  # noqa: E402

from ledgerforge.gnucash_xml import GnuCashBook  # noqa: E402

DEMO = Path(__file__).resolve().parents[2]           # …/ledgerforge/demo
SQLITE_BOOK = DEMO / "build" / "demo.gnucash"
XML_OUT = DEMO / "web" / "static" / "demo.gnucash"

NS = [
    ("gnc", "http://www.gnucash.org/XML/gnc"),
    ("act", "http://www.gnucash.org/XML/act"),
    ("book", "http://www.gnucash.org/XML/book"),
    ("cd", "http://www.gnucash.org/XML/cd"),
    ("cmdty", "http://www.gnucash.org/XML/cmdty"),
    ("price", "http://www.gnucash.org/XML/price"),
    ("slot", "http://www.gnucash.org/XML/slot"),
    ("split", "http://www.gnucash.org/XML/split"),
    ("trn", "http://www.gnucash.org/XML/trn"),
    ("ts", "http://www.gnucash.org/XML/ts"),
]


def guid(*parts: str) -> str:
    return hashlib.md5("::".join(parts).encode()).hexdigest()


def frac(amount: Decimal) -> str:
    return f"{int((amount * 100).to_integral_value())}/100"


def ts(d) -> str:
    return f"{d.isoformat()} 00:00:00 +0000"


def commodity_block(mnemonic: str, indent: str) -> str:
    return (f"{indent}<cmdty:space>CURRENCY</cmdty:space>\n"
            f"{indent}<cmdty:id>{escape(mnemonic)}</cmdty:id>")


def main() -> int:
    book = piecash.open_book(str(SQLITE_BOOK), readonly=True, open_if_lock=True)

    ROOT = guid("root-account")
    accts = [a for a in sorted(book.accounts, key=lambda x: x.fullname) if a.type != "ROOT"]
    aguid = {a.fullname: guid("acct", a.fullname) for a in accts}
    currencies = sorted({a.commodity.mnemonic for a in accts} | {book.default_currency.mnemonic})

    def parent_guid(a) -> str:
        return ROOT if (a.parent is None or a.parent.type == "ROOT") else aguid[a.parent.fullname]

    # deterministic transaction order: date, description, then the split signature
    def txn_key(t):
        sig = sorted((s.account.fullname, str(s.value)) for s in t.splits)
        return (t.post_date.isoformat(), t.description or "", tuple(sig))

    txns = sorted(book.transactions, key=txn_key)
    default_ccy = book.default_currency.mnemonic
    prices = list(book.prices)

    out = ['<?xml version="1.0" encoding="utf-8"?>']
    out.append("<gnc-v2\n     " + "\n     ".join(f'xmlns:{p}="{u}"' for p, u in NS) + ">")
    out.append('<gnc:count-data cd:type="book">1</gnc:count-data>')
    out.append('<gnc:book version="2.0.0">')
    out.append(f'  <book:id type="guid">{guid("demo-book")}</book:id>')
    out.append(f'  <gnc:count-data cd:type="commodity">{len(currencies)}</gnc:count-data>')
    out.append(f'  <gnc:count-data cd:type="account">{len(accts) + 1}</gnc:count-data>')
    out.append(f'  <gnc:count-data cd:type="transaction">{len(txns)}</gnc:count-data>')

    # commodities
    for cur in currencies:
        out.append('  <gnc:commodity version="2.0.0">')
        out.append(commodity_block(cur, "    "))
        out.append("    <cmdty:get_quotes/>")
        out.append("    <cmdty:quote_source>currency</cmdty:quote_source>")
        out.append("    <cmdty:quote_tz/>")
        out.append("  </gnc:commodity>")

    # root account
    out.append('  <gnc:account version="2.0.0">')
    out.append("    <act:name>Root Account</act:name>")
    out.append(f'    <act:id type="guid">{ROOT}</act:id>')
    out.append("    <act:type>ROOT</act:type>")
    out.append("    <act:commodity>")
    out.append(commodity_block(default_ccy, "      "))
    out.append("    </act:commodity>")
    out.append("    <act:commodity-scu>100</act:commodity-scu>")
    out.append("  </gnc:account>")

    # accounts
    for a in accts:
        out.append('  <gnc:account version="2.0.0">')
        out.append(f"    <act:name>{escape(a.name)}</act:name>")
        out.append(f'    <act:id type="guid">{aguid[a.fullname]}</act:id>')
        out.append(f"    <act:type>{a.type}</act:type>")
        out.append("    <act:commodity>")
        out.append(commodity_block(a.commodity.mnemonic, "      "))
        out.append("    </act:commodity>")
        out.append("    <act:commodity-scu>100</act:commodity-scu>")
        if a.code:
            out.append(f"    <act:code>{escape(a.code)}</act:code>")
        if a.placeholder:
            out.append("    <act:slots>")
            out.append("      <slot>")
            out.append("        <slot:key>placeholder</slot:key>")
            out.append('        <slot:value type="string">true</slot:value>')
            out.append("      </slot>")
            out.append("    </act:slots>")
        out.append(f'    <act:parent type="guid">{parent_guid(a)}</act:parent>')
        out.append("  </gnc:account>")

    # transactions
    for i, t in enumerate(txns):
        tg = guid("txn", str(i), t.post_date.isoformat(), t.description or "")
        out.append('  <gnc:transaction version="2.0.0">')
        out.append(f'    <trn:id type="guid">{tg}</trn:id>')
        out.append("    <trn:currency>")
        out.append(commodity_block(t.currency.mnemonic, "      "))
        out.append("    </trn:currency>")
        out.append(f"    <trn:date-posted><ts:date>{ts(t.post_date)}</ts:date></trn:date-posted>")
        out.append(f"    <trn:date-entered><ts:date>{ts(t.post_date)}</ts:date></trn:date-entered>")
        out.append(f"    <trn:description>{escape(t.description or '')}</trn:description>")
        out.append("    <trn:splits>")
        for j, s in enumerate(t.splits):
            out.append("      <trn:split>")
            out.append(f'        <split:id type="guid">{guid("split", tg, str(j))}</split:id>')
            out.append("        <split:reconciled-state>n</split:reconciled-state>")
            out.append(f"        <split:value>{frac(s.value)}</split:value>")
            out.append(f"        <split:quantity>{frac(s.quantity)}</split:quantity>")
            out.append(f'        <split:account type="guid">{aguid[s.account.fullname]}</split:account>')
            out.append("      </trn:split>")
        out.append("    </trn:splits>")
        out.append("  </gnc:transaction>")

    # price database (FX)
    if prices:
        out.append('  <gnc:pricedb version="1">')
        for k, p in enumerate(prices):
            pg = guid("price", str(k), p.commodity.mnemonic, p.currency.mnemonic)
            out.append("    <price>")
            out.append(f'      <price:id type="guid">{pg}</price:id>')
            out.append("      <price:commodity>")
            out.append(commodity_block(p.commodity.mnemonic, "        "))
            out.append("      </price:commodity>")
            out.append("      <price:currency>")
            out.append(commodity_block(p.currency.mnemonic, "        "))
            out.append("      </price:currency>")
            out.append(f"      <price:time><ts:date>{ts(p.date)}</ts:date></price:time>")
            out.append("      <price:source>user:price</price:source>")
            out.append("      <price:type>last</price:type>")
            num = int((Decimal(str(p.value)) * 1000).to_integral_value())
            out.append(f"      <price:value>{num}/1000</price:value>")
            out.append("    </price>")
        out.append("  </gnc:pricedb>")

    out.append("</gnc:book>")
    out.append("</gnc-v2>")
    book.close()

    xml = "\n".join(out) + "\n"
    XML_OUT.parent.mkdir(parents=True, exist_ok=True)
    XML_OUT.write_text(xml, encoding="utf-8")

    # --- validate: the engine's real-GnuCash-XML reader must parse it, accounts + balances intact
    gb = GnuCashBook.open(XML_OUT)
    n_read = len([a for a in gb.accounts.values() if a.account_type != "ROOT"])
    assert n_read == len(accts), f"account count mismatch: wrote {len(accts)}, read {n_read}"
    # spot-check a couple of balances against piecash
    b2 = piecash.open_book(str(SQLITE_BOOK), readonly=True, open_if_lock=True)
    checks = ["Assets:Bank:Current", "Assets:Bank:Savings", "Liabilities:Credit Card", "Income:Salary"]
    for fn in checks:
        want = b2.accounts(fullname=fn).get_balance(recurse=False)
        got = gb.account_balance(fn, gb.transactions[-1].txn_date if gb.transactions else None)
        # account_balance sums signed split values; compare magnitude to piecash balance
        assert abs(abs(got) - abs(want)) < Decimal("0.01"), f"{fn}: xml {got} vs sqlite {want}"
    b2.close()

    print(f"wrote {XML_OUT}  ({len(xml)} bytes, {len(accts)} accounts, {len(txns)} txns, {len(prices)} price)")
    print(f"validated: engine reader parsed {n_read} accounts; balances match for {', '.join(checks)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
