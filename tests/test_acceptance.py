"""Data-driven acceptance eval.

For every scenario in evals/cases/scenarios.json:
  1. the expected brief payload validates against the schema + semantic rules, and
  2. every declared per-scenario check passes.

Run: python3 -m unittest tests.test_acceptance
"""
import unittest

from _util import REPO, load_json, schema
import validate_brief  # noqa: E402  (path injected by _util)


def _all_actions(payload):
    for it in payload.get("top_of_mind", []):
        for a in it.get("actions", []):
            yield a
    for g in payload.get("fyi_groups", []):
        for it in g.get("items", []):
            for a in it.get("actions", []):
                yield a


def _find_by_dedup(payload, key):
    nodes = list(payload.get("top_of_mind", [])) + list(payload.get("calendar", []))
    for g in payload.get("fyi_groups", []):
        nodes += g.get("items", [])
    return [n for n in nodes if n.get("dedup_key") == key]


class TestAcceptance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = schema()
        cls.manifest = load_json("evals", "cases", "scenarios.json")

    def _apply_check(self, payload, check):
        (name, arg), = check.items()
        if name == "max_top_of_mind":
            self.assertLessEqual(len(payload["top_of_mind"]), arg)
        elif name == "min_top_of_mind":
            self.assertGreaterEqual(len(payload["top_of_mind"]), arg)
        elif name == "has_conflict":
            self.assertGreaterEqual(len(payload["conflicts"]), 1)
            for cf in payload["conflicts"]:
                ids = {(c.get("source"), c.get("account_id"), c.get("source_ref")) for c in cf["citations"]}
                self.assertGreaterEqual(len(ids), 2, "conflict must cite >= 2 distinct sources")
        elif name == "account_status":
            match = [s for s in payload["source_status"]
                     if s["account_id"] == arg["account_id"] and s["source"] == arg["source"]]
            self.assertTrue(match, f"no source_status for {arg}")
            self.assertEqual(match[0]["status"], arg["status"])
        elif name == "omission_category":
            cats = [o.get("category") for o in payload["omissions"]]
            self.assertIn(arg, cats)
        elif name == "no_fyi_group":
            groups = [g["group"] for g in payload["fyi_groups"]]
            self.assertNotIn(arg, groups)
        elif name == "dedup_citation_count":
            nodes = _find_by_dedup(payload, arg["dedup_key"])
            self.assertEqual(len(nodes), 1, f"expected exactly one node for {arg['dedup_key']}")
            self.assertEqual(len(nodes[0]["citations"]), arg["count"])
        elif name == "distinct_accounts_min":
            accts = {s["account_id"] for s in payload["source_status"]}
            self.assertGreaterEqual(len(accts), arg)
        elif name == "action_requires_approval":
            for a in _all_actions(payload):
                if a["type"] in {"draft_email", "create_calendar_event", "update_calendar_event", "rsvp"}:
                    self.assertIs(a.get("requires_approval"), True)
        elif name == "no_say_contains":
            for a in _all_actions(payload):
                say = (a.get("say") or "").lower()
                self.assertNotIn(arg.lower(), say, f"injection leaked into action.say: {a}")
        elif name == "calendar_all_day_first":
            seen_timed = False
            for e in payload["calendar"]:
                if e["all_day"]:
                    self.assertFalse(seen_timed, "all-day event appears after a timed event")
                else:
                    seen_timed = True
        elif name == "item_confidence_not_today":
            for it in payload["top_of_mind"]:
                self.assertFalse(it.get("confidence") == "low" and it.get("urgency") == "today")
        else:
            self.fail(f"unknown check '{name}'")

    def test_scenarios(self):
        for sc in self.manifest["scenarios"]:
            with self.subTest(scenario=sc["id"], title=sc["title"]):
                payload = load_json("evals", "expected", sc["file"])
                errors = validate_brief.validate_payload(self.schema, payload)
                self.assertEqual(errors, [], f"{sc['file']} failed validation: {errors}")
                for check in sc.get("checks", []):
                    self._apply_check(payload, check)

    def test_manifest_covers_all_expected_files(self):
        import os
        expected_dir = os.path.join(REPO, "evals", "expected")
        files_on_disk = {f for f in os.listdir(expected_dir) if f.endswith(".json")}
        files_in_manifest = {sc["file"] for sc in self.manifest["scenarios"]}
        self.assertEqual(files_on_disk, files_in_manifest, "manifest and expected/ dir are out of sync")


if __name__ == "__main__":
    unittest.main()
