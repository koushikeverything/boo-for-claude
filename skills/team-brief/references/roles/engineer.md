# Role pack — software_engineer

Ties the engineer's retrieval (`../engineer-sources.md`) and ranking (`../ranking-policy.md`) to
sections and actions. Pilot role.

## Slot → section mapping

| Capability | Top of mind | FYI subgroup | Calendar |
|-----------|-------------|--------------|----------|
| code (GitHub/GitLab) | PRs awaiting **your** review; failing CI on your branches; assigned issues due; change-requests on your PRs | **Reviews** (your mergeable PRs; others' status), **Deploys** (merges/releases) | — |
| incidents (PagerDuty) | active incidents you're on-call for | — | on-call handoff |
| chat (Slack/Teams) | @mentions/threads where you're blocking someone or asked a question | **Updates** | — |
| tracking (Jira/Linear) | issues assigned to you due today; blocked issues | **Updates** (status changes) | — |
| observability (Sentry/Datadog) | (rare) an alert you must act on now | **Alerts** (error spikes, firing monitors) | — |
| productivity (Google/M365) | a security review / reply the mail explicitly asks of you | **Updates** | standup, sprint, 1:1s, interviews |

## Top-of-mind ranking (from ranking-policy)

`incidents > code > chat > tracking > observability > productivity`, within urgency (today first).
An active incident ranks first even with no effort estimate.

## Available actions (drafts / preview only; approval-gated; never unattended)

| Capability | Action | Type | Notes |
|-----------|--------|------|-------|
| chat | Draft a reply | `say_command` → `draft_reply` | preview the draft; on approval, create a **draft**, never post |
| code | Open PR / run / issue | `open_source` | read-only |
| code | Draft a PR review comment | `comment` | preview → approval; creates a **pending** review comment, not submitted |
| tracking | Open issue | `open_source` | read-only |
| tracking | Update issue status | `update_*` | preview → approval |
| productivity | Draft an email | `draft_email` | draft only, never send |
| productivity | Add / change a calendar event | `create_calendar_event` | preview → approval |
| incidents | Acknowledge incident | (approval) | attended only; previewed; never during a scheduled run |

## Example follow-ups the engineer brief should support

- "Why is the CI failure top of mind?" · "Show me PR #514."
- "What came from Slack?" · "What's on my plate from Linear?"
- "Draft a reply to Dana, but show me first."
- "Am I on call today?" (once PagerDuty is connected)
- "What did you leave out?"

## Coverage specifics

If **code** (mandatory) is disconnected → blocking gap: "GitHub isn't connected — your engineering
brief is missing PRs and CI." If PagerDuty is absent (recommended) → "on-call/incidents not included."
