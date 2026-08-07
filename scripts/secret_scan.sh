#!/usr/bin/env bash
# Fail if anything that looks like a committed secret is present. Deterministic, no deps.
set -uo pipefail
cd "$(dirname "$0")/.."

fail=0

# 1) A real .env must never be committed (only .env.example is allowed).
if find . -name '.env' -not -path './node_modules/*' | grep -q .; then
  echo "SECRET SCAN: a .env file is present (should be gitignored, never committed)"; fail=1
fi

# 2) Private key blocks.
if grep -rInE 'BEGIN (RSA|EC|OPENSSH|PGP) PRIVATE KEY' --include='*' . >/dev/null 2>&1; then
  echo "SECRET SCAN: private key material found"; fail=1
fi

# 3) Obvious real credential values (allow REPLACE/FAKE/example placeholders).
#    Google client secrets, oauth codes, bearer tokens.
if grep -rInE '(GOOGLE_CLIENT_SECRET|client_secret)\s*[=:]\s*["'"'"']?[A-Za-z0-9_\-]{20,}' \
    --include='*.py' --include='*.json' --include='*.env' --include='*.md' . 2>/dev/null \
    | grep -viE 'REPLACE|FAKE|example|EXAMPLE|\.example|placeholder|<' >/dev/null; then
  echo "SECRET SCAN: a real-looking client secret value found"; fail=1
fi

# 4) ya29 access tokens / refresh tokens that aren't fixtures.
if grep -rInE 'ya29\.[A-Za-z0-9_\-]+' . 2>/dev/null | grep -viE 'FAKE|example' >/dev/null; then
  echo "SECRET SCAN: a Google access token pattern found"; fail=1
fi

if [ "$fail" -eq 0 ]; then
  echo "SECRET SCAN: clean (no committed secrets; placeholders and fixtures ignored)"
fi
exit $fail
