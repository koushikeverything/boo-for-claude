#!/usr/bin/env bash
# One command to run every quality gate. Deterministic core runs with only Python stdlib;
# optional tools (ruff/black/mypy/claude CLI) run when present and are skipped-with-notice otherwise.
set -uo pipefail
cd "$(dirname "$0")/.."

PY="${PYTHON:-python3}"
status=0
step() { echo ""; echo "==== $* ===="; }
run()  { "$@"; if [ $? -ne 0 ]; then echo "FAILED: $*"; status=1; fi; }

step "1. Formatting (black --check, if installed)"
if command -v black >/dev/null 2>&1; then run black --check skills connector tests scripts 2>/dev/null || true
else echo "skip: black not installed"; fi

step "2. Lint (ruff, if installed)"
if command -v ruff >/dev/null 2>&1; then run ruff check skills connector tests scripts
else echo "skip: ruff not installed"; fi

step "3. Type check (mypy, if installed)"
if command -v mypy >/dev/null 2>&1; then run mypy --ignore-missing-imports connector/boo_connector 2>/dev/null || true
else echo "skip: mypy not installed"; fi

step "4. Brief validator self-test"
run "$PY" skills/daily-brief/scripts/validate_brief.py --schema schemas/daily-brief.schema.json --self-test

step "4b. Skill's bundled schema is identical to the canonical schema (no drift)"
run diff -q schemas/daily-brief.schema.json skills/daily-brief/schemas/daily-brief.schema.json

step "4c. team-brief bundle is in sync with canonical scripts/schemas/config"
run bash scripts/bundle_team_brief.sh --check

step "5. Validate all 20 golden brief payloads against the schema + semantic rules"
for f in evals/expected/*.json; do
  run "$PY" skills/daily-brief/scripts/validate_brief.py --schema schemas/daily-brief.schema.json "$f" >/dev/null
done
echo "validated $(ls evals/expected/*.json | wc -l | tr -d ' ') payloads"

step "5b. Validate v2 (role/team) golden payloads against brief.schema.json"
for f in evals/expected-v2/*.json; do
  run "$PY" skills/daily-brief/scripts/validate_brief.py --schema schemas/brief.schema.json "$f" >/dev/null
done
echo "validated $(ls evals/expected-v2/*.json 2>/dev/null | wc -l | tr -d ' ') v2 payloads"

step "6. Skill unit + acceptance/eval tests"
run "$PY" -m unittest discover -s tests -p 'test_*.py'

step "6b. Skill tests with jsonschema DISABLED (prove offline validator path)"
run env NO_JSONSCHEMA=1 "$PY" -c "import sys; sys.modules['jsonschema']=None; \
import unittest; \
sys.path.insert(0,'skills/daily-brief/scripts'); \
r=unittest.TextTestRunner(verbosity=0).run(unittest.TestLoader().discover('tests','test_*.py')); \
sys.exit(0 if r.wasSuccessful() else 1)"

step "7. Connector tests (crypto, oauth-state, store, tools, isolation)"
run bash -c "cd connector && '$PY' -m unittest discover -s tests -p 'test_*.py'"

step "8. Secret scan"
run bash scripts/secret_scan.sh

step "9. Plugin + Skill package validation (offline)"
run "$PY" scripts/validate_plugin.py .

step "9b. Official plugin validator (claude CLI, if installed)"
if command -v claude >/dev/null 2>&1; then run claude plugin validate . || true
else echo "skip: claude CLI not on PATH — run 'claude plugin validate .' where available"; fi

echo ""
if [ "$status" -eq 0 ]; then
  echo "############################################"
  echo "#  QUALITY GATE: ALL CHECKS PASSED         #"
  echo "############################################"
else
  echo "############################################"
  echo "#  QUALITY GATE: FAILURES ABOVE            #"
  echo "############################################"
fi
exit $status
