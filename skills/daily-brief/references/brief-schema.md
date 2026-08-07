# Brief schema (human guide)

The machine-checkable contract is the bundled `schemas/daily-brief.schema.json` at the skill root
(JSON Schema 2020-12), which is byte-identical to the plugin's canonical
`schemas/daily-brief.schema.json`. This file is the human-readable companion; the JSON schema is
authoritative.

## Top-level object

| Field | Meaning |
|-------|---------|
| `schema_version` | Always `"1.0"`. Bump only with a migration note. |
| `generated_at` | ISO-8601 timestamp of generation. |
| `local_date` | `YYYY-MM-DD`, the covered local day. |
| `timezone` | IANA zone used to compute the day. |
| `preferred_name` | For the greeting. |
| `source_status[]` | Per-(account, source) health: complete / partial / unavailable. |
| `top_of_mind[]` | Actionable items (see item). |
| `fyi_groups[]` | `{ group, items[] }` subgroups. |
| `calendar[]` | Chronological events. |
| `conflicts[]` | Cross-source contradictions, each citing >= 2 sources. |
| `omissions[]` | What was left out and why. |

## item

Required: `id`, `title`, `detail`, `section`, `citations[>=1]`, `urgency`, `confidence`,
`dedup_key`, `conflict_state`. Optional: `evidence`, `when`, `effort_minutes`, `actions[]`.

Rules the validator enforces beyond raw types:
- `citations` must be non-empty (every displayed claim has provenance).
- A `say_command` action must include `say`.
- Any mutating action (`draft_email`, `create_calendar_event`, `update_calendar_event`, `rsvp`)
  must set `requires_approval: true`.
- A `low`-confidence item may not be `urgency: today` (financial-amount safety).

## calendar_event

Required: `id`, `title`, `citations[>=1]`, `all_day`, `dedup_key`. Optional: `start`, `end`,
`timezone`, `duration_minutes`, `location`, `attendees[]`, `context`, `conflict_state`.

## citation

Required: `source`, `account_id`, `account_label`. Optional: `source_ref` (resolvable, non-secret
id used by follow-ups and "Open …"), `link` (native connector URL).

## Versioning

`schema_version` is `"1.0"`. Any breaking change increments the major and ships a migration note in
`docs/ARCHITECTURE.md`. Additive optional fields may ship as `1.x` without breaking validation.
