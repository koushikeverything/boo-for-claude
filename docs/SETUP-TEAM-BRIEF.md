# Setup — the role/team brief (Engineer pilot)

How to install, connect tools, and run the role brief. Written from the live dry-run findings so you
don't hit the walls we did.

## 1. Install the skill

- **Claude Code / Desktop:** `claude --plugin-dir <path-to-your-boo-clone>` (or install
  the `boo` plugin). Invoke with `/boo:team-brief` or "what's my engineering brief?".
- **claude.ai:** upload `dist/team-brief-skill.zip` in Settings → Capabilities → Skills, and enable it.

## 2. Connect your role's tools

Run the **onboarding** skill ("set up Boo") — it presents only the *connectable* tools for your role,
grouped Mandatory → Recommended → Optional, and surfaces an **in-chat Connect card** where the surface
supports it (`suggest_connectors` / `suggest_plugin_install`). You click Connect and complete the
provider's consent in your browser. **Boo never enters your credentials or approves scopes** — the
final "Authorize" is your click, by design.

Engineer mandatory slots: **code** (GitHub/GitLab), **chat** (Slack/Teams), **productivity**
(Google/M365). Recommended: tracking (Jira/Linear), incidents (PagerDuty), observability (Sentry/Datadog).

### ⚠️ The "two GitHubs" gotcha (important)

There are **two different GitHub connections** in the Claude ecosystem:

| | What it does | Gives the brief PR/CI/issue tools? |
|---|---|---|
| **GitHub Integration** (Settings → Connectors → "GitHub Integration") | attach repos to chat, Projects codebase sync, Claude Code repo selection | **No** |
| **GitHub *tool* connector** (the `engineering`-style GitHub connector) | agentic tools: read PRs/reviews/CI/issues | **Yes** |

If you connect only the **GitHub Integration**, GitHub **tools won't appear** in a chat and the brief
will (correctly) flag GitHub as a missing mandatory slot. Authorize the **GitHub tool connector** —
in **Claude Code** via `/mcp` (authorize `engineering:github`), or via the in-chat Connect card on
claude.ai. Then re-check (below).

## 3. Verify tools actually loaded — the tool-list probe

"Connected in the account" ≠ "usable in this chat." Before running, ask in the chat:

```
List every connector and tool you have access to in this chat. Names only.
```

Confirm the expected tool groups appear (a `github_*` group, `slack_*`, Calendar tools, …). If one is
missing → enable it in the chat's tools menu, finish its authorization (grant repos/org), or fix the
flavor (tool connector, not the attach Integration). Also watch for **loadable-but-erroring**
connectors (stale token → reconnect) and **wrong-workspace** Slack (connect your *work* workspace).

## 4. Run it

```
Boo, what's my engineering brief? My role is software_engineer, timezone Asia/Kolkata.
```

Top of mind ranks incidents > code > chat > tracking (today first); every item cites its tool + scope;
the coverage line flags any missing mandatory slot and any degraded connector. Nothing is fabricated.

## 5. Schedule it

Paste `prompts/scheduled-team-brief.md` into a Cowork daily task. **Enable the same connectors on the
task** (a scheduled task does not inherit a chat's connectors) and hard-code your timezone. Each run is
its own Cowork session. See `docs/SETUP-SCHEDULE.md`.

## 6. Safety recap

Read + draft/preview only; **never sends/posts/merges autonomously**; every write previews and asks;
**no mutations during a scheduled run**; per-viewer scoped (only what you can already see). See
`skills/team-brief/references/safety-policy.md`.
