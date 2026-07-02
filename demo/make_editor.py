"""Generate the standalone rules editor page from demo/data/rules.json.

Exact duplicate of the household toolkit's rules-editor design: account-grouped, one match-token
per line; per token edit (with regex toggle) / move / delete; per account rename / delete-account /
add-token, a 'done' checkbox that collapses reviewed groups, a filter box, and Save-to-server /
Generate-text / Copy for the paste-back delta block.

Run:  python demo/make_editor.py
"""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).parent
OUT = HERE / "site/edit_rules.html"


def main() -> int:
    rules = json.loads((HERE / "data/rules.json").read_text())["rules"]

    G = [{"a": r["account"], "m": r.get("match", []), "r": r.get("regex", [])} for r in rules]
    EXTRAS = {
        "Expenses", "Income", "Assets", "Liabilities",
        "Expenses:Miscellaneous", "Expenses:Books", "Expenses:DIY", "Expenses:Shopping",
        "Expenses:Garden", "Income:Other Income", "Assets:Cash",
    }
    ACCTS = sorted({g["a"] for g in G} | EXTRAS)

    TEMPLATE = r"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Edit categorisation rules</title>
<style>
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Arial,sans-serif;margin:0;color:#1a1a1a;background:#fff;font-size:14px}
.bar{position:sticky;top:0;background:#fff;border-bottom:1px solid #ddd;padding:10px 16px;display:flex;gap:10px;align-items:center;flex-wrap:wrap;z-index:5}
.bar .count{color:#555;font-size:13px}
.bar input[type=text]{font-size:13px;padding:5px 8px;border:1px solid #ccc;border-radius:6px}
.bar label{font-size:13px;color:#555;display:inline-flex;align-items:center;gap:5px}
button{font-size:13px;padding:6px 12px;border:1px solid #2563eb;background:#2563eb;color:#fff;border-radius:6px;cursor:pointer}
button.sec{background:#fff;color:#2563eb}
button.mini,button.tb{font-size:12px;padding:3px 9px;border:1px solid #bbb;background:#fff;color:#333}
button.tb.on,button.mini.on{background:#fde2e2;border-color:#e0a0a0;color:#a32d2d}
.note{padding:10px 16px;color:#555;font-size:12px;line-height:1.6}.note b{color:#111}
#out{width:calc(100% - 32px);height:200px;margin:0 16px;font-family:ui-monospace,Menlo,Consolas,monospace;font-size:12px;box-sizing:border-box;display:none;border:1px solid #ccc;border-radius:6px;padding:8px}
.wrap{padding:0 16px 60px}
.grp{border:1px solid #e3e3e3;border-radius:10px;margin:10px 0;padding:8px 12px 6px}
.grp.adel{opacity:.45}
.grp.done{opacity:.6;background:#f6f8f6}
.grp.done .body,.grp.done .rev,.grp.done .addrow{display:none}
.gh{display:flex;align-items:center;gap:8px;flex-wrap:wrap;border-bottom:1px solid #eee;padding-bottom:6px;margin-bottom:4px}
.an{font-size:14px;font-weight:600;font-family:ui-monospace,Menlo,monospace}
.an.ren{color:#185fa5}
.cnt{font-size:11px;color:#999}
.tr{display:flex;align-items:center;gap:7px;padding:3px 0 3px 2px}
.tr.tdel .tt{opacity:.4;text-decoration:line-through}
.tt{flex:1;min-width:0;font-size:13px;word-break:break-word}
.tt.edt{color:#185fa5}.tt.addt{color:#1d9e75}
.tt .rx{color:#888;font-family:ui-monospace,Menlo,monospace}
.bd{font-size:12px;color:#185fa5;font-family:ui-monospace,Menlo,monospace}
.rev{display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin:2px 0 6px 4px}
.in{font-size:12px;font-family:ui-monospace,Menlo,Consolas,monospace;padding:5px 7px;border:1px solid #ccc;border-radius:6px}
.rl{font-size:12px;color:#555;display:inline-flex;align-items:center;gap:5px}
.addrow{margin-top:4px}
</style></head><body>
<div class="bar">
  <strong>Edit rules</strong>
  <span class="count"><span id="ed-ch">0</span> changes · <span id="ed-dn">0</span> done · __N__ accounts</span>
  <input type="text" id="ed-filter" placeholder="filter…">
  <label><input type="checkbox" id="ed-hidedone"> hide done</label>
  <span style="flex:1"></span>
  <button id="ed-save">Save to server</button>
  <button id="ed-gen" class="sec">Generate text</button>
  <button id="ed-copy" class="sec">Copy</button>
  <span id="ed-saved" style="font-size:12px;color:#0f6e56"></span>
</div>
<div class="note">One token per line. <b>edit</b> a token (tick <b>regex</b> for a pattern), <b>move</b> it to another account, <b>×</b> delete it, <b>+ add</b> a new one. On the heading: <b>rename</b> / <b>delete account</b>, and tick <b>done</b> to collapse a reviewed account. When finished, <b>Generate text → Copy</b> and paste back into the chat.</div>
<textarea id="out" readonly></textarea>
<div class="wrap"><div id="ed-list"></div></div>
<script>
var G=__DATA__, ACCTS=__ACCTS__;
var list=document.getElementById("ed-list"), cards=[];
var dl=document.createElement("datalist");dl.id="ed-accts";ACCTS.forEach(function(a){var o=document.createElement("option");o.value=a;dl.appendChild(o);});document.body.appendChild(dl);
var aDel={},aRen={},tDel={},tMov={},tEdit={},aAdd={},aDone={};
function mkbtn(t){var b=document.createElement("button");b.type="button";b.className="mini";b.textContent=t;return b;}
function mktb(t){var b=document.createElement("button");b.type="button";b.className="tb";b.textContent=t;return b;}
function mkin(){var i=document.createElement("input");i.type="text";i.className="in";return i;}
function mkcb(){var c=document.createElement("input");c.type="checkbox";return c;}
function mklab(){var l=document.createElement("label");l.className="rl";return l;}
function tn(s){return document.createTextNode(s);}
function eff(gi){return aRen[gi]||G[gi].a;}
function toks(gi){var g=G[gi],a=[];(g.m||[]).forEach(function(t,j){a.push({t:t,g:false,key:gi+"m"+j});});(g.r||[]).forEach(function(t,j){a.push({t:t,g:true,key:gi+"r"+j});});return a;}
function dd(t,g){return g?"/"+t+"/":t;}
function setTT(el,t,g){el.textContent="";if(g){var s=document.createElement("span");s.className="rx";s.textContent="/"+t+"/";el.appendChild(s);}else el.textContent=t;}
G.forEach(function(g,gi){
  var card=document.createElement("div");card.className="grp";cards.push(card);
  var hd=document.createElement("div");hd.className="gh";
  var done=mkcb();done.title="mark reviewed (collapse)";
  var an=document.createElement("span");an.className="an";an.textContent=g.a;
  var cnt=document.createElement("span");cnt.className="cnt";cnt.textContent=toks(gi).length;
  var sp=document.createElement("span");sp.style.flex="1";
  var bren=mkbtn("rename"),bdel=mkbtn("delete account"),badd=mkbtn("+ add");
  hd.appendChild(done);hd.appendChild(an);hd.appendChild(cnt);hd.appendChild(sp);hd.appendChild(bren);hd.appendChild(bdel);hd.appendChild(badd);card.appendChild(hd);
  var rin=mkin();rin.value=g.a;rin.setAttribute("list","ed-accts");rin.style.display="none";rin.style.width="320px";rin.style.maxWidth="100%";card.appendChild(rin);
  var body=document.createElement("div");body.className="body";card.appendChild(body);
  toks(gi).forEach(function(x){renderTok(body,gi,x);});
  var arow=document.createElement("div");arow.className="rev addrow";var aci=mkin();aci.placeholder="new token";aci.style.width="240px";var arl=mklab(),arc=mkcb();arl.appendChild(arc);arl.appendChild(tn("regex"));var acf=mktb("add");arow.appendChild(aci);arow.appendChild(arl);arow.appendChild(acf);arow.style.display="none";card.appendChild(arow);
  done.addEventListener("change",function(){aDone[gi]=done.checked;card.classList.toggle("done",done.checked);applyFilter();refresh();});
  bren.addEventListener("click",function(){rin.style.display=rin.style.display==="none"?"block":"none";if(rin.style.display!=="none")rin.focus();});
  rin.addEventListener("input",function(){var v=rin.value.trim();if(v&&v!==g.a){aRen[gi]=v;an.textContent=v;an.classList.add("ren");}else{delete aRen[gi];an.textContent=g.a;an.classList.remove("ren");}refresh();});
  bdel.addEventListener("click",function(){if(aDel[gi]){delete aDel[gi];card.classList.remove("adel");bdel.classList.remove("on");bdel.textContent="delete account";}else{aDel[gi]=true;card.classList.add("adel");bdel.classList.add("on");bdel.textContent="account deleted";}refresh();});
  badd.addEventListener("click",function(){arow.style.display=arow.style.display==="none"?"flex":"none";if(arow.style.display!=="none")aci.focus();});
  function doAdd(){var v=aci.value.trim();if(!v)return;var g2=arc.checked;var it={t:v,g:g2};(aAdd[gi]=aAdd[gi]||[]).push(it);
    var tr=document.createElement("div");tr.className="tr";var tt=document.createElement("div");tt.className="tt addt";setTT(tt,v,g2);var xb=mktb("×");tr.appendChild(tt);tr.appendChild(xb);body.appendChild(tr);
    xb.addEventListener("click",function(){var k=aAdd[gi].indexOf(it);if(k>=0)aAdd[gi].splice(k,1);tr.remove();refresh();});
    aci.value="";arc.checked=false;aci.focus();refresh();}
  acf.addEventListener("click",doAdd);
  aci.addEventListener("keydown",function(e){if(e.key==="Enter"){e.preventDefault();doAdd();}});
  list.appendChild(card);
});
function renderTok(host,gi,x){
  var tr=document.createElement("div");tr.className="tr";
  var tt=document.createElement("div");tt.className="tt";setTT(tt,x.t,x.g);
  var bd=document.createElement("span");bd.className="bd";
  var be=mktb("edit"),bm=mktb("move"),bx=mktb("×");
  tr.appendChild(tt);tr.appendChild(bd);tr.appendChild(be);tr.appendChild(bm);tr.appendChild(bx);host.appendChild(tr);
  var erow=document.createElement("div");erow.className="rev";var ei=mkin();ei.value=x.t;ei.style.width="240px";var rl=mklab(),rc=mkcb();rc.checked=x.g;rl.appendChild(rc);rl.appendChild(tn("regex"));erow.appendChild(ei);erow.appendChild(rl);erow.style.display="none";host.appendChild(erow);
  var mrow=document.createElement("div");mrow.className="rev";var mi=mkin();mi.setAttribute("list","ed-accts");mi.placeholder="move to account…";mi.style.width="280px";mrow.appendChild(mi);mrow.style.display="none";host.appendChild(mrow);
  be.addEventListener("click",function(){erow.style.display=erow.style.display==="none"?"flex":"none";if(erow.style.display!=="none")ei.focus();});
  bm.addEventListener("click",function(){mrow.style.display=mrow.style.display==="none"?"flex":"none";if(mrow.style.display!=="none")mi.focus();});
  function edc(){var nt=ei.value.trim(),ng=rc.checked;if(nt&&(nt!==x.t||ng!==x.g)){tEdit[x.key]={t:nt,g:ng};setTT(tt,nt,ng);tt.classList.add("edt");}else{delete tEdit[x.key];setTT(tt,x.t,x.g);tt.classList.remove("edt");}refresh();}
  ei.addEventListener("input",edc);rc.addEventListener("change",edc);
  bx.addEventListener("click",function(){if(tDel[x.key]){delete tDel[x.key];tr.classList.remove("tdel");bx.classList.remove("on");}else{tDel[x.key]=true;tr.classList.add("tdel");bx.classList.add("on");}refresh();});
  mi.addEventListener("input",function(){var v=mi.value.trim();if(v&&v!==eff(gi)){tMov[x.key]=v;bd.textContent="→ "+v;}else{delete tMov[x.key];bd.textContent="";}refresh();});
}
function applyFilter(){var q=document.getElementById("ed-filter").value.toUpperCase();var hd=document.getElementById("ed-hidedone").checked;
  G.forEach(function(g,gi){var acc=eff(gi).toUpperCase();var tk=toks(gi).some(function(x){return dd(x.t,x.g).toUpperCase().indexOf(q)>=0;});var show=(q===""||acc.indexOf(q)>=0||tk);if(hd&&aDone[gi])show=false;cards[gi].style.display=show?"":"none";});}
function refresh(){var ch=0,dn=0;G.forEach(function(g,gi){if(aDone[gi])dn++;if(aDel[gi]){ch++;return;}if(aRen[gi])ch++;toks(gi).forEach(function(x){if(tDel[x.key])ch++;else if(tMov[x.key])ch++;else if(tEdit[x.key])ch++;});ch+=(aAdd[gi]||[]).length;});document.getElementById("ed-ch").textContent=ch;document.getElementById("ed-dn").textContent=dn;}
document.getElementById("ed-filter").addEventListener("input",applyFilter);
document.getElementById("ed-hidedone").addEventListener("change",applyFilter);
function buildText(){
  var dT=[],mT=[],eT=[],adT=[],rA=[],dA=[];
  G.forEach(function(g,gi){var acct=eff(gi);
    if(aDel[gi]){var kept=toks(gi).filter(function(x){return !tMov[x.key];}).map(function(x){return dd(x.t,x.g);});dA.push("  - "+acct+"   ["+kept.join(", ")+"]");toks(gi).forEach(function(x){if(tMov[x.key])mT.push('  - "'+dd(x.t,x.g)+'"  '+acct+"  ->  "+tMov[x.key]);});(aAdd[gi]||[]).forEach(function(it){adT.push('  - "'+dd(it.t,it.g)+'" ('+(it.g?"regex":"literal")+")  to  "+acct);});return;}
    if(aRen[gi])rA.push("  - "+g.a+"  ->  "+aRen[gi]);
    toks(gi).forEach(function(x){if(tDel[x.key])dT.push('  - "'+dd(x.t,x.g)+'"  from  '+acct);else if(tMov[x.key])mT.push('  - "'+dd(x.t,x.g)+'"  '+acct+"  ->  "+tMov[x.key]);else if(tEdit[x.key]){var e=tEdit[x.key];eT.push('  - "'+dd(x.t,x.g)+'" ('+(x.g?"regex":"literal")+')  ->  "'+dd(e.t,e.g)+'" ('+(e.g?"regex":"literal")+")  in  "+acct);}});
    (aAdd[gi]||[]).forEach(function(it){adT.push('  - "'+dd(it.t,it.g)+'" ('+(it.g?"regex":"literal")+")  to  "+acct);});
  });
  var dn=Object.keys(aDone).filter(function(k){return aDone[k];}).length;
  var s="Mapping review (account-grouped, token-level):\n\n";
  s+="DELETE TOKENS:\n"+(dT.length?dT.join("\n"):"  (none)")+"\n\n";
  s+="MOVE TOKENS:\n"+(mT.length?mT.join("\n"):"  (none)")+"\n\n";
  s+="EDIT TOKENS (text and/or literal<->regex):\n"+(eT.length?eT.join("\n"):"  (none)")+"\n\n";
  s+="ADD TOKENS:\n"+(adT.length?adT.join("\n"):"  (none)")+"\n\n";
  s+="RENAME ACCOUNTS:\n"+(rA.length?rA.join("\n"):"  (none)")+"\n\n";
  s+="DELETE ACCOUNTS:\n"+(dA.length?dA.join("\n"):"  (none)")+"\n\n";
  s+="("+dn+" accounts marked done.) Apply to demo/data/rules.json, then re-run demo/build_demo.py.";
  return s;
}
function buildJSON(){
  var moves=[],deletes=[],adds=[],edits=[],renames=[],deleteAccounts=[];
  G.forEach(function(g,gi){var acct=eff(gi);
    if(aDel[gi]){deleteAccounts.push(acct);
      toks(gi).forEach(function(x){if(tMov[x.key])moves.push({token:dd(x.t,x.g),from:acct,to:tMov[x.key]});});
      (aAdd[gi]||[]).forEach(function(it){adds.push({token:dd(it.t,it.g),account:acct,regex:!!it.g});});return;}
    if(aRen[gi])renames.push({from:g.a,to:aRen[gi]});
    toks(gi).forEach(function(x){
      if(tDel[x.key])deletes.push({token:dd(x.t,x.g),account:acct});
      else if(tMov[x.key])moves.push({token:dd(x.t,x.g),from:acct,to:tMov[x.key]});
      else if(tEdit[x.key]){var e=tEdit[x.key];edits.push({token:dd(x.t,x.g),account:acct,to:dd(e.t,e.g),regex:!!e.g});}});
    (aAdd[gi]||[]).forEach(function(it){adds.push({token:dd(it.t,it.g),account:acct,regex:!!it.g});});
  });
  return {moves:moves,deletes:deletes,adds:adds,edits:edits,renames:renames,deleteAccounts:deleteAccounts};
}
var out=document.getElementById("out");
document.getElementById("ed-gen").addEventListener("click",function(){out.value=buildText();out.style.display="block";out.focus();out.select();});
document.getElementById("ed-copy").addEventListener("click",function(){if(!out.value)out.value=buildText();out.style.display="block";out.select();try{navigator.clipboard.writeText(out.value);}catch(e){document.execCommand("copy");}var b=this;b.textContent="Copied";setTimeout(function(){b.textContent="Copy";},1200);});
document.getElementById("ed-save").addEventListener("click",function(){var s=document.getElementById("ed-saved");s.textContent="saving…";fetch("/save/rules",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({delta:buildJSON(),text:buildText()})}).then(function(r){return r.json();}).then(function(j){s.textContent="saved ✓ "+j.bytes+" bytes";}).catch(function(e){s.textContent="";alert("Save failed — is the dev server running? "+e);});});
refresh();
</script></body></html>"""

    doc = (TEMPLATE
           .replace("__DATA__", json.dumps(G, ensure_ascii=False))
           .replace("__ACCTS__", json.dumps(ACCTS, ensure_ascii=False))
           .replace("__N__", str(len(G))))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(doc, encoding="utf-8")
    print(f"wrote {OUT}  ({len(doc)} bytes)  accounts: {len(G)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
