# ledgerforge manual

Reference for what the engine actually does, module by module. For a first-principles
explanation of the accounting model, see [docs/HOW_IT_WORKS.md](docs/HOW_IT_WORKS.md). For "how
do I run this", see [GUIDE.md](GUIDE.md).

The engine is a library (`import ledgerforge`), not a CLI. Every function below is a pure or
near-pure function operating on plain data (dicts, `Decimal`, `date`) or on a `piecash` book —
nothing in it knows a filesystem layout, an account name, or an account number. Those arrive
through a `Settings` object (`ledgerforge.config`), typically loaded from a private
`config.toml` (see [`config.example.toml`](config.example.toml)).

## Pipeline overview

```
statements (OFX / QIF / CSV)
        │  ledgerforge.parsers    one parser per bank format
        ▼
normalised transactions (date, amount, description, currency)
        │  ledgerforge.rules      categorise(description) → account, first match wins
        │  ledgerforge.transfers  detect own-account moves so they never count as income/expense
        │  ledgerforge.overrides  date- or currency-scoped exceptions that beat the rules
        ▼
double-entry GnuCash book (multi-currency, FX prices, coded chart of accounts)
        │  ledgerforge.book, ledgerforge.report, ledgerforge.serve — review toolkit
        ▼
you, checking and refining
```

## Supported formats

All parsers live in `ledgerforge.parsers` and are pure functions: text or a `Path` in, a list of
`{date, amount, desc, ...}` dicts out (amounts are signed `Decimal`, credits positive). None of
them touch a chart of accounts or decide where money goes — that's the rules/transfers/overrides
stages.

| Format | Function | Notes |
|---|---|---|
| OFX | `parse_ofx(text)` → `(txns, opening)` | Reads `<STMTTRN>` blocks; description is `NAME + MEMO`; opening balance is derived by subtracting the net of parsed transactions from `<LEDGERBAL><BALAMT>`. |
| QIF | `parse_qif(text)` → `txns` | `!Type:Bank` style. Dates are US `MM/DD/YYYY` (matches Wise exports). Description is `payee + memo`. |
| Co-operative Bank / Smile CSV | `parse_coop_csv(path)` → `(txns, opening, closing)` | Columns `Date, Description, Type, Money In, Money Out, Balance`, newest-first. Amount = Money In − Money Out. |
| Nationwide current-account CSV | `parse_nationwide_csv(path)` → `(txns, opening, closing)` | Columns `Date, Transaction type, Description, Paid out, Paid in, Balance`, oldest-first, `£`-prefixed amounts, `DD Mon YYYY` dates. Also derives a `ttype` signal (`POS`/`DIRECTDEBIT`/`INT`/`FEE`/`CASH`/`MEMBER`/`""`) from the bank's own transaction-type column, for a consumer's own contra-routing logic — the engine itself doesn't act on it. |
| Nationwide mortgage CSV | `parse_mortgage(path)` → `(txns, opening, closing)` | `cp1252` encoding, £-signed amounts; picks out opening/closing balance rows and interest/payment lines. |

`read_statements(txn_dir, glob, fmt)` dispatches every file matching a glob under a directory to
the right parser by a format string (`"ofx"`, `"qif"`, `"coop-csv"`, `"nationwide-csv"`) and
concatenates the results — useful when one account's statements span several export files.

Two optional extras are declared in `pyproject.toml` — `pdf` (pypdf) and `xlsx` (openpyxl) — but
nothing in the current codebase uses them; they're there for future parser formats, not wired to
anything yet.

## Categorisation rules (`ledgerforge.rules`)

`categorise(description, rules)` is the entire matching contract, dependency-free (stdlib only).

- **Input shape**: `rules` is a list of dicts, each with an `account` and either/both `match`
  (a list of substrings) and `regex` (a list of patterns).
- **Matching**: a rule matches if any of its `match` tokens appears as a substring of the
  normalised description, or any `regex` pattern searches successfully (case-insensitive).
