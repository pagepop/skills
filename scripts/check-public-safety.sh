#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

cd "$ROOT_DIR"

allowed_pagepop_hosts=(
  'pagepop.cn'
  'www.pagepop.cn'
  'pc-api.pagepop.cn'
)

generic_forbidden_patterns=(
  'gitlab\.[a-z0-9.-]+'
  '/tmp/[a-z0-9._-]*token'
)

is_allowed_pagepop_host() {
  local host="$1"
  local allowed
  for allowed in "${allowed_pagepop_hosts[@]}"; do
    if [[ "$host" == "$allowed" ]]; then
      return 0
    fi
  done
  return 1
}

failed=0

while IFS=: read -r file line _host; do
  host="$(printf '%s' "$_host" | tr '[:upper:]' '[:lower:]')"
  if ! is_allowed_pagepop_host "$host"; then
    echo "public safety check failed: non-allowlisted PagePop hostname in ${file}:${line}" >&2
    failed=1
  fi
done < <(
  rg -n -o --hidden \
    --glob '!.git/**' \
    '([a-zA-Z0-9-]+\.)*pagepop\.cn' . || true
)

for pattern in "${generic_forbidden_patterns[@]}"; do
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
