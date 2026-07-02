"""Generate the demo toolkit HOME PAGE -> demo/site/index.html.

Exact duplicate of the household toolkit's hub design: cards for each tool page, the workflow
steps, the common commands, and the trust & limits note — adapted to the fictional demo ledger.
Self-contained static HTML with RELATIVE links, so it works straight off the filesystem (file://).

Run:  python demo/make_home.py        (last, after the other make_* scripts)
"""
from __future__ import annotations

import html
from datetime import date
from pathlib import Path

HERE = Path(__file__).parent
SITE = HERE / "site"
OUT = SITE / "index.html"

# Interactive tool pages: (filename, title, tag, tag-class, one-line, longer help). Only those that
# actually exist on disk are shown as live links; the rest render as "not generated yet".
TOOLS = [
    ("edit_rules.html", "Edit rules", "categoriser", "b",
     "The rules editor — tune how payees map to accounts.",
     "Account-grouped view of every categorisation rule. Edit / move / delete / add the match-tokens, "
     "rename or delete an account, and tick <b>done</b> to collapse the ones you've checked. When you "
     "finish, click <b>Generate</b> and apply the delta to <span class=mono>demo/data/rules.json</span>, "
     "then rebuild."),
    ("unspec_assign.html", "Assign unspecified", "categoriser", "b",
     "Clear the pile of payees no rule has caught yet.",
     "Each card is a payee currently landing in <span class=mono>Unspecified</span>. Give it a token "
     "and a destination account (or clear to skip), then apply the result to the rules. Regenerated "
     "every build as the pile shrinks."),
    ("accounts.html", "Accounts & balances", "ledger", "g",
     "Every account and its final balance.",
     "A read-only snapshot straight from the book: the full chart of accounts with each account's "
     "closing balance, grouped by section, with chart codes on hover, a per-currency net-worth "
     "summary, the P&amp;L, and the accounting equation. Regenerated on every build."),
]

# Reference: the common command runs.
COMMANDS = [
    ("Build everything", "python demo/build_demo.py", "Parses the fictional statements, categorises by rules, builds the GnuCash book, regenerates all these pages."),
    ("Serve locally", "ddev start", "Serve this site at https://ledgerforge-demo.ddev.site/ (from demo/)."),
    ("Serve via the engine", "python -c \"from ledgerforge.serve import run; run('demo/site', 'demo/pending')\"", "The LAN-gated dev server; enables the pages' Save-to-server buttons."),
    ("Engine tests", "python -m pytest tests -q", "The ledgerforge test suite."),
]

# How the pieces fit together (the workflow), shown as numbered steps.
STEPS = [
    ("Download", "Export a statement (OFX) into <span class=mono>demo/data/statements/</span> — here they're fictional."),
    ("Register", "Add the account to the registry in <span class=mono>demo/build_demo.py</span> so the builder knows its currency, type and file."),
    ("Build", "<span class=mono>build_demo.py</span> parses everything, categorises by the rules, and reconciles every account to its closing balance."),
    ("Review", "Use the two categoriser pages above to catch anything in <b>Unspecified</b> or a wrong rule."),
    ("Rebuild", "Re-run the builder — balances always reconcile by construction, so you're only ever improving the <i>classification</i>, never breaking the books."),
]


def card(fn: str, title: str, tag: str, tagcls: str, oneline: str, helptext: str) -> str:
    live = (SITE / fn).exists()
    inner = (f'<div class="t">{html.escape(title)} <span class="tag {tagcls}">{html.escape(tag)}</span></div>'
             f'<div class="d">{oneline}</div><div class="help">{helptext}</div>')
    if live:
        return f'<a class="card" href="{fn}">{inner}</a>'
    return f'<div class="card off">{inner}<div class="d" style="color:#b00">not generated yet — run its make_* script</div></div>'


def main() -> int:
    cards = "\n".join(card(*t) for t in TOOLS)
    steps = "\n".join(f'<li><b>{html.escape(t)}.</b> {d}</li>' for t, d in STEPS)
    cmds = "\n".join(
        f'<tr><td class="cn">{html.escape(n)}</td><td><code>{html.escape(c)}</code></td>'
        f'<td class="cd">{html.escape(d)}</td></tr>' for n, c, d in COMMANDS)
    built = date.today().isoformat()
    doc = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>ledgerforge demo toolkit</title>
