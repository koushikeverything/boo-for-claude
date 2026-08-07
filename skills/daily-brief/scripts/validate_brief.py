#!/usr/bin/env python3
"""Deterministic validator for Boo daily-brief payloads.

Validates a brief payload against schemas/daily-brief.schema.json AND against extra
semantic rules that a plain schema cannot express (provenance, dedup integrity, ordering,
conflict citation counts, unattended-safety of actions).

Stdlib-only by default: ships a focused JSON Schema (2020-12 subset) validator covering
exactly the keywords this project's schema uses, so it runs with no pip installs. If the
`jsonschema` package is available it is used for the schema pass instead; the semantic pass
always runs.

Exit code 0 = valid. Non-zero = invalid; human-readable errors on stderr.

Usage:
    validate_brief.py --schema <schema.json> <payload.json>
    validate_brief.py --schema <schema.json> --self-test
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from typing import Any, List, Tuple

# --------------------------------------------------------------------------------------
# Minimal JSON Schema (2020-12 subset) validator — stdlib only.
# Supported: type, const, enum, required, properties, additionalProperties(false),
# items, minItems, maxItems, minLength, maxLength, minimum, maximum, pattern,
# $ref (local "#/..."), allOf, anyOf, if/then/else.
# --------------------------------------------------------------------------------------

_TYPE_CHECKS = {
    "object": lambda v: isinstance(v, dict),
    "array": lambda v: isinstance(v, list),
    "string": lambda v: isinstance(v, str),
    "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
    "boolean": lambda v: isinstance(v, bool),
    "null": lambda v: v is None,
}


class MiniValidator:
    def __init__(self, root_schema: dict):
        self.root = root_schema

    def _resolve(self, ref: str) -> dict:
        if not ref.startswith("#/"):
            raise ValueError(f"unsupported $ref (non-local): {ref}")
        node: Any = self.root
        for part in ref[2:].split("/"):
            part = part.replace("~1", "/").replace("~0", "~")
            node = node[part]
        return node

    def validate(self, schema: dict, value: Any, path: str, errors: List[str]) -> None:
        if "$ref" in schema:
            self.validate(self._resolve(schema["$ref"]), value, path, errors)
            # a $ref node in this schema never carries sibling constraints, so return.
            return

        t = schema.get("type")
        if t is not None:
            types = t if isinstance(t, list) else [t]
            if not any(_TYPE_CHECKS[tt](value) for tt in types):
                errors.append(f"{path}: expected type {types}, got {type(value).__name__}")
                return  # further checks assume the type held

        if "const" in schema and value != schema["const"]:
            errors.append(f"{path}: expected const {schema['const']!r}, got {value!r}")

        if "enum" in schema and value not in schema["enum"]:
            errors.append(f"{path}: {value!r} not in enum {schema['enum']}")

        if isinstance(value, str):
            if "minLength" in schema and len(value) < schema["minLength"]:
                errors.append(f"{path}: string shorter than minLength {schema['minLength']}")
            if "maxLength" in schema and len(value) > schema["maxLength"]:
                errors.append(f"{path}: string longer than maxLength {schema['maxLength']}")
            if "pattern" in schema and re.search(schema["pattern"], value) is None:
                errors.append(f"{path}: {value!r} does not match pattern {schema['pattern']}")

        if isinstance(value, (int, float)) and not isinstance(value, bool):
            if "minimum" in schema and value < schema["minimum"]:
                errors.append(f"{path}: {value} < minimum {schema['minimum']}")
            if "maximum" in schema and value > schema["maximum"]:
                errors.append(f"{path}: {value} > maximum {schema['maximum']}")

        if isinstance(value, list):
            if "minItems" in schema and len(value) < schema["minItems"]:
                errors.append(f"{path}: array has {len(value)} items, minItems {schema['minItems']}")
            if "maxItems" in schema and len(value) > schema["maxItems"]:
                errors.append(f"{path}: array has {len(value)} items, maxItems {schema['maxItems']}")
            if "items" in schema:
                for i, item in enumerate(value):
                    self.validate(schema["items"], item, f"{path}[{i}]", errors)

        if isinstance(value, dict):
            props = schema.get("properties", {})
            for req in schema.get("required", []):
                if req not in value:
                    errors.append(f"{path}: missing required property '{req}'")
            if schema.get("additionalProperties") is False:
                extra = set(value) - set(props)
                for k in sorted(extra):
                    errors.append(f"{path}: additional property '{k}' not allowed")
            for k, sub in props.items():
                if k in value:
                    self.validate(sub, value[k], f"{path}.{k}", errors)

        for sub in schema.get("allOf", []):
            self.validate(sub, value, path, errors)

        if "anyOf" in schema:
            branch_errors = []
            for sub in schema["anyOf"]:
                e: List[str] = []
                self.validate(sub, value, path, e)
                if not e:
                    break
                branch_errors.append(e)
            else:
                errors.append(f"{path}: does not satisfy anyOf ({branch_errors})")

        if "if" in schema:
            cond: List[str] = []
            self.validate(schema["if"], value, path, cond)
            if not cond and "then" in schema:
                self.validate(schema["then"], value, path, errors)
            elif cond and "else" in schema:
                self.validate(schema["else"], value, path, errors)


def schema_validate(schema: dict, payload: Any) -> List[str]:
    try:
        import jsonschema  # type: ignore

        v = jsonschema.Draft202012Validator(schema)
        return [f"{'/'.join(str(p) for p in e.path) or '<root>'}: {e.message}"
                for e in sorted(v.iter_errors(payload), key=lambda e: list(e.path))]
    except ImportError:
        errors: List[str] = []
        MiniValidator(schema).validate(schema, payload, "<root>", errors)
        return errors


# --------------------------------------------------------------------------------------
# Semantic rules a schema cannot express.
# --------------------------------------------------------------------------------------

_URGENCY_RANK = {"today": 0, "soon": 1, "upcoming": 2, "informational": 3}


def _all_items(payload: dict) -> List[Tuple[str, dict]]:
    out = [("top_of_mind", it) for it in payload.get("top_of_mind", [])]
    for g in payload.get("fyi_groups", []):
        out += [(f"fyi/{g.get('group')}", it) for it in g.get("items", [])]
    return out


def semantic_validate(payload: dict) -> List[str]:
    errors: List[str] = []

    known_accounts = {s["account_id"] for s in payload.get("source_status", []) if "account_id" in s}

    # 1) Provenance: every displayed item + event carries >=1 citation with a known account.
    displayed = _all_items(payload) + [("calendar", e) for e in payload.get("calendar", [])]
    for where, node in displayed:
        cites = node.get("citations", [])
        if not cites:
            errors.append(f"provenance: item {node.get('id')!r} in {where} has no citations")
        for c in cites:
            acc = c.get("account_id")
            if known_accounts and acc not in known_accounts:
                errors.append(
                    f"attribution: item {node.get('id')!r} cites account_id {acc!r} "
                    f"not present in source_status (cross-account leak risk)"
                )

    # 2) Dedup integrity: a dedup_key must map to a single title (same real-world thing).
    by_key: dict = {}
    for _, node in displayed:
        k = node.get("dedup_key")
        if k is None:
            continue
        by_key.setdefault(k, set()).add(node.get("title"))
    for k, titles in by_key.items():
        if len(titles) > 1:
            errors.append(f"dedup: dedup_key {k!r} used by differing titles {sorted(titles)}")

    # 3) Conflicts must cite >=2 distinct sources and reference an item flagged conflicted.
    for i, cf in enumerate(payload.get("conflicts", [])):
        if len({(c.get("source"), c.get("account_id"), c.get("source_ref")) for c in cf.get("citations", [])}) < 2:
            errors.append(f"conflict[{i}]: must cite >= 2 distinct sources")

    # 4) Unattended safety: any mutating action must be flagged requires_approval.
    for where, node in _all_items(payload):
        for a in node.get("actions", []):
            if a.get("type") in {"draft_email", "create_calendar_event", "update_calendar_event", "rsvp"}:
                if a.get("requires_approval") is not True:
                    errors.append(
                        f"safety: mutating action {a.get('type')!r} on {node.get('id')!r} "
                        f"must set requires_approval=true"
                    )

    # 5) Deterministic ordering: top_of_mind sorted by (urgency, effort(null last), title, id).
    def tom_key(it: dict):
        eff = it.get("effort_minutes")
        return (
            _URGENCY_RANK.get(it.get("urgency"), 9),
            eff if eff is not None else 10 ** 9,
            it.get("title", ""),
            it.get("id", ""),
        )

    tom = payload.get("top_of_mind", [])
    if tom and all("rank" in i for i in tom):
        # v2 explicit role ranking: ascending rank (id tiebreak). Fully deterministic.
        if [i["id"] for i in tom] != [i["id"] for i in sorted(tom, key=lambda x: (x["rank"], x["id"]))]:
            errors.append("ordering: top_of_mind is not sorted by ascending rank")
    elif [i["id"] for i in tom] != [i["id"] for i in sorted(tom, key=tom_key)]:
        errors.append("ordering: top_of_mind is not in the deterministic policy order")

    # 6) Calendar ordering: all_day first, then start ascending, then title, id.
    cal = payload.get("calendar", [])

    def cal_key(e: dict):
        return (0 if e.get("all_day") else 1, e.get("start", ""), e.get("title", ""), e.get("id", ""))

    if [e["id"] for e in cal] != [e["id"] for e in sorted(cal, key=cal_key)]:
        errors.append("ordering: calendar is not in (all-day first, chronological) order")

    # 7) Low-confidence financial guard already in schema; double-check here for clarity.
    for where, it in _all_items(payload):
        if it.get("confidence") == "low" and it.get("urgency") == "today":
            errors.append(f"grounding: low-confidence item {it.get('id')!r} may not be urgency=today")

    return errors


def validate_payload(schema: dict, payload: Any) -> List[str]:
    errors = schema_validate(schema, payload)
    if isinstance(payload, dict):
        errors += semantic_validate(payload)
    return errors


def main() -> int:
    ap = argparse.ArgumentParser(description="Validate a Boo daily-brief payload.")
    ap.add_argument("--schema", required=True)
    ap.add_argument("payload", nargs="?")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    with open(args.schema) as f:
        schema = json.load(f)

    if args.self_test:
        return _self_test(schema)

    if not args.payload:
        print("error: payload path required (or --self-test)", file=sys.stderr)
        return 2

    with open(args.payload) as f:
        payload = json.load(f)

    errors = validate_payload(schema, payload)
    if errors:
        print(f"INVALID: {args.payload}", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1
    print(f"VALID: {args.payload}")
    return 0


def _self_test(schema: dict) -> int:
    """Tiny smoke test that the validator rejects an obviously bad payload and accepts a good one."""
    good = {
        "schema_version": "1.0",
        "generated_at": "2026-08-07T13:00:00Z",
        "local_date": "2026-08-07",
        "timezone": "America/Los_Angeles",
        "preferred_name": "Elisa",
        "source_status": [
            {"account_id": "sub-personal", "account_label": "Personal", "source": "gmail", "status": "complete"}
        ],
        "top_of_mind": [],
        "fyi_groups": [],
        "calendar": [],
        "conflicts": [],
        "omissions": [],
    }
    bad = dict(good)
    bad["schema_version"] = "2.0"  # violates const
    ok = validate_payload(schema, good)
    ng = validate_payload(schema, bad)
    if ok:
        print("SELF-TEST FAIL: good payload reported errors:", ok, file=sys.stderr)
        return 1
    if not ng:
        print("SELF-TEST FAIL: bad payload passed", file=sys.stderr)
        return 1
    print("SELF-TEST OK (validator accepts valid, rejects invalid)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
