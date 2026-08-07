# Boo for Claude

A **Claude-native planning agent** that produces concise, evidence-grounded briefings **inside
Claude** — delivered as a scheduled Cowork result, not an email — and then becomes an interactive,
approval-gated workspace for follow-ups and safe actions. Two briefs, one engine:

1. **Personal "Your day ahead"** (v1) — across your Google accounts (Gmail, Calendar, Drive).
2. **Role-based team brief** (v2) — for product-team members across their connected work tools
   (GitHub/GitLab, Slack/Teams, Google/Microsoft 365, Jira/Linear, PagerDuty, Sentry/Datadog,
   Figma, Notion, Intercom). Pick your **role**; it reads only the tools that role needs, ranks by
   role, and never fabricates through a missing/failed connector.

> This is a side exploration, completely separate from the original Boo email app. It does not
> import from or modify that project.

## Why this is different from the email version

| Original Boo (email) | Boo for Claude |
|----------------------|----------------|
| Morning **email** is the primary surface | **Scheduled Cowork session** is the primary surface |
| An agent mailbox sends the briefing | **Claude presents the briefing directly** (no agent email address) |
| You reply by email | You **continue the Claude conversation** (ask, drill in, act) |
| Fake action chips / email HTML | **Real supported actions** or clearly-worded follow-up commands, in native Markdown |
| Custom mail-delivery + scheduling backend | **Cowork scheduling**; native Google connectors first |

The briefing preserves the same information hierarchy as the original design — Your day ahead →
greeting → Top of mind → FYI (with subgroups) → On your calendar → short closing — but rendered as
clean Claude Markdown with citations, effort estimates, and account attribution. See the target
rendering in [`skills/daily-brief/examples/reference-brief.md`](skills/daily-brief/examples/reference-brief.md).

## Completion status (2026-08-08)

**Built and passing all automated checks (123 tests — `make check`):**
- ✅ Plugin (`boo`, v0.2.0) with **7 Skills** — validates with the official `claude plugin validate`.
- ✅ **v1 personal "Your day ahead"** — Google Workspace, drafts-only, 20 eval scenarios; validated
  live on a real account.
- ✅ **v2 role/team brief** — **9 roles**: Product Designer, Design Lead, Software Engineer,
  Engineering Lead, Product Manager, Head of Product, QA Engineer, Data/Analyst, and **⚡ Superhuman**
  (a free-pick "many hats" role — the user connects any mix). Role model + availability gate,
  cross-source dedup/conflict, role-aware ranking; **16 golden payloads**.
- ✅ **Card-driven Cowork onboarding** — native selection cards (role → connect tools → delivery time
  → sources) writing a reviewable `role-profile.json`.
- ✅ **Deep-link invariant** — every "Open …" action carries a real source permalink (enforced by a
  test); versioned brief schema + deterministic validator (schema **and** semantic rules).
- ✅ Mode B multi-account MCP connector — crypto, OAuth (PKCE/state), store, narrow tools, isolation
  — fully tested against fixtures (**parked**; live deploy pending).
- ✅ Drafts-only + no-unattended-mutation governance; scheduled + manual + onboarding prompts;
  packaging + secret scan.

