"""Phase 11: bundled skill copies are byte-identical to canonical sources (drift guard in Python)."""
import filecmp
import os
import unittest

from _util import REPO

# Must mirror scripts/bundle_team_brief.sh
TEAM_BRIEF_PAIRS = [
    ("skills/daily-brief/scripts/validate_brief.py", "skills/team-brief/scripts/validate_brief.py"),
    ("skills/daily-brief/scripts/dedup.py", "skills/team-brief/scripts/dedup.py"),
    ("skills/daily-brief/scripts/dateutil.py", "skills/team-brief/scripts/dateutil.py"),
    ("lib/ranking.py", "skills/team-brief/scripts/ranking.py"),
    ("lib/xsource.py", "skills/team-brief/scripts/xsource.py"),
    ("lib/gating.py", "skills/team-brief/scripts/gating.py"),
    ("schemas/brief.schema.json", "skills/team-brief/schemas/brief.schema.json"),
    ("schemas/role-profile.schema.json", "skills/team-brief/schemas/role-profile.schema.json"),
    ("config/capability-catalog.json", "skills/team-brief/config/capability-catalog.json"),
    ("config/role-matrix.json", "skills/team-brief/config/role-matrix.json"),
]


class TestBundleSync(unittest.TestCase):
    def test_team_brief_bundle_identical(self):
        for src, dst in TEAM_BRIEF_PAIRS:
            s, d = os.path.join(REPO, src), os.path.join(REPO, dst)
            self.assertTrue(os.path.exists(d), f"missing bundled file {dst} (run scripts/bundle_team_brief.sh)")
            self.assertTrue(filecmp.cmp(s, d, shallow=False), f"bundle drift: {dst} != {src}")

    def test_daily_brief_schema_bundle_identical(self):
        s = os.path.join(REPO, "schemas", "daily-brief.schema.json")
        d = os.path.join(REPO, "skills", "daily-brief", "schemas", "daily-brief.schema.json")
        self.assertTrue(filecmp.cmp(s, d, shallow=False), "daily-brief bundled schema drifted")


if __name__ == "__main__":
    unittest.main()
