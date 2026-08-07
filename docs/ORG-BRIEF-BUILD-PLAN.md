# Org/role brief — full build plan (to shipped plugin)

Everything left to build for the **role-based team brief** (v2, Model A: per-viewer scoped),
from here to shipping as a plugin. Dry runs are first-class tasks. Checkboxes track status.

**Reused from v1 (already built + tested — do NOT rebuild):** WAT model, brief validator core
(provenance/dedup/ordering/conflicts/unattended-safety), the dedup engine, the safety model
(untrusted content, drafts-only, approval-gated mutations, partial-coverage honesty), Cowork
scheduling, the preference/profile pattern, the Mode-B connector pattern (for any custom source),
the quality-gate + packaging scripts.

Legend: `[ ]` todo · `[~]` conditional/decision-gated · acceptance criteria in _italics_.

---

## Phase 0 — Decisions & verification (unblocks everything)

- [ ] 0.1 Confirm the **role list** and the **M/R/O matrix** in `ROLE-TOOL-MODEL.md` (add/cut roles: Founder/Exec? Marketing?).
- [ ] 0.2 Pick the **pilot role** (recommendation: Designer or Engineer — full native connector coverage).
- [ ] 0.3 **Verify connector coverage** against current official docs for every provider; record a matrix (native? scopes? read/write? multi-workspace? citations? rate limits?) in `docs/PLATFORM-CAPABILITIES.md`.
  - [ ] Confirmed-native set: Google, Slack, GitHub, Linear, Atlassian, Notion, Asana, PagerDuty, Datadog, Intercom, Figma.
  - [ ] Verify tier: **Microsoft 365, Teams**, GitLab, Bitbucket, Opsgenie, Sentry, Grafana, Zendesk, ClickUp, Amplitude, Mixpanel, PostHog.
- [ ] 0.4 Decide **M365/Teams path**: native connector, or custom (Graph API) via the Mode-B pattern.
- [ ] 0.5 Decide skill structure: **one parametrized `team-brief` skill + role packs** (recommended) vs per-role skills.
- [ ] 0.6 Decide provider set for the pilot (mandatory + a couple optional) to bound the first build.
- _Acceptance: matrix confirmed, pilot role chosen, connector coverage documented with sources + access date, M365 decision recorded._

**Phase 0 — DONE (2026-08-07):**
- 0.1 ✅ role matrix confirmed (no changes). 0.2 ✅ **pilot = Engineer**.
- 0.3 ✅ connector coverage documented in `PLATFORM-CAPABILITIES.md` — **every Engineer slot is
  native**, in both provider options.
- 0.4 ✅ **M365/Teams = native** (one M365 connector covers Outlook + Teams + SharePoint + OneDrive)
  → **no custom connector needed; Phase 9 skipped for the pilot.**
- 0.5 ✅ decision: **one parametrized `team-brief` skill + per-role reference packs** (maintainable;
  role auto-detected from `role-profile.json`).
- 0.6 ✅ pilot providers (defaults): **GitHub** (code, M), **Google Workspace** (productivity, M),
  **Slack** (chat, M), + recommended **Linear**, **PagerDuty**, **Sentry/Datadog**. Substitutes
  (GitLab / M365+Teams) supported by the same slots.

## Phase 1 — Schema & contract generalization (v2)

- [x] 1.1 `schemas/brief.schema.json` v2 — widened `source` enum; `role`/`team`/`capability`/`workspace` added; superset of v1 (same field names).
- [x] 1.2 Validator unchanged — v2 uses the same field names, so all semantic rules carry over; verified against the engineer payload.
- [x] 1.3 `docs/SCHEMA-MIGRATION-v1-v2.md` written; v1→v2 superset compatibility tested.
- [~] 1.4 Bundle-copy into the skill — deferred to Phase 6 (when the `team-brief` skill is created).
- [x] 1.5 `tests/test_schema_v2.py` — engineer brief validates; v1 payload validates as v2 superset; missing-citation / cross-source-attribution / mutating-action / ordering all rejected.
- _Acceptance: **MET** — v2 schema + validator pass; engineer golden payload valid; v1 payloads still validate; gate step 5b added._

**Phase 1 — DONE (2026-08-07):** 28 skill tests pass (21 v1 + 7 v2); engineer brief in `evals/expected-v2/`.

