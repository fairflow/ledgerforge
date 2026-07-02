# ledgerforge demo

A public, self-contained showcase of the engine — safe to run with no real financial data.

## Plaid sandbox dress-rehearsal

[`plaid_sandbox.py`](plaid_sandbox.py) walks the full open-banking fetch flow against Plaid's
**Sandbox** — a fake bank with fake data. It proves the mechanism end to end without touching any
real account:

1. `/sandbox/public_token/create` — mint a public token for a fake institution (headless, no browser Link)
2. `/item/public_token/exchange` — exchange it for an access token
3. `/accounts/get` — list the (fake) accounts and balances
4. `/transactions/sync` — pull transactions with merchant names and counterparties

This is **AIS (read-only)**: it reads statement data. It never initiates a payment or moves money.

### Run it

```bash
cp demo/plaid.example.toml demo/plaid_secrets.toml     # then add your own sandbox keys
python demo/plaid_sandbox.py
```

Get free sandbox keys at <https://dashboard.plaid.com/developers/keys> (the **Sandbox** secret).
`demo/plaid_secrets.toml` is git-ignored — your keys never enter the repo.

## Roadmap

A fictional end-to-end example ledger (synthetic statements → chart → built GnuCash book → the local
review pages) will live here too, so the whole `ledgerforge` pipeline can be demonstrated with data
that is safe to publish.
