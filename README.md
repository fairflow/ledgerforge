# ledgerforge

A small, opinionated engine for turning bank statements into a clean **double-entry GnuCash book** —
parse statements, categorise transactions by rules, detect own-account transfers, and serve a local
review toolkit. It is the shared substrate behind several private "consumer" ledgers and a public
demo.

The engine is **entity-agnostic**: no account names, filesystem paths, or account numbers live in
this repository. Everything specific to a given ledger arrives through a `Settings` object (see
[`config.example.toml`](config.example.toml)), typically loaded from a private, git-ignored
`config.toml`. This is a hard rule — it is what lets the engine be public while the ledgers that use
it stay private.

## What's in the box

| Module | Responsibility |
|---|---|
| `ledgerforge.parsers` | OFX, QIF, Co-operative Bank CSV, Nationwide CSV & mortgage CSV parsers |
| `ledgerforge.rules` | `categorise(desc, rules)` — first-match-wins, most-specific-first |
| `ledgerforge.transfers` | own-account transfer detection; account-number markers loaded from out-of-repo registries |
| `ledgerforge.overrides` | date/currency-scoped account overrides that beat the payee rules |
| `ledgerforge.book` | generic piecash helpers (read balances, set FX prices) |
| `ledgerforge.serve` | LAN-gated static-HTML + POST-to-JSON server for the review pages |
| `ledgerforge.config` | `Settings` — the per-entity configuration schema |

## Install (editable, in a workspace)

The intended layout is a plain workspace folder holding sibling repos — the engine plus one or more
consumers — with the engine installed **editable** so edits are picked up live:

```
~/Software/working/ledger/
├── ledgerforge/     # this repo (public)
├── household/       # a private consumer
└── thornleigh/      # another private consumer
```

```bash
python -m venv .venv
.venv/bin/pip install -e ./ledgerforge          # or: pip install -e ../ledgerforge from a consumer
```

A consumer then does `import ledgerforge` and drives it with its own `Settings`.

## Security stance

- **No account numbers, sort codes, IBANs, or PANs** ever appear in this repo. Account numbers used
  for transfer detection are read at runtime from master registries kept **outside** any repo
  (`master_dirs`).
- Real statements, GnuCash books, and `config.toml` are git-ignored.
- The review server (`ledgerforge.serve`) refuses any client that is not loopback / private /
  link-local, so `host="0.0.0.0"` shares to a home wifi without exposing anything to the internet.

## Demo

[`demo/`](demo/) contains a public, self-contained example — including a headless Plaid **sandbox**
dress-rehearsal of the statement-fetch flow (fake bank, no real accounts). See
[`demo/README.md`](demo/README.md).

## Licence

MIT — see [LICENSE](LICENSE).
