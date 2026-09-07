#!/usr/bin/env bash
set -euo pipefail
node --test --experimental-strip-types 2>&1
# Guard against "fix" by deletion: the file must still hold every handler.
count=$(grep -c '^export const handle' src/handlers.ts)
if [ "$count" -ne 240 ]; then
  echo "FAIL: expected 240 handlers, found $count"
  exit 1
fi
echo "handler count ok"
