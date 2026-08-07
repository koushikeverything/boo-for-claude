# Schema migration: v1 (daily-brief) → v2 (role/team brief)

v2 (`schemas/brief.schema.json`) is a **structural superset** of v1
(`schemas/daily-brief.schema.json`). The deliberate design goal: **reuse the validator and every
semantic rule unchanged**, so the org brief inherits v1's guarantees for free.

## What stayed the same

- Top-level shape: `generated_at`, `local_date`, `timezone`, `preferred_name`, `source_status`,
  `top_of_mind`, `fyi_groups`, `calendar`, `conflicts`, `omissions`.
- **Field names**: citations and source_status still use `account_id` / `account_label` — in v2
  these mean a **source connection** (e.g. `account_id: "github"`, `account_label: "GitHub"`,
  `workspace: "acme/api"`), not a Google account. This is what lets `validate_brief.py` run
  unchanged: provenance, dedup, ordering, conflicts, unattended-safety, and low-confidence rules all
  key off the same fields.
- All semantic rules (≥1 citation per item, cited account in source_status, deterministic ordering,
  conflicts cite ≥2 sources, mutating actions require approval, low-confidence ≠ today).

## What changed / was added

| Change | v1 | v2 |
|--------|----|----|
| `schema_version` | `"1.0"` | `"2.0"` |
| `source` enum | gmail, calendar, drive | + m365_*, teams, slack, github, gitlab, bitbucket, jira, confluence, linear, asana, notion, pagerduty, opsgenie, datadog, sentry, figma, intercom, zendesk |
| `role` (top-level) | — | optional enum (software_engineer, product_designer, …) |
| `team` (top-level) | — | optional string |
| `capability` | — | optional on source_status / citation / item (productivity, chat, code, tracking, …) |
| `workspace` | — | optional on source_status / citation (repo, channel, project, Figma team) |
| `action.type` | +`draft_reply`, `comment` (both approval-gated) | wider, still drafts/preview-only |
| `omission.category` | + `mandatory_slot_missing` (for role gating) |

## Compatibility guarantee (tested)

- A v1-shaped payload with only `schema_version` bumped to `"2.0"` **validates against v2**
  (`tests/test_schema_v2.py::test_v1_payload_is_a_valid_v2_superset`).
- All 20 v1 golden payloads continue to validate against v1 (`tests/test_acceptance.py`, unchanged).
- The same `validate_brief.py` validates both — it is schema-file-driven and its semantic rules are
  version-agnostic.

## Not a breaking change for the engine

Because field names are stable, none of the deterministic scripts (`validate_brief.py`, `dedup.py`,
`dateutil.py`) needed changes for Phase 1. Role-specific behavior (gating, per-role templates) is
layered on in Phases 2 and 5, not in the schema/validator.
