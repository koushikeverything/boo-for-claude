#!/usr/bin/env python3
"""Cross-source grounding: dedup key conventions, cross-tool merge, and status-conflict detection.

Operates on NORMALIZED retrieved items (which may carry a `status` from their source tool) BEFORE
the brief payload is built. It collapses the same real-world thing seen in multiple tools and
flags contradictions (e.g. a ticket marked done while its PR is still open). Stdlib-only.
"""
from __future__ import annotations

import re
from typing import Dict, List

# --- dedup key conventions (stable identity of a real-world thing) ---------------------

def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (text or "").strip().lower()).strip("-")


def pr_key(repo: str, number) -> str:
    return f"code:pr-{_slug(repo)}-{number}"


def issue_key(tracker_key: str) -> str:
    return f"tracking:{_slug(tracker_key)}"


def incident_key(incident_id: str) -> str:
    return f"incident:{_slug(incident_id)}"


def deploy_key(repo: str, ref: str) -> str:
    return f"deploy:{_slug(repo)}-{_slug(ref)}"


def thread_key(channel: str, root_ts: str) -> str:
    return f"chat:{_slug(channel)}-{_slug(root_ts)}"


# --- cross-source merge + conflict detection ------------------------------------------

_DONE = {"done", "closed", "merged", "resolved", "completed", "shipped"}
_OPEN = {"open", "in_progress", "in-progress", "active", "triggered", "todo", "reopened"}


def status_class(status: str):
    s = (status or "").strip().lower()
    if s in _DONE:
        return "done"
    if s in _OPEN:
        return "open"
    return None


def group_by_dedup(items: List[dict]) -> Dict[str, List[dict]]:
    groups: Dict[str, List[dict]] = {}
    for it in items:
        groups.setdefault(it.get("dedup_key"), []).append(it)
    return groups


def find_status_conflicts(items: List[dict]) -> List[dict]:
    """A dedup group whose sources disagree on done-vs-open is a conflict. Returns conflict
    descriptors with the ≥2 disagreeing citations (for the brief's `conflicts[]`)."""
    conflicts = []
    for key, grp in group_by_dedup(items).items():
        by_class = {}
        for it in grp:
            cls = status_class(it.get("status"))
            if cls:
                by_class.setdefault(cls, []).append(it)
        if len(by_class) > 1:  # both done and open present
            citing = []
            for cls in ("done", "open"):
                for it in by_class.get(cls, [])[:1]:
                    citing.append({
                        "source": it.get("source"),
                        "account_id": it.get("account_id"),
                        "account_label": it.get("account_label", it.get("account_id", "")),
                        "source_ref": it.get("source_ref"),
                    })
            done_src = by_class["done"][0].get("account_label") or by_class["done"][0].get("source")
            open_src = by_class["open"][0].get("account_label") or by_class["open"][0].get("source")
            conflicts.append({
                "dedup_key": key,
                "description": f"{done_src} marks this done, but {open_src} still shows it open — please confirm.",
                "citations": citing,
            })
    return conflicts


def merge_cross_source(items: List[dict], merge_items) -> List[dict]:
    """Merge same-dedup_key items across tools (delegating to the shared dedup.merge_items), then
    set conflict_state='conflicted' on any merged item that had a status conflict."""
    conflicted_keys = {c["dedup_key"] for c in find_status_conflicts(items)}
    merged = merge_items(items)
    for it in merged:
        if it.get("dedup_key") in conflicted_keys:
            it["conflict_state"] = "conflicted"
    return merged


if __name__ == "__main__":
    items = [
        {"dedup_key": pr_key("acme/api", 514), "source": "github", "account_id": "github",
         "account_label": "GitHub", "source_ref": "github:acme/api#514", "status": "open"},
        {"dedup_key": issue_key("GRW-231"), "source": "linear", "account_id": "linear",
         "account_label": "Linear", "source_ref": "linear:GRW-231", "status": "done"},
    ]
    # same real-world thing under one key, disagreeing status:
    items[1]["dedup_key"] = items[0]["dedup_key"]
    print(find_status_conflicts(items))
