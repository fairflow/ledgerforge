"""Inter-account transfer detection.

An own-account transfer is one whose description carries a marker: an account holder's name, or
an account number belonging to the entity. The engine holds NO markers itself — the consumer
passes them in. Account numbers are loaded at runtime from out-of-repo master registries so they
never enter tracked source (public or private).
"""
from __future__ import annotations

import json
from pathlib import Path


def is_transfer(desc: str, markers) -> bool:
    """True if any marker (case-insensitive substring) appears in the description."""
    u = desc.upper()
    return any(m in u for m in markers)


def load_account_markers(master_dirs, master_files=("accounts.json", "accounts-master.json"),
                         min_len: int = 6) -> list[str]:
    """Union of `account_number` fields across every master registry found under `master_dirs`.

    Each is a genuine account of the entity, so an extra number only ever helps transfer detection,
    never causes a false hit. Missing dirs/files and unparseable JSON are skipped silently.
    """
    nums: set[str] = set()
    for d in master_dirs:
        if not d:
            continue
        for fn in master_files:
            p = Path(d) / fn
            if not p.is_file():
                continue
            try:
                accts = json.loads(p.read_text()).get("accounts", [])
            except Exception:
                continue
            for a in accts:
                num = str(a.get("account_number", "")).strip()
                if num.isdigit() and len(num) >= min_len:
                    nums.add(num)
    return sorted(nums)
