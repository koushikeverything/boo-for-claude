# Role pack — superhuman (the many-hats role)

For founders, cofounders, chiefs of staff, and generalists who wear several hats at once. Unlike the
fixed roles, **the user picks their own connector mix** — Boo adapts the brief to whatever they
connected. Only **productivity** (email + calendar) is baseline-mandatory; every other slot is
free-pick optional. See `config/role-matrix.json` → `superhuman`.

## Principle

One brief, several hats. Surface **the single most important item under each hat the user actually
wears** (i.e. each connected capability), rather than a deep list from any one tool. Breadth over
depth — this person's problem is context-switching, not missing detail in one system.

## Slot → section mapping (only for connected slots; skip the rest silently)

| Capability | Top of mind | FYI subgroup | Calendar |
|-----------|-------------|--------------|----------|
| support (Intercom) | customer escalations / churn-risk accounts | **Signals** | — |
| tracking (Jira/Linear/Asana) | decisions blocking a launch or the team | **Updates** | — |
| incidents (PagerDuty) | active incident you own | — | on-call |
| code (GitHub/GitLab) | a review/CI blocking the release | **Deploys** | — |
| design (Figma) | a sign-off design is blocked on | **Updates** | design reviews |
| chat (Slack/Teams) | a decision or reply people are waiting on | **Updates** | — |
| productivity (Google/M365) | an investor/partner/customer reply the mail explicitly asks of you | **Updates** | investor calls, all-hands, 1:1s |
| docs (Notion/Confluence) | — | **Updates** (board deck / spec edits) | — |
| analytics | *hidden — no connector yet; the brief says so* | — | — |

## Top-of-mind ranking (from ranking-policy → `superhuman`)

`incidents > support > tracking > code > design > chat > productivity > observability > docs > analytics`,
within urgency (today first). Rationale: **things blocking other people or the business** (an
incident, a churn-risk customer, a launch decision) rank above the founder's own execution work,
which ranks above pure awareness. No single hat is allowed to dominate the top of the list.

## Onboarding note

Superhuman onboarding presents the **full connectable menu** (every native provider), not a role-
filtered subset — see `skills/onboarding`. The availability gate still hides unconnectable slots
(analytics today). The coverage line names exactly the tools the user picked, e.g. *"Checked Gmail,
Slack, GitHub, Linear, Intercom, Figma and Notion — the tools you picked."*

## Available actions

Same drafts/preview-only, approval-gated matrix as every role (see `engineer.md` and
`../safety-policy.md`). Never send/post/merge; nothing mutates during a scheduled run.

## Coverage specifics

No slot except productivity is mandatory, so there is **no blocking "missing mandatory" gap** beyond
email/calendar. Instead, the coverage line is purely descriptive: it lists the connected hats and
notes any the user connected but that returned nothing, plus the standing analytics gap.
