-- Boo connector schema v1
-- Accounts are keyed by Google's stable subject ('sub'), never by email alone.

CREATE TABLE IF NOT EXISTS accounts (
    account_id     TEXT PRIMARY KEY,           -- Google 'sub' (stable, non-secret)
    user_id        TEXT NOT NULL,              -- the Boo/Claude user who owns this connection
    label          TEXT NOT NULL,              -- Personal / Work / Family / School
    email_verified TEXT,                       -- verified email where safely available (display only)
    scopes         TEXT NOT NULL DEFAULT '[]', -- JSON array of granted scopes
    status         TEXT NOT NULL DEFAULT 'active'
                     CHECK (status IN ('active','paused','reconnect_needed','removed')),
    created_at     TEXT NOT NULL,
    updated_at     TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_accounts_user ON accounts(user_id);

-- Refresh tokens live here, encrypted with versioned envelope encryption. Never returned to Claude.
CREATE TABLE IF NOT EXISTS credentials (
    account_id  TEXT PRIMARY KEY REFERENCES accounts(account_id) ON DELETE CASCADE,
    key_version INTEGER NOT NULL,
    ciphertext  TEXT NOT NULL,                 -- base64url envelope token
    updated_at  TEXT NOT NULL
);

-- Single-use OAuth state (replay defense): a jti is recorded once consumed.
CREATE TABLE IF NOT EXISTS oauth_state_consumed (
    jti         TEXT PRIMARY KEY,
    consumed_at TEXT NOT NULL
);
