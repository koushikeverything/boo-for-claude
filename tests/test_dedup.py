"""Unit tests for deterministic deduplication."""
import unittest

from _util import SCRIPTS  # noqa: F401  (ensures scripts on path)
import dedup


class TestDedup(unittest.TestCase):
    def test_key_is_stable_and_slugged(self):
        self.assertEqual(dedup.dedup_key("bill", "Daycare Invoice", "2026-08-07"),
                         "bill:daycare-invoice:2026-08-07")
        self.assertEqual(dedup.dedup_key("Bill", "  Daycare   Invoice!! "),
                         "bill:daycare-invoice")

    def test_merge_collapses_same_key_and_unions_citations(self):
        items = [
            {"id": "a", "dedup_key": "k", "urgency": "informational", "confidence": "medium",
             "conflict_state": "none",
             "citations": [{"source": "gmail", "account_id": "p", "source_ref": "1"}]},
            {"id": "b", "dedup_key": "k", "urgency": "today", "confidence": "high",
             "conflict_state": "conflicted",
             "citations": [{"source": "calendar", "account_id": "p", "source_ref": "2"}]},
        ]
        merged = dedup.merge_items(items)
        self.assertEqual(len(merged), 1)
        m = merged[0]
        self.assertEqual(len(m["citations"]), 2)
        self.assertEqual(m["urgency"], "today")        # strongest urgency wins
        self.assertEqual(m["confidence"], "high")       # strongest confidence wins
        self.assertEqual(m["conflict_state"], "conflicted")

    def test_merge_dedups_identical_citations(self):
        cite = {"source": "gmail", "account_id": "p", "source_ref": "1"}
        items = [
            {"id": "a", "dedup_key": "k", "urgency": "today", "confidence": "high",
             "conflict_state": "none", "citations": [dict(cite)]},
            {"id": "b", "dedup_key": "k", "urgency": "today", "confidence": "high",
             "conflict_state": "none", "citations": [dict(cite)]},
        ]
        merged = dedup.merge_items(items)
        self.assertEqual(len(merged[0]["citations"]), 1)

    def test_distinct_keys_preserved_in_order(self):
        items = [
            {"id": "a", "dedup_key": "k1", "urgency": "today", "confidence": "high",
             "conflict_state": "none", "citations": []},
            {"id": "b", "dedup_key": "k2", "urgency": "today", "confidence": "high",
             "conflict_state": "none", "citations": []},
        ]
        merged = dedup.merge_items(items)
        self.assertEqual([m["id"] for m in merged], ["a", "b"])


if __name__ == "__main__":
    unittest.main()
