"""OAuth connect/callback flow logic (testable, no web framework).

`begin_connect` builds the Google authorization URL (with PKCE + signed single-use state + nonce).
`complete_connect` verifies the returned state, exchanges the code for tokens, extracts the stable
Google subject (`sub`) + email from the id_token, and upserts the account with its encrypted
refresh token. The ASGI route handlers in server.py are thin wrappers over these.
"""
from __future__ import annotations

import base64
import json
from typing import Dict

from .http import HttpClient
from .oauth import (
    OAuthConfig,
    OAuthError,
    build_authorization_url,
    build_token_exchange_request,
    generate_pkce,
    issue_state,
    verify_state,
)


def begin_connect(cfg: OAuthConfig, state_secret: bytes, session_id: str, ttl: int = 600,
                  login_hint: str = None) -> Dict:
    """Return everything the route must stash in the server-side session + the redirect URL.

    The route must persist `code_verifier` (and `state`) in the browser session, keyed so the
    callback can retrieve them. They are secrets-in-transit; never expose them to Claude.
    """
    pkce = generate_pkce()
    st = issue_state(state_secret, session_id, ttl)
    url = build_authorization_url(cfg, st["state"], pkce["code_challenge"], st["nonce"],
                                  login_hint=login_hint)
    return {
        "auth_url": url,
        "state": st["state"],
        "nonce": st["nonce"],
        "code_verifier": pkce["code_verifier"],
    }


def _decode_jwt_payload(id_token: str) -> Dict:
    """Decode the JWT payload. The id_token is obtained directly from Google's token endpoint over
    TLS during the code exchange, so it is trusted without local signature verification (per
    Google's server-to-server guidance). Signature verification is a documented hardening item."""
    try:
        _, payload_b64, _ = id_token.split(".")
    except ValueError:
        raise OAuthError("malformed id_token")
    padded = payload_b64 + "=" * (-len(payload_b64) % 4)
    return json.loads(base64.urlsafe_b64decode(padded))


def complete_connect(cfg: OAuthConfig, state_secret: bytes, session_id: str, state: str, code: str,
                     code_verifier: str, http: HttpClient, store, user_id: str,
                     label: str = "Personal") -> Dict:
    # 1. verify signed, single-use, session-bound state (raises on replay/expiry/mismatch)
    verify_state(state_secret, state, session_id, store.is_state_consumed, store.mark_state_consumed)

    # 2. exchange the authorization code for tokens
    req = build_token_exchange_request(cfg, code, code_verifier)
    resp = http.request("POST", req["url"], form=req["data"])
    if not resp.ok:
        raise OAuthError(f"token exchange failed: HTTP {resp.status}")
    body = resp.body

    # 3. identify the account by stable Google subject (not email alone)
    claims = _decode_jwt_payload(body.get("id_token", ""))
    sub = claims.get("sub")
    email = claims.get("email")
    if not sub:
        raise OAuthError("no subject (sub) in id_token")

    granted_scopes = (body.get("scope") or "").split()
    store.upsert_account(sub, user_id, label, granted_scopes, email)

    # 4. store the refresh token (Google returns it on first consent; prompt=consent forces it)
    refresh_token = body.get("refresh_token")
    if refresh_token:
        store.store_refresh_token(sub, refresh_token)

    return {
        "account_id": sub,
        "email": email,
        "label": label,
        "granted_scopes": granted_scopes,
        "has_refresh_token": bool(refresh_token),
    }
