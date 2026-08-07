#!/usr/bin/env python3
"""Boo connector doctor — catch the silent 'connector failed' class before a user hits it.

Many connectors fail not because they're unauthorized, but because their MCP server config
references an environment variable (a token) that isn't set — e.g. the official GitHub connector's
`Authorization: Bearer ${GITHUB_PERSONAL_ACCESS_TOKEN}`. That surfaces as a cryptic "✗ failed" that
no amount of clicking "Connect" fixes.

This scans Claude Code's connector configs on disk (user MCPs + installed plugin MCP servers),
finds every `${ENV_VAR}` they require, and reports which are **unset** — with a targeted fix.
It never prints a variable's VALUE, only whether it is set. Stdlib only.

Usage:  python3 scripts/connector_doctor.py        (checks your live env)
        make doctor
"""
from __future__ import annotations

import glob
import json
import os
import re
import shutil

HOME = os.path.expanduser("~")
VAR_RE = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")

# Known remediations for common connectors (var name -> hint).
HINTS = {
    "GITHUB_PERSONAL_ACCESS_TOKEN": (
        "GitHub MCP needs a token. If the `gh` CLI is logged in, add to ~/.zshrc:\n"
        '        export GITHUB_PERSONAL_ACCESS_TOKEN="$(gh auth token)"\n'
        "      or create a fine-grained PAT (repo read) at https://github.com/settings/tokens."
    ),
    "GITLAB_PERSONAL_ACCESS_TOKEN": (
        "Create a GitLab PAT (read_api) and export GITLAB_PERSONAL_ACCESS_TOKEN in your shell profile."
    ),
}


def _config_files():
    paths = [os.path.join(HOME, ".claude.json")]
    for pat in (
        os.path.join(HOME, ".claude", "plugins", "**", ".mcp.json"),
        os.path.join(HOME, ".claude", "plugins", "**", "plugin.json"),
        os.path.join(HOME, ".claude", "settings.json"),
        os.path.join(os.getcwd(), ".mcp.json"),
    ):
        paths += glob.glob(pat, recursive=True)
    # de-dup, keep existing files
    seen, out = set(), []
    for p in paths:
        if p not in seen and os.path.isfile(p):
            seen.add(p)
            out.append(p)
    return out


def _iter_servers(obj):
    """Yield (server_name, server_config_dict) from the various shapes a config can take."""
    if not isinstance(obj, dict):
        return
    # {"mcpServers": {name: cfg}}
    if isinstance(obj.get("mcpServers"), dict):
        for name, cfg in obj["mcpServers"].items():
            yield name, cfg
    # a bare {name: {type/url/command...}} map (e.g. a plugin .mcp.json)
    for name, cfg in obj.items():
        if isinstance(cfg, dict) and (("url" in cfg) or ("command" in cfg) or ("type" in cfg)):
            yield name, cfg


def _vars_in(cfg) -> set:
    return set(VAR_RE.findall(json.dumps(cfg)))


def scan(files=None):
    findings = []  # (source_file, server, [ (var, is_set) ])
    for path in (files if files is not None else _config_files()):
        try:
            data = json.load(open(path))
        except Exception:
            continue
        for name, cfg in _iter_servers(data):
            vars_needed = _vars_in(cfg)
            # ignore Claude's own path substitutions, not real secrets
            vars_needed -= {"CLAUDE_PLUGIN_ROOT", "CLAUDE_PLUGIN_DATA", "CLAUDE_PROJECT_DIR"}
            if vars_needed:
                status = [(v, bool(os.environ.get(v))) for v in sorted(vars_needed)]
                findings.append((path, name, status))
    return findings


def main() -> int:
    findings = scan()
    if not findings:
        print("connector doctor: no env-var-based connectors found (or none require configuration).")
        return 0

    problems = 0
    print("Connector doctor — env-var requirements for your connectors:\n")
    for path, name, status in findings:
        missing = [v for v, ok in status if not ok]
        mark = "✗" if missing else "✓"
        where = path.replace(HOME, "~")
        print(f"  {mark} {name}   ({where})")
        for v, ok in status:
            print(f"       {'set' if ok else 'MISSING'}: {v}")
        for v in missing:
            problems += 1
            hint = HINTS.get(v)
            if hint:
                print(f"       → fix: {hint}")
            else:
                print(f"       → fix: set {v} in your shell profile (or the connector's env), then reopen the terminal.")
        print()

    if problems:
        print(f"{problems} connector(s) will FAIL until the MISSING variable(s) above are set.")
        print("After setting them, open a NEW terminal and relaunch Claude Code so they're picked up.")
        if not shutil.which("gh"):
            print("(Tip: the `gh` CLI isn't installed — some GitHub fixes assume it.)")
        return 1

    print("All connectors that need env vars have them set. ✓")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
