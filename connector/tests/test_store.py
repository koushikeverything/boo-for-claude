import os
import tempfile
import unittest

from _util import make_cipher, seeded_store
from boo_connector.store import Store, StoreError


class TestStore(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmp.cleanup()

    def test_migrations_run_and_are_idempotent(self):
        cipher = make_cipher()
        path = os.path.join(self.tmp.name, "m.db")
        s1 = Store(path, cipher)
        # reopening applies no new migrations and still works
        s1.close()
        s2 = Store(path, cipher)
        versions = {r["version"] for r in s2.conn.execute("SELECT version FROM schema_migrations")}
        self.assertEqual(versions, {1, 2})

    def test_credential_roundtrip_is_encrypted_at_rest(self):
        store, user = seeded_store(self.tmp.name)
        row = store.conn.execute(
            "SELECT ciphertext FROM credentials WHERE account_id='sub-personal'"
        ).fetchone()
        self.assertNotIn("FAKE-REFRESH-personal-000", row["ciphertext"])  # stored encrypted
        self.assertEqual(store.load_refresh_token("sub-personal"), "FAKE-REFRESH-personal-000")

    def test_list_accounts_scoped_to_user(self):
        store, user = seeded_store(self.tmp.name)
        accts = store.list_accounts(user)
        self.assertEqual({a.account_id for a in accts}, {"sub-personal", "sub-work"})
        self.assertEqual(store.list_accounts("someone-else"), [])

    def test_remove_account_isolates(self):
        store, user = seeded_store(self.tmp.name)
        store.remove_account("sub-work")
        self.assertFalse(store.has_credentials("sub-work"))          # creds gone
        self.assertTrue(store.has_credentials("sub-personal"))        # other untouched
        labels = {a.account_id: a.status for a in store.list_accounts(user, include_removed=True)}
        self.assertEqual(labels["sub-work"], "removed")
        self.assertEqual(labels["sub-personal"], "active")

    def test_delete_user_removes_all(self):
        store, user = seeded_store(self.tmp.name)
        n = store.delete_user(user)
        self.assertEqual(n, 2)
        self.assertEqual(store.list_accounts(user, include_removed=True), [])

    def test_set_status_validates(self):
        store, user = seeded_store(self.tmp.name)
        with self.assertRaises(StoreError):
            store.set_status("sub-personal", "bogus")
        self.assertEqual(store.set_status("sub-personal", "paused").status, "paused")

    def test_state_single_use_persistence(self):
        store, user = seeded_store(self.tmp.name)
        self.assertFalse(store.is_state_consumed("jti-1"))
        store.mark_state_consumed("jti-1")
        self.assertTrue(store.is_state_consumed("jti-1"))

    def test_audit_records_safe_metadata_only(self):
        store, user = seeded_store(self.tmp.name)
        audit = store.recent_audit(user)
        actions = {a["action"] for a in audit}
        self.assertIn("account_connected", actions)
        # ensure no token material leaked into audit meta
        blob = str(audit)
        self.assertNotIn("FAKE-REFRESH", blob)


if __name__ == "__main__":
    unittest.main()