- **`normalise(description)`**: upper-cases the description, decodes the literal `&AMP;` HTML
  entity back to `&` (OFX/CSV exports commonly encode it that way — `B &AMP; Q` → `B & Q`), and
  collapses whitespace. This is itself part of the matching contract, not incidental cleanup.
- **Winner selection: first-match-wins, most-specific-first.** For every matching rule, the
  "specificity" score is the length of its *longest* matching token or regex match. The rule
  with the longest match wins; ties break by array order (the earlier rule in the list wins).
  This is what lets a narrow rule like `"MORRISONS PETROL" → Expenses:Auto:Fuel` safely coexist
  with a broader `"MORRISON" → Expenses:Groceries`, in either order in the list — the longer
  token always wins regardless of position, and only a genuine tie falls back to order.
- **No match** returns `None` — the transaction has no home yet and belongs in the review queue
  (the "Unspecified" pattern described in [GUIDE.md](GUIDE.md#5-the-iteration-loop)).

## Transfer detection (`ledgerforge.transfers`)

The subtle pipeline stage. A transfer between two of your own accounts appears in *two*
statements — money out of one, money into the other. Categorised naively by payee text alone, it
becomes a phantom expense on one side and phantom income on the other.

- `is_transfer(desc, markers)` — `True` if any marker (an account holder's name, or an account
  number) appears as a case-insensitive substring of the description. Nothing more sophisticated
  than that; the engine relies on the marker list being complete for the entity.
- `load_account_markers(master_dirs, master_files=("accounts.json", "accounts-master.json"), min_len=6)`
  — unions the `account_number` field across every JSON registry file found under `master_dirs`,
  keeping only digit strings of at least `min_len` characters. Missing directories, missing
  files, and unparseable JSON are all skipped silently (not an error) — this is deliberate, since
  the registries live **outside any repository** and won't exist in, say, a CI checkout.

The engine holds no markers itself. A consumer supplies name markers via `Settings.name_markers`,
an emergency/orphan number via `Settings.extra_markers` (private config only, never committed),
and the bulk of real account numbers via out-of-repo registries under `master_dirs` — JSON files
each looking like `{"accounts": [{"account_number": "12345678", ...}, ...]}`.

Callers are expected to check `is_transfer()` before consulting rules or overrides — a matched
transfer is booked directly against the other asset/liability account, not routed through
`categorise()`.

## Overrides (`ledgerforge.overrides`)

`override_account(txn, currency, overrides)` returns the overriding account for a transaction, or
`None`. Each override is a dict with `_from`/`_to` (`date` objects, inclusive), an `account`, and
optional `currency` and `debits_only` filters. The first override whose window (and optional
currency/sign filter) contains the transaction wins.

This is for the case rules can't express cleanly: "this payee, but only during this date window,
and only in this currency, goes to a different account than usual" — a holiday, a one-off refund
period, and so on. Overrides are checked **before** the general rules and take precedence, but —
per the transfer-detection contract above — never override a transaction already identified as a
transfer.

## Multi-currency and FX

Accounts in the chart of accounts each carry a single currency (a `piecash` commodity) — GBP,
EUR, USD, whatever the account actually holds. A statement in a foreign currency posts directly
against its own-currency account and its own-currency contra account; there's no automatic
conversion at posting time (see the demo's EUR account, which routes all its spend to
`Expenses:Holiday EUR`, a EUR-denominated expense account, rather than converting to GBP).

Cross-currency *reporting* (net worth in one number, a combined balance sheet) is a separate,
explicit step: `ledgerforge.book.set_fx_prices(book, fx_to_base, base="GBP", on=date)` records a
fixed price per foreign currency against the base currency on a given date
(`piecash.Price(..., source="user:fixed")`). A reader (the accounts page, or your own code) can
then translate foreign balances into the base currency for presentation using that recorded rate
— but the underlying transactions and account balances stay in their original currency,
unaffected by the exchange rate used for reporting.

`Settings.fx_to_base` (a `{mnemonic: rate}` dict, e.g. `{"EUR": "0.855"}`) is where a consumer's
config supplies these rates; nothing in the engine fetches live rates.

## The self-checking invariant

Two related identities show up on the accounts/balance-sheet page, and they answer different
questions.

**The balance sheet identity** — the familiar accounting equation, always true by construction
once double-entry posting is followed:

> Assets − Liabilities = Equity

Income and expenses aren't a third term here; they're the *explanation* of how equity changed
over the period. Profit (income − expenses) is added to equity as retained earnings, and the
same profit already shows up on the assets/liabilities side, which is why the identity keeps
holding.

**The integrity check** — the stricter test, and the one that actually tells you whether the
book is broken. Take every account at its *recorded* value (no FX translation applied anywhere)
and sum, with income and expense signs flipped:

> Assets − Liabilities − Equity − Income + Expenses = 0

Because every split in every transaction has an equal-and-opposite partner, this residual is
*exactly* zero if — and only if — nothing has gone wrong. In the demo's accounts page this is
computed as:

```python
par_resid = sum(
    nw[c]["asset"] - nw[c]["liab"] - eqv[c] - incv[c] + expv[c]
    for c in all_currencies
)
```

and rendered as "✓ residual £0.00 — books balance" when `abs(par_resid) < Decimal("0.01")`, or
the actual nonzero residual otherwise. A nonzero residual is concrete and huntable — a missing
statement (an account whose opening balance was never posted), a duplicated import, or a
transfer that got categorised as income/expense on one leg instead of being recognised as a
transfer, are the usual causes. The size of the residual is generally close to the size of the
transaction that broke it, which is where to start looking.

Note this check is deliberately done **at par** (raw recorded values, no FX plug) — the separate
"FX translation reserve" line in the presented accounting equation absorbs the effect of
reporting foreign balances at a market rate, so it never masks a genuine integrity problem.

## Review toolkit

- **`ledgerforge.report.accounts_html(book_path, title=..., built=...)`** — the one packaged
  page generator. Self-contained (inline CSS, a small collapse-toggle script, no external
  assets); reads a book read-only via `piecash` and renders net-worth cards per currency, a
  collapsible account tree, and per-account balances. This is the function to reach for if you
  just want a publishable snapshot of a book.
- **`ledgerforge.serve`** — a local HTTP server (`ThreadingHTTPServer` + a `SimpleHTTPRequestHandler`
  subclass) that serves a directory of static HTML and accepts `POST /save/<tool>` to write
  `save_dir/pending_<tool>.json`. Every GET and POST is gated to loopback / private / link-local
  client addresses (`_lan_ok()`), so `host="0.0.0.0"` can be shared to a home network without
  exposing anything past it. `route_txn` saves append to a list rather than overwrite. `run(serve_root, save_dir, host="127.0.0.1", port=8765)` is the entry point.
- **The fuller four-page toolkit** (a home page, the accounts page, a rules editor, an
  "unspecified payee" assigner) is demonstrated end-to-end in `demo/make_home.py`,
  `demo/make_editor.py`, and `demo/make_unspec.py` — but these are demo-specific example scripts
  that import `ledgerforge.parsers`/`ledgerforge.rules` directly, not part of the installed
  package's public API. Treat them as the pattern to copy per entity, as the private consumer
  repos do, rather than something you `import`.

## Reading a GnuCash book directly (`ledgerforge.gnucash_xml`)

GnuCash books come in two on-disk formats: SQLite (what `ledgerforge.book` and `piecash` write
and read) and native XML (gzip-compressed `.gnucash` files, or plain XML). `GnuCashBook.open(path)`
parses the XML format directly with the standard library — no `piecash` dependency — giving
read-only access to `.accounts` (by GUID) and `.transactions`, plus convenience queries:
`account_by_fullname`, `account_balance(fullname, as_of, exclude_desc_keywords=...)`, and
`splits_in_period(start, end, exclude_desc_keywords=...)`. Useful when you need to read a book
someone else produced (or an older XML-format book) without pulling in `piecash`.

## Security stance

No account numbers, sort codes, IBANs, or PANs ever appear in this repository — see the
[README](README.md#security-stance) for the full statement. Real statements, GnuCash books, and
`config.toml` are all git-ignored.
