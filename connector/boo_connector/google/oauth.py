"""Google OAuth web-server flow helpers: PKCE, nonce, and signed single-use state.

These are pure builders and verifiers — no network. The live token exchange/refresh POSTs live in
`LiveGoogleClient` (client.py) and are gated PENDING real credentials. Keeping the crypto-sensitive
parts pure makes them fully unit-testable (see connector/tests/test_oauth_state.py).

State token design (defends against CSRF / replay / cross-session fixation):
  * bound to the browser session id (`sid`);
  * carries a random `nonce` (also sent to Google and checked on return);
  * carries a unique `jti` marked single-use in the DB after consumption;
  * carries an expiry (`exp`); short TTL;
  * HMAC-signed with a server secret; verified in constant time.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional
from urllib.parse import urlencode

AUTH_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"

DEFAULT_SCOPES = [
    "openid",
    "email",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.compose",  # drafts only; NOT gmail.send
    "https://www.googleapis.com/auth/calendar.events",
    "https://www.googleapis.com/auth/drive.metadata.readonly",
]


class OAuthError(Exception):
    pass


def _b64url(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode("ascii")


def _b64url_decode(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


@dataclass
class OAuthConfig:
    client_id: str
    client_secret: str
    redirect_uri: str
    scopes: List[str] = field(default_factory=lambda: list(DEFAULT_SCOPES))

    @classmethod
    def from_env(cls, env: Optional[Dict[str, str]] = None) -> "OAuthConfig":
        env = env or dict(os.environ)
        missing = [k for k in ("GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "GOOGLE_REDIRECT_URI")
                   if not env.get(k)]
        if missing:
            raise OAuthError(f"missing OAuth env vars: {missing}")
        scopes = env.get("GOOGLE_SCOPES")
        return cls(
            client_id=env["GOOGLE_CLIENT_ID"],
            client_secret=env["GOOGLE_CLIENT_SECRET"],
            redirect_uri=env["GOOGLE_REDIRECT_URI"],
            scopes=scopes.split() if scopes else list(DEFAULT_SCOPES),
        )


# -- PKCE --------------------------------------------------------------------------------

def generate_pkce() -> Dict[str, str]:
    verifier = _b64url(os.urandom(48))  # 43-128 chars per RFC 7636
    challenge = _b64url(hashlib.sha256(verifier.encode("ascii")).digest())
    return {"code_verifier": verifier, "code_challenge": challenge, "method": "S256"}


# -- signed single-use state -------------------------------------------------------------

def issue_state(secret: bytes, session_id: str, ttl_seconds: int = 600,
                now: Optional[float] = None, nonce: Optional[str] = None) -> Dict[str, str]:
    now = now if now is not None else time.time()
    payload = {
        "sid": session_id,
        "nonce": nonce or _b64url(os.urandom(16)),
        "jti": _b64url(os.urandom(12)),
        "exp": int(now) + ttl_seconds,
    }
    body = _b64url(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8"))
    sig = _b64url(hmac.new(secret, body.encode("ascii"), hashlib.sha256).digest())
    return {"state": f"{body}.{sig}", "nonce": payload["nonce"], "jti": payload["jti"]}


def verify_state(secret: bytes, state: str, session_id: str,
                 is_consumed: Callable[[str], bool], mark_consumed: Callable[[str], None],
                 now: Optional[float] = None) -> Dict:
    """Verify signature, session binding, expiry, and single-use. Raises OAuthError on any failure.
    On success, marks the jti consumed and returns the payload."""
    now = now if now is not None else time.time()
    try:
        body, sig = state.split(".", 1)
    except ValueError:
        raise OAuthError("malformed state")
    expected = _b64url(hmac.new(secret, body.encode("ascii"), hashlib.sha256).digest())
    if not hmac.compare_digest(expected, sig):
        raise OAuthError("bad state signature")
    payload = json.loads(_b64url_decode(body))
    if payload.get("sid") != session_id:
        raise OAuthError("state session mismatch (possible fixation)")
    if int(payload.get("exp", 0)) < now:
        raise OAuthError("state expired")
    jti = payload.get("jti", "")
    if is_consumed(jti):
        raise OAuthError("state already used (replay)")
    mark_consumed(jti)
    return payload


# -- request builders (no network) -------------------------------------------------------

def build_authorization_url(cfg: OAuthConfig, state: str, code_challenge: str, nonce: str,
                            login_hint: Optional[str] = None) -> str:
    params = {
        "client_id": cfg.client_id,
        "redirect_uri": cfg.redirect_uri,
        "response_type": "code",
        "scope": " ".join(cfg.scopes),
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
        "nonce": nonce,
        "access_type": "offline",       # request a refresh token
        "prompt": "consent",            # ensure a refresh token is returned on re-consent
        "include_granted_scopes": "true",
    }
    if login_hint:
        params["login_hint"] = login_hint
    return f"{AUTH_ENDPOINT}?{urlencode(params)}"


def build_token_exchange_request(cfg: OAuthConfig, code: str, code_verifier: str) -> Dict:
    """Returns {url, data} for the authorization-code -> tokens POST (application/x-www-form-urlencoded)."""
    return {
        "url": TOKEN_ENDPOINT,
        "data": {
            "grant_type": "authorization_code",
            "code": code,
            "client_id": cfg.client_id,
            "client_secret": cfg.client_secret,
            "redirect_uri": cfg.redirect_uri,
            "code_verifier": code_verifier,
        },
    }


def build_refresh_request(cfg: OAuthConfig, refresh_token: str) -> Dict:
    """Returns {url, data} for the refresh-token -> access-token POST."""
    return {
        "url": TOKEN_ENDPOINT,
        "data": {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": cfg.client_id,
            "client_secret": cfg.client_secret,
        },
    }
