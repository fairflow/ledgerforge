# ledgerforge demo toolkit — Svelte web app

A static [SvelteKit](https://svelte.dev/) app that reimplements the ledgerforge review toolkit
(the same pages as the private household toolkit and the Python-generated `demo/site/`), rendered
from data the **real engine** exported. Everything is fictional demo data; it deploys to GitHub Pages
with no backend.

Pages:

| Route | What it is |
|---|---|
| `/` | toolkit home — tool cards, workflow, commands, downloadable GnuCash book |
| `/accounts/` | **accounts & balances** — an in-browser book viewer: LIQUID/TOTAL/per-currency net-worth cards, P&L, the accounting equation with FX translation reserve, a true double-entry residual check, and a collapsible coded account tree |
| `/rules/` | **edit rules** — account-grouped categorisation-rule editor (edit/move/delete/add tokens, rename/delete accounts, generate & download the delta) |
| `/unspecified/` | **assign unspecified** — one row per uncaught payee, with an over-broad-token guard and "Route exact" |

## The engine is the source of truth

`scripts/export_data.py` runs the real `ledgerforge` engine over the fictional demo book +
statements and writes three JSON files the app renders from — it mirrors the data-prep of
`demo/make_accounts.py`, `demo/make_editor.py` and `demo/make_unspec.py` exactly:

```
src/lib/data/book.json     chart of accounts + balances   (accounts page)
src/lib/data/rules.json    grouped categorisation rules   (rules editor)
src/lib/data/unspec.json   payees no rule catches yet      (unspecified assigner)
```

The accounts page **recomputes** the balance sheet, P&L and accounting equation in the browser
(`src/lib/book.ts`), so it is a genuine book viewer: feed it another `book.json` and it re-derives
every figure.

## Develop

Needs **Node 20+** (see `.nvmrc`). Regenerate the data after rebuilding the demo book, then run:

```bash
python ../build_demo.py                 # (re)build the fictional GnuCash book
python scripts/export_data.py           # export book/rules/unspec JSON  (needs the ledger venv)
npm install
npm run dev                             # http://localhost:5173
```

## Build & deploy

```bash
npm run build                           # -> build/  (static; BASE_PATH='' serves at root)
BASE_PATH=/ledgerforge npm run build    # for GitHub Pages under /ledgerforge/
```

`.github/workflows/pages.yml` builds and publishes `build/` to GitHub Pages on every push to
`main` that touches `demo/web/`. Enable once in the repo's **Settings → Pages → Source: GitHub
Actions**; it then serves at <https://fairflow.github.io/ledgerforge/>.
