#!/usr/bin/env bash
# Binary-search the largest --max-model-len that boots and serves a real request
# for a given KV dtype. vLLM refuses to start when the KV cache does not fit, so
# a successful /health plus one completion is the pass condition.
#
# Usage: find-max-context.sh <profile> <low> <high>
#   e.g. find-max-context.sh a-bf16kv 32768 262144
set -euo pipefail
cd "$(dirname "$0")/../compose"
PROFILE="${1:?profile}"; LOW="${2:-32768}"; HIGH="${3:-262144}"
VAR=MAX_MODEL_LEN_BF16KV; [[ "$PROFILE" == *fp8* ]] && VAR=MAX_MODEL_LEN_FP8KV
BEST=0
try() {
  local n="$1"
  echo "--- trying $VAR=$n"
  docker compose --profile "$PROFILE" down >/dev/null 2>&1 || true
  if ! env "$VAR=$n" docker compose --profile "$PROFILE" up -d >/dev/null 2>&1; then return 1; fi
  for _ in $(seq 1 120); do
    if curl -fsS -m 3 "http://127.0.0.1:${PORT:-8000}/health" >/dev/null 2>&1; then
      curl -fsS -m 120 "http://127.0.0.1:${PORT:-8000}/v1/completions" \
        -H "Authorization: Bearer ${API_KEY:-change-me}" -H 'Content-Type: application/json' \
        -d '{"model":"'"${SERVED_NAME:-qwen38}"'","prompt":"ok","max_tokens":4}' >/dev/null 2>&1 && return 0
      return 1
    fi
    if [ "$(docker inspect -f '{{.State.Running}}' qwen38 2>/dev/null)" != "true" ]; then return 1; fi
    sleep 10
  done
  return 1
}
while [ $((HIGH - LOW)) -gt 4096 ]; do
  MID=$(( (LOW + HIGH) / 2 / 4096 * 4096 ))
  if try "$MID"; then BEST=$MID; LOW=$MID; else HIGH=$MID; fi
done
echo
echo "largest working $VAR = $BEST"
echo "Record this as an Experiment and update compose/.env plus STATUS.md."
