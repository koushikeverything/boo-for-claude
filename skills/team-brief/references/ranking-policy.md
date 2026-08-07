# Ranking, dedup & conflict policy (role brief)

How candidates become an ordered, de-duplicated, conflict-aware brief. Deterministic so evals can
assert it. Uses `lib/ranking.py` (order) and `lib/xsource.py` (dedup + conflicts).

## Cross-source deduplication (do this BEFORE ranking)

The same real-world thing appears in several tools. Give each a stable `dedup_key` and collapse to
one item with **merged citations** (union across tools). Key conventions (`lib/xsource.py`):

| Thing | Key | Example |
|-------|-----|---------|
| Pull request | `code:pr-<repo>-<num>` | `code:pr-acme-api-514` |
| Tracker issue | `tracking:<key>` | `tracking:grw-231` |
| Incident | `incident:<id>` | `incident:pd-88` |
| Deploy | `deploy:<repo>-<ref>` | `deploy:acme-api-v2` |
| Chat thread | `chat:<channel>-<ts>` | `chat:growth-1700` |

So a PR seen in GitHub, discussed in Slack, and tracked in Linear becomes **one** Top-of-mind item
citing all three. A deploy that shows as a GitHub merge + a Sentry spike + a Slack announce is
related, not three disconnected items.

## Cross-source conflict detection

When sources sharing a `dedup_key` disagree on **done-vs-open** (e.g. Linear marks GRW-231 done but
its GitHub PR is still open), emit a `conflicts[]` entry citing both, and set the item's
`conflict_state: conflicted`. Never pick an unsupported winner — ask the user. (`find_status_conflicts`.)

## Section assignment

- **Top of mind** — actionable, high-consequence, or needs your response soon.
- **FYI** (grouped: Alerts, Deploys, Reviews, Updates, Financial, …) — passive but useful.
- **On your calendar** — chronological local-day schedule (all-day first).

## Role ranking (Top of mind order)

Order is fully deterministic via an explicit `rank` (`lib/ranking.py::rank_items`), computed as:

`(urgency, role capability-priority, effort ascending [null last], title, id)`

- **Urgency dominates** — today items first.
- Within an urgency bucket, the **role's capability priority** decides. For **software_engineer**:
  `incidents > code > chat > tracking > observability > productivity`.
- This is why an **active incident with no effort estimate still ranks first** — capability priority
  beats effort, which the plain urgency/effort rule couldn't express.
- Effort then title/id give a total order.

The validator checks `top_of_mind` is in ascending `rank` order when `rank` is present.

## Confidence gating (unchanged from v1)

A `low`-confidence item may never be `urgency: today`; a financial/metric figure with insufficient
evidence is stated without asserting the number, and logged in `omissions`.
