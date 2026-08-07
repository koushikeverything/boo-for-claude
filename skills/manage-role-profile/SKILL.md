---
name: manage-role-profile
description: View, edit, or reset the user's Boo role profile and connected tools. Use when the user says "change my role", "add GitHub to my brief", "connect Linear", "pause Slack", "remove a tool", "switch from Google to Microsoft 365", "change my repos/channels scope", "set my brief time to 8am", "what tools am I connected to", or "export/delete my Boo profile". Every change is explicit, reviewable, reversible, and scoped — never inferred.
---

# Manage role profile & connected tools

Reads and edits the user's `role-profile.json` (schema `schemas/role-profile.schema.json`) and helps
manage their tool connections. Nothing is silent or inferred; echo every change before applying it.

## Where the profile lives

A reviewable `role-profile.json` saved to the user's Claude account / Drive so scheduled runs can read
it. (A purely local file can't be reached by a remote scheduled task.)

## Viewing

- **"What's my setup?"** → summarize role, team, timezone, brief time, and each connection
  (capability · provider · scope · status).
- **"What tools am I connected to?"** → list connections with status (active / paused /
  reconnect_needed / removed) and note any **missing mandatory** slots for the role (run gating,
  `lib/gating.py evaluate`).

## Editing (echo old → new, then save)

1. Read the current profile.
2. State the exact change and its scope ("future briefs only").
3. Apply it to the JSON; **show the updated profile**; save.
4. Confirm, and note it's reversible.

Examples:
- **"Add GitHub"** → add a `code` connection (provider `github`). Surface an in-chat **Connect card**
  where the surface supports it (`suggest_connectors` / `suggest_plugin_install`), or point to `/mcp`
  / Settings → Connectors. Use the **GitHub *tool* connector** (agentic PR/CI/issue tools), not the
  attach-style "GitHub Integration". Then **verify with the tool-list probe** that a `github_*` tool
  group is actually available in the chat before relying on it.
- **"Switch from Google to Microsoft 365"** → change the `productivity` connection's provider; note
  that M365 also covers Teams. (Substitution within a slot.)
- **"Pause Slack"** → set that connection's status to `paused` (skipped in future briefs, recoverable).
- **"Only watch acme/api and acme/web"** → set the `code` connection's `scope.repos`.
- **"Move my brief to 8am"** → set `brief_time`; remind the user to update the **Cowork schedule time**
  and to keep the scheduled task's connectors enabled.

## Provider validity

Only offer providers valid for the capability and **connectable** (`native_connector: true`); reject a
mismatch (e.g. Figma for `code`). Use `lib/gating.py` (`connectable_providers`) to enforce this.

## Account/tool lifecycle

Support: list · connect another · switch provider · set scope · pause · resume · remove · change
default. For native connectors, connecting/disconnecting happens in Claude's connector settings —
this skill records the intent (label, provider, scope, status) and coaches the exact UI step.

## Export & delete (user rights)

- **Export:** return the `role-profile.json` contents.
- **Delete:** on request, delete the profile file. Confirm what will be removed first. For each
  connected tool, remind the user they can also revoke access in their connector settings.