<style>
body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Arial,sans-serif;margin:0;background:#f6f7f9;color:#1a1a1a;line-height:1.5}}
.wrap{{max-width:760px;margin:0 auto;padding:40px 20px 70px}}
h1{{font-size:25px;font-weight:650;margin:0 0 4px}}
h2{{font-size:15px;font-weight:650;margin:34px 0 12px;color:#333;text-transform:uppercase;letter-spacing:.04em}}
.sub{{color:#666;font-size:14px;margin:0 0 6px}}
.cards{{display:grid;gap:14px}}
a.card,.card{{display:block;text-decoration:none;color:inherit;background:#fff;border:1px solid #e3e3e3;border-radius:12px;padding:16px 18px;transition:border-color .12s,box-shadow .12s}}
a.card:hover{{border-color:#2563eb;box-shadow:0 1px 8px rgba(37,99,235,.13)}}
.card.off{{opacity:.7}}
.t{{font-size:16px;font-weight:650;display:flex;align-items:center;gap:8px}}
.tag{{font-size:11px;font-weight:500;color:#2563eb;background:#eaf1fe;border-radius:5px;padding:2px 7px}}
.tag.g{{color:#0f6e56;background:#e1f5ee}}
.d{{color:#555;font-size:13px;margin-top:5px}}
.help{{color:#666;font-size:12.5px;margin-top:8px;border-top:1px solid #f0f0f0;padding-top:8px}}
ol.steps{{margin:0;padding-left:18px;color:#444;font-size:13.5px}}
ol.steps li{{margin:7px 0}}
table{{border-collapse:collapse;width:100%;font-size:13px;background:#fff;border:1px solid #e3e3e3;border-radius:10px;overflow:hidden}}
td{{padding:9px 12px;border-bottom:1px solid #f0f0f0;vertical-align:top}}
tr:last-child td{{border-bottom:none}}
.cn{{font-weight:600;white-space:nowrap;width:1%}}
.cd{{color:#777}}
code,.mono{{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:12px}}
code{{background:#f1f2f4;border-radius:5px;padding:1px 5px}}
.note{{background:#fff;border:1px solid #e3e3e3;border-left:3px solid #2563eb;border-radius:8px;padding:12px 14px;font-size:13px;color:#444}}
.foot{{margin-top:30px;color:#999;font-size:12px;line-height:1.6}}
</style></head><body>
<div class="wrap">
  <h1>ledgerforge demo toolkit</h1>
  <p class="sub">The hub for the demo tools — <b>everything here is fictional data.</b></p>

  <h2>Tools</h2>
  <div class="cards">
{cards}
    <div class="card off">
      <div class="t">The book <span class="tag g">GnuCash</span></div>
      <div class="d">The book of record — opens in GnuCash, not the browser:</div>
      <div class="help mono">demo/build/demo.gnucash</div>
    </div>
  </div>

  <h2>How it fits together</h2>
  <ol class="steps">
{steps}
  </ol>

  <h2>Commands</h2>
  <table>
{cmds}
  </table>

  <h2>Trust &amp; limits</h2>
  <div class="note">
    <b>Balances</b> reconcile to the statements by construction — high confidence.
    <b>Categorisation</b> depends on the rules — that's what the two pages above are for.
    Cross-currency totals are valued at a fixed reporting rate. GnuCash stays the source of truth;
    this is a demonstration of the <a href="https://github.com/fairflow/ledgerforge">ledgerforge</a>
    engine with entirely fictional data.
  </div>

  <p class="foot">Self-contained, relative links — keep this file alongside the tool pages (it works via
  file://, no server). Generated by <span class="mono">demo/make_home.py</span> on {built}.</p>
</div>
</body></html>"""
    SITE.mkdir(parents=True, exist_ok=True)
    OUT.write_text(doc, encoding="utf-8")
    print(f"wrote {OUT}  ({len(doc)} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
