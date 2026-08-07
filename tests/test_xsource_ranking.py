"""Phase 4: cross-source dedup + conflict detection, and role-based ranking (with validator honoring rank)."""
import copy
import os
import sys
import unittest

from _util import REPO, load_json, schema
import validate_brief
import dedup  # from skills/daily-brief/scripts (on path via _util)

sys.path.insert(0, os.path.join(REPO, "lib"))
import ranking  # noqa: E402
import xsource  # noqa: E402


class TestDedupKeys(unittest.TestCase):
    def test_key_builders(self):
        self.assertEqual(xsource.pr_key("acme/api", 514), "code:pr-acme-api-514")
        self.assertEqual(xsource.issue_key("GRW-231"), "tracking:grw-231")
        self.assertEqual(xsource.incident_key("PD-88"), "incident:pd-88")


class TestCrossSourceMerge(unittest.TestCase):
    def test_pr_seen_in_three_tools_collapses_to_one(self):
        key = xsource.pr_key("acme/api", 514)
        items = [
            {"id": "gh", "dedup_key": key, "urgency": "today", "confidence": "high", "conflict_state": "none",
             "citations": [{"source": "github", "account_id": "github", "source_ref": "github:acme/api#514"}]},
            {"id": "sl", "dedup_key": key, "urgency": "soon", "confidence": "medium", "conflict_state": "none",
             "citations": [{"source": "slack", "account_id": "slack", "source_ref": "slack:c/1"}]},
            {"id": "ln", "dedup_key": key, "urgency": "upcoming", "confidence": "low", "conflict_state": "none",
             "citations": [{"source": "linear", "account_id": "linear", "source_ref": "linear:GRW-231"}]},
        ]
        merged = dedup.merge_items(items)
        self.assertEqual(len(merged), 1)
        self.assertEqual(len(merged[0]["citations"]), 3)          # merged provenance across tools
        self.assertEqual(merged[0]["urgency"], "today")           # strongest urgency wins
        self.assertEqual(merged[0]["confidence"], "high")


class TestConflictDetection(unittest.TestCase):
    def setUp(self):
        self.key = xsource.pr_key("acme/api", 514)
        self.items = [
            {"dedup_key": self.key, "source": "github", "account_id": "github", "account_label": "GitHub",
             "source_ref": "github:acme/api#514", "status": "open",
             "urgency": "today", "confidence": "high", "conflict_state": "none", "citations": [
                 {"source": "github", "account_id": "github", "source_ref": "github:acme/api#514"}]},
            {"dedup_key": self.key, "source": "linear", "account_id": "linear", "account_label": "Linear",
             "source_ref": "linear:GRW-231", "status": "done",
             "urgency": "soon", "confidence": "high", "conflict_state": "none", "citations": [
                 {"source": "linear", "account_id": "linear", "source_ref": "linear:GRW-231"}]},
        ]

    def test_done_vs_open_is_a_conflict(self):
        conflicts = xsource.find_status_conflicts(self.items)
        self.assertEqual(len(conflicts), 1)
        self.assertGreaterEqual(len(conflicts[0]["citations"]), 2)

    def test_merge_sets_conflict_state(self):
        merged = xsource.merge_cross_source(self.items, dedup.merge_items)
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]["conflict_state"], "conflicted")

    def test_agreeing_status_no_conflict(self):
        same = copy.deepcopy(self.items)
        same[1]["status"] = "open"
        self.assertEqual(xsource.find_status_conflicts(same), [])


class TestRanking(unittest.TestCase):
    def test_incident_outranks_code_even_with_no_effort(self):
        items = [
            {"id": "c", "capability": "code", "urgency": "today", "effort_minutes": 15, "title": "review"},
            {"id": "i", "capability": "incidents", "urgency": "today", "effort_minutes": None, "title": "incident"},
        ]
        ranked = ranking.rank_items("software_engineer", items)
        order = [it["id"] for it in ranked]
        self.assertEqual(order, ["i", "c"])           # incident first despite null effort
        self.assertEqual(ranked[0]["rank"], 0)

    def test_urgency_dominates_capability(self):
        items = [
            {"id": "soon-incident", "capability": "incidents", "urgency": "soon", "effort_minutes": None, "title": "x"},
            {"id": "today-code", "capability": "code", "urgency": "today", "effort_minutes": 30, "title": "y"},
        ]
        ranked = ranking.rank_items("software_engineer", items)
        self.assertEqual([it["id"] for it in ranked][0], "today-code")  # today beats a 'soon' incident

    def test_engineer_payload_matches_rank_order_and_validates(self):
        payload = load_json("evals", "expected-v2", "01-engineer-brief.json")
        # payload order already equals rank order
        self.assertEqual([i["rank"] for i in payload["top_of_mind"]], [0, 1, 2, 3])
        self.assertEqual(validate_brief.validate_payload(schema_v2(), payload), [])

    def test_validator_flags_broken_rank_order(self):
        payload = load_json("evals", "expected-v2", "01-engineer-brief.json")
        bad = copy.deepcopy(payload)
        bad["top_of_mind"][0], bad["top_of_mind"][1] = bad["top_of_mind"][1], bad["top_of_mind"][0]
        errors = validate_brief.validate_payload(schema_v2(), bad)
        self.assertTrue(any("rank" in e for e in errors), errors)


def schema_v2():
    return load_json("schemas", "brief.schema.json")


if __name__ == "__main__":
    unittest.main()
