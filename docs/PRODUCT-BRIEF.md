# Product brief — Boo for Claude

## The idea

Boo turns scattered Google Workspace information into one trustworthy morning briefing, delivered
**inside Claude**. The original Boo mailed you a digest; the Claude-native version makes the brief
the *start* of a working session — you can immediately ask why something matters, open the source,
draft a reply, or add an event, all with citations and explicit approval.

## Outcomes (the product must)

1. Read relevant info from Gmail, Google Calendar, and Google Drive.
2. Support **all** of a person's approved Google accounts, not one hard-coded account.
3. Produce a concise, evidence-grounded "Your day ahead" briefing.
4. Deliver it inside Claude as a **scheduled Cowork result** (not an email).
5. Support follow-up questions in the resulting session.
6. Let the user act via natural language or real supported controls.
7. Create Gmail **drafts** — never send.
8. Require explicit approval before create/update/delete.
9. Keep source citations + account attribution for every material claim.
10. Handle missing permissions, empty sources, revoked accounts, conflicts, and partial results honestly.

## Information hierarchy (preserved from the reference design)

Your day ahead → personal greeting → **Top of mind** → **FYI** (Financial / RSVP needed /
Deliveries / Deals / Updates) → **On your calendar** → short closing coverage line.

Rendered as native Claude Markdown: scannable entries, bold only for key actions/amounts/deadlines/
event titles, effort estimates, secondary-but-present citations, connected-account attribution,
real actions or clearly-worded follow-up commands. **No** Gmail chrome, sender headers, agent
mailbox, email footer, or fake chips. The canonical target is
[`../skills/daily-brief/examples/reference-brief.md`](../skills/daily-brief/examples/reference-brief.md).

## Critical architectural principle

A Skill is **not** a background service or OAuth provider. SKILL.md alone cannot schedule itself,
hold OAuth tokens, connect multiple Google identities, keep durable state, push into an existing
chat, or bypass connector approvals. We therefore use each ecosystem primitive for its real purpose:

- **Agent Skill** → briefing policy, retrieval strategy, output contract, safety rules, workflows,
  examples, deterministic validation scripts.
- **Cowork scheduled task** → daily execution + delivery into Claude.
- **Native Google connectors** → preferred source/action layer (single account).
- **Plugin** → distributable bundle of Skills (+ optional connector reference).
- **Custom remote MCP connector** → only for the multi-account identity/state/retrieval that native
  connectors don't support.
- **Reviewable preference file / Memory** → user preferences, through user-controllable mechanisms.

## WAT operating model

- **Workflows** — deterministic Markdown policies (`skills/*`): brief generation, details,
  preference update, account connection, safe actions, scheduled execution, deletion.
- **Agent** — the model: relevance, extraction, ambiguity resolution (only when supported), ranking,
  summarizing. Never stores secrets, never bypasses approvals.
- **Tools** — deterministic code/connectors (`connector/`, `skills/daily-brief/scripts/`): connector
  calls, OAuth, token encryption, schema validation, normalization, dedup, date handling, account
  scoping, action execution.

## Success criteria (measurable)

No unsupported facts · every displayed claim has provenance · no cross-account confusion ·
deterministic section ordering · correct timezone boundaries · correct deduplication · partial
failures visible · prompt-injection text ignored · unattended runs perform no mutations · Gmail
actions produce a draft, never a send. These are enforced by `scripts/validate_brief.py` and the
`tests/` + `connector/tests/` suites — not by model judgement where code can decide.
