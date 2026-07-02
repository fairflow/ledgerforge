# ledgerforge demo

A public, self-contained showcase of the engine — entirely fictional data, safe to run and publish.

## The full toolkit (statements → categorised book → four tool pages)

[`build_demo.py`](build_demo.py) runs the whole pipeline end to end with the real engine:

1. **parse** fictional OFX statements — current, savings, credit card, and a EUR account
   (`ledgerforge.parsers.parse_ofx`)
2. **categorise** each transaction by rules (`ledgerforge.rules.categorise`, see [`data/rules.json`](data/rules.json))
3. **build** a multi-currency double-entry GnuCash book with chart codes and FX prices
   (piecash + `ledgerforge.book.set_fx_prices`)
4. **generate** the four toolkit pages into `demo/site/`:

| Page | What it shows |
|---|---|
| `index.html` | the toolkit **home** — tool cards, workflow, commands, trust & limits |
| `accounts.html` | **accounts & balances** — LIQUID/TOTAL net-worth cards per currency, P&L, the accounting equation with FX translation reserve and a true double-entry check, and a collapsible account tree |
| `edit_rules.html` | the **rules editor** — edit/move/delete/add match-tokens, rename accounts, generate a paste-back delta |
| `unspec_assign.html` | the **unspecified assigner** — one card per payee no rule catches yet, with suggested token + account and an over-broad-token guard |

```bash
python demo/build_demo.py
# -> demo/build/demo.gnucash   (the book)
# -> demo/site/*.html          (the toolkit)
```

These duplicate the design of the private household toolkit exactly — same pages, same workflow —
with fictional data. The books balance by construction (the double-entry check on the accounts page
is a true zero).

### Serving it as a web service (DDEV)

The generated `demo/site/` is a static page you can serve any way you like. With
[DDEV](https://ddev.com) (as the fairflow sites are run):

```bash
cd demo
ddev start            # -> https://ledgerforge-demo.ddev.site/
```

`ddev config` here is already set (project `ledgerforge-demo`, docroot `site`, type `php`). The first
`ddev start` needs your password once, to add the hostname to `/etc/hosts`.

Or serve it with the engine's own LAN-gated server, no DDEV needed:

```bash
python -c "from ledgerforge.serve import run; run('demo/site', 'demo/site')"
# -> http://localhost:8765/
```

## Plaid sandbox dress-rehearsal

[`plaid_sandbox.py`](plaid_sandbox.py) walks the full open-banking fetch flow against Plaid's
**Sandbox** — a fake bank, read-only, no real accounts. See the credentials note below.

```bash
cp demo/plaid.example.toml demo/plaid_secrets.toml     # add your own sandbox keys
python demo/plaid_sandbox.py
```

Free sandbox keys: <https://dashboard.plaid.com/developers/keys>. `demo/plaid_secrets.toml` is
git-ignored — your keys never enter the repo.
