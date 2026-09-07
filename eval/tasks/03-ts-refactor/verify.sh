#!/usr/bin/env bash
# Passes only if behaviour is preserved AND the duplication is actually gone.
set -euo pipefail
node --test --experimental-strip-types 2>&1
hits=$(grep -rc 'age must be at least 13' src/ --include='*.ts' | awk -F: '{s+=$2} END {print s+0}')
if [ "$hits" -ne 1 ]; then
  echo "FAIL: the age rule appears $hits times in src/, expected exactly 1"
  exit 1
fi
echo "duplication check ok"
