"""Durable, encrypted account store (SQLite) with a tiny migration runner.

Design notes:
  * Refresh tokens are encrypted with the versioned EnvelopeCipher before they touch disk.
  * `load_refresh_token` returns plaintext and is INTERNAL — only the server's token-refresh path
    calls it. MCP tools never do; tokens never reach Claude.
  * `remove_account` deletes credentials and marks the account removed, isolating that account.
  * Only safe metadata is written to the audit log.

SQLite here is the portable default; the same schema/migrations apply to Postgres for production
(swap the connection). See connector/README.md.
"""
from __future__ import annotations

import glob
import json
import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional

from ..crypto import EnvelopeCipher

MIGRATIONS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "migrations")


class StoreError(Exception):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Account:
    account_id: str
    user_id: str
    label: str
    status: str
    scopes: List[str]
    email_verified: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    @property
    def granted_capabilities(self) -> List[str]:
        caps = []
        joined = " ".join(self.scopes)
        if "gmail" in joined:
            caps.append("gmail")
        if "calendar" in joined:
            caps.append("calendar")
        if "drive" in joined:
            caps.append("drive")
        return caps


class Store:
    def __init__(self, db_path: str, cipher: EnvelopeCipher, migrations_dir: str = MIGRATIONS_DIR):
        self.db_path = db_path
        self.cipher = cipher
        self.migrations_dir = migrations_dir
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self._migrate()

    # -- migrations --------------------------------------------------------------------
    def _migrate(self) -> None:
        self.conn.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations (version INTEGER PRIMARY KEY, applied_at TEXT)"
        )
        applied = {r["version"] for r in self.conn.execute("SELECT version FROM schema_migrations")}
        for path in sorted(glob.glob(os.path.join(self.migrations_dir, "*.sql"))):
            version = int(os.path.basename(path).split("_", 1)[0])
            if version in applied:
                continue
            with open(path) as f:
                self.conn.executescript(f.read())
            self.conn.execute(
                "INSERT INTO schema_migrations (version, applied_at) VALUES (?, ?)", (version, _now())
            )
        self.conn.commit()

    # -- accounts ----------------------------------------------------------------------
    def upsert_account(self, account_id: str, user_id: str, label: str, scopes: List[str],
                       email_verified: Optional[str] = None) -> Account:
        now = _now()
        existing = self.get_account(account_id)
        if existing:
            self.conn.execute(
                "UPDATE accounts SET label=?, scopes=?, email_verified=?, status='active', updated_at=? "
                "WHERE account_id=?",
                (label, json.dumps(scopes), email_verified, now, account_id),
            )
            self._audit(user_id, account_id, "account_reconnected", {"label": label})
        else:
            self.conn.execute(
                "INSERT INTO accounts (account_id, user_id, label, email_verified, scopes, status, "
                "created_at, updated_at) VALUES (?, ?, ?, ?, ?, 'active', ?, ?)",
                (account_id, user_id, label, email_verified, json.dumps(scopes), now, now),
            )
            self._audit(user_id, account_id, "account_connected", {"label": label})
        self.conn.commit()
        return self.get_account(account_id)

    def get_account(self, account_id: str) -> Optional[Account]:
        r = self.conn.execute("SELECT * FROM accounts WHERE account_id=?", (account_id,)).fetchone()
        return self._row_to_account(r) if r else None

    def list_accounts(self, user_id: str, include_removed: bool = False) -> List[Account]:
        q = "SELECT * FROM accounts WHERE user_id=?"
        if not include_removed:
            q += " AND status != 'removed'"
        q += " ORDER BY created_at"
        return [self._row_to_account(r) for r in self.conn.execute(q, (user_id,))]

    def set_status(self, account_id: str, status: str) -> Account:
        if status not in ("active", "paused", "reconnect_needed", "removed"):
            raise StoreError(f"invalid status {status!r}")
        acc = self.get_account(account_id)
        if not acc:
            raise StoreError("account not found")
        self.conn.execute(
            "UPDATE accounts SET status=?, updated_at=? WHERE account_id=?", (status, _now(), account_id)
        )
        self._audit(acc.user_id, account_id, f"account_{status}", {})
        self.conn.commit()
        return self.get_account(account_id)

    def remove_account(self, account_id: str) -> None:
        """Delete stored credentials and mark the account removed. Isolated: other accounts untouched.
        The caller should ALSO revoke the Google grant via the live client when enabled."""
        acc = self.get_account(account_id)
        if not acc:
            raise StoreError("account not found")
        self.conn.execute("DELETE FROM credentials WHERE account_id=?", (account_id,))
        self.conn.execute(
            "UPDATE accounts SET status='removed', updated_at=? WHERE account_id=?", (_now(), account_id)
        )
        self._audit(acc.user_id, account_id, "account_removed", {})
        self.conn.commit()

    def delete_user(self, user_id: str) -> int:
        """Full user deletion: remove all their accounts + credentials. Returns count removed."""
        accs = self.list_accounts(user_id, include_removed=True)
        for a in accs:
            self.conn.execute("DELETE FROM credentials WHERE account_id=?", (a.account_id,))
        self.conn.execute("DELETE FROM accounts WHERE user_id=?", (user_id,))
        self._audit(user_id, None, "user_deleted", {"accounts_removed": len(accs)})
        self.conn.commit()
        return len(accs)

    # -- credentials (INTERNAL; never exposed to tools/Claude) --------------------------
    def store_refresh_token(self, account_id: str, refresh_token: str) -> None:
        token = self.cipher.encrypt(refresh_token, aad=account_id.encode("utf-8"))
        self.conn.execute(
            "INSERT INTO credentials (account_id, key_version, ciphertext, updated_at) "
            "VALUES (?, ?, ?, ?) ON CONFLICT(account_id) DO UPDATE SET "
            "key_version=excluded.key_version, ciphertext=excluded.ciphertext, updated_at=excluded.updated_at",
            (account_id, self.cipher.current_version, token, _now()),
        )
        self.conn.commit()

    def load_refresh_token(self, account_id: str) -> str:
        r = self.conn.execute(
            "SELECT ciphertext FROM credentials WHERE account_id=?", (account_id,)
        ).fetchone()
        if not r:
            raise StoreError("no credentials for account")
        return self.cipher.decrypt(r["ciphertext"], aad=account_id.encode("utf-8"))

    def has_credentials(self, account_id: str) -> bool:
        return self.conn.execute(
            "SELECT 1 FROM credentials WHERE account_id=?", (account_id,)
        ).fetchone() is not None

    # -- oauth single-use state --------------------------------------------------------
    def is_state_consumed(self, jti: str) -> bool:
        return self.conn.execute(
            "SELECT 1 FROM oauth_state_consumed WHERE jti=?", (jti,)
        ).fetchone() is not None

    def mark_state_consumed(self, jti: str) -> None:
        self.conn.execute(
            "INSERT OR IGNORE INTO oauth_state_consumed (jti, consumed_at) VALUES (?, ?)", (jti, _now())
        )
        self.conn.commit()

    # -- audit -------------------------------------------------------------------------
    def _audit(self, user_id: Optional[str], account_id: Optional[str], action: str, meta: dict) -> None:
        self.conn.execute(
            "INSERT INTO audit_log (ts, user_id, account_id, action, meta) VALUES (?, ?, ?, ?, ?)",
            (_now(), user_id, account_id, action, json.dumps(meta)),
        )

    def recent_audit(self, user_id: str, limit: int = 50) -> List[dict]:
        rows = self.conn.execute(
            "SELECT ts, account_id, action, meta FROM audit_log WHERE user_id=? ORDER BY id DESC LIMIT ?",
            (user_id, limit),
        )
        return [{"ts": r["ts"], "account_id": r["account_id"], "action": r["action"],
                 "meta": json.loads(r["meta"] or "{}")} for r in rows]

    def close(self) -> None:
        self.conn.close()

    @staticmethod
    def _row_to_account(r: sqlite3.Row) -> Account:
        return Account(
            account_id=r["account_id"], user_id=r["user_id"], label=r["label"], status=r["status"],
            scopes=json.loads(r["scopes"]), email_verified=r["email_verified"],
            created_at=r["created_at"], updated_at=r["updated_at"],
        )
