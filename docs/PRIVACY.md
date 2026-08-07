# Privacy model

Boo is designed to see as little as possible, keep almost nothing, and never act without you.

## What Boo reads

- **Only** what a morning brief needs: today's/near-future calendar events, and Gmail messages in a
  small set of relevant categories (deadlines, bills, invitations/RSVPs, deliveries, docs/signatures,
  family/school logistics, travel, event changes, replies needed). Drive is queried only for files a
  message/event references. Bounded by documented per-run limits (`skills/daily-brief/references/retrieval-policy.md`).
- No broad mailbox dumps. No scanning of unrelated mail.

## What Boo keeps

- **The brief itself** lives in the Cowork session output.
- **Preferences** live in a user-owned `boo-preferences.json` you can read, edit, export, and delete.
- **Evidence snippets** — Boo retains only the short quote needed to justify a displayed claim, not
  full message bodies. Scheduled runs explicitly avoid copying full sensitive messages.
- **Mode B store** keeps: account id (Google `sub`), label, granted scopes, health, an **encrypted**
  refresh token, single-use OAuth state jtis, and a **safe** audit log (metadata only — never tokens,
  codes, or message contents).

## What Boo never does

- Never **sends** email — Gmail actions create a **draft** only.
- Never mutates anything without a preview and your explicit "yes".
- Never mutates during an **unattended** scheduled run.
- Never exposes refresh tokens, access tokens, OAuth codes, or ciphertext to Claude.
- Never treats email/file/link content as instructions.
- Never puts personal data in URL query strings; never auto-submits forms reached from source links.

## Secrets handling (Mode B)

- Refresh tokens are encrypted with **versioned envelope encryption** before storage
  (`connector/boo_connector/crypto/envelope.py`): per-record random nonce, encrypt-then-MAC
  authentication, key versions for rotation. Keys come from the environment/secret manager, never code.
- Access tokens are used only to sign outbound Google calls inside the connector and are never returned.
- `.env` is never committed; a secret scan runs in the quality gate.

## Your controls

| Action | How |
|--------|-----|
| **View** preferences | "What are my Boo settings?" → returns `boo-preferences.json` |
| **Change** a preference | e.g. "remove shopping deals" — Boo echoes old→new, then saves |
| **Export** | preferences file + (Mode B) `boo_list_accounts` labels/health (no tokens) |
| **Pause / resume / remove** an account | `manage-boo-preferences` / `boo_update_account_status` |
| **Delete** all Boo data | deletes the preferences file; Mode B removes each account's encrypted creds |
| **Revoke Google access** | Claude connector settings (Mode A) and https://myaccount.google.com/permissions (Mode B) |

## Data retention notes

- Agent Skills are **not** covered by zero-data-retention arrangements (per Anthropic docs); Skill
  definitions/execution follow standard retention. Boo minimizes what enters the session accordingly.
- Mode B store retention is operator-controlled; the schema keeps only what's listed above. Removing
  an account deletes its credentials immediately; deleting a user removes all their rows.

## Role brief (v2)

- **Per-viewer scoping.** The role brief is assembled only from tools the user connected with their
  **own** credentials, so it never contains data the user couldn't already see. No service/bot
  identity aggregates across people in v2. This holds for the **⚡ Superhuman** free-pick role too:
  connecting more tools only ever widens the brief within the user's *own* access — it never crosses
  into anyone else's.
- **What Boo keeps:** a reviewable `role-profile.json` (role, team, timezone, brief time, the provider
  chosen per capability slot, per-connection scope, preferences) — the user owns and can edit it. As
  in v1, Boo retains only short `evidence` snippets to justify displayed claims, never full private
  message/PR/ticket/alert bodies.
- **Tokens** for each work tool stay inside that native connector; Boo never sees them and receives
  only tool results.
- **What Boo never does:** send email, post/DM in chat, merge/close/comment-submit in code, or
  resolve/ack incidents autonomously; mutate anything during an unattended run; egress work data.
- **Your controls:** `manage-role-profile` skill — view, edit (role/provider/scope/brief-time),
  pause/resume/remove a tool, **export** the profile, or **delete** it. Revoke a tool's access in
  your connector settings. See `skills/team-brief/references/safety-policy.md`.