## Phase 2 — Role & capability model

- [x] 2.1 `config/capability-catalog.json` — 10 slots, 25 providers, cardinality, provider→source map.
- [x] 2.2 `config/role-matrix.json` — 8 roles → slot requirement (M/R/O), with the native-provider invariant.
- [x] 2.3 `schemas/role-profile.schema.json` + `schemas/sample-role-profile.json`.
- [x] 2.4 `lib/gating.py` — evaluate(role, profile) → connected/missing_mandatory/missing_recommended/degraded/problems + coverage_note.
- [x] 2.5 `tests/test_role_model.py` — catalog integrity (providers defined, sources in brief schema, min/max sane), matrix integrity (productivity always mandatory; every mandatory slot has a native provider), profile schema, and gating behavior.
- _Acceptance: **MET** — catalog + matrix cross-validate; gating deterministically flags missing mandatory slots; integrity test caught + fixed the analytics-has-no-native-connector case._

**Phase 2 — DONE (2026-08-07):** 41 skill tests pass (28 + 13 role-model). Key finding: analytics has no native connector → downgraded to recommended (invariant enforced in code).

## Phase 3 — Retrieval adapters (per capability/provider)

For each provider in the pilot scope (then expand):

- [x] 3.1 Normalized item contract — `skills/team-brief/references/retrieval-policy.md` (maps onto brief.schema.json).
- [x] 3.2 Retrieval policy per capability (Engineer scope) — `skills/team-brief/references/engineer-sources.md`:
  - [ ] productivity (Google/M365): email + calendar + docs
  - [ ] chat (Slack/Teams): @mentions, threads needing reply, unread in scoped channels
  - [ ] design (Figma): review requests, comments/@mentions, file activity
  - [ ] code (GitHub/GitLab): PRs to review, comments on your PRs, CI status, assigned issues, mentions
  - [ ] tracking (Jira/Linear/Asana): assigned/blocked/due, sprint, status changes
  - [ ] incidents (PagerDuty/Opsgenie): active incidents, on-call
  - [ ] observability (Datadog/Sentry): alerts, error spikes
  - [ ] support (Intercom/Zendesk): escalations, assigned conversations
  - [ ] analytics (Amplitude/Mixpanel): metric anomalies, flagged dashboards
- [x] 3.3 Untrusted-content handling — documented per source in both reference files (messages/PRs/CI logs/alerts/tickets = data).
- [x] 3.4 Scope application (repos/channels/projects/services) — in retrieval-policy.md, applied from `profile.connections[].scope`.
- _Acceptance: **MET (Engineer scope)** — retrieval is documented, bounded (per-source caps), injection-safe, and gated to active+connectable sources. Non-engineer role source packs land in Phase 5._

**Phase 3 — DONE for Engineer (2026-08-07):** `team-brief` skill shell + retrieval policy + engineer per-capability spec; plugin validates with the new skill (5 skills total).

## Phase 4 — Grounding, dedup, ranking (cross-source)

- [x] 4.1 `lib/xsource.py` — dedup_key builders (pr/issue/incident/deploy/thread) + cross-source merge; doc in ranking-policy.md.
- [x] 4.2 `lib/ranking.py` — deterministic role ranking via explicit `rank` (urgency > role capability-priority > effort); validator honors `rank` (backward-compatible with v1).
- [x] 4.3 `lib/xsource.find_status_conflicts` — done-vs-open across tools → conflicts[] + conflict_state.
- [x] 4.4 `tests/test_xsource_ranking.py` — PR-in-3-tools collapses to one (3 citations); conflict detection; incident-outranks-code-with-null-effort; validator flags broken rank order.
- _Acceptance: **MET** — cross-tool duplicates collapse with merged provenance; ranking deterministic + role-aware (incident-first solved); conflicts surfaced not resolved._

**Phase 4 — DONE (2026-08-07):** 106 tests (55 skill + 51 connector); engineer payload re-ranked by the engine and validates; v1 payloads still valid under the rank-aware validator.

## Phase 5 — Role brief templates (role packs)

