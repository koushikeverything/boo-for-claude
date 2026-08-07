# Limitations

Candid list of what is and isn't verified, and what each remaining item needs.

## Verified with automated checks (no external access needed)

- Plugin (7 Skills) + Skill structure valid (`claude plugin validate .` passes; offline validator passes).
- Brief schema + semantic contract (provenance, dedup, ordering, conflicts, unattended-safety):
  **20 v1 + 16 v2** golden payloads validate; validator rejects each defect class.
- **v2 role model:** capability catalog + role matrix integrity, availability gate (hides
  unconnectable slots), gating (missing-mandatory flags), cross-source dedup/conflict, role-aware
  ranking (incl. **⚡ Superhuman**), and the **deep-link invariant** (every `open_source` action has a
  real permalink).
- Deduplication, timezone-boundary, and date-formatting logic (unit tests); bundle-drift guard.
- Mode B connector: envelope crypto (roundtrip, tamper, AAD binding, key rotation), OAuth PKCE +
  signed single-use state (session binding, replay, expiry, signature), store (migrations, encrypted
  creds, isolation, deletion, audit), narrow tools (no secret egress, approval-gating, draft-only,
  idempotency), and account isolation. **123 tests total** (72 skill + 51 connector) via `make check`.
- Secret scan clean; both standalone Skill ZIPs (daily-brief, team-brief) have the correct root layout
  and are self-contained.

## Live-only gates (PENDING — not exercised here)

| Gate | Needs | Why it can't run here |
|------|-------|-----------------------|
| Real scheduled Cowork brief | Paid Claude plan + Cowork + connected Google account(s) | No account/credentials in this environment |
| Native multi-account test (T1) | 2 Google accounts on a paid plan | Confirms/refutes the documented single-account limit |
| Scheduler timezone control (T2) | Cowork task UI | Not documented; verify empirically |
| Unattended approval-mode behavior (T3) | Cowork scheduled run | Confirm no mutation path exists unattended |
| Interactive MCP App component (T4) | Supported surface | Availability unverified; Markdown brief works without it |
| **Role briefs on live data** | Connected work tools (Slack/GitHub/Linear/…) on a paid plan | Connectors need interactive OAuth; the 7 non-engineer roles + a full multi-connector engineer run haven't been exercised on real accounts (only GitHub confirmed live) |
| Mode B **live** Google calls | Google Cloud OAuth app + public HTTPS host + real accounts | Network + real credentials + hosting required |
| Mode B token refresh / revoke live | Same as above | `LiveGoogleClient` methods raise `LIVE GATE PENDING` by design |

## Known functional limits (by platform design)

- **Gmail attachment content** is not accessible via connectors (metadata only) — Boo cites
  attachments by name and never asserts their contents.
- **Drive** returns text only; images embedded in documents aren't processed — Boo never claims
  image contents.
- **Gmail send** is impossible by design — Boo creates drafts only (this is a feature, not a gap).
- **Scheduled results** are separate sessions; Boo cannot deliver into one fixed, pre-existing chat.
- **Custom Skills don't sync across surfaces** — install/upload separately for Claude Code, claude.ai,
  and API.

### Role/team brief (v2) specifics

- **No product-analytics connector yet** (Amplitude/Mixpanel/PostHog have no native connector), so the
  analytics slot is **hidden** and PM/Head-of-Product/Data briefs say so plainly. This is the single
  biggest content gap and the top candidate for a custom connector (Phase 9).
- **Deep-links depend on the connector exposing a permalink.** Where a source has no addressable URL,
  the brief offers a chat-prompt action instead of an "Open …" link (never a dead link) — see the
  retrieval-policy invariant.
- **M365/Teams is native** (one connector covers Outlook + Teams + SharePoint), so the M365 path needs
  no custom connector — but it hasn't been exercised on a live tenant here.
- **Non-native providers are hidden, not broken** (Bitbucket, Opsgenie, Grafana, Zendesk, ClickUp): the
  availability gate never offers them; the golden path uses their native substitutes.
- **Onboarding coaches, never authorizes** — the final OAuth "Authorize" is always the user's action;
  Claude cannot connect a tool or create a schedule on the user's behalf (platform boundary).

## Implementation scope notes

- The MCP transport wiring in `connector/boo_connector/server.py` requires the `mcp` SDK and is
  marked `pragma: no cover`; the tool logic it serves is fully tested independently.
- `LiveGoogleClient` intentionally raises until the network execution is implemented against real
  credentials; `FixturesGoogleClient` backs all tests.
- The AES-256-GCM crypto backend is available (`BOO_CRYPTO_BACKEND=aesgcm`) but the stdlib
  encrypt-then-MAC backend is the tested default so the suite needs no third-party packages.

## Next highest-value improvements

1. **Live role-brief data runs** — connect the work tools (Calendar reconnect + work Slack + the rest)
   and run all roles on real data, capturing observations. Only GitHub is confirmed live today; this
   is the single biggest step toward "shippable with confidence."
2. **A product-analytics connector** — unblocks the analytics slot for PM/Head-of-Product/Data (the
   biggest content gap). Reuses the parked Mode-B pattern.
3. **T1 native multi-account test** (2 Google accounts) — confirms whether Mode B is strictly required
   for the multi-account promise; lower priority now that v2 ships native-only per-viewer.
