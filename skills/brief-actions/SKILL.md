---
name: brief-actions
description: Safely act on briefing items through preview-and-approval. Use when the user says "draft a reply to …", "draft the sitter email", "add … to my calendar", "RSVP to …", "update the event", or similar. Always previews the exact change and requires explicit approval before doing anything. Creates Gmail drafts only (never sends). Never runs during an unattended scheduled brief.
---

# Brief actions — preview, approve, then act

Every action here is a real, supported connector operation gated by explicit approval. There are
no fake buttons. Follow `../daily-brief/references/safety-policy.md` and the `CLAUDE.md` invariants.

## Universal flow

1. **Resolve the target** from the brief item (source_ref, account, and any extracted fields).
2. **Choose the account.** If more than one account could be the target, **ask** which one, or use a
   previously confirmed, reviewable routing preference (default drafting / default calendar).
   **Never guess.**
3. **Preview** the exact change (fields below) and the supporting source.
4. **Ask for explicit approval.** Wait for a clear "yes". Do not infer consent from the original
   request when the effect is consequential or ambiguous.
5. **Perform ONE idempotent action** via the connector (Mode A native tool or the Mode B
   `boo_create_*` tool). Use an idempotency key so a retry does not duplicate.
6. **Report the verified result** (draft id / event link) only after the connector confirms success.
   If it fails, say so plainly; never claim success.

## Draft email (drafts only — never send)

Preview must show: **target Google account**, recipient(s), subject, the **full draft body**, the
supporting source, and the statement "This will create a draft in your {account} Gmail. It will
**not** be sent." After approval → create a Gmail **draft** and return the draft location. Boo
never sends.

## Add / change a calendar event

Preview must show: target account **and** calendar, title, date, start/end **with timezone**,
location, guests, recurrence, and the source. After approval → create/update **one** event and
return the event link. For an update, show a before/after diff.

## RSVP, delete, labels, other changes

Same preview → approval → single action → verified result pattern. Deletions and other
irreversible/consequential effects require an especially explicit confirmation and are never
inferred.

## Unattended (scheduled) runs

**Do nothing that mutates.** A scheduled brief runs unattended; there is no human to approve.
Surface the action as a follow-up the user can approve when they open the resulting session, and
stop. This holds regardless of any "approval mode" setting.

## Multi-account safety

- Actions target exactly one account, identified by its stable `account_id` (+ label).
- A paused/removed/reconnect-needed account cannot be an action target; say so and offer to reconnect.
- Confirm the destination account in the preview so the user sees where the change will land.
