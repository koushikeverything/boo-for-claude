# Platform Capabilities & Gap Analysis

> **First deliverable.** This document is the verified basis for every architecture
> decision in Boo for Claude. Nothing downstream may assume a capability that is not
> confirmed here. Where a capability is not documented, it is marked **UNVERIFIED** and
> gated behind a manual capability test (see `docs/MULTI-ACCOUNT.md`).

**Access date for all sources below: 2026-08-07.** (Re-verify before any public release;
Claude platform surfaces change frequently.)

## Sources consulted

| # | Source | URL |
|---|--------|-----|
| S1 | Agent Skills overview | https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview |
| S2 | Plugins reference | https://code.claude.com/docs/en/plugins-reference |
| S3 | Slash commands | https://code.claude.com/docs/en/slash-commands |
| S4 | Plugins (authoring) | https://code.claude.com/docs/en/plugins |
| S5 | MCP in Claude Code | https://code.claude.com/docs/en/mcp |
| S6 | Use Google Workspace connectors | https://support.claude.com/en/articles/10166901-use-google-workspace-connectors |
| S7 | Schedule recurring tasks in Claude Cowork | https://support.claude.com/en/articles/13854387-schedule-recurring-tasks-in-claude-cowork |
| S8 | How to create custom Skills | https://support.claude.com/en/articles/12512198-creating-custom-skills |
| S9 | Use plugins in Claude | https://support.claude.com/en/articles/13837440-use-plugins-in-claude |
| S10 | Use connectors to extend Claude's capabilities | https://support.claude.com/en/articles/11176164-use-connectors-to-extend-claude-s-capabilities |

## Verified capability matrix

| Requirement | Native Claude support | Evidence | Gap | Chosen implementation |
|-------------|-----------------------|----------|-----|-----------------------|
| Custom Skill authored + discovered in Claude Code | **Yes** | S1: "place them in `~/.claude/skills/` (personal) or `.claude/skills/` (project)"; "Claude discovers and uses them automatically." | None | `skills/` in the Boo plugin, loaded via `--plugin-dir` or `.claude/skills/` |
| Custom Skill uploaded to claude.ai | **Yes**, Pro/Max/Team/Enterprise with code execution | S1: "Upload your own Skills as zip files through Settings > Features"; S8: ZIP root = the skill folder | None | `scripts/package_skill.sh` builds a claude.ai-shaped ZIP (skill folder at ZIP root) |
| Skill auto-invoked by request phrasing | **Yes** | S1: `description` "is what Claude matches your request against"; must state what + when | None | `daily-brief` description enumerates trigger phrases (see SKILL.md) |
| Skill name may contain "Claude"/"Anthropic" | **No — reserved** | S1: `name` "Cannot contain reserved words: 'anthropic', 'claude'" | Naming | Plugin/skill names avoid both words: `boo`, `daily-brief`, etc. |
| Skill = scheduler / OAuth provider / multi-identity store | **No** | S1: Skills are filesystem instructions + scripts run in a VM; no durable service, no token store, no network in API surface | Fundamental | Scheduling → Cowork; identity/tokens → connectors or Mode B MCP server |
| Gmail: read + search email | **Yes** | S6: "Search and read emails, access metadata" | None | Native Gmail connector (Mode A); `boo_search_relevant_mail` (Mode B) |
| Gmail: attachment **content** | **No** | S6: "Gmail attachment content inaccessible (metadata only)" | Content gap | Brief cites attachment by name only; never asserts attachment contents |
| Gmail: create draft | **Yes** | S6: "Claude creates drafts in your Gmail account" | None | Draft-only action workflow (Mode A + `boo_create_gmail_draft`) |
| Gmail: **send** email | **No (by design)** | S6: "cannot send emails on your behalf" | Aligns with our rule | Boo never sends; drafts only |
| Calendar: read events | **Yes** | S6: "View events and shared calendars" | None | Native Calendar connector; `boo_list_day_events` |
| Calendar: create/update/delete events | **Yes** | S6: "Create, update, and delete events" | None | Approval-gated `boo_create_calendar_event` |
| Drive: search + read text | **Yes** (text only) | S6: "read Sheets/Slides/PDFs/images/MS Office files"; "extracts text content only … Images embedded in documents are not processed" | Image gap | `boo_get_referenced_drive_metadata`; brief never claims image contents |
| Connector citations | **Yes** | S6: "Responses include citations with links to original sources when available" | None | Preserve native citation UI; Mode B returns `source_ref` links |
| Connector actions require approval | **Yes** | S6: "Each action requires explicit user approval" | None | Reinforced by our own preview/approval workflow |
| **Multiple Google accounts for one user, queried in one task** | **NOT documented / effectively No** | S6 does not mention multi-account. Help-center guidance and search indicate the connector is single-account per connection; adding another account means disconnect + reconnect. | **CORE GAP** | **Mode B** custom multi-account MCP connector (see below) |
| Custom Skill usable inside a Cowork scheduled task | **Yes** | S7: "Scheduled tasks have access to the same capabilities as regular Cowork tasks, including connected tools, skills, and installed plugins." | None | Daily-brief Skill invoked by the scheduled prompt |
| Plugin usable inside a Cowork scheduled task | **Yes** | S7 (same sentence: "installed plugins") | None | Boo plugin installed once, used by the schedule |
| Google connectors usable inside a scheduled task | **Yes** | S7: "work with your connectors and the files saved to your Claude account" | None | Mode A path for scheduled runs |
| Custom remote MCP connector usable inside a scheduled task | **Yes** (as a connected tool) | S7: "same capabilities … including connected tools"; S5: remote MCP servers are connectable tools | Live-gated | Mode B connector added as a remote MCP connector, then referenced by the schedule |
| Scheduled result appends to a fixed existing conversation | **No** | S7: "Each scheduled task runs as its own Cowork session." | Cannot promise a fixed thread | Each daily brief is its own Cowork session; follow-ups happen inside that session |
| Set timezone/time for schedule | **Partial** | S7 lists cadences (hourly/daily/weekly/weekdays/manual); timezone control not explicitly documented → treat as **UNVERIFIED**; the Skill computes the local day from a stored IANA timezone regardless | Timezone gap | Timezone lives in Boo preferences; Skill derives the local day deterministically |
| Approval mode for unattended runs | **Exists, under-documented** | S7 mentions an "approval mode" setting at task creation; details not specified | Behavior gap | Scheduled prompt performs **read-only** work only; all mutations deferred to attended follow-up |
| Claude Memory / user-reviewable preference file | **Yes** | S1/S8: Skills can read bundled/user files; Cowork works with "files saved to your Claude account" | None | Reviewable `boo-preferences.json` (Drive or Claude files) + optional Memory |
| Interactive MCP App / custom UI components | **UNVERIFIED for this surface** | Not documented as available/testable for scheduled Cowork briefs | Treat as optional | Markdown brief is fully usable without any custom component |

