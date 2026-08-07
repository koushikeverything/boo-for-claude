# Connector health — diagnosis playbook

A connector can be unusable for **six different reasons**, and only one of them is "you didn't click
Connect." Each looks different and needs a different fix. Boo's onboarding + brief use this playbook so
a new user never faces a cryptic dead end — the failure is named, with the exact remedy.

## The universal diagnostic: the tool-list probe

In any chat, ask:

```
List every connector and tool you have access to in this chat. Names only.
```

What you see tells you which class you're in below. "Connected in the account" is **not** the same as
"usable in this chat."

## The six failure classes

| # | Symptom | Cause | Fix |
|---|---------|-------|-----|
| 1 | Tool group **absent** from the list; Settings shows nothing | **Not connected** | Connect it — in-chat Connect card (`suggest_connectors`), `/mcp` in Claude Code, or Settings → Connectors. |
| 2 | Connected in Settings, but tool group **absent in this chat** | **Not enabled for this chat** | Enable it in the chat's tools menu. **Scheduled tasks need it enabled per-task**, not just per-chat. |
| 3 | Shows **✗ failed** (not "needs auth") in `/mcp` | **Server can't start** — usually a **missing env-var/token** in its config (e.g. `${GITHUB_PERSONAL_ACCESS_TOKEN}`), or a missing binary | Run `python3 scripts/connector_doctor.py` / `make doctor` — it names the missing variable and the fix. Set it, reopen the terminal, relaunch. |
| 4 | A GitHub (or similar) link is "connected" but no read tools appear | **Wrong flavor** — the attach-style "GitHub Integration" instead of the **GitHub tool connector** | Authorize the tool connector (`engineering:github` via `/mcp`, or the in-chat Connect card) — not the attach Integration. |
| 5 | Tool loads but **errors on every call**, including a bare list | **Stale/expired token** | Disconnect and reconnect the provider (re-auth). |
| 6 | Tools work but return nothing / permission errors; or the *wrong* data | **Insufficient scope** or **wrong workspace/account** (e.g. a non-work Slack) | Broaden the grant (repos/org), or reconnect the correct workspace/account. |

## The proactive guard: `connector_doctor`

Class **3** is the nastiest because it's silent and cryptic — clicking "Connect" never fixes a missing
env var. `scripts/connector_doctor.py` scans your Claude Code connector configs on disk, finds every
`${ENV_VAR}` a connector requires, and reports which are **unset**, with a targeted fix — **before** you
waste time. It never prints a variable's value, only whether it's set.

```bash
make doctor          # or: python3 scripts/connector_doctor.py
```

Example (real): it flags GitHub/GitLab/Terraform/Greptile connectors that need a token env var, and
for GitHub suggests wiring it from the `gh` CLI:
`export GITHUB_PERSONAL_ACCESS_TOKEN="$(gh auth token)"`.

## How Boo uses this

- **Onboarding** runs the tool-list probe per expected connector, offers the in-chat Connect card, and
  (in Claude Code) points to `connector_doctor` for any `✗ failed` server — so each gap is coached with
  its specific fix, never a generic "not connected."
- **The brief's coverage line** distinguishes the classes: missing (blocking gap), degraded/reconnect,
  wrong workspace, partial — and never fabricates through any of them.

## What stays the user's action (by design)

The final **Authorize** on a provider's consent screen, and setting a secret env var, are the user's
actions — an agent must never enter credentials or grant scopes on your behalf. Boo detects, explains,
and hands you the one-click Connect card or the exact command; you approve.
