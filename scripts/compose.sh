#!/usr/bin/env bash
# Keep measured tuning in Git while credentials stay in the server's private .env.
# Usage: bash scripts/compose.sh --profile a-int4draft up -d
# Experiment: MTP_TOKENS=2 bash scripts/compose.sh --profile a-int4draft up -d --no-deps vllm-a-int4draft
set -euo pipefail
cd "$(dirname "$0")/../compose"
exec docker compose --env-file .env --env-file tuning.env "$@"
