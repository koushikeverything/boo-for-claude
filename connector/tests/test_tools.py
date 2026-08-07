import tempfile
import unittest

from _util import seeded_store, fixtures_client
from boo_connector.tools import ToolContext, ToolError
from boo_connector.tools import boo_tools as T


class TestTools(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store, self.user = seeded_store(self.tmp.name)
        self.client = fixtures_client()
        self.ctx = ToolContext(self.store, self.client, self.user, attended=True)

    def tearDown(self):
        self.tmp.cleanup()

    def test_list_accounts_no_secrets(self):
        out = T.boo_list_accounts(self.ctx)
        ids = {a["account_id"] for a in out["accounts"]}
        self.assertEqual(ids, {"sub-personal", "sub-work"})
        self.assertNotIn("FAKE-REFRESH", str(out))
        self.assertNotIn("ciphertext", str(out))

    def test_search_mail_returns_snippets_not_bodies(self):
        out = T.boo_search_relevant_mail(self.ctx, "sub-personal")
        self.assertEqual(out["source_status"]["status"], "complete")
        self.assertTrue(out["items"])
        for it in out["items"]:
            self.assertNotIn("body", it)          # full body only via get_source_details
            self.assertIn("source_ref", it)

    def test_search_mail_isolates_broken_account(self):
        # sub-work gmail fixture is an error; must degrade to unavailable, not raise
        out = T.boo_search_relevant_mail(self.ctx, "sub-work")
        self.assertEqual(out["source_status"]["status"], "unavailable")
        self.assertEqual(out["items"], [])

    def test_source_details_marked_untrusted(self):
        out = T.boo_get_source_details(self.ctx, "sub-personal", "gmail:msg-daycare-001")
        self.assertTrue(out["content_is_untrusted"])
        self.assertIn("body", out["detail"])

    def test_preview_draft_does_not_write(self):
        out = T.boo_preview_gmail_draft(self.ctx, "sub-personal", ["x@example.com"], "Hi", "Body")
        self.assertTrue(out["requires_approval"])
        self.assertEqual(self.client.created_drafts, [])

    def test_create_draft_requires_approval(self):
        with self.assertRaises(ToolError):
            T.boo_create_gmail_draft(self.ctx, "sub-personal", ["x@example.com"], "Hi", "Body",
                                     "idem-1", approved=False)

    def test_create_draft_refused_when_unattended(self):
        unattended = ToolContext(self.store, self.client, self.user, attended=False)
        with self.assertRaises(ToolError):
            T.boo_create_gmail_draft(unattended, "sub-personal", ["x@example.com"], "Hi", "Body",
                                     "idem-1", approved=True)

    def test_create_draft_never_sends_and_is_idempotent(self):
        r1 = T.boo_create_gmail_draft(self.ctx, "sub-personal", ["x@example.com"], "Hi", "Body",
                                      "idem-1", approved=True)
        r2 = T.boo_create_gmail_draft(self.ctx, "sub-personal", ["x@example.com"], "Hi", "Body",
                                      "idem-1", approved=True)
        self.assertFalse(r1["result"]["sent"])
        self.assertEqual(r1["result"]["draft_id"], r2["result"]["draft_id"])  # idempotent
        self.assertEqual(len(self.client.created_drafts), 1)

    def test_calendar_event_requires_approval_and_isolation(self):
        with self.assertRaises(ToolError):
            T.boo_create_calendar_event(self.ctx, "sub-personal", "primary", {"title": "X"},
                                        "idem-e1", approved=False)
        r = T.boo_create_calendar_event(self.ctx, "sub-personal", "primary", {"title": "X"},
                                        "idem-e1", approved=True)
        self.assertIn("event_id", r["result"])

    def test_cannot_draft_from_paused_account(self):
        T.boo_update_account_status(self.ctx, "sub-personal", "pause")
        with self.assertRaises(ToolError):
            T.boo_preview_gmail_draft(self.ctx, "sub-personal", ["x@example.com"], "Hi", "Body")

    def test_update_account_status_lifecycle(self):
        self.assertEqual(T.boo_update_account_status(self.ctx, "sub-work", "pause")["status"], "paused")
        self.assertEqual(T.boo_update_account_status(self.ctx, "sub-work", "resume")["status"], "active")
        self.assertEqual(T.boo_update_account_status(self.ctx, "sub-work", "remove")["status"], "removed")

    def test_tool_rejects_foreign_user_account(self):
        foreign = ToolContext(self.store, self.client, "someone-else", attended=True)
        out = T.boo_search_relevant_mail(foreign, "sub-personal")
        self.assertEqual(out["source_status"]["status"], "unavailable")


if __name__ == "__main__":
    unittest.main()
