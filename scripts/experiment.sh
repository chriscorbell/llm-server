#!/usr/bin/env bash
# Restart a Profile with env overrides, wait for health, and benchmark it.
#
#   scripts/experiment.sh <profile> "<label>" "<KEY=VAL ...>" "<prompt-token sizes>"
#
# Example:
#   scripts/experiment.sh a-bf16kv "batched 16384" "MAX_BATCHED_TOKENS=16384" "32768 90000"
#
# Prints one line per prompt size. Everything it prints is meant to be pasted
# straight into a log entry, so it always states the overrides it applied.
set -uo pipefail
cd "$(dirname "$0")/.."

PROFILE="${1:?profile}"; LABEL="${2:?label}"; OVERRIDES="${3:-}"; SIZES="${4:-32768}"
REPS="${REPS:-2}"; GEN="${GEN:-128}"
HOST="${SERVER_HOST:-vllm}"
BASE="${BASE_URL:-http://100.103.136.98:8000}"
KEY="${API_KEY:-$(ssh -o BatchMode=yes "$HOST" 'grep ^API_KEY ~/Code/llm-server/compose/.env | cut -d= -f2')}"

echo "=== $LABEL"
echo "    profile=$PROFILE overrides=${OVERRIDES:-none}"

ssh -o BatchMode=yes "$HOST" "cd ~/Code/llm-server/compose && \
  docker compose --profile a-bf16kv --profile a-fp8kv --profile a-nospec down >/dev/null 2>&1; \
  env $OVERRIDES docker compose --profile $PROFILE up -d >/dev/null 2>&1" || {
    echo "    FAILED to start"; exit 1; }

for _ in $(seq 1 90); do
  if ssh -o BatchMode=yes "$HOST" "curl -fsS -m 3 $BASE/health >/dev/null 2>&1"; then break; fi
  if [ "$(ssh -o BatchMode=yes "$HOST" 'docker inspect -f "{{.State.Running}}" qwen38 2>/dev/null')" != "true" ]; then
    echo "    CONTAINER DIED. Root cause:"
    ssh -o BatchMode=yes "$HOST" 'docker logs qwen38 2>&1 | grep -E "ValueError|RuntimeError|Error:" | tail -3' | sed 's/^/      /'
    exit 1
  fi
  sleep 20
done

ssh -o BatchMode=yes "$HOST" 'docker logs qwen38 2>&1 | grep -oE "GPU KV cache size: [0-9,]+ tokens" | tail -1' | sed 's/^/    /'

for p in $SIZES; do
  out=$(mktemp)
  ./scripts/bench.py --base-url "$BASE" --key "$KEY" --corpus code \
    --prompt-tokens "$p" --gen "$GEN" -n "$REPS" --json "$out" >/dev/null 2>&1
  python3 -c "
import json,sys
d=json.load(open('$out'))['result']
print(f\"    p{d['prompt_tokens']:<6} ttft {d['ttft_s_median']:7.2f}s  prefill {d['prefill_tok_s_median']:6.0f} tok/s  decode {d['decode_tok_s_median']:5.1f} tok/s  accept {d['mtp_acceptance_pct']}%\")" 2>/dev/null \
    || echo "    p$p  MEASUREMENT FAILED"
  rm -f "$out"
done
