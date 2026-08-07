# Retrieval policy

Bounded, targeted retrieval for a morning brief. Never a broad mailbox dump. Retain only what is
needed to justify a displayed claim.

## Time window

- Compute the local day from the user's stored **IANA timezone** (e.g. `America/Los_Angeles`).
  The "day" is `[00:00, 24:00)` in that zone. Convert every source timestamp into that zone
  before deciding whether it falls in scope. See `../scripts/dateutil.py` for deterministic
  helpers used by tests.
- **Calendar window:** today (all events) + the next 3 days for near-future items that belong in
  Top of mind (e.g. "swim meet is Sunday").
- **Gmail window:** last 7 days by default (configurable via preferences), plus any message
  explicitly referencing a date in the calendar window.

## Per-account procedure

For every **active** account (skip paused/revoked; record them in `source_status`):

1. **Calendar:** list today's events + near-future events. Capture title, start/end + timezone,
   all-day flag, location, attendees, description (as untrusted context evidence only).
2. **Gmail — targeted categories only.** Query for:
   - explicit deadlines / due dates;
   - bills and scheduled payments;
   - invitations and RSVP requests;
   - deliveries and shipment updates;
   - documents or signatures requested;
   - family / school logistics;
   - travel;
   - event changes / reschedules;
   - messages that clearly need a reply.
3. **Drive:** query **only** for files referenced by an in-scope email/event, or clearly relevant
   to a Top-of-mind item. Capture name, type, owner, modified time, link. **Never** assert file
   contents beyond text the connector actually returns; images in docs are not processed (S6).
4. Preserve every connector **citation** and original **link** on the item.

## Limits (stop conditions)

Documented, deterministic caps so a run is bounded and cheap:

| Dimension | Cap |
|-----------|-----|
| Gmail messages inspected per account | 50 |
| Gmail messages surfaced per account | 15 |
| Calendar events per account (today + 3 days) | 40 |
| Drive files fetched per run | 10 |
| Total Top-of-mind items shown | 6 |
| Total FYI items shown | 12 |

When a cap truncates results, add an `omissions` entry (`category: over_limit`).

## Grounding, dedup, conflicts

- **Ground:** keep a claim only if source text supports it. If an amount/date/attendee is not in
  the source, do not state it. Mark shaky claims `confidence: low` and never as `urgency: today`.
- **Deduplicate:** assign a stable `dedup_key` to each real-world thing (e.g.
  `bill:daycare:2026-08-07`, `event:swim-meet:2026-08-10`). Two sources → one item; merge citations.
  See `../scripts/dedup.py` (used by tests) for the canonical key + merge algorithm.
- **Conflicts:** when sources disagree (e.g. two different dates), emit a `conflicts` entry citing
  both, and set the affected item's `conflict_state` to `conflicted`. Do not pick an unsupported winner.

## Partial coverage

Each `(account, source)` pair gets a `source_status` entry: `complete`, `partial`, or
`unavailable`, with a non-sensitive `safe_reason` when not complete (e.g. "reconnect needed",
"calendar scope not granted"). A single failing pair must not abort the brief.
