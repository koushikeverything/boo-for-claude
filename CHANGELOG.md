# Changelog

All notable changes to the **Boo for Claude** plugin. Format follows
[Keep a Changelog](https://keepachangelog.com/); this project uses semantic-ish versioning while
pre-1.0 (minor = features, patch = fixes/docs).

## [0.3.0] — 2026-08-08

### Added
- **⚡ Superhuman role** — a free-pick "many hats" role (founders/generalists). Only productivity is
  baseline-mandatory; every other slot is optional, so the user connects any mix. Wired end-to-end:
  role matrix, ranking weights, role pack, golden payload, and role enum.
- **Card-driven Cowork onboarding** — setup is now a sequence of native selection cards (role →
  connect tools → delivery time → sources), completed by clicking; writes a reviewable
  `role-profile.json`.
- **Deep-link invariant** — every item that offers an "Open …" action carries a real source permalink;
  otherwise it falls back to an in-chat action. Enforced by `tests/test_acceptance_v2.py` and the
  retrieval policy (per-source permalink shapes documented).
- **Local marketplace** — `.claude-plugin/marketplace.json` for one-command install.

### Changed
- **Documentation (Phase 14)** brought fully current: README (v2 status, 9 roles, Model-A delivery),
  ARCHITECTURE (role/team-mode role-flow + card-onboarding diagrams, v2 schema/invariants),
  ROLE-TOOL-MODEL (built + Superhuman), LIMITATIONS, SETUP-CLAUDE/SCHEDULE, PRIVACY/THREAT-MODEL.

### Notes
- Native-only, per-viewer scoping (Model A). Mode B multi-account connector remains built +
  fixtures-tested but **parked** (needs a Google OAuth app + HTTPS host).
- Green: **123 tests** (72 skill + 51 connector) via `make check`.

## [0.2.0] — 2026-08-07

### Added
- **v2 role/team brief** (`skills/team-brief`) for product teams — **8 roles** (Product Designer,
  Design Lead, Software Engineer, Engineering Lead, Product Manager, Head of Product, QA Engineer,
  Data/Analyst) across native connectors (GitHub/GitLab, Slack/Teams, Google/M365, Jira/Linear,
  PagerDuty, Sentry/Datadog, Figma, Notion, Intercom).
- **Role & capability model** (`config/`), **availability gate** (`lib/gating.py`), cross-source
  dedup/conflict (`lib/xsource.py`), role-aware ranking (`lib/ranking.py`).
- Companion skills: `onboarding`, `manage-role-profile`. **16 v2 golden payloads** + acceptance harness.
- v2 schema (`schemas/brief.schema.json`) as a structural superset of v1.

### Changed
- Plugin grows to **7 Skills**; standalone `team-brief` ZIP added.

## [0.1.0] — 2026-08-07

### Added
- **v1 personal "Your day ahead"** brief across Google Workspace (Gmail, Calendar, Drive) — delivered
  inside Claude as a scheduled Cowork result, drafts-only, approval-gated.
- Skills: `daily-brief`, `brief-details`, `brief-actions`, `manage-boo-preferences`. Versioned brief
  schema + deterministic validator; **20 eval scenarios**.
- **Mode B** multi-account MCP connector (crypto, OAuth PKCE/state, encrypted store, narrow tools,
  isolation) — fully tested against fixtures.

[0.3.0]: #030--2026-08-08
[0.2.0]: #020--2026-08-07
[0.1.0]: #010--2026-08-07
