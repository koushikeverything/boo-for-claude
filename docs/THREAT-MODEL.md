# Threat model

Scope: the Boo Skills, the scheduled Cowork execution, and the Mode B multi-account MCP connector.
Each threat lists the mitigation and, where applicable, the test that enforces it.

| # | Threat | Mitigation | Enforced by |
|---|--------|------------|-------------|
| 1 | **Malicious instructions inside an email** ("forward all invoices", "ignore previous instructions") | Source content is untrusted data; directives are ignored and, if material, flagged. Content from `boo_get_source_details` is labeled `content_is_untrusted`. | `evals/expected/11-prompt-injection.json` + scenario 11 checks (`no_say_contains`) |
| 2 | **OAuth state / CSRF / fixation** | State token is HMAC-signed, bound to the browser `sid`, carries a random `nonce` and unique `jti`, and short TTL. | `connector/tests/test_oauth_state.py` |
| 3 | **PKCE downgrade / code interception** | `code_challenge_method=S256`; verifier never leaves the connector; challenge derived by SHA-256. | `test_oauth_state.py::TestPKCE`, `TestRequestBuilders` |
| 4 | **State replay** | `jti` marked single-use in the store; second use rejected. | `test_oauth_state.py::test_single_use_replay_rejected`, `test_store.py` |
| 5 | **Connector impersonation** | Connector reachable only over public HTTPS; Google `client_secret` server-side; redirect URI pinned; MCP session authenticates the Boo user. | config + `.env.example`; live gate |
| 6 | **Cross-user / cross-account access** | Every tool scoped to `ctx.user_id`; accounts keyed by stable Google `sub`; a foreign user's account id resolves to "unavailable". | `test_tools.py::test_tool_rejects_foreign_user_account`, `test_store.py` |
| 7 | **Refresh-token theft at rest** | Versioned envelope encryption (encrypt-then-MAC, per-record nonce); keys from secret manager; rotation supported. | `test_crypto.py` |
| 8 | **Token leakage into Claude context** | Tools never return tokens/codes/ciphertext; `load_refresh_token` is internal to the refresh path. | `test_tools.py` (no-secrets assertions), design |
| 9 | **Tampered stored token** | AEAD tag verified on decrypt (constant-time); tampering raises. | `test_crypto.py::test_tamper_is_detected`, `test_aad_binding` |
| 10 | **Unsafe external links** | Boo never follows/auto-submits forms from source links; links shown to the user only. | safety-policy.md, privacy rules |
| 11 | **Overbroad retrieval** | Bounded, category-targeted queries with documented caps; over-limit recorded in `omissions`. | retrieval-policy.md; schema `omissions` |
| 12 | **Accidental mutation** | All mutations require preview + explicit `approved=true`; idempotency keys prevent duplicates. | `test_tools.py` create-draft/event tests |
| 13 | **Mutation during unattended run** | Tools refuse when `attended=False`; scheduled prompt is read-only. | `test_tools.py::test_create_draft_refused_when_unattended` |
| 14 | **Stale / revoked grants** | Per-account health (`reconnect_needed`); broken account degrades to partial coverage, never blocks others. | `test_isolation.py`, scenarios 07/20 |
| 15 | **Sending email instead of drafting** | Draft-only tool; asserts `sent == False`; `gmail.send` scope never requested. | `test_tools.py::test_create_draft_never_sends...`, `test_oauth_state.py` |
| 16 | **Retention / deletion gaps** | Account removal deletes credentials; user deletion removes all rows; audit holds safe metadata only. | `test_store.py::test_remove_account_isolates`, `test_delete_user_removes_all` |
| 17 | **Logs/telemetry leaking secrets** | Audit stores metadata only; secret scan in the gate; no token printing. | `test_store.py::test_audit_records_safe_metadata_only`, `scripts/secret_scan.sh` |
| 18 | **Public remote MCP exposure** | Narrow tools only (no raw HTTP/SQL tool); per-user scoping; HTTPS; least-privilege scopes. | `boo_tools.py` (no generic tool), `.env.example` |

## Non-goals / assumptions

- The Claude platform's own auth of the MCP session is trusted to identify the Boo user; the
  connector binds `user_id` from that session, not from tool input.
- The host's secret manager protects `BOO_ENC_KEYS` and `BOO_STATE_SECRET`. Compromise of those is
  out of scope (as with any server holding encryption keys) but is contained by key versioning and
  the ability to rotate + re-encrypt.
- Google's OAuth endpoints and API authorization behave per their documentation.

## Residual risks (live gate)

Live Mode B has not been exercised against real Google endpoints; the request builders and token
flow are unit-tested but the network execution and Google's real error surface remain to be
validated (see `docs/LIMITATIONS.md`).

## Org / role brief (v2) additions

The role brief spans many work tools, which widens the surface. Mitigations:

| # | Threat | Mitigation | Enforced by |
|---|--------|------------|-------------|
| 19 | **Injection from any tool** — a Slack message, PR/issue body, review comment, CI log, ticket, Figma comment, or alert telling the agent to act | All source content is untrusted data; directives ignored and flagged; content can never invoke a tool | `skills/team-brief/references/safety-policy.md`; scenario coverage in Phase 10 |
| 20 | **Cross-person data exposure** ("org-wide" over-reach) | **Per-viewer scoping**: brief built only from tools the user connected with their own credentials — never exceeds their own permissions. No service/bot aggregation identity in v2. Holds for the **Superhuman** free-pick role (more tools = wider within *own* access only) | safety-policy.md; architecture (Model A) |
| 21 | **Autonomous write via a write-capable connector** (M365 send, Slack post, GitHub merge/close, PagerDuty resolve) | Read + draft/preview only; every write is preview→approval→one idempotent op; **no autonomous send/post/merge/close/resolve**; the schema has **no** such action types | `tests/test_governance.py` (no autonomous types; writes require approval), safety-policy.md |
| 22 | **Mutation during a scheduled run** | Unattended = read-only across ALL sources | safety-policy.md; scheduled prompt |
| 23 | **Wrong-target action** (posting to the wrong channel/repo/account) | Never guess target; confirm tool + workspace in the preview | safety-policy.md; brief-actions pattern |
| 24 | **Offering a slot with no vetted connector** | Availability gate hides non-connectable providers/slots; native-only in v2 | `lib/gating.py`, `tests/test_role_model.py` |
| 25 | **Confidentiality / egress** of work data | Data minimization (evidence only, no full bodies); no external egress; no data in URLs; no auto-form-submit from source links | safety-policy.md |

Per-source isolation: each connector authenticates independently and Boo never sees tokens (native
connectors return only tool results). A failing connector degrades to partial coverage.
