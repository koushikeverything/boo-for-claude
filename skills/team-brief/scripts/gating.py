#!/usr/bin/env python3
"""Role gating: given a role and a role-profile, compute which capability slots are satisfied and
which mandatory ones are missing. Deterministic, stdlib-only. The brief uses this to decide whether
a role's brief is "complete" and what to flag in the coverage line (reusing v1 partial-coverage).
"""
from __future__ import annotations

import json
import os
from typing import Dict, List

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CATALOG_PATH = os.path.join(ROOT, "config", "capability-catalog.json")
MATRIX_PATH = os.path.join(ROOT, "config", "role-matrix.json")


def _load(path: str) -> dict:
    with open(path) as f:
        return json.load(f)


def load_catalog(path: str = CATALOG_PATH) -> dict:
    return _load(path)


def load_matrix(path: str = MATRIX_PATH) -> dict:
    return _load(path)


def is_connectable(provider: str, catalog: dict) -> bool:
    """A provider is connectable today iff it has a native connector (or a configured custom one).
    Providers without either are roadmap-only and are never offered."""
    p = catalog["providers"].get(provider, {})
    return bool(p.get("native_connector") or p.get("custom_connector"))


def connectable_providers(capability: str, catalog: dict) -> List[str]:
    return [p for p in catalog["capabilities"][capability]["providers"] if is_connectable(p, catalog)]


def offered_slots(role: str, matrix: dict, catalog: dict = None) -> Dict[str, str]:
    """Slots for a role. With a catalog, only slots that have >=1 CONNECTABLE provider are returned —
    a slot no one can connect today (e.g. analytics, with no native connector) is not offered."""
    if role not in matrix["roles"]:
        raise KeyError(f"unknown role {role!r}")
    slots = matrix["roles"][role]["slots"]
    if catalog is None:
        return slots
    return {s: lvl for s, lvl in slots.items() if connectable_providers(s, catalog)}


def active_capabilities(profile: dict) -> set:
    return {c["capability"] for c in profile.get("connections", []) if c.get("status") == "active"}


def evaluate(role: str, profile: dict, matrix: dict, catalog: dict) -> dict:
    """Return a gating report:
      { role, connected[], missing_mandatory[], missing_recommended[], degraded[], satisfied, problems[] }
    - satisfied: True iff every mandatory slot for the role has an ACTIVE provider.
    - degraded: slots with a connection that is not active (paused/reconnect_needed/removed).
    - problems: config errors (provider not valid for capability, capability not offered to role, over max).
    """
    full_slots = matrix["roles"][role]["slots"]
    slots = offered_slots(role, matrix, catalog)  # connectable-only
    hidden = sorted(s for s in full_slots if s not in slots)  # in matrix but no connector yet
    connected = active_capabilities(profile)

    missing_mandatory = sorted(s for s, lvl in slots.items() if lvl == "mandatory" and s not in connected)
    missing_recommended = sorted(s for s, lvl in slots.items() if lvl == "recommended" and s not in connected)

    degraded = sorted({c["capability"] for c in profile.get("connections", [])
                       if c.get("status") in ("paused", "reconnect_needed", "removed")}
                      - connected)

    problems: List[str] = []
    per_slot_count: Dict[str, int] = {}
    for c in profile.get("connections", []):
        cap, prov = c.get("capability"), c.get("provider")
        per_slot_count[cap] = per_slot_count.get(cap, 0) + 1
        if cap not in catalog["capabilities"]:
            problems.append(f"unknown capability {cap!r}")
            continue
        if prov not in catalog["capabilities"][cap]["providers"]:
            problems.append(f"provider {prov!r} is not valid for capability {cap!r}")
        if cap not in full_slots:
            problems.append(f"capability {cap!r} is not offered to role {role!r}")
    for cap, n in per_slot_count.items():
        if cap in catalog["capabilities"] and n > catalog["capabilities"][cap]["max"]:
            problems.append(f"capability {cap!r} has {n} providers, exceeds max {catalog['capabilities'][cap]['max']}")

    return {
        "role": role,
        "connected": sorted(connected),
        "missing_mandatory": missing_mandatory,
        "missing_recommended": missing_recommended,
        "degraded": degraded,
        "hidden_slots": hidden,
        "satisfied": not missing_mandatory,
        "problems": problems,
    }


def role_slot_menu(role: str, matrix: dict, catalog: dict) -> dict:
    """What onboarding should present for a role: each offered slot grouped by requirement level,
    listing only CONNECTABLE providers. `hidden` are slots in the role's matrix that have no
    connector yet (roadmap; not shown to the user)."""
    full = matrix["roles"][role]["slots"]
    menu = {"mandatory": [], "recommended": [], "optional": [], "hidden": []}
    for slot, lvl in full.items():
        provs = connectable_providers(slot, catalog)
        if not provs:
            menu["hidden"].append(slot)
        else:
            menu[lvl].append({"capability": slot, "providers": provs})
    return menu


def coverage_note(report: dict, matrix: dict) -> str:
    """A short human line for the brief's coverage, from a gating report."""
    role_label = matrix["roles"][report["role"]]["label"]
    if report["satisfied"] and not report["missing_recommended"] and not report["degraded"]:
        return f"All connected tools for your {role_label} brief were checked."
    parts = []
    if report["missing_mandatory"]:
        parts.append("missing required: " + ", ".join(report["missing_mandatory"]))
    if report["degraded"]:
        parts.append("needs reconnect: " + ", ".join(report["degraded"]))
    if report["missing_recommended"]:
        parts.append("not connected (optional): " + ", ".join(report["missing_recommended"]))
    return f"{role_label} brief — " + "; ".join(parts) + "."


if __name__ == "__main__":
    import sys
    prof = _load(sys.argv[1]) if len(sys.argv) > 1 else _load(os.path.join(ROOT, "schemas", "sample-role-profile.json"))
    m, c = load_matrix(), load_catalog()
    rep = evaluate(prof["role"], prof, m, c)
    print(json.dumps(rep, indent=2))
    print(coverage_note(rep, m))