- [x] 5.1 Engineer role pack — `skills/team-brief/references/roles/engineer.md` (slot→section mapping, ranking, actions/approval matrix). Other roles: post-pilot.
- [x] 5.2 `skills/team-brief/references/output-style.md` — role-brief presentation contract; `skills/team-brief/examples/engineer-brief.md` rendered target.
- _Acceptance: **MET (Engineer)** — engineer pack renders the standard skeleton in rank order with role-appropriate sections; example matches the validated golden payload._

**Phase 5 — DONE for ALL 8 roles (2026-08-07):** role packs for software_engineer, product_designer,
design_lead, engineering_lead, product_manager, head_of_product, qa_engineer, data_analyst
(`references/roles/*.md`), per-role ranking weights (`lib/ranking.py`), output-style + engineer
rendered example. Each role's Top-of-mind ranks by its own capability priority (Eng-Lead incident-first,
PM tracking-first, Head-of-Product support-first, Data analytics-first-when-connected).

## Phase 6 — The `team-brief` Skill(s)

- [x] 6.1 `skills/team-brief/SKILL.md` — role-parametrized workflow, wired to bundled paths.
- [x] 6.2 references/: retrieval-policy, ranking-policy, output-style, roles/engineer, examples/engineer-brief (safety folded into retrieval-policy).
- [x] 6.3 Self-contained bundle via `scripts/bundle_team_brief.sh`: validator + dedup + dateutil + ranking + xsource + gating + brief/role-profile schemas + catalog/matrix; drift-guarded in the gate (step 4c).
- [x] 6.4 Trigger phrases in description (team/work/engineering brief, "what needs my attention across my tools").
- _Acceptance: **MET** — `claude --plugin-dir` loads `boo:team-brief` and renders the validated engineer brief end-to-end (headless verified); bundled scripts resolve bundled config/schema._

**Phase 6 — DONE (2026-08-07):** team-brief is a self-contained, valid, loadable skill; engineer brief renders. 106 tests + bundle drift guard green.

## Phase 7 — Onboarding & profile management Skills

- [x] 7.1 `skills/manage-role-profile/SKILL.md` — view/edit role/team/provider/scope/brief-time, provider-validity via gating, pause/resume/remove, export/delete; reversible.
- [x] 7.2 `skills/onboarding/SKILL.md` — role pick → connectable-only slot menu (M→R→O) → coach connect → scope → timezone → gate → save; hand off run + schedule.
- [x] 7.3 R1–R4 baked in: verify tools actually loaded + coach per-chat/per-task connector enablement (R1/R3); Drive-write fallback — inline or manual upload (R2); timezone fill, no placeholder (R4/O4); reassure about irrelevant connectors.
- [x] 7.4 Connector-status reporting via gating (active/paused/reconnect_needed + missing-mandatory).
- _Acceptance: **MET** — onboarding guides role→runnable profile with every gap coached; plugin now ships 7 skills; `prompts/scheduled-team-brief.md` added for the handoff._

**Phase 7 — DONE (2026-08-07):** onboarding + manage-role-profile skills; plugin valid (7 skills); gate green.

## Phase 8 — Safety, privacy & governance

