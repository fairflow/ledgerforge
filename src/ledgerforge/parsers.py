"""Bank-statement parsers: OFX, QIF, Co-operative Bank CSV, Nationwide CSV, Nationwide mortgage CSV.

Pure functions — no filesystem layout, account names, or entity specifics baked in. Each returns
plain dicts with `date`/`amount`/`desc` (amounts are signed Decimals: credits positive). These are
the reusable substrate; an entity's consumer decides which file feeds which account.
"""
from __future__ import annotations

import csv
import re
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}


def field(block: str, tag: str) -> str:
    m = re.search(rf"<{tag}>([^<\r\n]*)", block, re.I)
    return m.group(1).strip() if m else ""


def parse_ofx(text: str):
    """-> (txns, opening). opening is derived from the ledger balance minus the net of txns."""
    txns = []
    for chunk in re.split(r"<STMTTRN>", text, flags=re.I)[1:]:
        block = re.split(r"</STMTTRN>|</BANKTRANLIST>|<LEDGERBAL>", chunk, flags=re.I)[0]
        try:
            amount = Decimal(field(block, "TRNAMT"))
        except (InvalidOperation, ValueError):
            continue
        ds = field(block, "DTPOSTED")[:8]
        if len(ds) != 8:
            continue
        desc = (field(block, "NAME") + " " + field(block, "MEMO")).strip()
        txns.append({"date": date(int(ds[:4]), int(ds[4:6]), int(ds[6:8])), "amount": amount, "desc": desc,
                     "ref": field(block, "FITID"), "ttype": field(block, "TRNTYPE").upper()})
    m = re.search(r"<LEDGERBAL>.*?<BALAMT>([^<\r\n]*)", text, re.S | re.I)
    ledger = Decimal(m.group(1).strip()) if m else None
    net = sum((t["amount"] for t in txns), Decimal(0))
    opening = (ledger - net) if ledger is not None else Decimal(0)
    return txns, opening


def parse_qif(text: str):
    """Parse a QIF (!Type:Bank). Dates are US MM/DD/YYYY (Wise exports). -> [{date, amount, desc}]."""
    out = []
    for chunk in text.split("^"):
        amt = None
        ds = pay = memo = ""
        for line in chunk.splitlines():
            k = line[:1]
            if k == "T":
                try:
                    amt = Decimal(line[1:].replace(",", "").strip())
                except (InvalidOperation, ValueError):
                    amt = None
            elif k == "D":
                ds = line[1:].strip()
            elif k == "P":
                pay = line[1:].strip()
            elif k == "M":
                memo = line[1:].strip()
        if amt is None:
            continue
        d = None
        m = re.match(r"(\d{1,2})/(\d{1,2})/(\d{2,4})", ds)
        if m:
            mm, dd, yy = int(m.group(1)), int(m.group(2)), int(m.group(3))
            d = date(yy + 2000 if yy < 100 else yy, mm, dd)
        out.append({"date": d, "amount": amt, "desc": (pay + " " + memo).strip() or pay})
    return out


def parse_coop_csv(path: Path):
    """Co-operative Bank / Smile CSV (Date,Description,Type,Money In,Money Out,Balance), newest-first.
    Amount = Money In - Money Out (signed). -> (txns, opening, closing)."""
    def dec(s):
        s = (s or "").replace(",", "").strip()
        try:
            return Decimal(s) if s else Decimal(0)
        except InvalidOperation:
            return Decimal(0)
    rows = []
    for r in csv.DictReader(Path(path).open(encoding="utf-8-sig", errors="replace")):
        m = re.match(r"(\d{4})-(\d{2})-(\d{2})", (r.get("Date") or "").strip())
        if not m:
            continue
        rows.append({"date": date(int(m.group(1)), int(m.group(2)), int(m.group(3))),
                     "amount": dec(r.get("Money In")) - dec(r.get("Money Out")),
                     "desc": (r.get("Description") or "").strip(), "bal": dec(r.get("Balance"))})
    if not rows:
        return [], Decimal(0), Decimal(0)
    closing = rows[0]["bal"] if rows[0]["date"] >= rows[-1]["date"] else rows[-1]["bal"]  # newest balance
    opening = closing - sum((x["amount"] for x in rows), Decimal(0))
    txns = [{"date": x["date"], "amount": x["amount"], "desc": x["desc"]} for x in sorted(rows, key=lambda x: x["date"])]
    return txns, opening, closing