**Live-only gates (marked PENDING — require credentials/hosting we don't have here):**
- ⏳ Connected work tools + a paid Claude plan with Cowork to run real role briefs on **live data**
  (the 7 non-engineer roles + a full multi-connector engineer run).
- ⏳ Public HTTPS hosting + Google OAuth app to run Mode B live.

Details: [`docs/LIMITATIONS.md`](docs/LIMITATIONS.md).

## Two operating modes (Google multi-account)

- **Mode A — Native.** Claude's built-in Google connectors, **one** account, no backend, no custom
  OAuth app. The default and simplest path.
- **Mode B — Multi-account connector.** A custom remote MCP connector (in [`connector/`](connector/))
  for the one core promise native connectors do **not** documentably support: **several Google
  accounts for one user in a single task**. **Built + fixtures-tested, currently parked** (needs a
  Google OAuth app + HTTPS host). See [`docs/PLATFORM-CAPABILITIES.md`](docs/PLATFORM-CAPABILITIES.md)
  for the sourced gap analysis.

## v2 delivery model (role/team brief)

The role/team brief ships **native-only** and uses **Model A — per-viewer scoping**: each person
connects **their own** tools, so the brief never exceeds what they can already see (access control by
construction; no service/bot aggregation). An **availability gate** (`lib/gating.py`) offers only
connectable providers and hides any slot with no connector (e.g. analytics today). *Model A (scoping)
is distinct from Mode A/B (Google multi-account) above.* See
[`docs/ROLE-TOOL-MODEL.md`](docs/ROLE-TOOL-MODEL.md) and [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## Prerequisites

- Python 3.9+ (only the stdlib is needed for tests/validation).
- To load the plugin in Claude Code: Claude Code CLI.
- To upload the standalone Skill: a claude.ai Pro/Max/Team/Enterprise plan with code execution.
- To schedule: Claude Cowork on a paid plan.
- For Mode B live: a Google Cloud OAuth app + public HTTPS host (see `connector/README.md`).

## Exact local test commands

```bash
# everything (validation, 123 tests, bundle-drift guard, secret scan, plugin validation)
make check

# or piecemeal:
make test              # skill unit + acceptance/eval tests (72)
make connector-test    # Mode B connector tests (51)
make validate          # plugin + all 20 v1 + 16 v2 golden payloads
make doctor            # flag any connector that will fail on a missing env-var/token
make package           # build dist/daily-brief-skill.zip + team-brief-skill.zip (claude.ai uploads)
```

## Install / upload

- **Claude Code (one-command, via the bundled marketplace):**
  ```bash
  claude plugin marketplace add <your-org>/boo-for-claude   # GitHub owner/repo (or a local ./path)
  claude plugin install boo@boo-marketplace
  ```
  Installs all 7 Skills (verified: `make check` + a full install→uninstall roundtrip). Uninstall with
  `claude plugin uninstall boo`.
- **Claude Code (dev / no install):** `claude --plugin-dir <path-to-your-boo-clone>`
  (see [`docs/SETUP-CLAUDE.md`](docs/SETUP-CLAUDE.md)). Validate with `claude plugin validate .`.
- **claude.ai (standalone Skill):** `make package`, then upload `dist/daily-brief-skill.zip` (personal
  brief) or `dist/team-brief-skill.zip` (role/team brief) in Settings → Features/Skills. Each ZIP has
  the skill folder at its root and is self-contained (bundles its own scripts/schemas/config).

## Schedule a brief

Paste [`prompts/scheduled-daily-brief.md`](prompts/scheduled-daily-brief.md) (personal) or
[`prompts/scheduled-team-brief.md`](prompts/scheduled-team-brief.md) (role/team) into a Cowork
scheduled task set to run each weekday. Each run appears as its **own** Cowork session (Cowork does
not append to a fixed conversation), and unattended runs are **read-only**. Remember to enable the
same connectors on the scheduled task, not just in chat. Full steps:
[`docs/SETUP-SCHEDULE.md`](docs/SETUP-SCHEDULE.md).

## Privacy model (short)

Read-minimally; cite everything; **drafts only, never send**; explicit approval before any change;
**no mutations during unattended runs**; secrets never reach Claude; source content is untrusted
data. Full model: [`docs/PRIVACY.md`](docs/PRIVACY.md) and [`docs/THREAT-MODEL.md`](docs/THREAT-MODEL.md).

## Limitations

Candidly enumerated in [`docs/LIMITATIONS.md`](docs/LIMITATIONS.md), including every live-only gate.

## Uninstall / revoke

- **Claude Code:** stop passing `--plugin-dir`, or `claude plugin uninstall boo` if installed from a
  marketplace.
- **claude.ai Skill:** disable/remove it in Settings.
- **Connectors:** disconnect Google in Claude connector settings; for Mode B, run account removal
  (deletes stored encrypted credentials) and revoke the grant at
  https://myaccount.google.com/permissions. See [`docs/PRIVACY.md`](docs/PRIVACY.md).

## Repository layout

```
Boo-Claude/
├── .claude-plugin/                   # plugin.json (name: boo, v0.3.0) + marketplace.json
├── skills/                           # 7 Skills (WAT: Workflows)
│   ├── daily-brief/                  #   v1 personal brief + references/ examples/ scripts/ schemas/
│   ├── brief-details/                #   grounded follow-ups
│   ├── brief-actions/                #   preview → approval → action (drafts only)
│   ├── manage-boo-preferences/       #   personal preferences + account management
│   ├── team-brief/                   #   v2 role/team brief — self-contained bundle + role packs
│   ├── onboarding/                   #   card-driven Cowork first-run setup
│   └── manage-role-profile/          #   view/edit/pause/remove the role profile
├── config/                           # capability-catalog.json + role-matrix.json (role model)
├── lib/                              # gating.py · ranking.py · xsource.py (shared v2 logic)
├── prompts/                          # scheduled / manual / onboarding prompts (personal + team)
├── schemas/                          # daily-brief (v1) · brief (v2) · role-profile schemas
├── evals/                            # 20 v1 + 16 v2 golden payloads + scenario manifests
├── tests/                            # skill-side unit + acceptance tests (stdlib, 72)
├── connector/                        # Mode B multi-account MCP connector (Tools, 51 tests, parked)
├── scripts/                          # quality gate, packaging, bundling, validators, connector_doctor
├── docs/                             # capabilities, architecture, privacy, threat model, setup…
├── CLAUDE.md  README.md  CHANGELOG.md  TASKS.md  Makefile
```

See [`TASKS.md`](TASKS.md) for the build sequence and status, and
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for diagrams.
