"""Boo remote MCP server — HTTP entrypoint (OAuth routes + MCP transport).

The security-critical logic (state signing, token exchange, account linking, tool behavior) lives
in tested modules (`google/oauth_flow.py`, `google/live.py`, `tools/boo_tools.py`). This file is
thin ASGI glue that exposes them over HTTP. It requires `starlette`, `uvicorn`, and `mcp`
(see requirements.txt) and is the one piece validated at deploy time rather than in unit tests.

Routes:
  GET  /healthz                 liveness
  GET  /oauth/connect?label=…   begin account linking (redirects to Google)
  GET  /oauth/callback          finish linking (verifies state, exchanges code, stores account)
  ALL  /mcp                     MCP Streamable HTTP endpoint exposing the boo_* tools

Run:
  uvicorn boo_connector.server:app --host 0.0.0.0 --port 8080
"""
from __future__ import annotations

import json
import os
import secrets
from typing import Dict

from .config import build_runtime
from .google import oauth_flow
from .tools import TOOLS, ToolContext, ToolError


def _build():
    settings, cipher, store, oauth_config, client = build_runtime()
    if oauth_config is None:
        raise RuntimeError("OAuth is required to serve live; unset BOO_USE_FIXTURES and set Google env vars")
    from .google.http import HttpxClient
    return settings, cipher, store, oauth_config, client, HttpxClient()


def create_app():  # pragma: no cover - requires starlette + mcp; validated at deploy time
    from starlette.applications import Starlette
    from starlette.responses import JSONResponse, RedirectResponse, PlainTextResponse
    from starlette.routing import Route, Mount

    settings, cipher, store, oauth_config, client, http = _build()

    # Server-side session store for the short-lived PKCE verifier + state during the OAuth round
    # trip. In-memory is fine for a single instance; use Redis for multiple instances.
    pending: Dict[str, Dict] = {}

    def resolve_user_id(request) -> str:
        """Bind the Boo user from the authenticated session.

        Single-tenant deploy: set BOO_DEFAULT_USER_ID. Multi-tenant: replace this with your real
        session/JWT auth so each user only ever sees their own accounts. NEVER take user_id from
        tool input.
        """
        return os.environ.get("BOO_DEFAULT_USER_ID", "default-user")

    def resolve_attended(request) -> bool:
        # Scheduled/unattended MCP sessions should set this False (mutations are then refused).
        return request.headers.get("X-Boo-Attended", "true").lower() != "false"

    async def healthz(request):
        return PlainTextResponse("ok")

    async def oauth_connect(request):
        label = request.query_params.get("label", "Personal")
        session_id = request.cookies.get("boo_sid") or secrets.token_urlsafe(24)
        user_id = resolve_user_id(request)
        begun = oauth_flow.begin_connect(oauth_config, settings.state_secret, session_id)
        pending[begun["state"]] = {"verifier": begun["code_verifier"], "session_id": session_id,
                                   "user_id": user_id, "label": label}
        resp = RedirectResponse(begun["auth_url"])
        resp.set_cookie("boo_sid", session_id, httponly=True, secure=True, samesite="lax")
        return resp

    async def oauth_callback(request):
        state = request.query_params.get("state", "")
        code = request.query_params.get("code", "")
        ctx = pending.pop(state, None)
        if not ctx or ctx["session_id"] != request.cookies.get("boo_sid"):
            return JSONResponse({"error": "invalid or expired session"}, status_code=400)
        try:
            result = oauth_flow.complete_connect(
                oauth_config, settings.state_secret, ctx["session_id"], state, code,
                ctx["verifier"], http, store, ctx["user_id"], label=ctx["label"],
            )
        except Exception as e:
            return JSONResponse({"error": "linking failed", "detail": str(e)}, status_code=400)
        # Return only non-secret confirmation.
        return JSONResponse({"connected": True, "account_id": result["account_id"],
                             "label": result["label"], "email": result.get("email")})

    # --- MCP endpoint ---------------------------------------------------------------
    from mcp.server import Server
    import mcp.types as mcp_types

    mcp_server = Server("boo-connector")

    @mcp_server.list_tools()
    async def _list_tools():
        return [mcp_types.Tool(name=n, description=s["description"], inputSchema=s["input_schema"])
                for n, s in TOOLS.items()]

    @mcp_server.call_tool()
    async def _call_tool(name: str, arguments: dict):
        request = _current_request.get(None)
        user_id = resolve_user_id(request) if request else os.environ.get("BOO_DEFAULT_USER_ID", "default-user")
        attended = resolve_attended(request) if request else True
        tctx = ToolContext(store=store, client=client, user_id=user_id, attended=attended)
        spec = TOOLS.get(name)
        if not spec:
            raise ToolError(f"unknown tool {name!r}")
        result = spec["fn"](tctx, **arguments)
        return [mcp_types.TextContent(type="text", text=json.dumps(result, default=str))]

    # Streamable HTTP transport. The exact helper name can vary by mcp version; confirm on deploy.
    from mcp.server.streamable_http_manager import StreamableHTTPSessionManager

    session_manager = StreamableHTTPSessionManager(app=mcp_server)

    import contextvars
    _current_request = contextvars.ContextVar("request")

    async def mcp_endpoint(scope, receive, send):
        await session_manager.handle_request(scope, receive, send)

    app = Starlette(routes=[
        Route("/healthz", healthz),
        Route("/oauth/connect", oauth_connect),
        Route("/oauth/callback", oauth_callback),
        Mount("/mcp", app=mcp_endpoint),
    ])
    return app


def main() -> int:
    try:
        app = create_app()
    except Exception as e:
        print(f"startup error: {e}", file=sys.stderr)
        print("For local logic testing without serving, use FixturesGoogleClient + the unit tests.",
              file=sys.stderr)
        return 2
    import uvicorn  # pragma: no cover
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", "8080")))
    return 0


import sys  # noqa: E402

# ASGI servers import `app`; build it lazily so importing this module never requires the deps.
def __getattr__(name):  # pragma: no cover
    if name == "app":
        return create_app()
    raise AttributeError(name)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
