"""End-to-end proof that a broken/removed account never blocks a healthy one — the core
multi-account guarantee (scenarios 7 and 20)."""
import tempfile
import unittest

from _util import seeded_store, fixtures_client
from boo_connector.tools import ToolContext
from boo_connector.tools import boo_tools as T


class TestIsolation(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store, self.user = seeded_store(self.tmp.name)
        self.ctx = ToolContext(self.store, fixtures_client(), self.user, attended=True)

    def tearDown(self):
        self.tmp.cleanup()

    def test_broken_account_does_not_block_healthy(self):
        personal = T.boo_search_relevant_mail(self.ctx, "sub-personal")
        work = T.boo_search_relevant_mail(self.ctx, "sub-work")
        self.assertEqual(personal["source_status"]["status"], "complete")
        self.assertTrue(personal["items"])
        self.assertEqual(work["source_status"]["status"], "unavailable")  # degraded, not fatal

    def test_removing_one_account_leaves_the_other_fully_functional(self):
        T.boo_update_account_status(self.ctx, "sub-work", "remove")
        accts = {a["account_id"]: a["status"] for a in T.boo_list_accounts(self.ctx)["accounts"]}
        self.assertEqual(accts.get("sub-personal"), "active")
        self.assertNotIn("sub-work", accts)  # removed accounts are hidden from the active list
        # personal still works after the removal
        out = T.boo_search_relevant_mail(self.ctx, "sub-personal")
        self.assertEqual(out["source_status"]["status"], "complete")

    def test_paused_account_is_skipped_but_recoverable(self):
        T.boo_update_account_status(self.ctx, "sub-personal", "pause")
        out = T.boo_list_day_events(self.ctx, "sub-personal", "2026-08-07", "America/Los_Angeles")
        self.assertEqual(out["source_status"]["status"], "unavailable")
        self.assertEqual(out["source_status"]["safe_reason"], "paused")
        T.boo_update_account_status(self.ctx, "sub-personal", "resume")
        out2 = T.boo_list_day_events(self.ctx, "sub-personal", "2026-08-07", "America/Los_Angeles")
        self.assertEqual(out2["source_status"]["status"], "complete")


if __name__ == "__main__":
    unittest.main()
