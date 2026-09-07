#!/usr/bin/env bash
set -euo pipefail
node --test --experimental-strip-types 2>&1
out=$(node --experimental-strip-types src/main.ts 2>&1)
echo "$out"
echo "$out" | grep -q '0.0.0.0:8080' || { echo "FAIL: main.ts still prints the wrong config"; exit 1; }
