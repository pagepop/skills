#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

cd "$ROOT_DIR"

patterns=(
  't-[a-z0-9.-]*pagepop\.cn'
  'gitlab\.epian1\.com'
  'pagepop-login-token'
  '/tmp/[a-z0-9._-]*token'
)

failed=0

for pattern in "${patterns[@]}"; do
  if rg -n --hidden \
    --glob '!.git/**' \
    --glob '!scripts/check-public-safety.sh' \
    --glob '!scripts/build-skill.py' \
    "$pattern" .; then
    echo "public safety check failed: pattern matched: $pattern" >&2
    failed=1
  fi
done

if git status --short | rg -n '(__pycache__|\.pyc$|\.env($|\.))' | rg -v '\.env\.example$'; then
  echo "public safety check failed: ignored or generated files appear in git status" >&2
  failed=1
fi

if [[ "$failed" -ne 0 ]]; then
  exit 1
fi

echo "public safety check passed"
