# Multi-account support

## The core question and the honest answer

**Can one Claude user connect and query multiple different Google accounts in a single task using
the native Google Workspace connectors?**

Per the official documentation and help center (access date 2026-08-07), this is **not documented**,
and the available guidance indicates the native connector is **single-account per connection** —
switching accounts means disconnect + reconnect. See `docs/PLATFORM-CAPABILITIES.md` for the sourced
matrix. We therefore do **not** assume native multi-account support.

Two consequences:

1. **Mode A** (native) is correct and complete for a **single** account, and remains the default.
2. **Mode B** (the custom multi-account MCP connector) exists specifically to fulfil requirement 2 —
   "all of a person's approved Google accounts, not merely one hard-coded account." It is required,
   not decorative.

## Manual capability test (run when you have access)

**T1 — native multi-account.** With a paid Claude plan:
1. Connect Google account A (native connector). Ask: *"list my next 3 calendar events."*
2. Attempt to also connect a **different** Google account B. Observe whether both remain connected or
   B replaces A.
3. In one conversation ask Boo to read events from **both** A and B.
4. **Record the result** in `docs/PLATFORM-CAPABILITIES.md` (update the T1 row). If both are queryable
   in one task, Mode A can serve multi-account and Mode B becomes optional. If not (expected), Mode B
   is the supported path.

## Multi-account model (Mode B)

Every account has:

- a **stable internal id** = Google's `sub` (never email alone);
- a **user-visible label** (Personal / Work / Family / School);
- **verified email** where safely available (display only);
- **granted capabilities** (gmail / calendar / drive), derived from granted scopes;
- **status**: active · paused · reconnect_needed · removed;
- **independent source health** (per Gmail/Calendar/Drive);
- **independent removal** (deletes that account's encrypted credentials only);
- **independent action targeting**.

A broken account **never** blocks a healthy one — it degrades to partial coverage. Proven by
`connector/tests/test_isolation.py` and scenarios 07 (revoked work) and 20 (removal isolation).

## Account lifecycle commands / tools

| Intent | Mode A | Mode B tool |
|--------|--------|-------------|
| List accounts | connector settings + preferences | `boo_list_accounts` |
| Connect another | connector settings (one account) | connector OAuth connect URL (PKCE + state) |
| Label an account | `manage-boo-preferences` | preferences (label stored per account) |
| Reconnect | connector settings | re-run OAuth; `upsert_account` refreshes scopes |
| Pause / Resume | preferences (intent) | `boo_update_account_status` pause/resume |
| Remove | connector settings | `boo_update_account_status` remove (deletes creds) |
| Default calendar / drafting account | `manage-boo-preferences` | preferences (`default_*_account`) |

## Never guess the destination

When an action (draft or calendar write) could target more than one account, Boo **asks** or uses a
previously confirmed, reviewable routing preference (`default_drafting_account` /
`default_calendar_account`). It never guesses. See scenario 18 (draft requires account selection).
