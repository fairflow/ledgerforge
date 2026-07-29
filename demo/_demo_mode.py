"""Build mode for the demo pages: static by default, save-to-server on request.

The demo exists to be *published*, so it must work with no Python behind it —
shared hosting, GitHub Pages, or a bare `file://` open. That is the default
build, and in it the toolkit's "Save to server" buttons become client-side
downloads of the identical JSON. Everything genuinely interesting about the
pages (editing tokens, moving them between accounts, the over-broad-token
guard, Generate text / Copy) is already pure browser JavaScript and is
unaffected.

The real toolkit, driven by `ledgerforge.serve`, does have a save endpoint. To
build pages that talk to it:

    python demo/build_demo.py --local
    LEDGERFORGE_DEMO_LOCAL=1 python demo/make_editor.py   # one page

Both write to the same `demo/site/`, so whichever you built last is what gets
served. The published demo should always be a default (static) build.
"""
from __future__ import annotations

import os

ENV_VAR = "LEDGERFORGE_DEMO_LOCAL"

_TRUTHY_OFF = ("", "0", "false", "no", "off")


def local_mode() -> bool:
    """True when building pages that POST to the ledgerforge dev server."""
    return os.environ.get(ENV_VAR, "").strip().lower() not in _TRUTHY_OFF


def static_mode() -> bool:
    """True when building for hosting with no save backend (the default)."""
    return not local_mode()


# ── Banner ────────────────────────────────────────────────────────────────────

BANNER_CSS = """
.lfdemo{background:#fffbea;border-bottom:1px solid #efdfa4;color:#6b5900;
  padding:8px 16px;font-size:12.5px;line-height:1.55}
.lfdemo b{color:#584a00}
.lfdemo a{color:#6b5900;font-weight:600}
"""

_BANNER = (
    '<div class="lfdemo"><b>Public demo &mdash; every figure here is fictional.</b> '
    "Nothing is saved to a server: use <b>Download</b>, or <b>Generate text</b> then "
    "<b>Copy</b>, to take your edits away. "
    '<a href="https://github.com/fairflow/ledgerforge">How it works &rarr;</a></div>'
)


def banner() -> str:
    """The demo banner. Omitted for local builds, which are not a public demo."""
    return _BANNER if static_mode() else ""


def banner_css() -> str:
    return BANNER_CSS if static_mode() else ""


# ── Client-side download helper ───────────────────────────────────────────────

DOWNLOAD_JS = """
function lfDownload(name,text){
  try{
    var b=new Blob([text],{type:"application/json;charset=utf-8"});
    var u=URL.createObjectURL(b);
    var a=document.createElement("a");
    a.href=u;a.download=name;a.style.display="none";
    document.body.appendChild(a);a.click();document.body.removeChild(a);
    setTimeout(function(){URL.revokeObjectURL(u);},1500);
    return true;
  }catch(e){return false;}
}
"""


def download_js() -> str:
    return DOWNLOAD_JS if static_mode() else ""


def save_button(btn_id: str, server_label: str = "Save to server",
                static_label: str = "Download JSON") -> str:
    """The primary save button, labelled for whichever mode we are building."""
    label = server_label if local_mode() else static_label
    return f'<button id="{btn_id}">{label}</button>'
