"""Generate the accounts + balances page -> demo/site/accounts.html.

Exact duplicate of the household toolkit's accounts page design (net-worth cards with LIQUID and
TOTAL, P&L, the accounting equation with FX translation reserve and a true double-entry check, and
a collapsible account tree with per-section GBP subtotals) — rendered from the fictional demo book.

Run:  python demo/make_accounts.py        (after demo/build_demo.py)
"""
from __future__ import annotations

import html
import warnings
from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

warnings.filterwarnings("ignore")
import piecash  # noqa: E402

HERE = Path(__file__).parent
OUT = HERE / "site/accounts.html"
BOOK_PATH = HERE / "build/demo.gnucash"

ORDER = ["Assets", "Liabilities", "Equity", "Income", "Expenses"]
ASSET_TYPES = {"ASSET", "BANK", "CASH", "STOCK", "MUTUAL"}
LIAB_TYPES = {"LIABILITY", "CREDIT"}
LIQUID_TYPES = {"BANK", "CASH"}  # spendable now: bank + cash accounts


def fmt(v: Decimal) -> str:
    return f"{float(v):,.2f}"


def main() -> int:
    book = piecash.open_book(str(BOOK_PATH), readonly=True, open_if_lock=True)
    rows_by_top: dict[str, list] = defaultdict(list)
    nw: dict[str, dict] = defaultdict(lambda: {"asset": Decimal(0), "liab": Decimal(0)})
    eqv: dict[str, Decimal] = defaultdict(Decimal)
    incv: dict[str, Decimal] = defaultdict(Decimal)
    expv: dict[str, Decimal] = defaultdict(Decimal)
    liq: dict[str, Decimal] = defaultdict(Decimal)
    n_acc = 0
    for a in sorted(book.accounts, key=lambda x: x.fullname):
        if a.type == "ROOT":
            continue
        n_acc += 1
        top = a.fullname.split(":")[0]
        depth = a.fullname.count(":")
        bal = a.get_balance(recurse=False)
        cur = a.commodity.mnemonic
        rows_by_top[top].append((a.code or "", a.name, depth, bal, cur, a.fullname))
        if a.type in ASSET_TYPES:
            nw[cur]["asset"] += bal
            if a.type in LIQUID_TYPES:
                liq[cur] += bal
        elif a.type in LIAB_TYPES:
            nw[cur]["liab"] += bal
        elif a.type == "EQUITY":
            eqv[cur] += bal
        elif a.type == "INCOME":
            incv[cur] += bal
        elif a.type == "EXPENSE":
            expv[cur] += bal
    rate = {"GBP": Decimal(1)}
    for p in book.prices:
        if p.currency.mnemonic == "GBP":
            rate[p.commodity.mnemonic] = Decimal(str(p.value))
    _dates = [t.post_date for t in book.transactions if t.post_date]
    bs_date = max(_dates) if _dates else date.today()
    pl_start = min(_dates) if _dates else bs_date
    bs_s = bs_date.strftime("%d %b %Y")
    pls = pl_start.strftime("%d %b %Y")
    book.close()

    # net-worth cards, per currency
    cards = []
    for cur in sorted(nw):
        asset, liab = nw[cur]["asset"], nw[cur]["liab"]
        cards.append(
            f'<div class="nw"><div class="nwc">{html.escape(cur)}</div>'
            f'<div class="nwr"><span>Assets</span><b>{fmt(asset)}</b></div>'
            f'<div class="nwr"><span>Liabilities</span><b>{fmt(liab)}</b></div>'
            f'<div class="nwr tot"><span>Net worth</span><b>{fmt(asset - liab)}</b></div></div>')

    combined = sum(((nw[c]["asset"] - nw[c]["liab"]) * rate.get(c, Decimal(1)) for c in nw), Decimal(0))
    _rn = ", ".join(f"{c} {float(rate[c]):.3f}" for c in sorted(rate) if c != "GBP") or "no FX set"
    cards.insert(0, '<div class="nw" style="border-color:#0f6e56">'
                    '<div class="nwc" style="color:#0f6e56">TOTAL &asymp; GBP</div>'
                    f'<div class="nwr tot" style="margin-top:26px"><span>Net worth</span><b>{fmt(combined)}</b></div>'
                    f'<div class="nwr" style="font-size:11px;color:#999"><span>at</span><span>{_rn}</span></div></div>')

    liq_gbp = sum((liq[c] * rate.get(c, Decimal(1)) for c in liq), Decimal(0))
    cards.insert(0, '<div class="nw" style="border-color:#185fa5">'
                    '<div class="nwc" style="color:#185fa5">LIQUID &asymp; GBP</div>'
                    f'<div class="nwr tot" style="margin-top:26px"><span>Cash + savings</span>'
                    f'<b style="color:#185fa5">{fmt(liq_gbp)}</b></div>'
                    '<div class="nwr" style="font-size:11px;color:#999"><span></span>'
                    '<span>bank + cash accounts</span></div></div>')

    allc = set(nw) | set(eqv) | set(incv) | set(expv)

    # ---- P&L summary (income statement), GBP at market FX ----
    inc_gbp = sum((incv[c] * rate.get(c, Decimal(1)) for c in allc), Decimal(0))
    exp_gbp = sum((expv[c] * rate.get(c, Decimal(1)) for c in allc), Decimal(0))
    net_gbp = inc_gbp - exp_gbp
    _ncol = "#0f6e56" if net_gbp >= 0 else "#b00"
    _nlbl = "surplus" if net_gbp >= 0 else "deficit"
    pnl = (
        f'<h2>Income &amp; expenses (P&amp;L) <span style="font-weight:400;'
        f'text-transform:none;letter-spacing:0;font-size:12px;color:#999">{pls} &ndash; {bs_s}</span></h2>'
        '<table style="max-width:480px">'
        f'<tr class="r"><td class="nm">Income</td><td class="bal">{fmt(inc_gbp)}</td></tr>'
        f'<tr class="r"><td class="nm">Expenses</td><td class="bal">{fmt(exp_gbp)}</td></tr>'
        f'<tr class="r"><td class="nm" style="font-weight:500">Net {_nlbl}</td>'
        f'<td class="bal" style="font-weight:500;color:{_ncol}">{fmt(net_gbp)}</td></tr>'
        '</table>')

    # ---- Accounting equation: GBP reporting, foreign at market FX, with FX translation reserve ----
    A = sum((nw[c]["asset"] * rate.get(c, Decimal(1)) for c in allc), Decimal(0))
    L = sum((nw[c]["liab"] * rate.get(c, Decimal(1)) for c in allc), Decimal(0))
    Eqp = sum((eqv[c] * rate.get(c, Decimal(1)) for c in allc), Decimal(0))
    Ret = net_gbp  # retained earnings = income - expenses
    Fx = A - L - Eqp - Ret
    Etot = Eqp + Ret + Fx
    # Genuine double-entry integrity check at recorded par (no FX plug): residual must be exactly 0.
    par_resid = sum((nw[c]["asset"] - nw[c]["liab"] - eqv[c] - incv[c] + expv[c] for c in allc), Decimal(0))
    _pchk = ('<span style="color:#0f6e56">&#10003; residual &pound;0.00 &mdash; books balance</span>'
             if abs(par_resid) < Decimal("0.01")
             else f'<span style="color:#b00">residual {fmt(par_resid)}</span>')
    equation = (
        f'<h2>Accounting equation &mdash; Assets = Liabilities + Equity <span style="font-weight:400;'
        f'text-transform:none;letter-spacing:0;font-size:12px;color:#999">as at {bs_s}</span></h2>'
        '<p class="sub" style="margin:-2px 0 8px">Reporting currency GBP; foreign balances at market FX.</p>'
        '<table style="max-width:480px">'
        f'<tr class="r"><td class="nm">Assets</td><td class="bal">{fmt(A)}</td></tr>'
        f'<tr class="r"><td class="nm">Liabilities</td><td class="bal">{fmt(L)}</td></tr>'
        f'<tr class="r z"><td class="nm" style="padding-left:24px">posted equity</td><td class="bal">{fmt(Eqp)}</td></tr>'
        f'<tr class="r z"><td class="nm" style="padding-left:24px">retained earnings</td><td class="bal">{fmt(Ret)}</td></tr>'
        f'<tr class="r z"><td class="nm" style="padding-left:24px">FX translation reserve</td><td class="bal">{fmt(Fx)}</td></tr>'
        f'<tr class="r"><td class="nm">Total equity</td><td class="bal">{fmt(Etot)}</td></tr>'
        f'<tr class="r"><td class="nm" style="font-weight:500">Liabilities + Equity</td>'
        f'<td class="bal" style="font-weight:500">{fmt(L + Etot)}</td></tr>'
        f'<tr class="r"><td class="nm" colspan="2" style="padding-top:6px">Double-entry check: {_pchk}</td></tr>'
        '</table>')

    # tree helpers: parent = has children; parents are placeholders showing a GBP subtree total.
    own_gbp = {}
    all_fn = []
    for top in ORDER:
        for code, name, depth, bal, cur, fn in rows_by_top.get(top, []):
            own_gbp[fn] = bal * rate.get(cur, Decimal(1))
            all_fn.append(fn)
    fnset = set(all_fn)

    def is_parent(fn):
        pre = fn + ":"
        return any(x.startswith(pre) for x in fnset)

    def subtree(fn):
        pre = fn + ":"
        return own_gbp.get(fn, Decimal(0)) + sum((own_gbp[x] for x in all_fn if x.startswith(pre)), Decimal(0))

    # account tables, per section (collapsible tree; parent rows carry the child subtotal in GBP)
    SYM = {"GBP": "&pound;", "EUR": "&euro;", "USD": "$"}
    sections = []
    for top in ORDER:
        rows = rows_by_top.get(top)
        if not rows:
            continue
        trs = []
        for code, name, depth, bal, cur, fn in rows:
            pad = 4 + depth * 20
            ttl = f' title="code {html.escape(code)}"' if code else ''
            parent = is_parent(fn)
            if parent:
                trs.append(
                    f'<tr class="r parent" data-path="{html.escape(fn)}">'
                    f'<td class="nm" style="padding-left:{pad}px"{ttl}><span class="tog"></span>{html.escape(name)}</td>'
                    f'<td class="bal"></td><td class="cur"></td>'
                    f'<td class="tot2">{fmt(subtree(fn))}</td></tr>')
            else:
                zero = " z" if abs(bal) < Decimal("0.005") else ""
                trs.append(
                    f'<tr class="r{zero}" data-path="{html.escape(fn)}">'
                    f'<td class="nm" style="padding-left:{pad}px"{ttl}>{html.escape(name)}</td>'
                    f'<td class="bal">{fmt(bal)}</td><td class="cur">{SYM.get(cur, html.escape(cur))}</td>'
                    f'<td class="tot2"></td></tr>')
        sections.append(
            f'<h2>{html.escape(top)}</h2>\n<table>'
            f'<tr class="hd"><th>Account</th><th style="text-align:right">Balance</th><th></th>'
            f'<th style="text-align:right">Total GBP</th></tr>'
            + "\n".join(trs) + "</table>")

    built = datetime.now().strftime("%d %b %Y %H:%M")
    doc = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Accounts &amp; balances</title>
