"""Tests for the connector doctor — the proactive 'a connector will fail on a missing env var' guard."""
import json
import os
import sys
import tempfile
import unittest

from _util import REPO

sys.path.insert(0, os.path.join(REPO, "scripts"))
import connector_doctor as cd  # noqa: E402


class TestConnectorDoctor(unittest.TestCase):
    def test_vars_in_finds_placeholders(self):
        cfg = {"type": "http", "url": "https://x/${A_TOKEN}", "headers": {"Authorization": "Bearer ${B_KEY}"}}
        self.assertEqual(cd._vars_in(cfg), {"A_TOKEN", "B_KEY"})

    def test_iter_servers_both_shapes(self):
        bare = {"github": {"type": "http", "url": "u"}}
        wrapped = {"mcpServers": {"x": {"command": "y"}}}
        self.assertEqual(dict(cd._iter_servers(bare)).keys(), {"github"})
        self.assertEqual(dict(cd._iter_servers(wrapped)).keys(), {"x"})

    def test_scan_flags_missing_and_set(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, ".mcp.json")
            json.dump({"gh": {"type": "http", "url": "u",
                              "headers": {"Authorization": "Bearer ${DOCTOR_TEST_TOKEN}"}}}, open(path, "w"))
            # ensure unset
            os.environ.pop("DOCTOR_TEST_TOKEN", None)
            findings = cd.scan(files=[path])
            self.assertEqual(len(findings), 1)
            _, name, status = findings[0]
            self.assertEqual(name, "gh")
            self.assertEqual(status, [("DOCTOR_TEST_TOKEN", False)])
            # now set it → reported as set
            os.environ["DOCTOR_TEST_TOKEN"] = "x"
            try:
                _, _, status2 = cd.scan(files=[path])[0]
                self.assertEqual(status2, [("DOCTOR_TEST_TOKEN", True)])
            finally:
                os.environ.pop("DOCTOR_TEST_TOKEN", None)

    def test_claude_path_substitutions_ignored(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, ".mcp.json")
            json.dump({"p": {"command": "${CLAUDE_PLUGIN_ROOT}/bin", "args": ["${CLAUDE_PROJECT_DIR}"]}},
                      open(path, "w"))
            self.assertEqual(cd.scan(files=[path]), [])  # only path substitutions → no real requirement

    def test_known_hint_present_for_github(self):
        self.assertIn("gh auth token", cd.HINTS["GITHUB_PERSONAL_ACCESS_TOKEN"])


if __name__ == "__main__":
    unittest.main()