- [x] 8.1 Per-viewer scoping documented + enforced (own-credentials only; no service/bot aggregation) — `skills/team-brief/references/safety-policy.md`.
- [x] 8.2 Per-source mutation inventory (mail/calendar/chat/code/tracking/incidents/observability/design) + approval-gated, drafts/preview-only; enforced in code by `tests/test_governance.py` (no autonomous send/post/merge types; writes require approval).
- [x] 8.3 Unattended = read-only across all sources (safety-policy + scheduled prompt).
- [x] 8.4 `docs/THREAT-MODEL.md` — org/role additions (#19–25: multi-source injection, cross-person exposure, autonomous-write, wrong-target, availability gate, confidentiality).
- [x] 8.5 `docs/PRIVACY.md` — role-brief section (per-viewer scoping, role-profile data, minimization, export/delete).
- _Acceptance: **MET** — every write action previews + requires approval (schema + governance test); scheduled runs mutate nothing; threat model + privacy cover all sources._

**Phase 8 — DONE (2026-08-07):** safety-policy + governance tests + threat-model/privacy updates. 111 tests (60 skill + 51 connector) green.

## Phase 9 — Custom connector(s) for gaps `[DEFERRED]`

> **DEFERRED (decision 2026-08-07): v2 ships native-only.** Native connectors cover the vast majority
> of product-team workflows; custom connectors add hosting/OAuth/maintenance burden for marginal
> gain. The **availability gate** (Phase 2, `lib/gating.py`) hides every non-connectable provider and
> any slot with no connector (analytics today), so the product degrades gracefully with zero custom
> code. Revisit this phase only when a mandatory-for-some-role slot (e.g. analytics for Data/PM) is
> worth a dedicated connector — then flip `custom_connector: true` in the catalog and the slot
> appears automatically.

- [~] 9.1 If M365/Teams (or another mandatory-slot substitute) is not native: build a Graph-based connector reusing the Mode-B pattern (OAuth PKCE/state, encrypted tokens, narrow tools, per-source health, isolation).
- [~] 9.2 Adapter + fixtures + tests (mock HTTP), like the current connector's live-client tests.
- [~] 9.3 Deploy runbook (Docker + public HTTPS), add as remote MCP connector.
- _Acceptance (if built): fixtures-tested; deploy documented; live gate marked pending until hosted._

## Phase 10 — Evals & fixtures

- [x] 10.1 De-identified fixtures embedded in golden payloads across GitHub/Slack/Linear/Sentry/PagerDuty/Figma/Google/M365/Teams (native-connector path needs golden payloads, not raw-source fixtures).
- [x] 10.2 Per-role golden briefs for **all 8 roles** (Engineer full + 8 edge variants; Designer, Design-Lead, Eng-Lead, PM, Head-of-Product, QA, Data) — 16 v2 payloads, each validated + rank-verified.
- [x] 10.3 Edge-case scenarios + `evals/cases/scenarios-v2.json`:
  - [x] missing mandatory slot (e02) · provider substitution M365+Teams (e03)
  - [x] cross-source dedup PR-in-3-tools (e04) · cross-source conflict done-vs-open (e05)
  - [x] revoked/paused provider isolation (e06) · prompt injection in a Slack message (e07)
  - [x] multi-workspace scope (e08) · rate-limited/partial source (e09) · designer role-generality (d01)
- [x] 10.4 `tests/test_acceptance_v2.py` — validates each v2 payload + applies role/capability/substitution/dedup/conflict/injection checks; manifest-vs-disk sync check.
- _Acceptance: **MET** — 10 v2 scenarios validate + assert their property deterministically; gate step 5b validates all v2 payloads._

**Phase 10 — DONE (2026-08-07):** 10 v2 golden payloads + acceptance manifest + harness. 113 tests total (62 skill + 51 connector).

## Phase 11 — Tests & quality gate

- [x] 11.1 Unit tests across phases: schema v2, gating + availability, catalog/matrix integrity, cross-source dedup/conflict, ranking, governance, v2 acceptance (10 scenarios), live-client (mocked HTTP). Added `tests/test_plugin_structure.py` + `tests/test_bundle_sync.py` so `make test` alone catches plugin + bundle issues.
- [x] 11.2 `scripts/quality_gate.sh` runs: validator self-test, v1 (20) + v2 (10) payload validation, daily-brief + team-brief bundle drift, all unit/acceptance tests (with jsonschema on AND forced-off), connector tests, secret scan, offline + official plugin validation.
- [x] 11.3 Offline stdlib core; mocked connector responses (FakeHttpClient) for determinism.
- _Acceptance: **MET** — `make check` green end-to-end._

**Phase 11 — DONE (2026-08-07):** 118 tests (67 skill + 51 connector) + full gate green; Python suite now self-sufficient for plugin/bundle integrity.

## Phase 12 — Packaging

- [x] 12.1 Plugin ships 7 skills (auto-discovered); `plugin.json` bumped to v0.2.0 with role/team description + keywords.
- [x] 12.2 Standalone ZIPs: `dist/team-brief-skill.zip` (self-contained — bundled scripts/schemas/config, **verified by isolated extraction + run**) and `dist/daily-brief-skill.zip`. Companion skills (onboarding, manage-role-profile) ship in the plugin.
- [x] 12.3 Offline validator + `claude plugin validate .` green; `make package` builds both ZIPs.
- _Acceptance: **MET** — plugin validates; both standalone ZIPs correctly shaped (folder at root) and self-contained._

**Phase 12 — DONE (2026-08-07):** plugin v0.2.0 (7 skills) + two self-contained standalone ZIPs; gate green.

## Phase 13 — Dry runs (explicit, staged)

- [x] 13.1 **Local plugin dry run** — `boo:team-brief` loads and renders the engineer payload (Phase 6) + the conflict scenario e05 honestly. Headless verified.
- [x] 13.2 **Trigger scoping** — "across my tools"/"engineering brief" → team-brief; "write a poem" → none; "set up Boo" → onboarding. Headless verified.
- [~] 13.3–13.8 **Live engineer dry run** — full checklist in internal dry-run notes (connect tools, mandatory-gap, substitution, dedup, action-flow, per-surface). PENDING real connectors.
- [x] 13.9 Local results logged to internal dry-run notes; regression-freeze process defined.
- _Acceptance: **local MET**; live checklist ready, gated on real connectors._

**Phase 13 — local DONE, live PENDING (2026-08-07):** local renders + trigger scoping pass; live engineer checklist documented.

## Phase 14 — Documentation

- [x] 14.1 `README.md` (v2 status: 123 tests, 7 skills, 9 roles incl. ⚡ Superhuman, Model-A delivery),
  `docs/ARCHITECTURE.md` (added §6 role/team-mode role-flow diagram + §7 card-onboarding sequence,
  component table, v2 schema versioning, per-viewer/permalink/role-rank invariants),
  `docs/PLATFORM-CAPABILITIES.md` (coverage matrix already current), `docs/PRIVACY.md` +
  `docs/THREAT-MODEL.md` (Superhuman note on per-viewer scoping).
- [x] 14.2 `docs/SETUP-CLAUDE.md` + `docs/SETUP-SCHEDULE.md` cover the role/team brief + onboarding +
  `scheduled-team-brief.md`; `docs/ROLE-TOOL-MODEL.md` marked BUILT, Superhuman added, decisions resolved.
- [x] 14.3 `docs/LIMITATIONS.md` (123 tests, v2 role limits, analytics gap, live-data role gate, M365
  native, deep-link/permalink dependency, onboarding-coaches-never-authorizes).
- _Acceptance: **MET** — a new user can self-serve install → onboard → schedule from the docs; every
  doc reflects the built 9-role, card-onboarding, permalink-enforced state._

**Phase 14 — DONE (2026-08-08):** docs current with the shipped v2 (Superhuman, card onboarding,
permalink invariant). Remaining: Phase 15 ship (CHANGELOG + marketplace.json) and live-data role runs.

## Phase 15 — Ship as plugin

- [x] 15.1 Version bump **0.2.0 → 0.3.0** + `CHANGELOG.md` (0.1.0 → 0.3.0 history).
- [x] 15.2 `.claude-plugin/marketplace.json` (`boo-marketplace`) for one-command install; **tested via a
  full local `marketplace add → install → details (7 skills, v0.3.0) → uninstall → remove` roundtrip**,
  leaving no trace. Offline shape check added to `scripts/validate_plugin.py`.
- [x] 15.3 Final full quality gate green (`make check`, 123 tests) + `claude plugin validate .` (plugin
  + marketplace) pass; both `dist/*-skill.zip` build via `make package`.
- [~] 15.4 Install + uninstall/revoke **instructions written** (README one-command install + uninstall;
  SETUP-CLAUDE). **Public publish** (push to a GitHub repo so others `marketplace add owner/repo`) is a
  user action — pending the repo being made public/remote.
- [ ] 15.5 Post-ship backlog: live-data role runs; **analytics** connector (unblocks PM/Head/Data);
  deploy the parked **Mode B** multi-account connector; render examples for non-engineer roles.
- _Acceptance: **MET locally** — plugin installs cleanly from the local marketplace (verified), all 7
  skills load, and every automated check passes. Remaining: public distribution + live-data runs._

**Phase 15 — DONE locally (2026-08-08):** v0.3.0 shipped as an installable plugin + local marketplace;
install roundtrip verified; gate green. Public repo publish + live-data runs are the only follow-ups.

---

## Critical path (shortest route to a shippable pilot)

0.1–0.6 → 1.x → 2.x → (pilot-only) 3.x → 4.x → 5.(pilot role) → 6.x → 7.x → 10.(pilot fixtures) →
11.x → 12.x → 13.1/13.3/13.8 → 14 → 15. Everything else (more roles, more providers, custom M365
connector) is additive after the pilot ships.
