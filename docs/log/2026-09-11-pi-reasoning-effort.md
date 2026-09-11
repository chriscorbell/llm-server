# 2026-09-11 Pi reasoning effort and completed task time

Status: concluded, medium documented for routine edits; xhigh remains default
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

### Fresh xhigh control

The fresh xhigh run passed 8/8 in 199.6 seconds, generated 11,604 tokens and used 56 tool calls, concurrency 1. Per-task maximum prompt lengths ranged from 7,626 to 10,320 tokens. Medium's first run was 26.9% shorter than this fresh control. The second medium run is now active, with all serving settings unchanged.

### Completed effort comparison

All runs use the same original engine, MTP4 and unrestricted CPUs, with Pi 0.85.1 and the current extension. Concurrency is one task. Prompt lengths grow with tool turns; the last column records the range of each task's maximum actual prompt length. The earlier xhigh control used the corrected attachment/sandbox runner before its optional metrics-copy correction; its task times and token counts come from saved Pi transcripts.

| Run | Effort | Passed | Task seconds | Generated tokens | Tool calls | Per-task maximum input tokens |
|---|---|---:|---:|---:|---:|---|
| mtp4-tasks-isolated | xhigh | 8/8 | 222.7 | 13,653 | 49 | 7,621 to 12,689 |
| effort-medium-1 | medium | 8/8 | 145.9 | 7,154 | 49 | 7,138 to 9,569 |
| effort-xhigh-1 | xhigh | 8/8 | 199.6 | 11,604 | 56 | 7,626 to 10,320 |
| effort-medium-2 | medium | 8/8 | 132.9 | 7,320 | 47 | 7,236 to 9,801 |

Mean task time across two runs per effort is 139.4 s for medium and 211.15 s for xhigh, a 34.0% reduction on these fixtures. Both efforts pass 16/16 task instances. Medium's generated output is lower in both runs. Individual task paths and tool-call counts vary, so these are complete-task observations rather than a fixed-output decode comparison.

Medium is useful for these small, well-scoped coding and vision tasks. `clients/pi/README.md` now documents `pi --thinking medium` for that use. The global default remains xhigh: this suite does not establish quality equivalence on difficult repository changes or complex work across compaction. No global client setting was modified.

Final verification found the original engine healthy on MTP4, 98,304-token context, empty Docker CPU affinity metadata and the Tailscale-only binding. Both draft overlay flags and XPU graphs are enabled. The watchdog is active and enabled. The kernel journal since 12:28 UTC contains 104 container-network entries and no GPU/fault-related entries. No source fixture changed. The API has zero running or waiting requests after the suite. The temporary one-second GPU sampler was deliberately stopped after its PID and command were verified.
