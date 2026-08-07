"""Phase 8: governance enforced in code — no autonomous send/post, every write action needs approval."""
import copy
import unittest

from _util import load_json


def v2_schema():
    return load_json("schemas", "brief.schema.json")


def base():
    return load_json("evals", "expected-v2", "01-engineer-brief.json")


class TestGovernance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = v2_schema()
        import validate_brief
        cls.vb = validate_brief

    def test_no_autonomous_action_types_exist(self):
        enum = self.schema["$defs"]["action"]["properties"]["type"]["enum"]
        for forbidden in ["send", "post", "merge", "close", "delete", "publish", "deploy"]:
            self.assertNotIn(forbidden, enum, f"autonomous action type {forbidden!r} must not exist")

    def test_every_write_action_requires_approval(self):
        writes = ["draft_email", "draft_reply", "create_calendar_event", "update_calendar_event", "comment", "rsvp"]
        for t in writes:
            p = base()
            p["top_of_mind"][0]["actions"] = [{"type": t, "label": "x"}]  # missing requires_approval
            errors = self.vb.validate_payload(self.schema, p)
            self.assertTrue(errors, f"write action {t!r} without approval must be rejected")

    def test_approved_write_action_is_accepted(self):
        p = base()
        p["top_of_mind"][0]["actions"] = [{"type": "draft_reply", "label": "Reply", "requires_approval": True}]
        self.assertEqual(self.vb.validate_payload(self.schema, p), [])

    def test_readonly_actions_need_no_approval(self):
        p = base()
        p["top_of_mind"][0]["actions"] = [{"type": "open_source", "label": "Open PR"}]
        self.assertEqual(self.vb.validate_payload(self.schema, p), [])

    def test_say_command_still_requires_its_phrase(self):
        p = base()
        p["top_of_mind"][0]["actions"] = [{"type": "say_command", "label": "Draft reply"}]  # missing 'say'
        self.assertTrue(self.vb.validate_payload(self.schema, p))


if __name__ == "__main__":
    unittest.main()
