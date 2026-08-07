# Role → Tool model (org brief for product teams)

A **role-based team brief** for product companies, shipped in the `boo` plugin. Model A (per-viewer
scoped): each person connects **their own** tools, and their brief contains only what they're already
allowed to see — so access control is solved by construction.

> **Status (2026-08-08): BUILT.** All roles below are implemented (role packs + ranking weights +
> golden payloads), plus a **⚡ Superhuman** free-pick role (see below). The availability gate, gating,
> cross-source dedup/ranking, and card-driven onboarding are done and green (`make check`). The "open
> decisions" at the foot of this doc are resolved; the connector tiers were verified in
> `docs/PLATFORM-CAPABILITIES.md` (Phase 0.3).

## The four layers

1. **Role** — what the person does (Designer, Engineer, Eng Lead, PM, …). Selects a *requirement
   profile* and a *brief template*.
2. **Capability slot** — a job-to-be-done ("design", "code", "chat"), filled by **one of several
   interchangeable providers**. This is where substitution lives (Google *or* M365; Slack *or* Teams).
3. **Requirement level** — per role, each slot is **Mandatory / Recommended / Optional**. Mandatory
   slots gate a "complete" brief.
4. **Scope** — within a chosen provider, which workspaces/repos/projects/channels/files count
   (the "team" dimension).

A per-user `role-profile.json` (the generalization of `boo-preferences.json`) records: role, team,
timezone, brief time, chosen provider per slot, scope, and preferences.

## Capability catalog (the slots + their providers)

