---
description: Run scripts/bench.py against vllm and report the numbers
argument-hint: "[prompt-token sizes] [--thinking]"
---
Benchmark the running server with `./scripts/bench.py --base-url http://vllm:8000 --corpus code --gen 128 -n 3` for each prompt size in: ${1:-512 8192 32768}
Extra flags to pass through: ${@:2}

Run the sizes one at a time. Report a table with prompt tokens, time to first token (s), prefill tok/s, decode tok/s and MTP acceptance %, all at concurrency 1, and say whether thinking was on. Compare against the Findings in STATUS.md and point out any number that moved by more than 10%. Do not write a log entry or edit STATUS.md; I will decide whether this run is an experiment.
