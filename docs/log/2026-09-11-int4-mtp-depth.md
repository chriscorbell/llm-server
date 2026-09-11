# 2026-09-11 MTP depth with the INT4 draft

Status: in progress
Profile: a-int4draft

## Hypothesis

Quantizing the draft changed the cost of each speculative step, so a depth other than 3 may improve code-generation throughput while retaining the target model's output quality.

## Configuration

Baseline: image `sha256:f01e24f6c7ff01f1e0662234255a1372297d1dbd89d003cf13c8fad3eab1ba4f`, model revision `9d189a60`, INT4 draft overlay, MTP3, FP16 KV, 98,304 context, utilization 0.95, 8,192 batched tokens, one sequence, prefix caching and XPU graphs enabled, no CPU pinning. [Earlier draft comparison](2026-09-07-int4-draft-overlay.md).

The single serving variable is `MTP_TOKENS`. Compare 3, 2 and 4, followed by a baseline recheck. Each restart first captures kernel and container diagnostics. Only the inference service is recreated; SearXNG stays running. Environment overrides change the container configuration without editing the server's checkout or `.env`.

The benchmark now accepts a fixed corpus, separate code/tool-call output workloads, explicit effort and sampling seeds. It reports actual input/output tokens, cached tokens, spread and per-position acceptance, excludes warmup from acceptance, and saves each repetition before proceeding. Tool argument deltas count as output. A warm request no longer reports cached tokens divided by TTFT as prefill throughput. Output text is retained in ignored result files to distinguish generated code from reasoning and to inspect truncated responses.

```bash
mkdir -p eval/results/2026-09-11-tuning
git show 4b82d94:scripts/bench.py > eval/results/2026-09-11-tuning/corpus.txt
python3 scripts/bench.py --base-url http://100.103.136.98:8000 \
  --corpus-file eval/results/2026-09-11-tuning/corpus.txt \
  --workload code --thinking --prompt-tokens 8192 --gen 1536 -n 6 --warm \
  --json eval/results/2026-09-11-tuning/mtp3-code-p8192-warm.json
# Other arms change only MTP_TOKENS:
ssh vllm 'cd /home/chris/Code/llm-server/compose && env MTP_TOKENS=2 docker compose --profile a-int4draft up -d --no-deps vllm-a-int4draft'
```

Input-size arguments are character estimates. Tables will use the actual API token counts. Sampling is held fixed within each comparison; microbenchmark seed is 42000 plus repetition number. Concurrency is 1 throughout. The small task suite remains an integration check, not proof of parity on all repository work.

## Measurements

No new throughput or quality result yet. On September 11 at 12:34 UTC the baseline was healthy, idle, and had zero requests since startup. Startup KV capacity is 111,509 tokens. PyTorch reports device total memory 34,242,297,856 bytes; its separate inspection process reported 4,041,633,792 bytes free. This is an idle snapshot, not peak VRAM.

## What happened

Preparation: verified both checkouts at `4b82d94`, no server changes, working CPU topology confirms `0-3,32-35` share L3 cache 0. Benchmark Python compilation and CLI argument parsing pass. Live benchmark validation follows.

At 12:40 UTC, the first live validation completed: 8,287 input tokens, 6,656 cached, 1,536 generated tokens, concurrency 1, xhigh, TTFT 0.930 s, decode 58.8 tok/s, acceptance 46.3%. All 6,477 returned characters were reasoning; there was no code output before the token limit. This is not a valid code-output measurement. The sweep will separate non-thinking code/tool output from thinking-on reasoning and use complete Pi tasks for the daily xhigh workload. The measured response and exact request controls are in `eval/results/2026-09-11-tuning/validation-code.json`.

Global VRAM can be sampled without another GPU context: `sudo cat /sys/kernel/debug/dri/0000:4c:00.0/tile0/vram_mm` reports `size` and `usage` in bytes. `scripts/sample-gpu.py` samples that counter and GPU clock every second. During the initial validation the counter reported 31,794,946,048 bytes used of 34,242,297,856 bytes total. This single snapshot is not a peak.

The first screening launcher exited before sending a request with `scripts/bench-arm.sh: line 19: extra[@]: unbound variable`. macOS ships Bash 3.2, where an empty array under `set -u` fails this expansion. Keeping the common `--effort xhigh` argument in the array fixes the launcher without changing request semantics.

## Outcome

Pending measurements.

## Consequences

The server still runs MTP3. No tuning value has been promoted.
