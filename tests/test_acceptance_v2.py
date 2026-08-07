"""v2 role/team-brief acceptance eval. Validates each golden payload and applies its checks."""
import os
import unittest

from _util import REPO, load_json
import validate_brief


def v2_schema():
    return load_json("schemas", "brief.schema.json")


def _all_items(payload):
    out = list(payload.get("top_of_mind", []))
    for g in payload.get("fyi_groups", []):
        out += g.get("items", [])
    return out


def _all_actions(payload):
    for it in _all_items(payload):
        for a in it.get("actions", []):
            yield a


def _find_by_dedup(payload, key):
    nodes = _all_items(payload) + list(payload.get("calendar", []))
    return [n for n in nodes if n.get("dedup_key") == key]


class TestAcceptanceV2(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = v2_schema()
        cls.manifest = load_json("evals", "cases", "scenarios-v2.json")

    def _apply(self, payload, check):
        (name, arg), = check.items()
        if name == "role_is":
            self.assertEqual(payload.get("role"), arg)
        elif name == "ranked":
            tom = payload["top_of_mind"]
            self.assertTrue(all("rank" in i for i in tom))
            self.assertEqual([i["id"] for i in tom], [i["id"] for i in sorted(tom, key=lambda x: (x["rank"], x["id"]))])
        elif name == "max_top_of_mind":
            self.assertLessEqual(len(payload["top_of_mind"]), arg)
        elif name == "min_top_of_mind":
            self.assertGreaterEqual(len(payload["top_of_mind"]), arg)
        elif name == "has_conflict":
            self.assertGreaterEqual(len(payload["conflicts"]), 1)
            for cf in payload["conflicts"]:
                ids = {(c.get("source"), c.get("account_id"), c.get("source_ref")) for c in cf["citations"]}
                self.assertGreaterEqual(len(ids), 2)
        elif name == "omission_category":
            self.assertIn(arg, [o.get("category") for o in payload["omissions"]])
        elif name == "no_say_contains":
            for a in _all_actions(payload):
                self.assertNotIn(arg.lower(), (a.get("say") or "").lower())
        elif name == "dedup_citation_count":
            nodes = _find_by_dedup(payload, arg["dedup_key"])
            self.assertEqual(len(nodes), 1)
            self.assertEqual(len(nodes[0]["citations"]), arg["count"])
        elif name == "calendar_all_day_first":
            seen_timed = False
            for e in payload["calendar"]:
                if e["all_day"]:
                    self.assertFalse(seen_timed)
                else:
                    seen_timed = True
        elif name == "action_requires_approval":
            for a in _all_actions(payload):
                if a["type"] in {"draft_email", "draft_reply", "create_calendar_event", "update_calendar_event", "comment", "rsvp"}:
                    self.assertIs(a.get("requires_approval"), True)
        elif name == "capability_status":
            match = [s for s in payload["source_status"]
                     if s.get("capability") == arg["capability"] and s["status"] == arg["status"]]
            self.assertTrue(match, f"no source_status {arg}")
        elif name == "capability_not_active":
            active = [s for s in payload["source_status"]
                      if s.get("capability") == arg and s["status"] in ("complete", "partial")]
            self.assertEqual(active, [], f"expected {arg} to be missing/blocked")
        elif name == "source_present":
            self.assertIn(arg, [s["source"] for s in payload["source_status"]])
        elif name == "distinct_workspaces_min":
            ws = set()
            for it in _all_items(payload):
                if it.get("capability") == arg["capability"]:
                    for c in it.get("citations", []):
                        if c.get("workspace"):
                            ws.add(c["workspace"])
            self.assertGreaterEqual(len(ws), arg["n"], f"workspaces {ws}")
        else:
            self.fail(f"unknown check {name}")

    def test_scenarios(self):
        for sc in self.manifest["scenarios"]:
            with self.subTest(scenario=sc["id"], title=sc["title"]):
                payload = load_json("evals", "expected-v2", sc["file"])
                errors = validate_brief.validate_payload(self.schema, payload)
                self.assertEqual(errors, [], f"{sc['file']} failed validation: {errors}")
                for check in sc.get("checks", []):
                    self._apply(payload, check)

    def test_open_source_actions_have_deep_links(self):
        # Invariant: any item offering an `open_source` action must carry a real permalink in a
        # citation, so `[Open …]` is a live deep-link and never a dead label (retrieval-policy).
        d = os.path.join(REPO, "evals", "expected-v2")
        for f in sorted(os.listdir(d)):
            if not f.endswith(".json"):
                continue
            payload = load_json("evals", "expected-v2", f)
            for it in _all_items(payload):
                if any(a.get("type") == "open_source" for a in it.get("actions", [])):
                    links = [c.get("link") for c in it.get("citations", []) if c.get("link")]
                    self.assertTrue(links, f"{f}: item {it['id']} has open_source but no citation link")

    def test_manifest_covers_all_v2_files(self):
        d = os.path.join(REPO, "evals", "expected-v2")
        on_disk = {f for f in os.listdir(d) if f.endswith(".json")}
        in_manifest = {sc["file"] for sc in self.manifest["scenarios"]}
        self.assertEqual(on_disk, in_manifest, "manifest and expected-v2/ out of sync")


if __name__ == "__main__":
    unittest.main()
