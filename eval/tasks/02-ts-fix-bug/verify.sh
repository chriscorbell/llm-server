#!/usr/bin/env bash
set -euo pipefail
node --test --experimental-strip-types 2>&1
