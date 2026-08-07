"""Phase 11: plugin structure is valid as a unit test (so `make test` catches it, not only the gate)."""
import os
import sys
import unittest

from _util import REPO

sys.path.insert(0, os.path.join(REPO, "scripts"))
import validate_plugin  # noqa: E402


class TestPluginStructure(unittest.TestCase):
    def test_plugin_validates(self):
        errors = validate_plugin.validate(REPO)
        self.assertEqual(errors, [], f"plugin validation errors: {errors}")

    def test_expected_skills_present(self):
        skills_dir = os.path.join(REPO, "skills")
        present = {d for d in os.listdir(skills_dir) if os.path.isdir(os.path.join(skills_dir, d))}
        for expected in ["daily-brief", "team-brief", "onboarding", "manage-role-profile",
                         "brief-actions", "brief-details", "manage-boo-preferences"]:
            self.assertIn(expected, present)
            self.assertTrue(os.path.isfile(os.path.join(skills_dir, expected, "SKILL.md")))

    def test_manifest_has_name(self):
        import json
        m = json.load(open(os.path.join(REPO, ".claude-plugin", "plugin.json")))
        self.assertEqual(m["name"], "boo")


if __name__ == "__main__":
    unittest.main()
