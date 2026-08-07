# Boo connector (Mode B) — multi-account remote MCP server

Built **only** because native Google connectors don't documentably expose multiple Google accounts
to one Claude task (see `../docs/PLATFORM-CAPABILITIES.md`, `../docs/MULTI-ACCOUNT.md`). It lets one
Boo identity connect several Google accounts, keeps every result attributed to a stable account id,
and never returns tokens to Claude.

**Status:** core (crypto, OAuth builders, store, tools, isolation) fully implemented and tested
against fixtures — 40 tests. **Live gate PENDING:** real Google API execution + MCP serving need
OAuth credentials and public HTTPS hosting.

## Layout

```
connector/
├── boo_connector/
│   ├── crypto/envelope.py     # versioned envelope encryption (encrypt-then-MAC; AES-GCM optional)
│   ├── google/oauth.py        # PKCE, signed single-use state, auth/token/refresh request builders
│   ├── google/client.py       # GoogleClient: FixturesGoogleClient (tested) + LiveGoogleClient (gated)
│   ├── store/db.py            # SQLite store + migration runner (accounts, encrypted creds, audit)
│   ├── tools/boo_tools.py     # narrow boo_* MCP tools (no raw HTTP/SQL; no token egress)
│   ├── config.py             # env-driven runtime assembly
│   └── server.py             # thin MCP entrypoint (lazy-imports the mcp SDK)
├── migrations/               # 0001_init.sql, 0002_audit.sql
├── fixtures/                 # deterministic offline data for tests
├── tests/                    # 40 tests
├── Dockerfile  requirements.txt  .env.example
```

## Narrow tool surface (what Claude can call)

`boo_list_accounts` · `boo_search_relevant_mail` · `boo_list_day_events` ·
`boo_get_referenced_drive_metadata` · `boo_get_source_details` · `boo_preview_gmail_draft` ·
`boo_create_gmail_draft` · `boo_preview_calendar_event` · `boo_create_calendar_event` ·
`boo_update_account_status`.

There is deliberately **no** generic HTTP tool and **no** raw-SQL tool. Read tools isolate
per-account failures into a `source_status`; mutating tools refuse during unattended runs and
require `approved=true`; drafts are never sent.

## Run the tests (no dependencies)

```bash
cd connector
python3 -m unittest discover -s tests -p 'test_*.py'
```

## Run locally in fixtures mode (no Google creds)

```bash
export BOO_STATE_SECRET=dev-secret
export BOO_ENC_KEYS="1:$(python3 -c 'import os,base64;print(base64.urlsafe_b64encode(os.urandom(32)).decode().rstrip("="))')"
export BOO_USE_FIXTURES=true
python3 -m boo_connector.server   # prints guidance if the `mcp` SDK isn't installed
```

## Deploy live (the PENDING gate)

1. **Google Cloud:** create an OAuth 2.0 **Web application** client. Add the redirect URI
   `https://<your-host>/oauth/callback`. Request only the scopes in `oauth.py::DEFAULT_SCOPES`
   (read-only + `gmail.compose` for drafts + `calendar.events`). **Do not** request `gmail.send`.
2. **Secrets:** set every var in `.env.example` (generate `BOO_ENC_KEYS` and `BOO_STATE_SECRET`;
   fill Google client id/secret/redirect). Store them in a secret manager, not in the image.
3. **The live edges are implemented and unit-tested** (fake-HTTP): real Gmail/Calendar/Drive calls
   (`google/live.py`), token refresh (`google/tokens.py`), and OAuth linking (`google/oauth_flow.py`).
   The one deploy-time integration point is the ASGI/MCP transport in `server.py` — confirm the MCP
   `StreamableHTTPSessionManager` import matches your installed `mcp` version, and set
   `BOO_DEFAULT_USER_ID` (single-tenant) or replace `resolve_user_id` with your real session auth.
4. **Build & run:**
   ```bash
   docker build -t boo-connector .
   # single-tenant example:
   docker run --env-file .env -e BOO_DEFAULT_USER_ID=koushik -v boo-data:/data -p 8080:8080 boo-connector
   ```
5. **Expose over public HTTPS** (managed ingress / reverse proxy) so the redirect URI and `/mcp`
   endpoint are reachable.
6. **Link accounts:** visit `https://<host>/oauth/connect?label=Personal`, approve on Google; repeat
   with `?label=Work` (and any others) — each links a distinct Google `sub`. Verify with a call to
   `boo_list_accounts`.
7. **Add it in Claude** as a **remote MCP connector** (URL `https://<host>/mcp`). The `daily-brief`
   Skill's `boo_*` calls then work unchanged, now across all linked accounts.
6. **Key rotation:** add a new version to `BOO_ENC_KEYS`, bump `BOO_ENC_CURRENT_VERSION`; new writes
   use it and `EnvelopeCipher.needs_rotation()` flags old tokens for re-encryption on next refresh.

## Production storage

SQLite is the portable default. For production, point `BOO_DB_PATH` at Postgres (same schema +
migrations; add `psycopg`), which gives durable state and concurrent access for scheduled runs.
