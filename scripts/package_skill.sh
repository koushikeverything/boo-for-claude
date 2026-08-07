#!/usr/bin/env bash
# Build a claude.ai-uploadable Skill ZIP: the skill folder sits at the ZIP ROOT (per the
# documented format in docs/PLATFORM-CAPABILITIES.md, source S8). Default: the daily-brief skill.
set -euo pipefail
cd "$(dirname "$0")/.."

SKILL="${1:-daily-brief}"
SRC="skills/${SKILL}"
OUT="dist"

if [ ! -f "${SRC}/SKILL.md" ]; then
  echo "no SKILL.md at ${SRC}" >&2; exit 1
fi

mkdir -p "${OUT}"
ZIP="${OUT}/${SKILL}-skill.zip"
rm -f "${ZIP}"

# Zip so the archive contains "<skill>/..." at its root (not "skills/<skill>/...").
( cd skills && zip -r -q "../${ZIP}" "${SKILL}" -x '*/__pycache__/*' -x '*.pyc' )

echo "Built ${ZIP}"
echo "Contents (top level must be '${SKILL}/'):"
unzip -l "${ZIP}" | awk 'NR>3{print $4}' | grep -E "^${SKILL}/" | head -20
