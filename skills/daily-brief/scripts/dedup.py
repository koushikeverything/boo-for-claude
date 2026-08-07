#!/usr/bin/env python3
"""Canonical deduplication for brief items.

The same real-world thing (a bill, an event) can appear in Gmail and Calendar, or twice in
Gmail (e.g. duplicate delivery notifications). We collapse them by a stable `dedup_key` and
merge their citations, keeping the strongest urgency/confidence. Deterministic and stdlib-only.
"""
from __future__ import annotations

import re
from typing import Dict, List

_URGENCY_RANK = {"today": 0, "soon": 1, "upcoming": 2, "informational": 3}
_CONFIDENCE_RANK = {"high": 0, "medium": 1, "low": 2}


def slug(text: str) -> str:
    """Lowercase, alnum-and-hyphen slug for stable keys."""
    text = (text or "").strip().lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")


def dedup_key(kind: str, subject: str, date: str = "") -> str:
    """Build a stable dedup key, e.g. dedup_key('bill', 'Daycare invoice', '2026-08-07')
    -> 'bill:daycare-invoice:2026-08-07'."""
    parts = [slug(kind), slug(subject)]
    if date:
        parts.append(date)
    return ":".join(p for p in parts if p)


def _citation_identity(c: dict):
    return (c.get("source"), c.get("account_id"), c.get("source_ref"))


def merge_items(items: List[dict]) -> List[dict]:
    """Merge items sharing a dedup_key. Preserves order of first appearance.

    Merge rules:
      - citations: union (dedup by (source, account_id, source_ref))
      - urgency: strongest (today > soon > upcoming > informational)
      - confidence: strongest (high > medium > low)
      - conflict_state: 'conflicted' if any is conflicted
      - other fields: taken from the first occurrence
    """
    order: List[str] = []
    merged: Dict[str, dict] = {}

    for it in items:
        key = it.get("dedup_key")
        if key is None:
            # no key → treat as unique by id
            key = f"__nokey__:{it.get('id')}"
        if key not in merged:
            merged[key] = dict(it)
            merged[key]["citations"] = list(it.get("citations", []))
            order.append(key)
            continue

        base = merged[key]
        # union citations
        seen = {_citation_identity(c) for c in base["citations"]}
        for c in it.get("citations", []):
            if _citation_identity(c) not in seen:
                base["citations"].append(c)
                seen.add(_citation_identity(c))
        # strongest urgency / confidence
        if _URGENCY_RANK.get(it.get("urgency"), 9) < _URGENCY_RANK.get(base.get("urgency"), 9):
            base["urgency"] = it["urgency"]
        if _CONFIDENCE_RANK.get(it.get("confidence"), 9) < _CONFIDENCE_RANK.get(base.get("confidence"), 9):
            base["confidence"] = it["confidence"]
        if it.get("conflict_state") == "conflicted":
            base["conflict_state"] = "conflicted"

    return [merged[k] for k in order]


if __name__ == "__main__":
    print(dedup_key("bill", "Daycare invoice", "2026-08-07"))