| Slot | What it feeds in the brief | Providers | Pick |
|------|----------------------------|-----------|------|
| **productivity** | email, calendar, docs/drive (the brief's spine) | Google Workspace \| Microsoft 365 | exactly 1 |
| **chat** | @mentions, threads needing reply, channel updates | Slack \| Microsoft Teams | 1 (2 allowed) |
| **design** | review requests, comments/mentions, file activity | Figma | 1+ |
| **code** | PRs to review, review comments, CI status, mentions | GitHub \| GitLab \| Bitbucket | 1+ |
| **tracking** | assigned/blocked issues, due items, sprint, status changes | Jira \| Linear \| Asana \| ClickUp | 1+ |
| **docs** | spec/doc changes, mentions | Notion \| Confluence \| Google Docs \| SharePoint | 0+ |
| **incidents** | active incidents, on-call | PagerDuty \| Opsgenie | 0+ |
| **observability** | alerts, error spikes | Datadog \| Sentry \| Grafana | 0+ |
| **support** | escalations, assigned conversations | Intercom \| Zendesk | 0+ |
| **analytics** | metric anomalies, dashboards | Amplitude \| Mixpanel \| PostHog | 0+ |

Note: **productivity is the spine** — email + calendar drive the "On your calendar" and deadline
logic, so it's mandatory for every role regardless of which provider.

## Role × requirement matrix

Legend: **M** = Mandatory (gates a complete brief) · **R** = Recommended (offered, skippable) ·
**O** = Optional · — = not offered.

| Slot \ Role | Designer | Design Lead | Engineer | Eng Lead/Head | PM | Head of Product | QA | Data/Analyst |
|---|---|---|---|---|---|---|---|---|
| productivity | **M** | **M** | **M** | **M** | **M** | **M** | **M** | **M** |
| chat | **M** | **M** | **M** | **M** | **M** | **M** | R | R |
| design (Figma) | **M** | **M** | O | O | R | R | O | — |
| code (GitHub…) | — | O | **M** | **M** | R | O | R | O |
| tracking | R | R | R | **M** | **M** | **M** | **M** | R |
| docs | O | R | O | R | R | R | O | R |
| incidents | — | — | R | **M** | O | O | R | — |
| observability | — | — | R | R | O | — | R | O |
| support | — | O | — | O | R | **M** | O | R |
| analytics | O | R | O | O | R | R | O | R |

> **Invariant:** a slot is **Mandatory** only if at least one of its providers has a native
> connector. Analytics (Amplitude/Mixpanel/PostHog) has **no native connector yet**, so it's
> **Recommended** (not mandatory) for PM/Head/Data until an analytics connector is verified or built
> (Phase 9). Enforced by `tests/test_role_model.py`.

Reading it: **Figma is mandatory for designers; GitHub gets added (mandatory) for engineers and eng
heads; productivity + chat are mandatory across the board; everything else flexes by role.** Exactly
your intent.

### ⚡ Superhuman — the many-hats role

For founders, cofounders, chiefs of staff, and generalists who wear several hats at once. Unlike the
fixed roles, **the user picks their own connector mix**: only **productivity** is baseline-mandatory;
**every other slot is free-pick optional**. Onboarding presents the *full* connectable menu (not a
role-filtered subset); the availability gate still hides unconnectable slots (analytics today). The
brief surfaces **the single most important item under each hat the user actually connected**, ranked
`incidents > support > tracking > code > design > chat > productivity > …` (things blocking other
people or the business first). Role pack: `skills/team-brief/references/roles/superhuman.md`; ranking
weights in `lib/ranking.py`; golden payload `evals/expected-v2/r-superhuman.json`.

## Gating rule (reuses partial-coverage)

- **Brief is "complete"** only when every **M** slot for the role has ≥1 connected, healthy provider.
- A missing **M** slot → the brief still runs, but the coverage line flags a **blocking gap**
  ("Figma isn't connected — your design brief is missing review requests"). Same mechanism as the
  personal brief's `source_status` / coverage line.
- **R** slots → offered in onboarding, skippable, noted in coverage if absent.
- **O** slots → offered, silent if absent.

## Role → brief template (sections adapt, skeleton stays)

Every role renders the same skeleton (Top of mind → FYI → On your calendar → coverage), but each
slot maps to role-specific content and ranking:

| Role | Top of mind (examples) |
|------|------------------------|
| Designer | Figma review requests · @mentions needing a reply · design reviews on calendar · spec changes on your files |
| Engineer | PRs awaiting **your** review · new comments on **your** PRs · failing CI on your branch · issues due today · incidents you're on |
| Eng Lead/Head | Stale PRs on the team · sprint-at-risk (tracking) · open/active incidents · on-call handoffs · blocked stories |
| PM | Decisions needed · blocked stories · launch tasks due · customer escalations (support) · metric anomalies (analytics) |
| Head of Product | Cross-team launch risks · escalations · metric moves · exec-relevant releases |
| QA | Test/regression tickets due · builds ready to test · reopened bugs · release-blocking issues |
| Data/Analyst | Metric anomalies · dashboards flagged · data-request tickets · pipeline alerts |
| ⚡ Superhuman | Top item under each connected hat — e.g. customer escalation · launch decision · PR to review · design sign-off · investor reply |

Same grounding/dedup/conflict/omission rules as v1. Cross-source dedup shines here (a PR discussed in
GitHub + Slack + Linear collapses to one cited item).

## Connector-availability reality (drives the build)

Honest tiering — **native connectors already exist** for most of these in the Claude ecosystem, so
they're orchestration, not new backends. To verify against current docs before committing:

| Tier | Providers |
|------|-----------|
| **Native (confirmed in ecosystem)** | Google Workspace, Slack, GitHub, Linear, Atlassian (Jira/Confluence), Notion, Asana, PagerDuty, Datadog, Intercom, Figma |
| **Verify** | Microsoft 365, Microsoft Teams, GitLab, Bitbucket, Opsgenie, Sentry, Grafana, Zendesk, ClickUp, Amplitude, Mixpanel, PostHog |
| **Likely custom (Mode-B pattern)** | anything in "Verify" without a native connector — **Microsoft 365 / Teams is the key one**, since it's a mandatory-slot substitute for Google/Slack |

So the one substitution that may need a custom connector is exactly your example (M365/Teams). That
becomes the first custom-connector candidate — and reuses the parked Mode B pattern.

## `role-profile.json` (per user; generalizes boo-preferences.json)

```json
{
  "version": "2.0",
  "user": "koushik",
  "role": "product_designer",
  "team": "Growth",
  "timezone": "Asia/Kolkata",
  "brief_time": "08:00",
  "connections": [
    { "capability": "productivity", "provider": "google_workspace", "scope": {}, "status": "active" },
    { "capability": "design", "provider": "figma", "scope": { "teams": ["Growth"], "files": [] }, "status": "active" },
    { "capability": "chat", "provider": "slack", "scope": { "channels": ["#growth", "#design"] }, "status": "active" },
    { "capability": "tracking", "provider": "linear", "scope": { "teams": ["GRW"] }, "status": "active" }
  ],
  "preferences": { "verbosity": "short", "quiet_categories": ["promotions"], "important_projects": ["Zero to One"] }
}
```

## Selection / onboarding flow (logic)

1. Pick **role** + **team**.
2. Show that role's slots grouped **Mandatory → Recommended → Optional**, each listing its provider
   options.
3. Per slot: pick provider(s) (substitution) → connect → optionally set **scope**.
4. Enforce the **gating rule**: can't finish onboarding "complete" until all **M** slots are connected
   (can proceed with gaps, which are flagged).
5. Save `role-profile.json`; the brief runs on the role template.

## What this reuses from v1 (so the build is mostly generalization)

- Brief contract, validator, WAT model, safety model, Cowork scheduling, preference pattern — all carry.
- Schema change: `source` enum widens; `account` → `source_system + workspace`; add `role`, `team`,
  `capability`, `department`. Validator rules unchanged.
- The Skill becomes a **role-parametrized `team-brief`** (role packs as reference files) + a
  `manage-role-profile` skill, shipped in the **`boo` plugin** (add these Skills alongside the
  personal `daily-brief`).

## Decisions (all resolved — see `docs/ORG-BRIEF-BUILD-PLAN.md` §0)

1. ✅ Role list + matrix confirmed (no changes); **⚡ Superhuman** added as a free-pick role.
2. ✅ Connector coverage verified in `docs/PLATFORM-CAPABILITIES.md`; **M365/Teams is native** (one
   connector covers Outlook + Teams + SharePoint) → no custom connector needed; Phase 9 deferred.
3. ✅ **One parametrized `team-brief` skill + per-role reference packs** (role auto-detected from
   `role-profile.json`).
4. ✅ Pilot = **Engineer**; then all roles built. Native-only; the parked Mode B pattern covers any
   future custom source.
