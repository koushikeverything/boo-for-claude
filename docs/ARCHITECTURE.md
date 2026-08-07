# Architecture

Boo separates **Workflows** (Skills), the **Agent** (Claude), and **Tools** (connectors + scripts).
Sections 1–5 cover the personal brief (native Google — Mode A; the parked multi-account MCP connector
— Mode B). Sections 6–7 cover the **v2 role/team brief** (native-only, per-viewer scoping) and its
card-driven onboarding. Diagrams use Mermaid (renders in most Markdown viewers; readable as text
otherwise).

## 1. Native connector mode (Mode A)

```mermaid
flowchart LR
  User([User]) -->|"my day ahead"| Claude
  subgraph ClaudeEnv[Claude session]
    Claude[Claude + Boo Skills]
    Skill[[daily-brief SKILL.md<br/>+ references + validate_brief.py]]
    Claude --- Skill
  end
  Claude -->|read, approval-gated| GC[Native Google connectors]
  GC --> Gmail[(Gmail)]
  GC --> Cal[(Calendar)]
  GC --> Drive[(Drive)]
  Claude -->|validated payload| Brief[[Your day ahead\nMarkdown brief]]
  Brief --> User
  Prefs[(boo-preferences.json\nDrive / Claude files)] --> Claude
  note1["Single account. No custom OAuth app, no backend."]
```

## 2. Multi-account MCP mode (Mode B)

```mermaid
flowchart LR
  User([User]) --> Claude
  Claude[Claude + Boo Skills] -->|narrow boo_* tools| MCP
  subgraph Connector[Boo remote MCP connector  ·  public HTTPS]
    MCP[MCP tool layer\nboo_list_accounts, boo_search_relevant_mail, …]
    OAuth[OAuth: PKCE + signed single-use state + nonce]
    Store[(Encrypted store\naccounts · versioned envelope tokens · audit)]
    Client[Google client\nper-account, token-scoped]
    MCP --- Store
    MCP --- Client
    OAuth --- Store
  end
  Client -->|access token per account| G1[(Personal Google)]
  Client --> G2[(Work Google)]
  Client --> G3[(Family Google)]
  MCP -.->|never returns tokens/codes| Claude
  note2["One Boo identity ↔ many Google accounts.\nEvery result attributed to a stable account_id."]
```

## 3. Scheduled-run sequence

```mermaid
sequenceDiagram
  participant Cowork as Cowork scheduler
  participant Claude
  participant Skill as daily-brief Skill
  participant Src as Connectors (Mode A / Mode B tools)
  Cowork->>Claude: fire scheduled prompt (daily, local time)
  Note over Claude: attended = FALSE (unattended) → READ-ONLY
  Claude->>Skill: load workflow + preferences
  Skill->>Src: bounded reads per ACTIVE account (Gmail/Cal/Drive)
  Src-->>Skill: items + per-source status (complete/partial/unavailable)
  Skill->>Skill: ground · dedup · rank · build payload
  Skill->>Skill: validate against schema + semantic rules
  Skill-->>Claude: validated payload
  Claude-->>Cowork: render "Your day ahead" (its OWN session)
  Note over Claude: NO drafts, NO calendar writes, NO RSVPs. Actions surfaced as follow-ups.
```

## 4. Follow-up action & confirmation sequence

```mermaid
sequenceDiagram
  participant User
  participant Claude
  participant Actions as brief-actions Skill
  participant Conn as Connector
  User->>Claude: "Draft the sitter email, but show me first"
  Claude->>Actions: resolve target + choose account (ask if ambiguous)
  Actions->>Conn: boo_preview_gmail_draft(account, to, subject, body)
  Conn-->>Actions: preview (requires_approval=true)
  Actions-->>User: show account + recipient + subject + full body
  User->>Claude: "Yes"
  Claude->>Conn: boo_create_gmail_draft(..., approved=true, idempotency_key)
  Conn-->>Claude: draft_id, location, sent=FALSE
  Claude-->>User: "Draft created in {account} Gmail — not sent."
```

## 5. Data & trust boundaries

```mermaid
flowchart TB
  subgraph Untrusted[UNTRUSTED source content]
    Mail[Email bodies]:::u
    Ev[Event descriptions]:::u
    Files[File / attachment names]:::u
    Links[Linked pages]:::u
  end
  subgraph Trusted[TRUSTED instructions]
    UserI[User chat instructions]:::t
    SkillI[Skill / CLAUDE.md policies]:::t
  end
  Untrusted -->|"data only, never commands"| Agent[Claude / Agent]
  Trusted -->|"authoritative"| Agent
  Agent --> Brief[Validated brief payload]

  subgraph Secrets[SECRET zone — never crosses to Claude]
    RT[(Refresh tokens\nencrypted at rest)]:::s
    AC[OAuth codes]:::s
    AT[Access tokens]:::s
  end
  Secrets -. blocked .-> Agent
  Conn[Boo connector] --- Secrets
  Conn -->|narrow tool results\nno secrets| Agent

  classDef u fill:#fde,stroke:#b36;
  classDef t fill:#dfe,stroke:#3a6;
  classDef s fill:#eee,stroke:#900,stroke-dasharray:4 3;
```

## 6. Role/team brief mode (v2 — Model A, per-viewer scoping)

Native-only. The role selects a requirement profile; the **availability gate** offers only
connectable providers; retrieval runs across the tools the user actually connected (their own
credentials, their own permissions); cross-source dedup/conflict collapses the same real-world thing
seen in several tools; role-aware ranking stamps an explicit `rank`; the same validator + output
contract render the brief. **⚡ Superhuman** is the free-pick role — every non-productivity slot is
optional, so the user connects any mix.

