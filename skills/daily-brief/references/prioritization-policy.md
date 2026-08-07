# Prioritization & section policy

Deterministic section assignment and ordering. Presentation ordering must be stable (same payload
→ same order) so evals can assert it.

## Top of mind (actionable)

Include, in this priority order:

1. Actions **due today** or very soon (bills, forms, signatures).
2. High-consequence items (money, legal, health, missed-deadline risk).
3. Quick actions that remove meaningful friction (< 5 min wins).
4. Unresolved decisions.
5. Messages clearly needing a response.
6. Documents requiring review or signature.

Cap: 6 items. Prefer omission over low-confidence noise.

## FYI (passive), grouped into subgroups

Subgroup order is fixed:

1. **Financial** — scheduled transactions (rent, loans, auto-pay).
2. **RSVP needed** — pending invitations.
3. **Deliveries** — shipment/tracking status.
4. **Deals** — promotions (only if preferences allow; default off is respected).
5. **Updates** — useful non-actionable status changes.

Cap: 12 items total across subgroups. Omit empty subgroups.

## On your calendar (chronological)

- Chronological by local start time.
- **All-day events first**, then timed events ascending.
- Include location and attendees only when relevant.
- Include short, **evidence-backed** context (e.g. "your second visit; the earlier thread mentions
  checking the backyard"). **Never invent a meeting goal or a personal reminder.**
- Flag calendar conflicts and insufficient travel gaps as `conflict_state: conflicted` + a
  `conflicts` entry.

## Deterministic ordering rules (for evals)

- Within Top of mind: sort by `(urgency rank: today<soon<upcoming<informational, then
  effort_minutes ascending with null last, then title)`.
- Within an FYI subgroup: sort by `(urgency rank, then title)`.
- Calendar: `(all_day desc, start ascending, title)`.
- Ties broken by `id` to guarantee total order.

## Confidence gating

- `confidence: low` items may appear only in FYI/Updates or as caveated context, never as a
  `today` action. A financial **amount** with insufficient evidence is shown without asserting the
  number (e.g. "a rent payment appears scheduled — amount not confirmed") and logged in `omissions`.
