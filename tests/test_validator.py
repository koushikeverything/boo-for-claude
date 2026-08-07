"""Unit tests for the deterministic brief validator.

Asserts the validator ACCEPTS a well-formed payload and REJECTS each class of defect the
semantic rules exist to catch. Run: python3 -m unittest tests.test_validator
"""
import copy
import unittest

from _util import load_json, schema
import validate_brief


def base_payload():
    # A minimal valid payload with one citable account and one item.
    return {
        "schema_version": "1.0",
        "generated_at": "2026-08-07T13:00:00-07:00",
        "local_date": "2026-08-07",
        "timezone": "America/Los_Angeles",
        "preferred_name": "Test",
        "source_status": [
            {"account_id": "sub-a", "account_label": "A", "source": "gmail", "status": "complete"}
        ],
        "top_of_mind": [
            {
                "id": "i1",
                "title": "Do the thing",
                "detail": "detail",
                "section": "top_of_mind",
                "citations": [
                    {"source": "gmail", "account_id": "sub-a", "account_label": "A", "source_ref": "gmail:1"}
                ],
                "urgency": "today",
                "confidence": "high",
                "effort_minutes": 5,
                "conflict_state": "none",
                "dedup_key": "task:thing:2026-08-07",
            }
        ],
        "fyi_groups": [],
        "calendar": [],
        "conflicts": [],
        "omissions": [],
    }


class TestValidator(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = schema()

    def assertValid(self, payload):
        self.assertEqual(validate_brief.validate_payload(self.schema, payload), [])

    def assertInvalid(self, payload, needle):
        # Case-insensitive substring match so the assertion holds under both the stdlib
        # validator and the optional `jsonschema` fast-path (their wording differs).
        errors = validate_brief.validate_payload(self.schema, payload)
        self.assertTrue(errors, "expected errors but got none")
        n = needle.lower()
        self.assertTrue(any(n in e.lower() for e in errors), f"no error matching {needle!r} in {errors}")

    def test_base_is_valid(self):
        self.assertValid(base_payload())

    def test_reference_brief_is_valid(self):
        self.assertValid(load_json("evals", "expected", "01-reference-brief.json"))

    def test_wrong_schema_version_rejected(self):
        p = base_payload()
        p["schema_version"] = "9.9"
        self.assertInvalid(p, "expected")

    def test_missing_citation_rejected(self):
        p = base_payload()
        p["top_of_mind"][0]["citations"] = []
        self.assertInvalid(p, "citation")

    def test_cross_account_citation_rejected(self):
        p = base_payload()
        p["top_of_mind"][0]["citations"][0]["account_id"] = "sub-unknown"
        self.assertInvalid(p, "attribution")

    def test_mutating_action_without_approval_rejected(self):
        p = base_payload()
        p["top_of_mind"][0]["actions"] = [{"type": "create_calendar_event", "label": "Add"}]
        # schema requires requires_approval=true for mutating actions
        self.assertInvalid(p, "requires_approval")

    def test_conflict_with_single_source_rejected(self):
        p = base_payload()
        p["conflicts"] = [
            {
                "description": "x",
                "citations": [
                    {"source": "gmail", "account_id": "sub-a", "account_label": "A", "source_ref": "gmail:1"},
                    {"source": "gmail", "account_id": "sub-a", "account_label": "A", "source_ref": "gmail:1"},
                ],
            }
        ]
        self.assertInvalid(p, "distinct sources")

    def test_low_confidence_today_rejected(self):
        p = base_payload()
        p["top_of_mind"][0]["confidence"] = "low"
        # schema-level if/then also forbids this; semantic rule reinforces it
        errors = validate_brief.validate_payload(self.schema, p)
        self.assertTrue(errors)

    def test_top_of_mind_out_of_order_rejected(self):
        p = base_payload()
        p["top_of_mind"].append(
            {
                "id": "i0",
                "title": "Earlier by urgency",
                "detail": "d",
                "section": "top_of_mind",
                "citations": [{"source": "gmail", "account_id": "sub-a", "account_label": "A", "source_ref": "gmail:2"}],
                "urgency": "today",
                "confidence": "high",
                "effort_minutes": 1,
                "conflict_state": "none",
                "dedup_key": "task:earlier:2026-08-07",
            }
        )
        # i0 (effort 1) should sort before i1 (effort 5); appended out of order → error
        self.assertInvalid(p, "ordering")

    def test_dedup_key_collision_rejected(self):
        p = base_payload()
        p["fyi_groups"] = [
            {
                "group": "Financial",
                "items": [
                    {
                        "id": "i2",
                        "title": "A different title, same key",
                        "detail": "d",
                        "section": "fyi",
                        "citations": [{"source": "gmail", "account_id": "sub-a", "account_label": "A", "source_ref": "gmail:3"}],
                        "urgency": "informational",
                        "confidence": "high",
                        "effort_minutes": None,
                        "conflict_state": "none",
                        "dedup_key": "task:thing:2026-08-07",
                    }
                ],
            }
        ]
        self.assertInvalid(p, "dedup")

    def test_additional_property_rejected(self):
        p = base_payload()
        p["surprise"] = True
        self.assertInvalid(p, "additional propert")


if __name__ == "__main__":
    unittest.main()