```mermaid
flowchart LR
  User([User]) -->|"my engineering brief"| Claude
  subgraph ClaudeEnv[Claude session]
    Claude[Claude + team-brief Skill]
    Profile[(role-profile.json\nrole · providers · scope · tz)]
    Gate[[gating.py\navailability + coverage]]
    Claude --- Profile
    Claude --- Gate
  end
  Gate -->|only connected + connectable| Conns[Native tool connectors]
  Conns --> Code[(GitHub / GitLab)]
  Conns --> Chat[(Slack / Teams)]
  Conns --> Track[(Jira / Linear)]
  Conns --> Inc[(PagerDuty)]
  Conns --> Obs[(Sentry / Datadog)]
  Conns --> Design[(Figma)]
  Conns --> Prod[(Google / M365)]
  Conns --> More[(Notion · Intercom …)]
  Conns --> Retrieve[[retrieve → dedup/conflict xsource.py → rank ranking.py]]
  Retrieve --> Validate[[validate_brief.py\nschema + semantic rules]]
  Validate -->|validated payload| Brief[[Your day ahead\nrole-ranked · every claim cited]]
  Brief --> User
  note6["Per-viewer scoping: brief never exceeds the user's own access.\nUnconnectable slots (analytics) hidden. Missing mandatory slot → flagged, not fabricated.\nEvery open action carries a real permalink."]
```

## 7. Card-driven onboarding (Cowork)

Setup is a sequence of **native selection cards** — the user completes it by clicking. Claude coaches
each connection but never authorizes: the final consent is always the user's, in the provider's OAuth
screen.

```mermaid
sequenceDiagram
  participant User
  participant Claude as Claude + onboarding Skill
  participant Gate as gating.py
  participant Conn as Connector (provider OAuth)
  Claude->>User: Card 1 — pick role (incl. ⚡ Superhuman)
  User-->>Claude: role
  Claude->>Gate: role_slot_menu(role) — connectable only
  Gate-->>Claude: slots (M/R/O), hidden slots
  Claude->>User: Card 2 — connect tools (in-chat Connect card)
  User->>Conn: click Authorize (in browser)
  Note over Claude: tool-list probe — verify the tool group is reachable in this chat
  Claude->>User: Card 3 — delivery time · Card 4 — sources
  Claude->>Claude: build + gate role-profile.json (show before saving)
  Claude-->>User: save + hand off run/schedule (enable connectors per-task)
```

## Component responsibilities

| Layer | Component | Responsibility |
|-------|-----------|----------------|
| Workflow | `skills/daily-brief` | v1 retrieval, grounding/dedup/rank, output contract, validation |
| Workflow | `skills/brief-details` | Cited follow-ups (read-only) |
| Workflow | `skills/brief-actions` | Preview → approval → single action → verified result (drafts only) |
| Workflow | `skills/manage-boo-preferences` | Personal preferences + account lifecycle |
| Workflow | `skills/team-brief` | v2 role brief — role packs, retrieval/ranking/output policy; self-contained bundle |
| Workflow | `skills/onboarding` | Card-driven first-run: role → tools → time → sources → role-profile.json |
| Workflow | `skills/manage-role-profile` | View/edit/pause/remove the role profile (reversible) |
| Tool | `config/` + `lib/gating.py` | Role model (catalog + matrix), availability gate, coverage note |
| Tool | `lib/ranking.py` · `lib/xsource.py` | Role-aware `rank`; cross-source dedup + conflict detection |
| Agent | Claude | Relevance, extraction, ranking, summarizing; never holds secrets |
| Tool | `connector/boo_connector/crypto` | Versioned envelope encryption of refresh tokens |
| Tool | `connector/boo_connector/google/oauth.py` | PKCE, signed single-use state, request builders |
| Tool | `connector/boo_connector/store` | Accounts, encrypted creds, health, audit, migrations |
| Tool | `connector/boo_connector/tools` | Narrow `boo_*` MCP tools (no raw HTTP/SQL, no token egress) |
| Tool | `skills/daily-brief/scripts` | Deterministic validation, dedup, date handling |

## Schema versioning

The personal brief is `schema_version "1.0"` (`schemas/daily-brief.schema.json`); the role/team brief
is `"2.0"` (`schemas/brief.schema.json`) — a **structural superset** with the same field names (so
`validate_brief.py` is unchanged), a widened `source` enum, and added `role`/`team`/`capability`/
`workspace`/`rank`. See `docs/SCHEMA-MIGRATION-v1-v2.md`. Each standalone skill bundles a byte-identical
copy of its scripts/schemas/config (a gate check enforces no drift) so the claude.ai upload is
self-contained.

## Key data-flow invariants

- Presentation is a **pure function** of the validated payload.
- Source content is **untrusted data**; it can inform the brief but never issue instructions or
  invoke a tool.
- Secrets (refresh/access tokens, OAuth codes, ciphertext) **never** cross into Claude's context.
- Unattended runs are **read-only**; mutations require attended, explicit approval (drafts/preview only).
- **Per-viewer scoping (v2):** the role brief is built only from tools the user connected with their
  own credentials — it never exceeds their own permissions; no service/bot aggregation.
- **Availability gate:** only connectable providers are offered; a slot with no connector (analytics
  today) is hidden, never fabricated.
- **Deep-link invariant:** any item with an `open_source` action carries a real permalink in a
  citation (enforced by `tests/test_acceptance_v2.py`); otherwise it offers a chat-prompt action.
- **Role ranking:** Top of mind is ordered by an explicit `rank` (urgency → role capability-priority
  → effort), honored by the validator.
