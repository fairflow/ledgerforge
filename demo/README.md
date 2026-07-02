# ledgerforge demo

A public, self-contained showcase of the engine — entirely fictional data, safe to run and publish.

## The accounts demo (statements → categorised book → balance sheet)

[`build_demo.py`](build_demo.py) runs the whole pipeline end to end with the real engine:

1. **parse** fictional OFX statements (`ledgerforge.parsers.parse_ofx`)
2. **categorise** each transaction by rules (`ledgerforge.rules.categorise`, see [`data/rules.json`](data/rules.json))
3. **build** a double-entry GnuCash book (piecash)
4. **render** a balance-sheet / accounts page (`ledgerforge.report.accounts_html`)

```bash
python demo/build_demo.py
# -> demo/build/demo.gnucash   (the book)
# -> demo/site/index.html      (the accounts page)
```

The result is a clean, collapsible balance sheet — net worth £8,309.75 across a current account,
savings, and cash, with expenses grouped by category. All figures are fictional.

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