## Skill authoring facts (locked)

From S1 (quoted / paraphrased):

- **Required frontmatter:** `name`, `description`.
- `name`: ≤ 64 chars; lowercase letters, numbers, hyphens only; no XML tags; **must not contain "anthropic" or "claude".**
- `description`: non-empty, ≤ 1024 chars (S8 notes claude.ai historically rendered ~200 chars — keep the trigger-critical text first); must state **what** the Skill does and **when** to use it.
- Progressive disclosure: Level 1 metadata (always), Level 2 SKILL.md body (on trigger, keep < ~5k tokens), Level 3 referenced files/scripts (on demand). Scripts run via bash; only their output enters context.
- Claude Code Skills are filesystem-based (`.claude/skills/`, `~/.claude/skills/`); claude.ai Skills upload as ZIP with the **skill folder at the ZIP root**; API Skills upload via the Skills API. **Skills do not sync across surfaces.**

## Plugin facts (locked)

From S2 (quoted / paraphrased):

- Manifest: `.claude-plugin/plugin.json`. **`name` is the only required field.** Optional: `version`, `description`, `author`, `homepage`, `repository`, `license`, `keywords`, `displayName`, `defaultEnabled`, and component-path fields (`skills`, `commands`, `agents`, `hooks`, `mcpServers`, …).
- Skills live in `skills/<name>/SKILL.md`; auto-discovered when the plugin is enabled.
- MCP servers: `.mcp.json` at plugin root or inline `mcpServers` in `plugin.json`.
- All component dirs (`skills/`, `commands/`, `agents/`, `hooks/`, …) sit at the **plugin root**, not inside `.claude-plugin/`.
- Validate with `claude plugin validate ./Boo-Claude` (add `--strict` to fail on unknown fields).
- Local test load: `claude --plugin-dir ./Boo-Claude` for the duration of a session.

## Architecture decision (driven by the matrix)

- **Mode A (Native)** satisfies requirements for a **single** Google account end to end, with
  no custom OAuth app and no Boo backend. It is the default and the recommended starting point.
