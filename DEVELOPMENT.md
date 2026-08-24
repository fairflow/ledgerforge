# Developing ledgerforge

Architecture, how to extend it, and how to run the tests. For what the engine does, see
[MANUAL.md](MANUAL.md); for how to use it, see [GUIDE.md](GUIDE.md).

## Directory layout

```
src/ledgerforge/
  parsers.py      bank-statement parsers (OFX, QIF, Co-op CSV, Nationwide CSV, mortgage CSV)
  rules.py        categorise() — the payee → account matching contract
  transfers.py    own-account transfer detection
  overrides.py    date/currency-scoped exceptions that beat the rules
  book.py         generic piecash helpers: read balances, set FX prices
  report.py       accounts_html() — the packaged balance-sheet page generator
  serve.py        LAN-gated static-HTML + POST-to-JSON review server
  gnucash_xml.py  read-only parser for GnuCash's native XML book format (no piecash needed)
  config.py       Settings — the per-entity configuration schema, loaded from TOML
tests/
  test_engine.py       parsers, rules, transfers, overrides — the pipeline stages
  test_report.py       accounts_html() against a tiny in-memory book
  test_gnucash_xml.py  the XML book reader
demo/
  build_demo.py    end-to-end demo driver — the template for a real entity's driver script
  make_*.py        the four review-toolkit page generators (demo-specific example code)
  data/            fictional OFX statements + rules.json
  plaid_sandbox.py Plaid Sandbox dress-rehearsal of a statement-fetch flow (fake bank)
docs/
  HOW_IT_WORKS.md  first-principles explanation of the accounting model
```

There is no `ledgerforge` package outside `src/ledgerforge/`, and no CLI entry point — it's
installed and used as a library (`pyproject.toml` declares no `[project.scripts]`).

## Setting up

```bash
python -m venv .venv
.venv/bin/pip install -e ".[dev]"
```

`dev` pulls in `pytest>=8`. The core dependency is `piecash>=1.2,<2`; two more extras
(`pdf` → pypdf, `xlsx` → openpyxl) are declared for future parser work but nothing in the
codebase imports them yet — don't assume a PDF or XLSX parser exists.

## Running the tests

```bash
.venv/bin/python -m pytest
```

Three files, ~190 lines total:

- `tests/test_engine.py` — OFX parsing (amount, date, opening-balance derivation), rules
  matching (most-specific-wins, the `&AMP;` decode), transfer marker matching, the "missing
  master-dir is not an error" contract, and override date/currency filtering.
- `tests/test_report.py` — builds a tiny two-account `piecash` book in a tmp dir and checks
  `accounts_html()` renders the right title, balance, and as-at date.
- `tests/test_gnucash_xml.py` — the XML book reader against a hand-built fixture book.

There's no test runner config beyond pytest defaults (no `pytest.ini`/`conftest.py`) — plain
`pytest` discovery over `tests/`.

## Adding a new bank parser

Every existing parser in `parsers.py` follows the same contract, and a new one should too:

1. **Pure function, no filesystem assumptions beyond reading the one file/text you're given.**
   Signature is either `parse_X(text: str)` (OFX, QIF — content already read) or
   `parse_X(path: Path)` (the CSV parsers — they need to control the file encoding, e.g.
   `utf-8-sig` for Co-op, `cp1252` for the Nationwide mortgage export).
2. **Return normalised transactions**: a list of `{"date": date, "amount": Decimal, "desc": str}`
   dicts at minimum (amounts signed, credits positive), plus whatever extra fields are genuinely
   useful downstream — the Nationwide parser adds a `ttype` signal, for instance. Don't invent
   fields a consumer has no way to interpret.
3. **If the format carries a running balance**, return `(txns, opening, closing)` (or just
   `(txns, opening)` for OFX, which only has a ledger balance) so a consumer can post an
   opening-balance entry without guessing it — see how the existing CSV parsers derive `opening`
   from the first/last row's balance and the net of parsed transactions.
4. **No categorisation, no account names, no entity specifics.** A parser's only job is turning
   a bank's export format into plain, normalised data — everything about where the money *goes*
   is `rules`/`transfers`/`overrides`, later in the pipeline.
5. **Wire it into `read_statements()`** by adding an `elif fmt == "your-format":` branch, and
   **write tests** in `tests/test_engine.py` following the existing pattern — a small literal
   sample of the format in the test itself, asserting on amount, date, and description exactly
   as `test_parse_ofx_basic` does.

## How the rules engine is tested

`categorise()` is exercised directly with small literal rule lists in
`tests/test_engine.py::test_categorise_most_specific` (checks that a longer, more specific token
wins regardless of list order) and `test_categorise_amp_decode` (checks the `&AMP;` → `&`
normalisation is actually applied before matching). There's no golden-file or fixture-based test
of the full rules pipeline; `demo/data/rules.json` plus `demo/build_demo.py`'s
matched/unmatched count serves as the closest thing to an integration check — running the demo
and reading its "N categorised, M → Unspecified" output is a fast manual sanity check when
changing matching logic.

If you touch the specificity/tie-break logic in `_best_token_len`/`categorise`, add a case to
`test_categorise_most_specific` covering the scenario, since it's the one place the contract is
pinned down in an executable form.

## Architecture principles

These are enforced by the code shape, not by discipline, and any change should preserve them:

- **The engine is entity-agnostic.** No account names, account numbers, or filesystem paths
  live in `src/ledgerforge/`. Everything specific to a given ledger (a household, a business, the
  demo) arrives through a `Settings` object, normally loaded from a private `config.toml`. This
  is what lets the engine live in a public repo while every real ledger built on it stays
  private — don't add a function that needs a hardcoded path or account name to work.
- **Account numbers never enter tracked source, public or private.** They're read at runtime
  from JSON registries kept in `master_dirs`, outside any repository
  (`transfers.load_account_markers`). `Settings.extra_markers` is documented as private-config-only
  for exactly this reason.
- **Pure functions over stateful objects wherever the data allows it.** Parsers, `categorise`,
  `is_transfer`, `override_account` all take plain data in and return plain data out — no
  instance state, nothing to construct beyond the arguments. This is what makes them easy to
  unit test with a few lines of literal input.
- **piecash is the only place GnuCash-book-writing knowledge lives**, and it stays inside
  `book.py` plus each consumer's own driver script (chart of accounts, contra-account routing)
  — `book.py` itself only offers the generic bits (`read_balances`, `set_fx_prices`) that every
  consumer needs identically.
- **The review server refuses non-local clients** (`serve.py`'s `_lan_ok()`) — any change to
  request handling needs to preserve that gate; it's the thing that makes `host="0.0.0.0"` safe
  to use on a home network.

## Contribution notes

- Keep new parsers, rules changes, and review-toolkit tweaks covered by a test in the relevant
  file under `tests/` — the suite is small enough that there's no excuse to skip it.
- If you add real personal data to a fixture or example by mistake, it doesn't belong in this
  repo at all, even in a test — see the security stance in [MANUAL.md](MANUAL.md#security-stance).
- `demo/` is meant to be run and published as-is (`demo/deploy.sh` refuses to publish a build
  that still calls a `/save` endpoint) — if you change something that affects the demo's output,
  regenerate it (`python demo/build_demo.py`) and check `demo/site/` still renders sensibly
  before committing.
