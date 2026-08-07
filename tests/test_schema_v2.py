"""Phase 1: v2 schema is a working superset of v1, and the semantic validator carries over."""
import copy
import unittest

from _util import load_json, REPO
import validate_brief


def v2_schema():
    return load_json("schemas", "brief.schema.json")


class TestSchemaV2(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = v2_schema()

    def test_engineer_brief_validates(self):
        payload = load_json("evals", "expected-v2", "01-engineer-brief.json")
        errors = validate_brief.validate_payload(self.schema, payload)
        self.assertEqual(errors, [], f"engineer brief failed: {errors}")

    def test_v1_payload_is_a_valid_v2_superset(self):
        # A v1-shaped payload, with only schema_version bumped, must validate against v2.
        v1 = load_json("evals", "expected", "01-reference-brief.json")
        upgraded = copy.deepcopy(v1)
        upgraded["schema_version"] = "2.0"
        errors = validate_brief.validate_payload(self.schema, upgraded)
        self.assertEqual(errors, [], f"v1→v2 superset broke: {errors}")

    def test_widened_source_and_role_accepted(self):
        payload = load_json("evals", "expected-v2", "01-engineer-brief.json")
        self.assertEqual(payload["role"], "software_engineer")
        # sources like github/slack/linear/sentry are only valid under v2's widened enum
        sources = {s["source"] for s in payload["source_status"]}
        self.assertTrue({"github", "slack", "linear", "sentry"} <= sources)

    def test_missing_citation_still_rejected(self):
        payload = load_json("evals", "expected-v2", "01-engineer-brief.json")
        bad = copy.deepcopy(payload)
        bad["top_of_mind"][0]["citations"] = []
        self.assertTrue(validate_brief.validate_payload(self.schema, bad))

    def test_cross_source_attribution_rejected(self):
        payload = load_json("evals", "expected-v2", "01-engineer-brief.json")
        bad = copy.deepcopy(payload)
        bad["top_of_mind"][1]["citations"][0]["account_id"] = "not-a-connected-source"
        errors = validate_brief.validate_payload(self.schema, bad)
        self.assertTrue(any("attribution" in e for e in errors), errors)

    def test_mutating_action_requires_approval(self):
        payload = load_json("evals", "expected-v2", "01-engineer-brief.json")
        bad = copy.deepcopy(payload)
        bad["top_of_mind"][0]["actions"] = [{"type": "draft_reply", "label": "Reply"}]  # no requires_approval
        self.assertTrue(validate_brief.validate_payload(self.schema, bad))

    def test_ordering_enforced_in_v2(self):
        payload = load_json("evals", "expected-v2", "01-engineer-brief.json")
        bad = copy.deepcopy(payload)
        bad["top_of_mind"] = list(reversed(bad["top_of_mind"]))  # break the effort ordering
        errors = validate_brief.validate_payload(self.schema, bad)
        self.assertTrue(any("ordering" in e for e in errors), errors)


if __name__ == "__main__":
    unittest.main()
