# Getting started with ledgerforge

This is a walkthrough for going from "a folder of bank statements" to "a GnuCash book that
proves its own arithmetic". For the underlying model — what a GnuCash book is, why
double-entry is worth the trouble — read [docs/HOW_IT_WORKS.md](docs/HOW_IT_WORKS.md) first if
you haven't. This document is about running the thing.

One thing to be clear about up front: **ledgerforge is a library, not a command-line tool.**
There is no `ledgerforge build` command you point at a folder. You write a small driver script
that imports the engine's pieces (parsers, `categorise`, transfer detection, overrides, piecash)
and wires them together for your own chart of accounts. [`demo/build_demo.py`](demo/build_demo.py)
is that script for the bundled demo, and it is the template to copy for a real entity.

## 1. Install

```bash
python -m venv .venv
.venv/bin/pip install -e .
```

That pulls in `piecash`, the library ledgerforge uses to read and write GnuCash books. Two
optional extras exist for future parser work but nothing in the engine uses them yet:
`.[pdf]` (pypdf) and `.[xlsx]` (openpyxl). For running the test suite: `.venv/bin/pip install -e ".[dev]"`.

## 2. Run the demo end to end

The fastest way to see the whole pipeline work is the bundled demo — entirely fictional
statements, safe to run and look at:

```bash
.venv/bin/python demo/build_demo.py
```

This does, with the real engine, exactly what a real entity's driver script would do:

1. parses four fictional OFX statements (current account, savings, credit card, a EUR account)
2. categorises every transaction against [`demo/data/rules.json`](demo/data/rules.json)
3. builds a multi-currency GnuCash book (`demo/build/demo.gnucash`) with a coded chart of
   accounts and an FX price for EUR
4. generates four static HTML pages into `demo/site/`: a home page, the accounts/balance-sheet
   page, a rules editor, and an "unspecified payees" assigner

Open `demo/build/demo.gnucash` in GnuCash and you'll see the same accounts and balances the
HTML pages show — it's a genuine book, not a mockup. Open `demo/site/accounts.html` directly in
a browser, or serve the folder:

```bash
.venv/bin/python -c "from ledgerforge.serve import run; run('demo/site', 'demo/site')"
# -> http://localhost:8765/
```

## 3. Point it at your own statements

There's no generic "just run this" command for real data, because the chart of accounts, the
categorisation rules, and which statement feeds which account are all yours to decide. The
shape of the driver script is fixed; the content isn't. Concretely:

### a. Lay out a private config

Copy [`config.example.toml`](config.example.toml) to a `config.toml` that stays **out of any
repo** (or in a private repo — never this public one). It tells `Settings.from_toml()` where
your statements live, where the book should be written, where your rules file is, and where your
real account numbers are kept (`master_dirs`, outside any repo, never tracked):

```toml
entity = "household"
base_currency = "GBP"

[paths]
txn_dir    = "data/statements"
book_path  = "build/household.gnucash"
rules_path = "rules/household.json"

master_dirs = ["~/.config/ledgerforge/household"]

[markers]
names = ["YOUR NAME", "Y NAME"]

[fx_to_base]
EUR = "0.855"
```

### b. Drop your bank exports in `txn_dir`

Whatever your bank gives you: OFX, QIF, or one of the supported CSV shapes (Co-operative Bank /
Smile, Nationwide current account, Nationwide mortgage). See
[MANUAL.md](MANUAL.md#supported-formats) for the exact format each parser expects.

### c. Write a driver script

Model it on `demo/build_demo.py`. The shape is always: define your chart of accounts, then for
each statement — parse it, then for each transaction decide where the money went:

```python
from ledgerforge.config import Settings
from ledgerforge.parsers import parse_ofx
from ledgerforge.rules import categorise
from ledgerforge.transfers import is_transfer, load_account_markers
from ledgerforge.overrides import override_account
import piecash, json

s = Settings.from_toml("config.toml")
rules = json.loads(s.rules_path.read_text())["rules"]
markers = s.name_markers + s.extra_markers + load_account_markers(s.master_dirs, s.master_files)

book = piecash.create_book(sqlite_file=str(s.book_path), currency=s.base_currency, overwrite=True)
# ... define Accounts (see demo/build_demo.py's CHART list for the pattern) ...

for txn in parse_ofx(statement_text)[0]:
    if is_transfer(txn["desc"], markers):
        contra = ...  # the other side of your own transfer
    else:
        acct = override_account(txn, currency, overrides) or categorise(txn["desc"], rules)
        contra = accounts_by_name.get(acct, unspecified_account)
    piecash.Transaction(currency=..., post_date=txn["date"], description=txn["desc"],
                         splits=[piecash.Split(account=target, value=txn["amount"]),
                                 piecash.Split(account=contra, value=-txn["amount"])])
book.save()
```

Everything you need is a pure function that takes plain data in and gives plain data (or a
`piecash.Account`/`Transaction`) out — nothing in the engine assumes a filesystem layout or
knows your account names.

### d. Generate a review page

For a quick read-only balance sheet, the engine ships one page generator:

```python
from ledgerforge.report import accounts_html
Path("accounts.html").write_text(accounts_html(s.book_path, title="Household"))
```

For the fuller four-page toolkit (rules editor, unspecified-payee assigner, home page) that the
demo shows, treat `demo/make_editor.py`, `demo/make_unspec.py`, and `demo/make_home.py` as the
pattern to copy and adapt — they are demo-specific example code, not part of the installed
package.

## 4. Interpreting the self-check

Open the accounts page (or `demo/site/accounts.html`). Near the top is:

> Double-entry check: ✓ residual £0.00 — books balance

That's not a presentational balance sheet check — it's the raw identity
`Assets − Liabilities − Equity − Income + Expenses = 0`, computed at each account's recorded
value with no FX conversion. Because every transaction you post has two (or more) splits that
sum to zero, that identity holds automatically *unless* something is actually wrong: a missing
statement, a duplicated import, a transfer booked as income on one side and never matched on the
other. If the residual isn't zero, that number is what you go and hunt for — see
[MANUAL.md](MANUAL.md#the-self-checking-invariant) for how it's computed and what typically
breaks it.

## 5. The iteration loop

Run the driver script, look at the accounts page. If the double-entry check isn't zero, or the
"Unspecified" expense account has a nonzero balance, that means transactions fell through the
rules with nowhere to go. The `unspec_assign.html` pattern (see `demo/make_unspec.py`) groups
those payees, suggests a token and account for each, and lets you paste a delta back into your
rules file. Re-run the driver script; the residual should shrink towards zero and Unspecified
towards nothing. Repeat until both are clean.

## Where next

- [MANUAL.md](MANUAL.md) — reference for every pipeline stage, the rules-matching contract,
  transfer detection, FX handling, and the self-checking invariant in full.
- [DEVELOPMENT.md](DEVELOPMENT.md) — architecture, adding a new bank parser, running the tests.
- [docs/HOW_IT_WORKS.md](docs/HOW_IT_WORKS.md) — the conceptual explanation, no accounting
  background assumed.