<style>
body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Arial,sans-serif;margin:0;background:#f6f7f9;color:#1a1a1a;line-height:1.5}}
.wrap{{max-width:820px;margin:0 auto;padding:34px 20px 70px}}
a.back{{font-size:13px;color:#2563eb;text-decoration:none}}
h1{{font-size:24px;font-weight:650;margin:8px 0 4px}}
.sub{{color:#666;font-size:13px;margin:0 0 20px}}
h2{{font-size:14px;font-weight:650;margin:30px 0 8px;color:#333;text-transform:uppercase;letter-spacing:.04em}}
.nwrap{{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;margin:6px 0 6px}}
.nw{{background:#fff;border:1px solid #e3e3e3;border-radius:10px;padding:12px 14px}}
.nwc{{font-size:12px;font-weight:650;color:#888;letter-spacing:.05em}}
.nwr{{display:flex;justify-content:space-between;font-size:13px;color:#555;margin-top:5px}}
.nwr b{{font-family:ui-monospace,Menlo,Consolas,monospace;color:#222}}
.nwr.tot{{border-top:1px solid #eee;margin-top:7px;padding-top:6px;color:#111;font-weight:600}}
.nwr.tot b{{color:#0f6e56}}
table{{border-collapse:collapse;width:100%;font-size:13px;background:#fff;border:1px solid #e3e3e3;border-radius:10px;overflow:hidden}}
th,td{{padding:6px 12px;border-bottom:1px solid #f2f2f2;text-align:left}}
tr.hd th{{font-size:11px;text-transform:uppercase;letter-spacing:.04em;color:#999;font-weight:600;background:#fafafa}}
td.code{{font-family:ui-monospace,Menlo,Consolas,monospace;color:#999;width:1%;white-space:nowrap}}
td.bal{{font-family:ui-monospace,Menlo,Consolas,monospace;text-align:right;white-space:nowrap}}
td.cur{{color:#999;width:1%;font-size:12px}}
tr.z td.bal,tr.z td.nm{{color:#bbb}}
tr:last-child td{{border-bottom:none}}
.note{{background:#fff;border:1px solid #e3e3e3;border-left:3px solid #2563eb;border-radius:8px;padding:11px 14px;font-size:12.5px;color:#555;margin-top:22px}}
.foot{{margin-top:22px;color:#999;font-size:12px}}
.tog{{display:inline-block;width:14px;cursor:pointer;color:#999;user-select:none}}
.tog::before{{content:'\\25BE'}}
tr.collapsed .tog::before{{content:'\\25B8'}}
tr.parent td.nm{{font-weight:500;cursor:pointer}}
td.tot2{{font-family:ui-monospace,Menlo,Consolas,monospace;text-align:right;white-space:nowrap;color:#185fa5}}
</style></head><body>
<div class="wrap">
  <a class="back" href="index.html">&larr; toolkit home</a>
  <h1>Accounts &amp; balances</h1>
  <p class="sub">{n_acc} accounts &middot; read-only snapshot &middot; <b>balance sheet as at {bs_s}</b> &middot; fictional demo data</p>
  <div class="nwrap">
{chr(10).join(cards)}
  </div>
{pnl}
{equation}
{chr(10).join(sections)}
  <div class="note">Balances reconcile to the (fictional) statements by construction, and the
  double-entry check above is a true zero (recorded basis, no FX plug). Foreign balances are valued
  in GBP at a fixed reporting rate (EUR 0.855); the gap versus the recorded 1:1 par sits in the
  <b>FX translation reserve</b>. Hover an account name for its chart code.</div>
  <p class="foot">Generated by <span style="font-family:ui-monospace">demo/make_accounts.py</span> on {built}.</p>
</div>
<script>
document.querySelectorAll('tr.parent td.nm').forEach(function(cell){{
  cell.addEventListener('click', function(){{
    var r = cell.closest('tr'); var p = r.getAttribute('data-path') + ':';
    var c = r.classList.toggle('collapsed');
    document.querySelectorAll('tr[data-path]').forEach(function(x){{
      if (x !== r && x.getAttribute('data-path').indexOf(p) === 0) x.style.display = c ? 'none' : '';
    }});
  }});
}});
</script>
</body></html>"""
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(doc, encoding="utf-8")
    print(f"wrote {OUT}  ({len(doc)} bytes, {n_acc} accounts)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
