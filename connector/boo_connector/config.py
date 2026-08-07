"""Environment-driven configuration. Never hard-code secrets; supply them via env / secret manager."""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Dict, Optional

from .crypto import EnvelopeCipher
from .google.oauth import OAuthConfig


@dataclass
class Settings:
    db_path: str
    state_secret: bytes
    public_base_url: str
    use_fixtures: bool

    @classmethod
    def from_env(cls, env: Optional[Dict[str, str]] = None) -> "Settings":
        env = env or dict(os.environ)
        secret = env.get("BOO_STATE_SECRET")
        if not secret:
            raise RuntimeError("BOO_STATE_SECRET not set")
        return cls(
            db_path=env.get("BOO_DB_PATH", "boo.db"),
            state_secret=secret.encode("utf-8"),
            public_base_url=env.get("BOO_PUBLIC_BASE_URL", "https://localhost:8080"),
            use_fixtures=env.get("BOO_USE_FIXTURES", "false").lower() in ("1", "true", "yes"),
        )


def build_runtime(env: Optional[Dict[str, str]] = None):
    """Assemble cipher, store, oauth config, and google client from the environment.

    Returns (settings, cipher, store, oauth_config, client). In fixtures mode, uses
    FixturesGoogleClient and does not require Google OAuth credentials.
    """
    env = env or dict(os.environ)
    settings = Settings.from_env(env)
    cipher = EnvelopeCipher.from_env(env)

    from .store import Store
    store = Store(settings.db_path, cipher)

    if settings.use_fixtures:
        from .google.client import FixturesGoogleClient
        client = FixturesGoogleClient()
        oauth_config = None
    else:
        oauth_config = OAuthConfig.from_env(env)
        from .google.http import HttpxClient
        from .google.tokens import TokenManager
        from .google.live import LiveGoogleClient

        http = HttpxClient()
        token_manager = TokenManager(store, oauth_config, http)
        client = LiveGoogleClient(token_manager, http)

    return settings, cipher, store, oauth_config, client
