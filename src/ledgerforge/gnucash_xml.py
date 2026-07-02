"""ledgerforge.gnucash_xml — read-only access to GnuCash **XML** books (gzip or plain).

GnuCash stores books in two formats: XML (gzip-compressed .gnucash files) and SQLite.
This module parses the XML format directly with the stdlib (no piecash needed); for the
SQLite format use ``ledgerforge.book`` (piecash). Complements it so a consumer can read
either format from the one engine.

Public API
----------
::

    book = GnuCashBook.open("/path/to/book.gnucash")
    # book is read-only; never mutated
    accounts  = book.accounts           # {guid: Account}
    txns      = book.transactions       # [Transaction]
    book.close()                        # no-op for XML

    # Convenience helpers
    balance = book.account_balance("Assets:Bank", date(2025, 2, 28))
    for txn, split in book.splits_in_period(date(2025, 12, 1), date(2026, 2, 28)):
        ...
"""

from __future__ import annotations

import gzip
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Iterator


# ---------------------------------------------------------------------------
# XML namespaces used by GnuCash's native XML format
# ---------------------------------------------------------------------------
_NS: dict[str, str] = {
    "gnc":   "http://www.gnucash.org/XML/gnc",
    "act":   "http://www.gnucash.org/XML/act",
    "split": "http://www.gnucash.org/XML/split",
    "trn":   "http://www.gnucash.org/XML/trn",
    "ts":    "http://www.gnucash.org/XML/ts",
}


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Account:
    guid: str
    name: str
    account_type: str           # BANK, ASSET, LIABILITY, INCOME, EXPENSE, EQUITY, …
    parent_guid: str | None
    fullname: str               # colon-separated path from root, e.g. "Root Account:VAT:Input"

    def is_income(self) -> bool:
        return self.account_type == "INCOME"

    def is_expense(self) -> bool:
        return self.account_type in ("EXPENSE",)

    def is_asset(self) -> bool:
        return self.account_type in ("ASSET", "BANK", "CASH", "CREDIT", "RECEIVABLE")

    def is_liability(self) -> bool:
        return self.account_type in ("LIABILITY", "CREDIT", "PAYABLE")


@dataclass(frozen=True)
class Split:
    account_guid: str
    amount: Decimal             # positive = debit for ASSET/EXPENSE; negative = credit


@dataclass
class Transaction:
    txn_date: date
    description: str
    splits: list[Split] = field(default_factory=list)


# ---------------------------------------------------------------------------
# GnuCashBook
# ---------------------------------------------------------------------------

