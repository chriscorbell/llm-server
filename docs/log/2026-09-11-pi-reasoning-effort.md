# 2026-09-11 Pi reasoning effort and completed task time

Status: prepared, awaiting CPU measurements
Profile: selected a-int4draft configuration, Pi 0.85.1

## Hypothesis

Medium reasoning effort reduces completed-task time and generated tokens on the eight fixed fixtures without reducing their pass count.

## Configuration

Change only Pi's per-run thinking level between `medium` and `xhigh`. Record the final serving configuration before starting. Keep the current extension, explicit sampling controls, 98,304-token window and 32,768-token output cap. Each task receives a fresh temporary fixture and uses the corrected, protected runner. The global Pi default remains xhigh during the experiment.

```bash
PI_LLM_SERVER_LOG=/Users/chris/Code/llm-server/eval/results/2026-09-11-tuning/effort-medium-1-requests.jsonl \
  python3 -u eval/run.py --client pi --model llm-server/qwen38 \
  --thinking medium --timeout 600 \
  --out eval/results/2026-09-11-tuning/effort-medium-1 < /dev/null
```

Use `--thinking xhigh` with an `effort-xhigh-1` output label for the control, then repeat medium if its first run warrants it. Each run is sequential at concurrency 1. Keep effort constant throughout each task because changing it changes the prompt prefix.

## Measurements

Pending. Record pass count, completed-task seconds, generated tokens, tool calls and actual prompt lengths from completed Pi messages. Report each run separately; different amounts of generated work affect time independently of engine throughput.

## Outcome

No result yet. This suite covers small coding and vision fixtures. It does not establish quality equivalence for difficult repository changes or complex reasoning across compaction.

## Consequences

No global client setting has changed. The measurements will determine whether medium is useful for these routine tasks; broad quality remains the priority for the default.
