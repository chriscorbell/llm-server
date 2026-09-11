# 2026-09-11 Pi reasoning effort and completed task time

Status: in progress, xhigh control active
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

The serving selection is now fixed: original digest `sha256:f01e24f6c7ff01f1e0662234255a1372297d1dbd89d003cf13c8fad3eab1ba4f`, MTP4, no CPU pin, FP16 KV, 98,304 context, 8,192 batched tokens, utilization 0.95 and one sequence. The earlier corrected xhigh run on this configuration passed 8/8 in 222.7 seconds with 13,653 generated tokens and 49 tool calls. The next runs compare medium and xhigh with request-metrics collection working on both.

The final container started at 14:38:02 UTC from the committed defaults, with no shell overrides. Smoke checks passed for the models endpoint, text, reasoning, tool calls and a red image. Pi's installed `defaultThinkingLevel` is still `xhigh`; the medium arm changes only the CLI option for that run. Both medium and xhigh map directly to their same-named server reasoning effort values in the installed model configuration.

### First medium run

Medium passed 8/8 in 145.9 seconds, generated 7,154 tokens and used 49 tool calls, concurrency 1. Per-task maximum prompt lengths ranged from 7,138 to 9,569 tokens. The earlier corrected xhigh run took 222.7 seconds, generated 13,653 tokens and also used 49 tool calls. The global default remains xhigh after the medium CLI run. A fresh xhigh control and a second medium run follow before drawing a task-time conclusion.
