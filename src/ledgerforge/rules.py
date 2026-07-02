"""Rule-based transaction categoriser.

Dependency-free (stdlib only). `categorise()` IS the matching contract: first-match-wins,
most-specific-first (longest matching token). Rules are a list of dicts with an `account` and
`match` (substrings) and/or `regex` (patterns) — the shape is entity-agnostic.
"""
from __future__ import annotations

import re


def normalise(description: str) -> str:
    """Upper-case, decode the & HTML entity, and collapse internal whitespace.

    OFX/CSV descriptions arrive with '&' encoded as the literal text '&AMP;' (e.g. 'B &AMP; Q');
    decoding it here lets a clean token like 'B & Q' match. This is the matching contract.
    """
    return " ".join(description.upper().replace("&AMP;", "&").split())


def _best_token_len(rule: dict, desc_norm: str) -> int | None:
    """Length of this rule's longest matching token, or None if it doesn't match. Length is the
    "most-specific" score: the longer the matched token, the more specific the match."""
    best: int | None = None
    for token in rule.get("match", []):
        if token.upper() in desc_norm:
            best = max(best or 0, len(token))
    for pattern in rule.get("regex", []):
        m = re.search(pattern, desc_norm, re.IGNORECASE)
        if m:
            best = max(best or 0, len(m.group(0)) or 1)
    return best


def categorise(description: str, rules: list[dict]) -> str | None:
    """Return the matched account, or None (-> review queue). first-match-wins, most-specific-first:
    pick the rule with the longest matching token; ties break by array order (earliest wins)."""
    desc_norm = normalise(description)
    winner: tuple[int, int] | None = None  # (token_len, -index)
    winner_account: str | None = None
    for idx, rule in enumerate(rules):
        tok_len = _best_token_len(rule, desc_norm)
        if tok_len is None:
            continue
        key = (tok_len, -idx)
        if winner is None or key > winner:
            winner = key
            winner_account = rule["account"]
    return winner_account
