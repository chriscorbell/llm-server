#!/usr/bin/env bash
# Run one fixed benchmark matrix against an OpenAI-compatible endpoint.
# Used to compare engines or machines with identical requests, concurrency 1.
#   scripts/bench-compare.sh <label> <base-url> <model> [extra bench.py args...]
set -euo pipefail
cd "$(dirname "$0")/.."
label="${1:?label}"; base="${2:?base url}"; model="${3:?model}"; shift 3
output="${OUT:-eval/results/2026-09-22-splash-mbp}"
corpus="${CORPUS:-eval/results/2026-09-11-tuning/corpus.txt}"
mkdir -p "$output"
run() {
  local name="$1"; shift
  python3 -u scripts/bench.py --base-url "$base" --model "$model" --corpus-file "$corpus" \
    "$@" ${extra[@]+"${extra[@]}"} --json "$output/$label-$name.json" > "$output/$label-$name.log" 2>&1
  python3 - "$output/$label-$name.json" <<'PY'
import json, sys
d = json.load(open(sys.argv[1]))['result']
print(sys.argv[1].rsplit('/', 1)[1], 'input', d['prompt_tokens'], 'cached', d['cached_tokens_median'],
      'ttft', d['ttft_s_median'], 'decode', d['decode_tok_s_median'], 'sd', d['decode_tok_s_stdev'],
      'prefill', d['prefill_tok_s_median'], 'gen', d['gen_tokens_median'], 'accept', d['mtp_acceptance_pct'], flush=True)
PY
}
extra=("$@")
reps="${REPS:-3}"
run code-off-p4k    --workload code    --prompt-tokens 4096  --gen 384 -n "$reps" --warm --prompt-id compare-p4k
run code-xhigh-p4k  --workload code    --prompt-tokens 4096  --gen 384 -n "$reps" --warm --prompt-id compare-p4k --thinking --effort xhigh
run summary-off-p4k --workload summary --prompt-tokens 4096  --gen 384 -n "$reps" --warm --prompt-id compare-p4k
run code-off-p32k   --workload code    --prompt-tokens 32768 --gen 384 -n "$reps" --warm --prompt-id compare-p32k
run cold-p8k        --workload summary --prompt-tokens 8192  --gen 32  -n 2
run cold-p32k       --workload summary --prompt-tokens 32768 --gen 32  -n 2
