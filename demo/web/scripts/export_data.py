"""Export the fictional demo ledger to JSON for the Svelte toolkit.

The engine is the single source of truth. This runs the real ledgerforge engine over the
fictional demo book + statements and writes three JSON files the Svelte app renders from:

  src/lib/data/book.json     the chart of accounts with balances (accounts & balances page)
  src/lib/data/rules.json    the categorisation rules, grouped (rules editor)
  src/lib/data/unspec.json   payees no rule catches yet (unspecified assigner)

It mirrors the data-prep of demo/make_accounts.py, demo/make_editor.py and demo/make_unspec.py
exactly, so the Svelte pages match the Python-generated toolkit. All data is fictional.

Run (needs the ledger venv with piecash + ledgerforge):
  /path/to/ledger/.venv/bin/python demo/web/scripts/export_data.py
"""
from __future__ import annotations

import json
import re
import warnings
from collections import defaultdict
from decimal import Decimal
from pathlib import Path

warnings.filterwarnings("ignore")
import piecash  # noqa: E402

from ledgerforge.parsers import parse_ofx  # noqa: E402
from ledgerforge.rules import categorise, normalise  # noqa: E402

DEMO = Path(__file__).resolve().parents[2]          # …/ledgerforge/demo
DATA = DEMO / "data"
BOOK = DEMO / "build" / "demo.gnucash"
OUT = DEMO / "web" / "src" / "lib" / "data"

# ── accounts & balances (mirrors make_accounts.py data-prep) ────────────────────
ORDER = ["Assets", "Liabilities", "Equity", "Income", "Expenses"]


def export_book() -> dict:
    book = piecash.open_book(str(BOOK), readonly=True, open_if_lock=True)
    accounts = []
    for a in sorted(book.accounts, key=lambda x: x.fullname):
        if a.type == "ROOT":
            continue
        accounts.append({
            "fullname": a.fullname,
            "name": a.name,
            "code": a.code or "",
            "type": a.type,
            "top": a.fullname.split(":")[0],
            "depth": a.fullname.count(":"),
            "balance": float(a.get_balance(recurse=False)),
            "currency": a.commodity.mnemonic,
        })
    rate = {"GBP": 1.0}
    for p in book.prices:
        if p.currency.mnemonic == "GBP":
            rate[p.commodity.mnemonic] = float(p.value)
    dates = [t.post_date for t in book.transactions if t.post_date]
    bs_date = max(dates).isoformat() if dates else None
    pl_start = min(dates).isoformat() if dates else None
    book.close()
    return {"base": "GBP", "order": ORDER, "fx": rate,
            "bs_date": bs_date, "pl_start": pl_start, "accounts": accounts}


# ── rules editor (mirrors make_editor.py) ───────────────────────────────────────
EDITOR_EXTRAS = {
    "Expenses", "Income", "Assets", "Liabilities",
    "Expenses:Miscellaneous", "Expenses:Books", "Expenses:DIY", "Expenses:Shopping",
    "Expenses:Garden", "Income:Other Income", "Assets:Cash",
}


def export_rules() -> dict:
    rules = json.loads((DATA / "rules.json").read_text())["rules"]
    groups = [{"a": r["account"], "m": r.get("match", []), "r": r.get("regex", [])} for r in rules]
    accts = sorted({g["a"] for g in groups} | EDITOR_EXTRAS)
    return {"groups": groups, "accts": accts}


# ── unspecified assigner (mirrors make_unspec.py) ───────────────────────────────
UNSPEC_ACCOUNTS = [  # (registry id, short source label, statement file, unspecified-eligible?)
    ("demo-current", "Current", DATA / "statements/current.ofx", True),
    ("demo-savings", "Savings", DATA / "statements/savings.ofx", True),
    ("demo-card", "Credit Card", DATA / "statements/card.ofx", True),
    ("demo-euro", "Euro Account", DATA / "statements/euro.ofx", False),
]


def firstwords(desc: str, n: int = 3) -> str:
    s = desc.upper().replace("&AMP;", "&")
    s = re.sub(r"\*\S+", "", s)
    s = re.sub(r"\s+\d[\d.,]*\s+(USD|EUR|GBP)\b.*", "", s)
    s = re.sub(r"\s+\d{3}-\d+.*", "", s)
    s = re.sub(r"\s+[A-Z]{2}\s+\d{3,}.*", "", s)
    s = re.sub(r"\s+\d{4,}.*", "", s)
    s = re.sub(r"[^\w &.'/-]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return " ".join(s.split()[:n])


def classify(desc: str):
    u = desc.upper()

    def has(*ks):
        return any(k in u for k in ks)

    if "AMZN" in u or "AMAZON" in u:
        return ("AMAZON", "Expenses:Shopping")
    if has("WATERSTONES", "BOOKSHOP", "WH SMITH"):
        return (firstwords(desc), "Expenses:Books")
    if has("SCREWFIX", "B & Q", "JEWSON", "TOOLSTATION"):
        return (firstwords(desc), "Expenses:DIY")
    if has("GARDEN CENTRE", "NURSERY", "PLANTS"):
        return (firstwords(desc), "Expenses:Garden")
    if has("CAFE", "COFFEE", "RESTAURANT", "BAKERY", "FORGE"):
        return (firstwords(desc), "Expenses:Dining")
    return (firstwords(desc), "")


def export_unspec() -> dict:
    rules = json.loads((DATA / "rules.json").read_text())["rules"]
    rev: dict[str, dict] = defaultdict(lambda: {"count": 0, "total": Decimal(0), "accts": set(), "txns": []})
    alldesc: dict[str, int] = defaultdict(int)
    for aid, src, path, eligible in UNSPEC_ACCOUNTS:
        for t in parse_ofx(path.read_text())[0]:
            dn = normalise(t["desc"])
            alldesc[dn] += 1
            if not eligible or categorise(t["desc"], rules):
                continue
            g = rev[dn]
            g["count"] += 1
            g["total"] += t["amount"]
            g["accts"].add(src)
            g["txns"].append({"d": t["date"].isoformat(), "a": float(t["amount"]), "s": src, "aid": aid})
    rows = []
    for d, g in sorted(rev.items(), key=lambda kv: (-kv[1]["count"], kv[1]["total"])):
        tok, acct = classify(d)
        rows.append({"d": d, "c": g["count"], "t": float(g["total"]), "tok": tok, "acct": acct,
                     "src": sorted(g["accts"]), "txns": sorted(g["txns"], key=lambda x: x["d"])})
    accts = sorted({r["account"] for r in rules} | {
        "Expenses:Shopping", "Expenses:Books", "Expenses:DIY", "Expenses:Garden",
        "Expenses:Miscellaneous", "Income:Other Income", "Assets:Cash",
    })
    return {"rows": rows, "accts": accts, "alldesc": dict(alldesc)}


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    book = export_book()
    rules = export_rules()
    unspec = export_unspec()
    (OUT / "book.json").write_text(json.dumps(book, indent=2), encoding="utf-8")
    (OUT / "rules.json").write_text(json.dumps(rules, indent=2), encoding="utf-8")
    (OUT / "unspec.json").write_text(json.dumps(unspec, indent=2), encoding="utf-8")
    print(f"wrote {OUT}/book.json    ({len(book['accounts'])} accounts, "
          f"FX {book['fx']}, as at {book['bs_date']})")
    print(f"wrote {OUT}/rules.json   ({len(rules['groups'])} accounts, {len(rules['accts'])} in datalist)")
    print(f"wrote {OUT}/unspec.json  ({len(unspec['rows'])} payees)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
