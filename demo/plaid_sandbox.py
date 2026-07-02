"""Plaid SANDBOX dress-rehearsal — prove the token-exchange -> transactions flow end-to-end.

Headless: uses /sandbox/public_token/create so no browser Plaid Link is needed to test the mechanism.
Sandbox only — a fake bank with fake data; no real accounts are ever touched, no money moves (this is
AIS read-only anyway). Credentials come from a gitignored `demo/plaid_secrets.toml` (copy
`plaid.example.toml` and fill in your own sandbox keys from dashboard.plaid.com).

Run:  python demo/plaid_sandbox.py
"""
from __future__ import annotations

import json
import time
import tomllib
import urllib.error
import urllib.request
from pathlib import Path

CREDS = Path(__file__).parent / "plaid_secrets.toml"
if not CREDS.is_file():
    raise SystemExit(f"Missing {CREDS.name}: copy demo/plaid.example.toml to {CREDS.name} and add your sandbox keys.")
_c = tomllib.loads(CREDS.read_text())["plaid"]
CLIENT_ID, SECRET = _c["client_id"], _c["sandbox_secret"]
BASE = "https://sandbox.plaid.com"


def call(path: str, payload: dict) -> dict:
    body = json.dumps({**payload, "client_id": CLIENT_ID, "secret": SECRET}).encode()
    req = urllib.request.Request(BASE + path, data=body, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        return json.loads(e.read())  # Plaid returns JSON error bodies with error_code


def die_if_error(resp, step):
    if "error_code" in resp:
        raise SystemExit(f"[{step}] Plaid error: {resp['error_code']} — {resp.get('error_message')}")


print("1. /sandbox/public_token/create (fake bank ins_109508)...")
pt = call("/sandbox/public_token/create", {"institution_id": "ins_109508", "initial_products": ["transactions"],
                                           "options": {"transactions": {"days_requested": 90}}})
die_if_error(pt, "public_token")
print("   public_token:", pt["public_token"][:24], "...")

print("2. /item/public_token/exchange...")
ex = call("/item/public_token/exchange", {"public_token": pt["public_token"]})
die_if_error(ex, "exchange")
access = ex["access_token"]
print("   access_token:", access[:24], "...   item_id:", ex["item_id"])

print("3. /accounts/get...")
acc = call("/accounts/get", {"access_token": access})
die_if_error(acc, "accounts")
for a in acc["accounts"]:
    print(f"   {a['name'][:26]:26} {a['type']}/{a.get('subtype')}  current={a['balances'].get('current')} {a['balances'].get('iso_currency_code')}")

print("4. /transactions/sync (poll until transactions generate)...")
added = []
for _ in range(15):
    cursor, batch = None, []
    while True:
        resp = call("/transactions/sync", {"access_token": access, **({"cursor": cursor} if cursor else {})})
        if resp.get("error_code") == "PRODUCT_NOT_READY":
            break
        die_if_error(resp, "transactions")
        batch += resp["added"]
        cursor = resp["next_cursor"]
        if not resp["has_more"]:
            break
    if batch:
        added = batch
        break
    time.sleep(2)
print(f"   {len(added)} transactions pulled")
for t in added[:10]:
    cps = t.get("counterparties") or []
    cp = cps[0].get("name") if cps else ""
    print(f"   {t['date']}  {t['amount']:>9}  {t['name'][:32]:32}  merchant={t.get('merchant_name') or '-'}  cp={cp or '-'}")

print("\nSANDBOX DRESS-REHEARSAL OK — link/exchange/accounts/transactions all working against Plaid.")
