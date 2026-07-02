"""ledgerforge.report — render a read-only accounts / balance-sheet HTML page from a GnuCash book.

Self-contained: inline CSS + a tiny collapse toggle, no external assets. Entity-agnostic — it groups
by top-level account, totals assets/liabilities/net-worth per currency, and shows a collapsible
account tree. Use it to publish a viewable snapshot of any book the engine builds.
"""
from __future__ import annotations

import html as _html
from collections import defaultdict
from decimal import Decimal

import piecash

ASSET_TYPES = {"ASSET", "BANK", "CASH", "STOCK", "MUTUAL", "RECEIVABLE"}
LIAB_TYPES = {"LIABILITY", "CREDIT", "PAYABLE"}
SYM = {"GBP": "£", "EUR": "€", "USD": "$"}


def _sym(ccy: str) -> str:
    return SYM.get(ccy, ccy + " ")


def _money(ccy: str, v: Decimal) -> str:
    return f"{_sym(ccy)}{v:,.2f}"


def _own_balance(acc) -> Decimal:
    """This account's own balance (its direct splits only) — avoids cross-currency parent errors."""
    try:
        return acc.get_balance(recurse=False)
    except Exception:
        return Decimal(0)


def accounts_html(book_path, title: str = "Accounts", built: str = "") -> str:
    book = piecash.open_book(str(book_path), readonly=True, open_if_lock=True)
    try:
        accts = [a for a in book.accounts]
        own = {a.fullname: _own_balance(a) for a in accts}
        typ = {a.fullname: a.type for a in accts}
        ccy = {a.fullname: a.commodity.mnemonic for a in accts}
        names = set(own)
        post_dates = [t.post_date for t in book.transactions]
    finally:
        book.close()

    as_at = max(post_dates).strftime("%d %b %Y") if post_dates else "—"

    # per-currency totals (balances live in the leaves; summing own balances never double-counts)
    assets: dict[str, Decimal] = defaultdict(Decimal)
    liabs: dict[str, Decimal] = defaultdict(Decimal)
    for fn, bal in own.items():
        if typ[fn] in ASSET_TYPES:
            assets[ccy[fn]] += bal
        elif typ[fn] in LIAB_TYPES:
            liabs[ccy[fn]] += bal
    currencies = sorted(set(assets) | set(liabs))

    # subtree total per account (per currency), for the collapsible tree
    def subtotal(prefix: str) -> dict[str, Decimal]:
        agg: dict[str, Decimal] = defaultdict(Decimal)
        for fn, bal in own.items():
            if fn == prefix or fn.startswith(prefix + ":"):
                agg[ccy[fn]] += bal
        return agg

    def is_parent(fn: str) -> bool:
        return any(other != fn and other.startswith(fn + ":") for other in names)

    rows_html = []
    for fn in sorted(names):
        depth = fn.count(":")
        leaf = fn.split(":")[-1]
        parent = is_parent(fn)
        totals = subtotal(fn) if parent else {ccy[fn]: own[fn]}
        shown = "  ".join(_money(c, v) for c, v in sorted(totals.items()) if v != 0) or "—"
        pad = 6 + depth * 20
        cls = "parent" if parent else "leaf"
        caret = "<span class='caret'>▾</span> " if parent else ""
        rows_html.append(
            f"<tr class='{cls}' data-fn='{_html.escape(fn)}' data-depth='{depth}'>"
            f"<td class='nm' style='padding-left:{pad}px'>{caret}{_html.escape(leaf)}</td>"
            f"<td class='ty'>{typ[fn]}</td>"
            f"<td class='amt'>{shown}</td></tr>"
        )

    cards = []
    for c in currencies:
        a, l = assets.get(c, Decimal(0)), liabs.get(c, Decimal(0))
        cards.append(
            f"<div class='card'><div class='cc'>{c}</div>"
            f"<div class='nw'>{_money(c, a - l)}</div>"
            f"<div class='sub'>assets {_money(c, a)} &middot; liabilities {_money(c, l)}</div></div>"
        )
    if not cards:
        cards.append("<div class='card'><div class='nw'>—</div></div>")

    return _PAGE.format(
        title=_html.escape(title), as_at=as_at, built=_html.escape(built),
        cards="\n".join(cards), rows="\n".join(rows_html),
    )


_PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
  :root {{ --ink:#1d2530; --mut:#6b7785; --line:#e6e9ee; --bg:#f7f8fa; --card:#fff; --pos:#0a7d43; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; font:15px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;
         color:var(--ink); background:var(--bg); }}
  .wrap {{ max-width:820px; margin:0 auto; padding:28px 20px 60px; }}
  h1 {{ font-size:22px; margin:0 0 2px; }}
  .meta {{ color:var(--mut); font-size:13px; margin-bottom:22px; }}
  .cards {{ display:flex; gap:12px; flex-wrap:wrap; margin-bottom:26px; }}
  .card {{ flex:1 1 180px; background:var(--card); border:1px solid var(--line); border-radius:12px;
          padding:14px 16px; }}
  .card .cc {{ color:var(--mut); font-size:12px; letter-spacing:.04em; }}
  .card .nw {{ font-size:24px; font-weight:650; color:var(--pos); margin:2px 0; }}
  .card .sub {{ color:var(--mut); font-size:12px; }}
  table {{ width:100%; border-collapse:collapse; background:var(--card);
          border:1px solid var(--line); border-radius:12px; overflow:hidden; }}
  th,td {{ text-align:left; padding:7px 12px; border-bottom:1px solid var(--line); }}
  th {{ font-size:12px; color:var(--mut); text-transform:uppercase; letter-spacing:.04em; }}
  tr:last-child td {{ border-bottom:none; }}
  td.ty {{ color:var(--mut); font-size:12px; width:110px; }}
  td.amt {{ text-align:right; font-variant-numeric:tabular-nums; white-space:nowrap; }}
  tr.parent {{ cursor:pointer; font-weight:600; background:#fbfcfd; }}
  tr.parent .caret {{ color:var(--mut); font-size:11px; display:inline-block; width:12px;
                      transition:transform .12s; }}
  tr.parent.closed .caret {{ transform:rotate(-90deg); }}
  .foot {{ color:var(--mut); font-size:12px; margin-top:18px; }}
  .foot a {{ color:var(--mut); }}
</style></head>
<body><div class="wrap">
  <h1>{title}</h1>
  <div class="meta">Balance sheet as at {as_at}{built}</div>
  <div class="cards">{cards}</div>
  <table>
    <thead><tr><th>Account</th><th>Type</th><th style="text-align:right">Balance</th></tr></thead>
    <tbody>{rows}</tbody>
  </table>
  <div class="foot">Generated by <a href="https://github.com/fairflow/ledgerforge">ledgerforge</a>
    &middot; demo data &mdash; entirely fictional.</div>
</div>
<script>
  document.querySelectorAll('tr.parent td.nm').forEach(function (td) {{
    td.parentElement.addEventListener('click', function () {{
      var row = this, depth = +row.dataset.depth, closing = !row.classList.contains('closed');
      row.classList.toggle('closed');
      for (var el = row.nextElementSibling; el; el = el.nextElementSibling) {{
        if (+el.dataset.depth <= depth) break;
        el.style.display = closing ? 'none' : '';
        if (!closing) el.classList.remove('closed');
      }}
    }});
  }});
</script>
</body></html>
"""