NW_TTYPE = {  # Nationwide CSV 'Transaction type' -> routing signal a consumer's contra logic can use
    "Contactless Payment": "POS", "Visa purchase": "POS", "Visa Credit": "POS",
    "Direct debit": "DIRECTDEBIT", "Direct Debit - First Payment": "DIRECTDEBIT",
    "Interest added": "INT", "Correction of interest added": "INT",
    "Foreign currency transaction fee": "FEE",
    "Nationwide Fairer Share Payment": "MEMBER", "The Big Nationwide Thank You": "MEMBER",
}


def nw_ttype(nt: str) -> str:
    if nt in NW_TTYPE:
        return NW_TTYPE[nt]
    if nt.lower().startswith("atm withdrawal"):
        return "CASH"
    return ""  # transfers / credits / payments -> account-number markers + categorise decide


def parse_nationwide_csv(path: Path):
    """Nationwide statement CSV (Date, Transaction type, Description, Paid out, Paid in, Balance;
    oldest-first, GBP-prefixed, 'DD Mon YYYY'). The Transaction type -> a ttype signal
    (POS/DIRECTDEBIT/INT/FEE/CASH/MEMBER) for routing. -> (txns, opening, closing)."""
    def money(s):
        s = (s or "").replace("£", "").replace(",", "").strip()
        try:
            return Decimal(s) if s else Decimal(0)
        except InvalidOperation:
            return Decimal(0)
    rows, started = [], False
    for r in csv.reader(Path(path).open(encoding="utf-8-sig", errors="replace")):
        if r[:1] == ["Date"]:
            started = True
            continue
        if not started or len(r) < 6:
            continue
        m = re.match(r"(\d{1,2})\s+([A-Za-z]{3})[a-z]*\s+(\d{4})", r[0].strip())
        if not m:
            continue
        rows.append({"date": date(int(m.group(3)), MONTHS[m.group(2).lower()[:3]], int(m.group(1))),
                     "amount": money(r[4]) - money(r[3]), "desc": r[2].strip(),
                     "ttype": nw_ttype(r[1].strip()), "bal": money(r[5])})
    if not rows:
        return [], Decimal(0), Decimal(0)
    closing = rows[-1]["bal"] if rows[-1]["date"] >= rows[0]["date"] else rows[0]["bal"]
    opening = closing - sum((x["amount"] for x in rows), Decimal(0))
    txns = [{"date": x["date"], "amount": x["amount"], "desc": x["desc"], "ttype": x["ttype"]} for x in rows]
    return txns, opening, closing


def read_statements(txn_dir, glob: str, fmt: str):
    """Dispatch every file matching `glob` under `txn_dir` by format. -> [{date, amount, desc, ...}]."""
    out = []
    for f in sorted(Path(txn_dir).glob(glob)):
        if fmt == "ofx":
            out += parse_ofx(f.read_text(errors="replace"))[0]
        elif fmt == "qif":
            out += parse_qif(f.read_text(errors="replace"))
        elif fmt == "coop-csv":
            out += parse_coop_csv(f)[0]
        elif fmt == "nationwide-csv":
            out += parse_nationwide_csv(f)[0]
    return out


def parse_mdate(s: str):
    s = s.strip()
    m = re.match(r"(\d{1,2})\s+([A-Za-z]{3})[a-z]*\s+(\d{4})", s)
    if m:
        return date(int(m.group(3)), MONTHS[m.group(2).lower()[:3]], int(m.group(1)))
    m = re.match(r"([A-Za-z]{3})[a-z]*\s+(\d{2})", s)
    if m:
        return date(2000 + int(m.group(2)), MONTHS[m.group(1).lower()[:3]], 1)
    return None


def parse_mortgage(path: Path):
    """Nationwide mortgage CSV (cp1252, GBP sign). Returns (txns, opening, closing)."""
    def amt(s):
        s = s.replace("£", "").replace(",", "").strip()
        try:
            return Decimal(s) if s else None
        except InvalidOperation:
            return None
    txns, opening, closing, year = [], None, None, 2025
    for r in csv.reader(Path(path).open(encoding="cp1252")):
        if len(r) >= 2 and "Statement Year" in r[0]:
            m = re.search(r"(\d{4})", r[1])
            if m:
                year = int(m.group(1))
            continue
        if len(r) < 5:
            continue
        d, desc, paid_out, paid_in, bal = (r + [""] * 5)[:5]
        if "Opening Outstanding Balance" in desc:
            opening = amt(bal)
        elif desc.strip() == "Outstanding Balance":
            closing = amt(bal)
        elif "Interest" in desc and amt(paid_out):
            txns.append({"date": parse_mdate(d) or date(year, 1, 1), "amount": amt(paid_out), "kind": "interest"})
        elif "Payment" in desc and amt(paid_in):
            txns.append({"date": parse_mdate(d) or date(year, 1, 1), "amount": amt(paid_in), "kind": "payment"})
    return txns, opening, closing
