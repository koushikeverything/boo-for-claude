#!/usr/bin/env bash
# Make skills/team-brief self-contained by copying canonical scripts/schemas/config into it.
# `--check` diffs instead of copying and fails on drift (used by the quality gate).
# bash 3.2 compatible (no associative arrays).
set -uo pipefail
cd "$(dirname "$0")/.."

SKILL="skills/team-brief"
mkdir -p "$SKILL/scripts" "$SKILL/schemas" "$SKILL/config"

MODE="${1:-copy}"
fail=0

# src|dst pairs (canonical source -> bundled copy)
while IFS='|' read -r src dst; do
  [ -z "$src" ] && continue
  if [ "$MODE" = "--check" ]; then
    if ! diff -q "$src" "$dst" >/dev/null 2>&1; then
      echo "BUNDLE DRIFT: $dst differs from $src (run scripts/bundle_team_brief.sh)"; fail=1
    fi
  else
    cp "$src" "$dst"
  fi
done <<'EOF'
skills/daily-brief/scripts/validate_brief.py|skills/team-brief/scripts/validate_brief.py
skills/daily-brief/scripts/dedup.py|skills/team-brief/scripts/dedup.py
skills/daily-brief/scripts/dateutil.py|skills/team-brief/scripts/dateutil.py
lib/ranking.py|skills/team-brief/scripts/ranking.py
lib/xsource.py|skills/team-brief/scripts/xsource.py
lib/gating.py|skills/team-brief/scripts/gating.py
schemas/brief.schema.json|skills/team-brief/schemas/brief.schema.json
schemas/role-profile.schema.json|skills/team-brief/schemas/role-profile.schema.json
config/capability-catalog.json|skills/team-brief/config/capability-catalog.json
config/role-matrix.json|skills/team-brief/config/role-matrix.json
EOF

if [ "$MODE" = "--check" ]; then
  [ "$fail" -eq 0 ] && echo "BUNDLE OK: team-brief is in sync with canonical sources"
else
  echo "Bundled team-brief (scripts + schemas + config)."
fi
exit $fail
