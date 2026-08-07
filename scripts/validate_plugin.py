#!/usr/bin/env python3
"""Offline plugin + Skill package validator.

Enforces the rules from docs/PLATFORM-CAPABILITIES.md (sourced from the official Agent Skills and
Plugins references) without needing the `claude` CLI installed:

  * .claude-plugin/plugin.json parses and has a `name`.
  * every skills/<dir>/SKILL.md has YAML frontmatter with `name` + `description`.
  * name: <=64 chars, ^[a-z0-9-]+$, and NOT containing reserved words 'claude'/'anthropic'.
  * description: non-empty, <=1024 chars, no XML tags.
  * SKILL.md filename is upper-case 'SKILL.md'.

The quality gate ALSO runs `claude plugin validate` when the CLI is present; this script guarantees
the check runs everywhere. Exit 0 = valid.
"""
from __future__ import annotations

import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESERVED = ("claude", "anthropic")
NAME_RE = re.compile(r"^[a-z0-9-]+$")


def _parse_frontmatter(text: str):
    if not text.startswith("---"):
        return None, "missing YAML frontmatter"
    end = text.find("\n---", 3)
    if end == -1:
        return None, "unterminated frontmatter"
    block = text[3:end].strip("\n")
    fields = {}
    for line in block.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if ":" not in line:
            continue
        key, _, val = line.partition(":")
        fields[key.strip()] = val.strip()
    return fields, None


def _check_name(name: str, errors, where):
    if len(name) > 64:
        errors.append(f"{where}: name exceeds 64 chars")
    if not NAME_RE.match(name):
        errors.append(f"{where}: name must match ^[a-z0-9-]+$ (got {name!r})")
    low = name.lower()
    for word in RESERVED:
        if word in low:
            errors.append(f"{where}: name contains reserved word '{word}'")


def validate(root: str) -> list:
    errors = []

    manifest_path = os.path.join(root, ".claude-plugin", "plugin.json")
    plugin_name = None
    if not os.path.isfile(manifest_path):
        errors.append("missing .claude-plugin/plugin.json")
    else:
        try:
            manifest = json.load(open(manifest_path))
            if not manifest.get("name"):
                errors.append("plugin.json: required field 'name' missing")
            else:
                plugin_name = manifest["name"]
                _check_name(plugin_name, errors, "plugin.json")
        except json.JSONDecodeError as e:
            errors.append(f"plugin.json: invalid JSON: {e}")

    # Optional local marketplace (one-command install). If present, it must be well-formed and list
    # this plugin. Mirrors what `claude plugin validate` checks, so `make check` covers it offline.
    market_path = os.path.join(root, ".claude-plugin", "marketplace.json")
    if os.path.isfile(market_path):
        try:
            market = json.load(open(market_path))
            if not market.get("name"):
                errors.append("marketplace.json: required field 'name' missing")
            plugins = market.get("plugins")
            if not isinstance(plugins, list) or not plugins:
                errors.append("marketplace.json: 'plugins' must be a non-empty array")
            else:
                for i, p in enumerate(plugins):
                    if not isinstance(p, dict) or not p.get("name") or not p.get("source"):
                        errors.append(f"marketplace.json: plugins[{i}] needs 'name' and 'source'")
                names = {p.get("name") for p in plugins if isinstance(p, dict)}
                if plugin_name and plugin_name not in names:
                    errors.append(f"marketplace.json: does not list this plugin ({plugin_name!r})")
        except json.JSONDecodeError as e:
            errors.append(f"marketplace.json: invalid JSON: {e}")

    skills_dir = os.path.join(root, "skills")
    if not os.path.isdir(skills_dir):
        errors.append("missing skills/ directory")
        return errors

    found = 0
    for entry in sorted(os.listdir(skills_dir)):
        sdir = os.path.join(skills_dir, entry)
        if not os.path.isdir(sdir):
            continue
        skill_md = os.path.join(sdir, "SKILL.md")
        # enforce exact upper-case filename
        listing = os.listdir(sdir)
        if "SKILL.md" not in listing:
            wrong = [f for f in listing if f.lower() == "skill.md"]
            errors.append(f"skills/{entry}: SKILL.md not found"
                          + (f" (found {wrong[0]!r}; must be exactly 'SKILL.md')" if wrong else ""))
            continue
        found += 1
        text = open(skill_md, encoding="utf-8").read()
        fields, err = _parse_frontmatter(text)
        if err:
            errors.append(f"skills/{entry}/SKILL.md: {err}")
            continue
        name = fields.get("name")
        desc = fields.get("description")
        if not name:
            errors.append(f"skills/{entry}/SKILL.md: frontmatter missing 'name'")
        else:
            _check_name(name, errors, f"skills/{entry}/SKILL.md")
            if name != entry:
                errors.append(f"skills/{entry}/SKILL.md: name {name!r} should match directory {entry!r}")
        if not desc:
            errors.append(f"skills/{entry}/SKILL.md: frontmatter missing 'description'")
        else:
            if len(desc) > 1024:
                errors.append(f"skills/{entry}/SKILL.md: description exceeds 1024 chars")
            if "<" in desc and ">" in desc:
                errors.append(f"skills/{entry}/SKILL.md: description must not contain XML tags")

    if found == 0:
        errors.append("no skills found under skills/")
    return errors


def main() -> int:
    root = sys.argv[1] if len(sys.argv) > 1 else ROOT
    errors = validate(root)
    if errors:
        print("PLUGIN VALIDATION FAILED:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1
    print("PLUGIN VALID: plugin.json + all SKILL.md frontmatter conform to the documented rules")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
