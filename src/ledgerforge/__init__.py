"""ledgerforge — a small engine for building double-entry GnuCash books from bank statements,
categorising transactions by rules, and serving a local review toolkit.

The engine is entity-agnostic: no account names, paths, or numbers live here. A consumer supplies
those via `Settings` (see `ledgerforge.config`).
"""
__version__ = "0.1.0"

from ledgerforge import book, gnucash_xml, overrides, parsers, rules, serve, transfers  # noqa: F401
from ledgerforge.config import Settings  # noqa: F401
