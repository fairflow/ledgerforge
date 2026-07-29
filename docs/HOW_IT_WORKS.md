# How ledgerforge works — from bank statements to a GnuCash book

*This document explains the whole shape of ledgerforge: what GnuCash is, why double-entry
bookkeeping is worth the trouble, and how the pipeline turns a folder of raw bank statements
into an account book you can trust. It assumes no accounting background. For the module-by-module
reference and installation instructions, see the [README](../README.md).*

## What GnuCash is, and why double-entry

[GnuCash](https://www.gnucash.org/) is a free, open-source desktop accounting application,
30 years old and still actively maintained. Two things make it the right foundation:

1. **An open file format.** A GnuCash *book* is just a file (XML or SQLite) with a
   documented structure. Nothing is locked in; any program can read or write it. ledgerforge
   writes books through [piecash](https://piecash.readthedocs.io/), a Python library that
   treats the book as ordinary objects.
2. **Real double-entry bookkeeping**, which is the 500-year-old idea that makes an account
   book self-checking.

The idea is simple. Your finances are a set of named **accounts** — not just bank accounts,
but buckets of every kind:

- **Assets** — what you have: current account, savings, cash in your wallet
- **Liabilities** — what you owe: credit card, mortgage
- **Income** — where money comes from: salary, interest
- **Expenses** — where it goes: groceries, energy, insurance
- **Equity** — the starting point: opening balances when the book begins

Every transaction **moves value between two (or more) accounts**, and the amounts always
sum to zero. Buy £40 of groceries on the credit card, and the book records
*Expenses:Groceries +40, Liabilities:Credit Card −40*. Get paid, and it's
*Assets:Bank:Current +2000, Income:Salary −2000*. Nothing ever appears from nowhere or
vanishes into nowhere.

Because every entry has an equal and opposite partner, the whole book obeys one equation
at every moment:

> **Assets − Liabilities = Equity + Income − Expenses**

If the equation holds, every penny is accounted for. If it doesn't, something concrete is
wrong — a missing statement, a duplicated import, a miscoded transfer — and the size of the
discrepancy tells you what to hunt for. That self-checking property is the entire reason
for the double-entry ceremony, and it is what a shoebox of statements can never give you.

## The problem ledgerforge solves

Banks give you statements: OFX, QIF, or CSV files, one per account, full of lines like
`CARD PAYMENT TO TESCO STORES 3456, £23.71`. To become a double-entry book, every one of
those lines needs an answer to one question: **what is the other account?** A grocery
payment's partner is `Expenses:Groceries`; a salary line's partner is `Income:Salary`; a
transfer to your own savings account's partner is `Assets:Bank:Savings` — emphatically
*not* an expense.

Answering that question thousands of times is the real work, and it's what ledgerforge
automates:

```
statements (OFX / QIF / CSV)
        │  parsers      – one parser per bank format
        ▼
normalised transactions (date, amount, description, currency)
        │  rules        – categorise(description) → account, first match wins
        │  transfers    – detect own-account moves so they never count as income/expense
        │  overrides    – date- or currency-scoped exceptions that beat the rules
        ▼
double-entry GnuCash book (multi-currency, FX prices, coded chart of accounts)
        │  review toolkit – four local HTML pages
        ▼
you, checking and refining
```

### The pieces

- **Parsers** (`ledgerforge.parsers`) — read each bank's export format and produce one
  normalised transaction stream. New bank, new small parser; everything downstream is
  unchanged.
- **Rules** (`ledgerforge.rules`) — a JSON list of match-tokens mapped to accounts:
  `"TESCO" → Expenses:Groceries`. Matching is first-match-wins with the most specific
  token first, so `"TESCO PETROL" → Expenses:Motoring` can sit safely above the general
  grocery rule.
- **Transfer detection** (`ledgerforge.transfers`) — the subtle one. Moving £500 from
  current to savings shows up in *two* statements — as money out in one and money in the
  other. Naively categorised, it becomes both a phantom expense and phantom income.
  ledgerforge recognises own-account markers (your account numbers and name variants,
  loaded from registries kept *outside* the repository) and books such pairs as what they
  are: an internal transfer between two asset accounts.
- **Overrides** (`ledgerforge.overrides`) — scoped exceptions: "this payee, but only in
  2019, and only in EUR, goes to that account". They beat the general rules.
- **Book building** (`ledgerforge.book` + piecash) — writes the GnuCash book: a coded
  chart of accounts (Assets 1000s, Liabilities 2000s, Equity 3000s, Income 4000s,
  Expenses 5000s), multi-currency accounts, and FX prices so foreign balances translate
  into the base currency.
- **Review toolkit** (`ledgerforge.serve` + generators) — four static HTML pages served
  locally: a **home** page; **accounts & balances** (net worth per currency, P&L, the
  accounting equation with a genuine double-entry zero-check); a **rules editor**; and an
  **unspecified assigner** that shows one card per payee no rule catches yet, with a
  suggested token and account. You review, it generates a delta to paste back, the book
  rebuilds. The loop converges: each pass leaves fewer unspecified payees.

## The trust model

The engine is public; the ledgers that use it are private. This is enforced by design, not
by discipline:

- The engine source contains **no account names, numbers, or filesystem paths**. Everything
  entity-specific arrives through a `Settings` object loaded from a private, git-ignored
  `config.toml`.
- Real account numbers used for transfer detection live in **registries outside any
  repository** (e.g. `~/.config/ledgerforge/<entity>/accounts.json`).
- The same engine therefore drives private household ledgers and the
  **[public demo](https://github.com/fairflow/ledgerforge/tree/main/demo)** — entirely
  fictional data, real pipeline, safe to publish. Its books balance by construction, and
  the accounts page proves it with a true zero in the double-entry check.

## Try it

```bash
git clone https://github.com/fairflow/ledgerforge
cd ledgerforge
python -m venv .venv && .venv/bin/pip install -e .
.venv/bin/python demo/build_demo.py
# -> demo/build/demo.gnucash  (open it in GnuCash!)
# -> demo/site/*.html         (the toolkit — serve or just open in a browser)
```

The generated book is a genuine GnuCash file: open it in the GnuCash desktop app and
you'll see the same accounts, transactions and balances the toolkit pages show.
