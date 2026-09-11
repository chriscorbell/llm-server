#!/usr/bin/env bash
# Run a fixed, sequential screening set against the current inference container.
# This script does not change the server configuration.
set -euo pipefail
cd "$(dirname "$0")/.."
arm="${1:?arm label}"
output="${2:-eval/results/2026-09-11-tuning}"
repetitions="${REPS:-6}"
mkdir -p "$output"
for specification in code:8192:768 code:32768:768 reasoning:8192:512 tool:8192:768; do
  IFS=: read -r workload prompt generation <<< "$specification"
  extra=(--effort xhigh)
  task="$workload"
  if [[ "$workload" == reasoning ]]; then
    task=code
    extra=(--thinking --effort xhigh)
  fi
  label="$arm-$workload-p$prompt-warm"
  python3 -u scripts/bench.py --base-url http://100.103.136.98:8000 \
    --corpus-file "$output/corpus.txt" --workload "$task" \
    --prompt-tokens "$prompt" --gen "$generation" -n "$repetitions" \
    --warm "${extra[@]}" --json "$output/$label.json" > "$output/$label.log" 2>&1
  python3 - "$output/$label.json" <<'PY'
import json, sys
d = json.load(open(sys.argv[1]))['result']
print(sys.argv[1], 'input', d['prompt_tokens'], 'decode', d['decode_tok_s_median'],
      'sd', d['decode_tok_s_stdev'], 'ttft', d['ttft_s_median'],
      'accept', d['mtp_acceptance_pct'], flush=True)
PY
done