- **Requirement 2 (all of a person's approved Google accounts, in one task)** is the one core
  promise native connectors do **not** documentably support. Therefore **Mode B** (a custom
  multi-account remote MCP connector) is **required** to fulfil the product's central claim —
  it is not built for novelty. It is implemented and tested against fixtures here; the live
  OAuth/hosting gate is marked **PENDING** (see `docs/LIMITATIONS.md`).
- Scheduling is always **Cowork**, never the Skill. Each run is its own session (S7).

## Unverified items requiring a live manual test

These are explicitly **not** assumed. Each has a manual test in `docs/MULTI-ACCOUNT.md` / `docs/SETUP-SCHEDULE.md`:

1. Whether two native Google connections for one Claude user can be queried in a single task
   (documentation says no; test T1 confirms/refutes).
2. Whether a Cowork schedule exposes an explicit timezone control (T2).
3. Exact unattended "approval mode" behavior for mutations during a scheduled run (T3).
4. Availability of any interactive MCP App component in a scheduled Cowork brief (T4).

## Update — resolved by the live dry run (2026-08-07)

See internal dry-run notes for the full log. Two previously-unverified items are now answered:

- **T2 (scheduler timezone):** No clear IANA timezone control in the scheduler. Mitigation stands:
  the Skill computes the local day from a timezone **stated in the scheduled prompt** — so the
  timezone must be written into that prompt (do not rely on a placeholder).
- **T3 (unattended connectors + approval):** Unattended runs behaved **read-only** (no mutations).
  Critically, a scheduled Cowork task does **not** inherit the connectors toggled in an interactive
  chat — **Gmail/Calendar/Drive must be enabled per scheduled task** (or at the Cowork/account
  level). This is the biggest setup trap and is now documented in `docs/SETUP-SCHEDULE.md`.

- **T1 (native multi-account): CONFIRMED — not possible.** claude.ai → Connectors → Google Workspace
  offers **no "add another account"** control; you can only disconnect and reconnect a different
  account. A single Claude user therefore cannot query two Google accounts in one task natively.
  **This makes Mode B required.** (Confirmed live 2026-08-07; see internal dry-run notes.)

Still pending: T4 (interactive MCP App). Mode B is now being wired for live use.

## Connector coverage matrix — org/role brief (Phase 0.3, verified 2026-08-07)

For the **Engineer pilot**. "Native" = a first-party or ecosystem connector the user connects to
their own account (per-viewer scoping holds). Sources accessed 2026-08-07.

| Capability slot | Provider | Native connector? | Read | Write | Source |
|---|---|---|---|---|---|
| productivity | Google Workspace | **Yes** (live-verified) | email/cal/drive | drafts/cal/files | S6 |
| productivity | **Microsoft 365** (Outlook/SharePoint/OneDrive) | **Yes** | mail/files/cal | send/cal/files* | support.claude.com/articles/12542951, claude.com/connectors/microsoft-365, security: /articles/12684923 |
| chat | Slack | **Yes** (engineering plugin) | messages/mentions | post* | ecosystem `engineering:slack` |
| chat | **Microsoft Teams** | **Yes — via the M365 connector** | Teams messages | — | support.claude.com/articles/12542951 |
| code | GitHub | **Yes** (engineering plugin) | PRs/issues/CI | comment* | `engineering:github` |
| code | **GitLab** | **Yes** | projects/issues/MRs/code search | — | claude.com/connectors/gitlab |
| tracking | Jira / Confluence (Atlassian) | **Yes** (engineering plugin) | issues/pages | update* | `engineering:atlassian` |
| tracking | Linear | **Yes** (engineering plugin) | issues | update* | `engineering:linear` |
| tracking | Asana | **Yes** (engineering plugin) | tasks | update* | `engineering:asana` |
| incidents | PagerDuty | **Yes** (engineering plugin) | incidents/on-call | — | `engineering:pagerduty` |
| observability | Datadog | **Yes** (engineering plugin) | monitors/alerts | — | `engineering:datadog` |
| observability | **Sentry** | **Yes** | issues/errors/projects | trigger fix* | claude.com/connectors/sentry |
| design (opt) | Figma | **Yes** (figma plugin) | files/comments | — | `figma:figma` |
| docs (opt) | Notion | **Yes** (engineering plugin) | pages | update* | `engineering:notion` |
| — | Opsgenie / Bitbucket / Grafana | not confirmed | — | — | covered by PagerDuty / GitHub+GitLab / Datadog+Sentry substitutes |

`*` **Write capability exists but Boo does NOT use it beyond drafts/previews.** The M365 connector
in particular can *send* email — our Skill must use **read + draft only** and never invoke send,
consistent with the v1 drafts-only invariant. Enforce per-source in Phase 8.

**Conclusion:** every Engineer mandatory + recommended slot has native connector coverage, in both
provider options (Google **or** M365, Slack **or** Teams, GitHub **or** GitLab, Datadog **or**
Sentry). **No custom connector is required for the Engineer pilot** — Phase 9 is skipped for it.
Exact read scopes / rate limits per connector are confirmed during Phase 3 (retrieval adapters).
