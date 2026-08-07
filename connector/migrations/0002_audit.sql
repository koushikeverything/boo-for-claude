-- Boo connector schema v2: safe operational audit log.
-- Records only non-sensitive metadata (never tokens, codes, or private message bodies).

CREATE TABLE IF NOT EXISTS audit_log (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    ts         TEXT NOT NULL,
    user_id    TEXT,
    account_id TEXT,
    action     TEXT NOT NULL,   -- e.g. account_connected, account_paused, draft_created, event_created
    meta       TEXT             -- JSON of safe metadata only
);
CREATE INDEX IF NOT EXISTS idx_audit_user ON audit_log(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_ts ON audit_log(ts);
