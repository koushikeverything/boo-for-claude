# Setup — install Boo in Claude

## A. Claude Code (whole plugin)

1. Ensure the Claude Code CLI is installed and you're signed in.
2. Load the plugin for a session:
   ```bash
   claude --plugin-dir <path-to-your-boo-clone>
   ```
   Or validate first:
   ```bash
   claude plugin validate <path-to-your-boo-clone>
   ```
3. Confirm discovery: the `boo` plugin's **7 Skills** become available — personal brief
   (`daily-brief`, `brief-details`, `brief-actions`, `manage-boo-preferences`) and role/team brief
   (`team-brief`, `onboarding`, `manage-role-profile`). Trigger explicitly (`/daily-brief`,
   `/team-brief`) or naturally: *"Boo, what's my day ahead?"* · *"what's my engineering brief?"* ·
   *"set up Boo"* (runs `onboarding`).
4. **First run: onboard.** For the role/team brief, say *"set up Boo"* — `onboarding` walks role →
   connect tools → delivery time → sources as native selection cards, then saves `role-profile.json`.
   ⚡ **Superhuman** lets you free-pick any mix of tools.
5. **Enable connectors** you want Boo to use:
   - Personal brief: native Google Workspace (Gmail/Calendar/Drive), or the Mode B connector as a
     remote MCP connector (see `connector/README.md`).
   - Role/team brief: your role's native connectors (GitHub, Slack, Linear, PagerDuty, Sentry, Figma,
     Notion, Intercom, …). In Claude Code, authorize via `/mcp`. Run `make doctor` if any shows
     `✗ failed` — it names the missing token.

### Verifying discovery vs. non-triggering

- **Should trigger:** "my day ahead", "morning brief", "what needs my attention today", "review my
  email and calendar", "prepare my daily plan".
- **Should NOT trigger:** unrelated coding/help requests. The `daily-brief` description is scoped to
  planning/brief phrasing so it doesn't fire on general questions.

## B. claude.ai (standalone Skill)

1. Build the upload bundles:
   ```bash
   make package        # → dist/daily-brief-skill.zip + dist/team-brief-skill.zip (skill folder at ZIP root)
   ```
2. In claude.ai (Pro/Max/Team/Enterprise with code execution enabled), go to **Settings →
   Features / Skills** and **upload** `dist/daily-brief-skill.zip` (personal) and/or
   `dist/team-brief-skill.zip` (role/team). Each ZIP is self-contained (bundles its own
   scripts/schemas/config).
3. Enable the Skill, then test with several trigger prompts and confirm from Claude's thinking that
   it loads `daily-brief` / `team-brief`.

> Skills do not sync across surfaces — uploading to claude.ai is separate from Claude Code and the
> API. The standalone ZIP bundles its own copy of the schema so it is self-contained.

## C. Preferences / profile

- **Personal brief:** run `prompts/onboarding.md` to create `boo-preferences.json`
  (`skills/manage-boo-preferences/references/`).
- **Role/team brief:** run the `onboarding` skill (*"set up Boo"*) to create `role-profile.json`
  (role, team, connected providers, scope, timezone, brief time). Edit it later with
  `manage-role-profile`.

Save the file to your Claude account / Drive so scheduled runs can read it (a purely local file can't
be reached by a remote scheduled task).

## D. Sanity checks

```bash
make check     # runs the full quality gate locally (123 tests, validation, bundle-drift, secret scan, plugin validation)
```

Next: schedule the daily brief — `docs/SETUP-SCHEDULE.md`.
