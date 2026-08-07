"""Per-account access-token management.

Refreshes a short-lived access token from the encrypted refresh token in the store, caches it
until shortly before expiry, and marks an account `reconnect_needed` when Google rejects the
refresh (`invalid_grant`). Access tokens are used only to sign outbound Google requests and are
never returned to Claude.
"""
from __future__ import annotations

import time
from typing import Dict, Optional, Tuple

from .http import HttpClient
from .oauth import OAuthConfig, build_refresh_request


class TokenError(Exception):
    pass


class TokenManager:
    def __init__(self, store, oauth_config: OAuthConfig, http: HttpClient, clock=time.time):
        self.store = store
        self.cfg = oauth_config
        self.http = http
        self._clock = clock
        self._cache: Dict[str, Tuple[str, float]] = {}  # account_id -> (access_token, expires_at)

    def access_token(self, account_id: str) -> str:
        cached = self._cache.get(account_id)
        now = self._clock()
        if cached and cached[1] > now:
            return cached[0]

        refresh_token = self.store.load_refresh_token(account_id)  # internal; never leaves the connector
        req = build_refresh_request(self.cfg, refresh_token)
        resp = self.http.request("POST", req["url"], form=req["data"])

        if not resp.ok:
            err = (resp.body or {}).get("error")
            if err in ("invalid_grant", "unauthorized_client"):
                # the grant was revoked or expired — flag the account for reconnect, isolate it
                try:
                    self.store.set_status(account_id, "reconnect_needed")
                except Exception:
                    pass
                raise TokenError(f"account {account_id} needs reconnect ({err})")
            raise TokenError(f"token refresh failed for {account_id}: HTTP {resp.status}")

        token = resp.body.get("access_token")
        if not token:
            raise TokenError("no access_token in refresh response")
        expires_in = int(resp.body.get("expires_in", 3600))
        # refresh a minute early to avoid edge expiry
        self._cache[account_id] = (token, now + max(expires_in - 60, 0))
        return token

    def invalidate(self, account_id: str) -> None:
        self._cache.pop(account_id, None)