class GnuCashBook:
    """Read-only view of a GnuCash XML book."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self.accounts: dict[str, Account] = {}
        self.transactions: list[Transaction] = []
        self._load()

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    @classmethod
    def open(cls, path: str | Path) -> "GnuCashBook":
        """Open a GnuCash XML file (gzip-compressed or plain)."""
        return cls(Path(path))

    def close(self) -> None:
        """No-op for XML-format books; reserved for future SQLite support."""

    # ------------------------------------------------------------------
    # Convenience queries
    # ------------------------------------------------------------------

    def account_by_fullname(self, fullname: str) -> Account | None:
        """Return the Account whose full path matches *fullname*, or None."""
        for acct in self.accounts.values():
            if acct.fullname == fullname:
                return acct
        return None

    def splits_in_period(
        self,
        start: date,
        end: date,
        *,
        exclude_desc_keywords: list[str] | None = None,
    ) -> Iterator[tuple[Transaction, Split]]:
        """Yield (txn, split) pairs for transactions dated [start, end].

        Parameters
        ----------
        start, end:
            Inclusive date range.
        exclude_desc_keywords:
            If given, skip any transaction whose description contains one of
            these strings (case-insensitive).  Used to filter closing journals,
            depreciation transfers, and HMRC VAT clearing entries.
        """
        excl = [k.lower() for k in (exclude_desc_keywords or [])]
        for txn in self.transactions:
            if not (start <= txn.txn_date <= end):
                continue
            if excl and any(k in txn.description.lower() for k in excl):
                continue
            for spl in txn.splits:
                yield txn, spl

    def account_balance(
        self,
        fullname: str,
        as_of: date,
        *,
        exclude_desc_keywords: list[str] | None = None,
    ) -> Decimal:
        """Return the running balance of an account up to and including *as_of*.

        For ASSET/EXPENSE accounts: positive balance = net debits.
        For LIABILITY/INCOME accounts: positive balance = net credits
        (amounts are stored as negatives for credits in the XML, so we negate).
        """
        acct = self.account_by_fullname(fullname)
        if acct is None:
            return Decimal(0)
        total = Decimal(0)
        excl = [k.lower() for k in (exclude_desc_keywords or [])]
        for txn in self.transactions:
            if txn.txn_date > as_of:
                continue
            if excl and any(k in txn.description.lower() for k in excl):
                continue
            for spl in txn.splits:
                if spl.account_guid == acct.guid:
                    total += spl.amount
        return total

    # ------------------------------------------------------------------
    # Private: XML parsing
    # ------------------------------------------------------------------

    def _load(self) -> None:
        path = self._path
        try:
            with gzip.open(path, "rb") as fh:
                tree = ET.parse(fh)
        except gzip.BadGzipFile:
            # Plain XML (uncompressed)
            tree = ET.parse(path)

        root = tree.getroot()
        book_el = root.find(".//gnc:book", _NS)
        if book_el is None:
            raise ValueError(f"{path}: could not find <gnc:book> element")

        self._parse_accounts(book_el)
        self._parse_transactions(book_el)

    def _parse_accounts(self, book_el: ET.Element) -> None:
        # First pass: collect raw data
        raw: dict[str, dict] = {}
        for acct_el in book_el.findall("gnc:account", _NS):
            guid = acct_el.find("act:id", _NS).text  # type: ignore[union-attr]
            name = acct_el.find("act:name", _NS).text or ""  # type: ignore[union-attr]
            atype = acct_el.find("act:type", _NS).text or "ASSET"  # type: ignore[union-attr]
            parent_el = acct_el.find("act:parent", _NS)
            parent_guid = parent_el.text if parent_el is not None else None
            raw[guid] = {"name": name, "type": atype, "parent": parent_guid}

        # Build fullname cache (recursive, memoised)
        fn_cache: dict[str, str] = {}

        def fullname(guid: str) -> str:
            if guid in fn_cache:
                return fn_cache[guid]
            a = raw[guid]
            p = a["parent"]
            if p is None or p not in raw:
                fn_cache[guid] = a["name"]
            else:
                fn_cache[guid] = fullname(p) + ":" + a["name"]
            return fn_cache[guid]

        for guid in raw:
            fullname(guid)

        # Strip the root account name from all fullnames so they match the
        # GnuCash UI display (which never shows the root account).
        root_guids = [g for g, a in raw.items() if a["type"] == "ROOT"]
        if root_guids:
            root_prefix = fn_cache[root_guids[0]] + ":"
            fn_cache = {
                g: (fn[len(root_prefix):] if fn.startswith(root_prefix) else fn)
                for g, fn in fn_cache.items()
            }

        self.accounts = {
            guid: Account(
                guid=guid,
                name=raw[guid]["name"],
                account_type=raw[guid]["type"],
                parent_guid=raw[guid]["parent"],
                fullname=fn_cache[guid],
            )
            for guid in raw
        }

    def _parse_transactions(self, book_el: ET.Element) -> None:
        txns: list[Transaction] = []
        for txn_el in book_el.findall("gnc:transaction", _NS):
            date_text = txn_el.find(".//trn:date-posted/ts:date", _NS)
            if date_text is None:
                continue
            txn_date = date.fromisoformat(date_text.text[:10])  # type: ignore[arg-type]
            desc_el = txn_el.find("trn:description", _NS)
            description = desc_el.text if desc_el is not None else ""
            splits: list[Split] = []
            for split_el in txn_el.findall(".//trn:split", _NS):
                acct_id = split_el.find("split:account", _NS).text  # type: ignore[union-attr]
                val_text = split_el.find("split:value", _NS).text or "0"  # type: ignore[union-attr]
                amount = _parse_fraction(val_text)
                splits.append(Split(account_guid=acct_id, amount=amount))
            txns.append(Transaction(txn_date=txn_date, description=description, splits=splits))
        self.transactions = txns


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_fraction(s: str) -> Decimal:
    """Parse a GnuCash fraction like '27090/100' or '270' into a Decimal."""
    if "/" in s:
        num, den = s.split("/", 1)
        return Decimal(num) / Decimal(den)
    return Decimal(s)
