#!/usr/bin/env python3
"""Role-based ranking for Top of mind.

Produces an explicit, deterministic `rank` per item so that role priority (e.g. an active incident
before a code review) is honored even when the default urgency/effort order can't express it. The
validator checks ascending `rank` when present. Stdlib-only.

Order key = (urgency, role capability-priority, effort ascending [null last], title, id).
Urgency dominates (today items first); within an urgency bucket, the role's capability priority
decides; then effort, then title/id for a total order.
"""
from __future__ import annotations

from typing import Dict, List

_URGENCY_RANK = {"today": 0, "soon": 1, "upcoming": 2, "informational": 3}

# Lower number = higher priority within an urgency bucket. Per role.
CAPABILITY_PRIORITY: Dict[str, Dict[str, int]] = {
    "software_engineer": {
        "incidents": 0, "code": 1, "chat": 2, "tracking": 3, "observability": 4,
        "productivity": 5, "docs": 6, "design": 7,
    },
    "product_designer": {
        "design": 0, "chat": 1, "tracking": 2, "docs": 3, "productivity": 4,
        "code": 5, "support": 6, "analytics": 7,
    },
    "design_lead": {
        "design": 0, "chat": 1, "tracking": 2, "docs": 3, "support": 4,
        "productivity": 5, "code": 6, "analytics": 7,
    },
    "engineering_lead": {
        "incidents": 0, "code": 1, "tracking": 2, "chat": 3, "observability": 4,
        "productivity": 5, "docs": 6, "support": 7, "analytics": 8,
    },
    "product_manager": {
        "tracking": 0, "support": 1, "chat": 2, "analytics": 3, "productivity": 4,
        "design": 5, "code": 6, "docs": 7, "incidents": 8, "observability": 9,
    },
    "head_of_product": {
        "support": 0, "tracking": 1, "analytics": 2, "chat": 3, "productivity": 4,
        "design": 5, "docs": 6, "code": 7, "incidents": 8,
    },
    "qa_engineer": {
        "tracking": 0, "incidents": 1, "code": 2, "observability": 3, "chat": 4,
        "productivity": 5, "design": 6, "docs": 7, "support": 8,
    },
    "data_analyst": {
        "analytics": 0, "tracking": 1, "productivity": 2, "chat": 3, "docs": 4,
        "support": 5, "code": 6, "observability": 7,
    },
    # Superhuman (many hats): things blocking other people first (incidents, customer
    # escalations, decisions), then own execution work, then awareness. No single hat dominates.
    "superhuman": {
        "incidents": 0, "support": 1, "tracking": 2, "code": 3, "design": 4,
        "chat": 5, "productivity": 6, "observability": 7, "docs": 8, "analytics": 9,
    },
    # Unknown role → all equal (falls back cleanly to urgency/effort).
}

_DEFAULT_CAP_PRIORITY = 50


def rank_key(role: str, item: dict):
    caps = CAPABILITY_PRIORITY.get(role, {})
    eff = item.get("effort_minutes")
    return (
        _URGENCY_RANK.get(item.get("urgency"), 9),
        caps.get(item.get("capability"), _DEFAULT_CAP_PRIORITY),
        eff if eff is not None else 10 ** 9,
        item.get("title", ""),
        item.get("id", ""),
    )


def rank_items(role: str, items: List[dict]) -> List[dict]:
    """Return items sorted by the role order, each stamped with an ascending integer `rank`.
    Mutates and returns the same dicts (rank added)."""
    ordered = sorted(items, key=lambda it: rank_key(role, it))
    for i, it in enumerate(ordered):
        it["rank"] = i
    return ordered


if __name__ == "__main__":
    demo = [
        {"id": "a", "capability": "tracking", "urgency": "today", "effort_minutes": 30, "title": "issue"},
        {"id": "b", "capability": "incidents", "urgency": "today", "effort_minutes": None, "title": "incident"},
        {"id": "c", "capability": "code", "urgency": "today", "effort_minutes": 15, "title": "review"},
    ]
    for it in rank_items("software_engineer", demo):
        print(it["rank"], it["capability"], it["title"])
