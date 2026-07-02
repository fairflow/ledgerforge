"""Generate the 'assign every Unspecified payee' page -> demo/site/unspec_assign.html.

Exact duplicate of the household toolkit's assigner design: one card per payee the current rules
leave Unspecified, with a cleaned suggested match token, a best-guess account, the dated
transactions it came from, an over-broad-token guard, and Save-to-server / Generate-text / Copy.
Data prep here is the demo-simple version: parse the fictional statements with the engine and keep
whatever categorise() misses.

Run:  python demo/make_unspec.py
"""
from __future__ import annotations

import json
import re
from collections import defaultdict
from decimal import Decimal
from pathlib import Path

from ledgerforge.parsers import parse_ofx
from ledgerforge.rules import categorise, normalise

HERE = Path(__file__).parent
OUT = HERE / "site/unspec_assign.html"

ACCOUNTS = [  # (registry id, short source label, statement file, unspecified-eligible?)
    ("demo-current", "Current", HERE / "data/statements/current.ofx", True),
    ("demo-savings", "Savings", HERE / "data/statements/savings.ofx", True),
    ("demo-card", "Credit Card", HERE / "data/statements/card.ofx", True),
    ("demo-euro", "Euro Account", HERE / "data/statements/euro.ofx", False),  # all spend -> Holiday EUR
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
    """Keyword best-guess (token, account) for a payee — the demo-generic subset."""
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


def main() -> int:
    rules = json.loads((HERE / "data/rules.json").read_text())["rules"]

    rev: dict[str, dict] = defaultdict(lambda: {"count": 0, "total": Decimal(0), "accts": set(), "txns": []})
    ALLDESC: dict[str, int] = defaultdict(int)
    for aid, src, path, eligible in ACCOUNTS:
        for t in parse_ofx(path.read_text())[0]:
            dn = normalise(t["desc"])
            ALLDESC[dn] += 1
            if not eligible:
                continue
            if categorise(t["desc"], rules):
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

    suggested = sum(1 for r in rows if r["acct"])
    print(f"rows: {len(rows)}   pre-suggested: {suggested}   blank: {len(rows) - suggested}")

    TEMPLATE = r"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Assign unspecified payees</title>
<style>
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Arial,sans-serif;margin:0;color:#1a1a1a;background:#fff;font-size:14px}
.bar{position:sticky;top:0;background:#fff;border-bottom:1px solid #ddd;padding:10px 16px;display:flex;gap:10px;align-items:center;flex-wrap:wrap;z-index:5}
.bar .count{color:#555;font-size:13px}
.bar input{font-size:13px;padding:5px 8px;border:1px solid #ccc;border-radius:6px}
button{font-size:13px;padding:6px 12px;border:1px solid #2563eb;background:#2563eb;color:#fff;border-radius:6px;cursor:pointer}
button.sec{background:#fff;color:#2563eb}
.note{padding:10px 16px;color:#555;font-size:12px;line-height:1.6}
.note b{color:#111}
#out{width:calc(100% - 32px);height:200px;margin:0 16px;font-family:ui-monospace,Menlo,Consolas,monospace;font-size:12px;box-sizing:border-box;display:none;border:1px solid #ccc;border-radius:6px;padding:8px}
.wrap{padding:0 16px 60px}
.ur{padding:7px 0;border-bottom:1px solid #eee}
.ur.skip{opacity:.45}
.ur.need .ud{color:#b45309}
.ud{font-size:12px;color:#555;margin-bottom:4px;word-break:break-word}
.ud b{color:#111;font-weight:600;font-variant-numeric:tabular-nums}
.uf{display:flex;gap:8px;flex-wrap:wrap}
.uf input{font-size:12px;font-family:ui-monospace,Menlo,Consolas,monospace;padding:5px 7px;border:1px solid #ccc;border-radius:6px}
.ut{width:240px;max-width:100%}
.ua{width:290px;max-width:100%}
.usrc{font-size:11px;color:#0f6e56;margin-top:3px}
.udet{font-size:11px;color:#999;margin-top:2px;font-family:ui-monospace,Menlo,Consolas,monospace;line-height:1.5}
</style></head><body>
<div class="bar">
  <strong>Assign unspecified payees</strong>
  <span class="count"><span id="u-as">0</span> assigned · <span id="u-sk">0</span> blank · __N__ total</span>
  <input id="u-filter" placeholder="filter…">
  <span style="flex:1"></span>
  <button id="u-save">Save to server</button>
  <button id="u-gen" class="sec">Generate text</button>
  <button id="u-copy" class="sec">Copy</button>
  <span id="u-saved" style="font-size:12px;color:#0f6e56"></span>
</div>
<div class="note">Each row: the payee (times seen · signed total), the <b style="color:#0f6e56">source account(s)</b> it came from, and the dated transactions — so you can place it. Set a <b>token</b> (what will match — pick a distinctive chunk, not 2–3 letters) and an <b>account</b>; clear the account to skip a payee. When done, click <b>Save to server</b> (needs the ledgerforge dev server) — the Generate/Copy buttons work anywhere.</div>
<textarea id="out" readonly></textarea>
<div class="wrap"><div id="u-list"></div></div>
<script>
var DATA=__DATA__, ACCTS=__ACCTS__, ALLDESC=__ALLDESC__;
var list=document.getElementById("u-list");
var dl=document.createElement("datalist");dl.id="ua-list";ACCTS.forEach(function(a){var o=document.createElement("option");o.value=a;dl.appendChild(o);});list.appendChild(dl);
function money(n){return (n<0?"-":"")+"£"+Math.abs(n).toLocaleString("en-GB",{minimumFractionDigits:2,maximumFractionDigits:2});}
DATA.forEach(function(r,i){
  var row=document.createElement("div");row.className="ur"+(r.acct?"":" need");row.dataset.i=i;
  var d=document.createElement("div");d.className="ud";
  var meta=document.createElement("b");meta.textContent=r.c+"× · "+money(r.t)+"   ";
  d.appendChild(meta);d.appendChild(document.createTextNode(r.d));
  var sc=document.createElement("div");sc.className="usrc";sc.textContent="from "+(r.src||[]).join(", ");d.appendChild(sc);
  if(r.txns&&r.txns.length){var dt=document.createElement("div");dt.className="udet";var L=r.txns.slice(0,8).map(function(x){return x.d+"&nbsp;&nbsp;"+money(x.a)+"&nbsp;&nbsp;"+x.s;});if(r.txns.length>8)L.push("…+"+(r.txns.length-8)+" more");dt.innerHTML=L.join("<br>");d.appendChild(dt);}
  var f=document.createElement("div");f.className="uf";
  var ut=document.createElement("input");ut.className="ut";ut.value=r.tok;ut.setAttribute("aria-label","token");
  var ua=document.createElement("input");ua.className="ua";ua.value=r.acct;ua.setAttribute("list","ua-list");ua.placeholder="account…";ua.setAttribute("aria-label","account");
  f.appendChild(ut);f.appendChild(ua);
  if(r.c===1&&r.txns&&r.txns.length===1&&r.txns[0].aid){
    var rb=document.createElement("button");rb.className="sec";rb.type="button";rb.textContent="Route exact";
    rb.addEventListener("click",(function(rr,rrow,rua,rrb){return function(){
      var acct=rua.value.trim();if(!acct){alert("Set an account first");return;}
      var txn=rr.txns[0];rrb.disabled=true;rrb.textContent="saving…";
      fetch("/save/route_txn",{method:"POST",headers:{"Content-Type":"application/json"},
        body:JSON.stringify({acct:txn.aid,date:txn.d,amount:txn.a.toFixed(2),to:acct})})
      .then(function(res){return res.json();})
      .then(function(){rrb.textContent="Saved ✓";rrow.style.opacity="0.4";})
      .catch(function(e){rrb.disabled=false;rrb.textContent="Route exact";alert("Failed: "+e);});
    };})(r,row,ua,rb));
    f.appendChild(rb);
  }
  row.appendChild(d);row.appendChild(f);list.appendChild(row);
  r._t=ut;r._a=ua;
  ua.addEventListener("input",function(){row.classList.toggle("skip",!ua.value.trim());if(ua.value.trim())row.classList.remove("need");refresh();});
});
function refresh(){var as=0,sk=0;DATA.forEach(function(r){if(r._a.value.trim()&&r._t.value.trim())as++;else sk++;});document.getElementById("u-as").textContent=as;document.getElementById("u-sk").textContent=sk;}
refresh();
document.getElementById("u-filter").addEventListener("input",function(e){var q=e.target.value.toUpperCase();Array.prototype.forEach.call(list.querySelectorAll(".ur"),function(row){var r=DATA[row.dataset.i];row.style.display=(r.d.indexOf(q)>=0||r.tok.toUpperCase().indexOf(q)>=0)?"":"none";});});
function buildText(){
  var map={};DATA.forEach(function(r){var t=r._t.value.trim(),a=r._a.value.trim();if(!t||!a)return;var k=a+"||"+t.toUpperCase();if(!map[k])map[k]={a:a,t:t};});
  var byA={};Object.keys(map).forEach(function(k){var m=map[k];(byA[m.a]=byA[m.a]||[]).push(m.t);});
  var lines=Object.keys(byA).sort().map(function(a){return "  - "+a+"  <-  "+byA[a].map(function(x){return '"'+x+'"';}).join(", ");});
  var skipped=DATA.filter(function(r){return !(r._a.value.trim()&&r._t.value.trim());}).length;
  return "Unspecified assignments (add these match tokens to demo/data/rules.json, merging into each account's rule):\n\n"+(lines.length?lines.join("\n"):"  (none)")+"\n\nLeft unassigned: "+skipped+" payees.\nAfter applying, re-run demo/build_demo.py.";
}
function matchCount(tok){tok=(tok||"").toUpperCase();if(!tok)return 0;var n=0;for(var k in ALLDESC){if(k.indexOf(tok)>=0)n+=ALLDESC[k];}return n;}
function guardOK(){var bad=[];DATA.forEach(function(r){var t=r._t.value.trim(),a=r._a.value.trim();if(!t||!a)return;var mc=matchCount(t);if(mc>r.c+5)bad.push('"'+t+'" matches '+mc+' transactions, but this payee has only '+r.c);});if(bad.length){alert("Some tokens are too broad — they would grab unrelated transactions:\n\n"+bad.join("\n")+"\n\nNarrow each to a distinctive chunk (a surname, shop name, or reference), or clear it to skip — then try again.");return false;}return true;}
var out=document.getElementById("out");
document.getElementById("u-gen").addEventListener("click",function(){if(!guardOK())return;out.value=buildText();out.style.display="block";out.focus();out.select();});
document.getElementById("u-copy").addEventListener("click",function(){if(!guardOK())return;if(!out.value)out.value=buildText();out.style.display="block";var tmp=document.createElement("textarea");tmp.value=out.value;tmp.style.cssText="position:fixed;opacity:0;top:0;left:0";document.body.appendChild(tmp);tmp.focus();tmp.select();document.execCommand("copy");document.body.removeChild(tmp);this.textContent="Copied";var b=this;setTimeout(function(){b.textContent="Copy";},1200);});
function buildJSON(){
  var map={};DATA.forEach(function(r){var t=r._t.value.trim(),a=r._a.value.trim();if(!t||!a)return;var k=a+"||"+t.toUpperCase();if(!map[k])map[k]={a:a,t:t};});
  var byA={};Object.keys(map).forEach(function(k){var m=map[k];(byA[m.a]=byA[m.a]||[]).push(m.t);});
  return {assignments:Object.keys(byA).sort().map(function(a){return {account:a,tokens:byA[a]};}),skipped:DATA.filter(function(r){return !(r._a.value.trim()&&r._t.value.trim());}).length};
}
document.getElementById("u-save").addEventListener("click",function(){if(!guardOK())return;var btn=this,s=document.getElementById("u-saved");s.textContent="saving…";var payload=buildJSON();fetch("/save/assignments",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(payload)}).then(function(r){return r.json();}).then(function(j){var n=payload.assignments.reduce(function(acc,a){return acc+a.tokens.length;},0);s.textContent="✓ "+n+" assignment"+(n===1?"":"s")+" saved";s.style.fontWeight="bold";DATA.forEach(function(r){if(r._t.value.trim()&&r._a.value.trim()){r._t.disabled=true;r._a.disabled=true;var row=r._t.closest(".ur");if(row)row.style.opacity="0.4";}});btn.disabled=true;btn.textContent="Saved";}).catch(function(e){s.textContent="";alert("Save failed — is the dev server running? "+e);});});
</script></body></html>"""

    doc = (TEMPLATE
           .replace("__DATA__", json.dumps(rows, ensure_ascii=False))
           .replace("__ACCTS__", json.dumps(accts, ensure_ascii=False))
           .replace("__ALLDESC__", json.dumps(dict(ALLDESC), ensure_ascii=False))
           .replace("__N__", str(len(rows))))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(doc, encoding="utf-8")
    print(f"wrote {OUT}  ({len(doc)} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
