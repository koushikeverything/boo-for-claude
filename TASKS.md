# TASKS — build sequence & status

Legend: ✅ done & acceptance criteria pass · ⏳ implemented, live gate pending · ▫️ not started.

| # | Task | Status | Evidence |
|---|------|--------|----------|
| 1 | Verify Claude ecosystem capabilities | ✅ | `docs/PLATFORM-CAPABILITIES.md` (sourced matrix, access date 2026-08-07) |
| 2 | Product brief & architecture decisions | ✅ | `docs/PRODUCT-BRIEF.md`, `docs/ARCHITECTURE.md` |
| 3 | Scaffold plugin + focused Skills | ✅ | `.claude-plugin/plugin.json`, `skills/*`; `claude plugin validate .` passes |
| 4 | Canonical briefing schema | ✅ | `schemas/daily-brief.schema.json` (v1.0) |
| 5 | Reference examples + validation scripts | ✅ | `skills/daily-brief/examples/*`, `scripts/validate_brief.py` (self-test + 20 payloads) |
| 6 | Native connector retrieval instructions | ✅ | `skills/daily-brief/references/retrieval-policy.md` |
| 7 | Grounding, dedup, ranking, presentation policies | ✅ | references/*, `scripts/dedup.py`, `test_dedup.py` |
| 8 | Details + preference workflows | ✅ | `skills/brief-details`, `skills/manage-boo-preferences` (+ preference schema) |
| 9 | Safe action workflows | ✅ | `skills/brief-actions`, connector action tools + tests |
| 10 | Scheduled Cowork prompt (created + validated) | ✅ | `prompts/scheduled-daily-brief.md` (read-only, partial-status, follow-ups) |
| 11 | Test native single-account behavior | ✅ | scenarios 01/06/08/09/10/12/16/17 + acceptance harness |
| 12 | Test native multiple-account behavior | ✅ (fixtures) / ⏳ (live) | scenarios 03/18/20; live multi-account is not natively supported → Mode B |
| 13 | Implement Mode B remote MCP connector (native multi-account fails) | ✅ (fixtures) / ⏳ (live) | `connector/` — 40 tests; live OAuth/hosting PENDING |
| 14 | Test two-account isolation with fixtures | ✅ | `connector/tests/test_isolation.py` |
| 15 | Package standalone Skill + plugin | ✅ | `scripts/package_skill.sh` → `dist/daily-brief-skill.zip`; plugin loads via `--plugin-dir` |
| 16 | Run full quality gates | ✅ | `make check` → all pass (61 tests, secret scan, plugin validation) |
| 17 | Manual Claude/Cowork dry run | ⏳ | Requires paid plan + Cowork + connected accounts; checklist in `docs/SETUP-SCHEDULE.md` |
| 18 | Freeze observed failures as regression cases | ✅ (framework) | `evals/cases/scenarios.json` is additive; new live failures append here |
| 19 | Final setup + limitation docs | ✅ | `docs/SETUP-CLAUDE.md`, `docs/SETUP-SCHEDULE.md`, `docs/MULTI-ACCOUNT.md`, `docs/LIMITATIONS.md` |

## Definition of done — checklist

- ✅ Skill structurally valid & uploadable to claude.ai (ZIP root = skill folder).
- ✅ Plugin validates & loads in Claude Code (`claude plugin validate .`).
- ✅ Daily brief invocable manually (trigger phrases in the Skill description).
- ✅ Scheduled-task prompt ready & documented.
- ✅ Reference scenario renders correctly as a Claude-native brief (payload validates).
- ✅ Every displayed fixture claim has provenance (validator enforces ≥1 citation).
- ✅ Two accounts supported (natively for reads where possible; Mode B for true multi-account).
- ✅ Account health & partial coverage visible (`source_status`, coverage line).
- ✅ A failed account does not block a healthy account (isolation tests).
- ✅ Follow-up questions work against source references (`brief-details`, `boo_get_source_details`).
- ✅ Gmail actions create drafts only (tool asserts `sent == False`).
- ✅ Mutating actions require explicit approval (schema + tool + tests).
- ✅ Prompt-injection fixtures fail safely (scenario 11 + untrusted-content labeling).
- ✅ Preferences reviewable & reversible (`manage-boo-preferences`, JSON model).
- ✅ All automated checks pass.
- ⏳ Live-only gates clearly marked pending (`docs/LIMITATIONS.md`).

## Roadmap / parked for v2

**Decision (2026-08-07): multi-account (Mode B) is parked for v2.** Mode A (single account) is live
and validated on a real account. The Mode B connector is **code-complete and tested** (72 tests:
crypto, OAuth PKCE/state, account linking by Google `sub`, live Gmail/Calendar/Drive via fake HTTP,
token refresh, isolation) — only the live **deploy** (Google OAuth app + public HTTPS host) is
deferred. When resuming: `connector/README.md` → "Deploy live", then link accounts and add the
`/mcp` endpoint as a remote MCP connector.

- **v1 (now):** Mode A daily brief on a single Google account, manual + scheduled; drafts-only;
  follow-ups; reviewable prefs. Working.
- **v2 (later):** deploy Mode B for true multi-account; guided onboarding skill (R1–R4 in
  internal dry-run notes); + a new idea (TBD, being scoped next).
