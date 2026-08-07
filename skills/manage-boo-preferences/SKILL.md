---
name: manage-boo-preferences
description: View, change, export, or delete the user's Boo planning preferences, and manage connected accounts. Use when the user says "move my brief to 7:30 AM", "remove shopping deals from future briefs", "rename my work account", "pause my work account", "set my default calendar", "what are my Boo settings?", "connect another account", or "delete my Boo data". Preference changes are explicit, reviewable, reversible, and scoped — never inferred from one ambiguous request.
---

# Manage Boo preferences & accounts

Preferences are a small, human-readable JSON document the user owns and can review. This skill
reads and edits it, and manages the connected-account list. Nothing here is silent or inferred.

## Where preferences live

A reviewable `boo-preferences.json` (schema: `references/preferences.schema.json`,
sample: `references/sample-preferences.json`). Store it in a platform-supported, user-controlled
location:

- **Recommended:** a file saved to the user's Claude account / Google Drive so scheduled Cowork
  runs can read it (a purely local file cannot be reached by a remote scheduled task — see
  `docs/PLATFORM-CAPABILITIES.md`).
- Optionally mirror the preferred name / timezone / brief time into **Claude Memory** for
  convenience, but the JSON file is the source of truth the user can inspect and edit.

## Preference model (summary — schema is authoritative)

preferred_name · timezone (IANA) · brief_time · weekday/weekend behavior · active accounts +
labels · default_calendar_account · default_drafting_account · included/excluded FYI categories ·
urgency rules · important people/topics · verbosity · show_deals (default false).

## How to change a preference

1. Read the current `boo-preferences.json`.
2. **Echo the specific change** you're about to make (old → new) and its scope (e.g. "future briefs
   only").
3. Apply the change to the JSON and save it back.
4. Confirm, and note it's reversible ("say 'undo that' or 'set deals back on'").

Examples:
- "Move the brief to 7:30 AM" → set `brief_time` to `07:30`. (The **schedule time itself** lives in
  the Cowork task; remind the user to update the scheduled task time too — see `docs/SETUP-SCHEDULE.md`.)
- "Remove shopping deals" → set `show_deals: false` / add `"deals"` to `excluded_fyi_categories`.
- "Mark anything from my kids' school as important" → add to `important_topics`.

## Managing accounts

Support: **list**, **connect another**, **label**, **reconnect**, **pause**, **resume**, **remove**,
choose **default calendar**, choose **default drafting account**.

- **Mode A (native):** connecting/removing an account happens in Claude's connector settings; this
  skill records the **label**, **default routing**, and **active/paused** intent in preferences, and
  explains the connector step to the user.
- **Mode B (multi-account connector):** call the connector tools — `boo_list_accounts` to list,
  `boo_update_account_status` to pause/resume/remove, and the connector's OAuth connect URL to add
  one. Each account keeps a stable id, label, granted scopes, and health. Removing or pausing one
  account never affects the others.

A paused or removed account is skipped in future briefs and can never be an action target until
resumed/reconnected.

## Export & delete (user rights)

- **Export:** return the `boo-preferences.json` contents and (Mode B) the account list from
  `boo_list_accounts` (labels + health only, never tokens).
- **Delete:** on request, delete the preferences file and, in Mode B, call the connector's account
  removal for each account (which deletes stored encrypted credentials and revokes the Google
  grant). Confirm what will be deleted before doing it. See `docs/PRIVACY.md`.
