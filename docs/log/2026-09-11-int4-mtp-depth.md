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

The first six measured baseline code repetitions completed at 8,251 actual input tokens, concurrency 1, thinking off, 768 output tokens, warm cache. Median decode is 84.3 tok/s, standard deviation 2.45 tok/s, median TTFT 0.911 s, overall draft acceptance 81.4%. This establishes a code-output baseline; it is not a configuration improvement. The remaining baseline workloads are still running.

The diagnostic script previously checked unpublished localhost and would print `UNREACHABLE` for a healthy service. Its default health URL now uses the existing Tailscale binding, matching the watchdog and benchmark. This fixes the diagnostic, not the inference server.

## Outcome

Pending measurements.

## Consequences

The server still runs MTP3. No tuning value has been promoted.

### MTP3 baseline screening

Six measured repetitions per row after one discarded warmup. Concurrency 1, cached prefix, fixed corpus SHA-256 `511644b905ef22dda8cd61c1ef32f997522fafbaf527da44bd49727d8dd1becd`. Warm prompts differ between workloads; each run has a fresh session nonce.

| Workload | Actual input tokens | Output tokens | Decode median (sd), tok/s | TTFT, s | Cached tokens | Draft acceptance | Peak global VRAM, GiB |
|---|---:|---:|---:|---:|---:|---:|---:|
| code, thinking off | 8251 | 768 | 84.3 (2.45) | 0.911 | 6656 | 81.4% | 30.302 |
| code, thinking off | 32589 | 768 | 75.9 (4.83) | 0.779 | 31616 | 78.8% | 30.478 |
| reasoning, xhigh | 8294 | 512 | 68.7 (6.4) | 0.937 | 6656 | 55.0% | 30.478 |
| tool, thinking off | 8531 | 768 | 84.0 (2.08) | 0.771 | 7488 | 78.7% | 30.479 |

These throughput runs end at the output cap and do not score code correctness. Complete task-suite validation is running.

Deployment preparation: `scripts/compose.sh` now loads private `compose/.env` followed by tracked `compose/tuning.env`. The tracked file initially contains the unchanged baseline, `MTP_TOKENS=3` and empty `CPUSET`. This permits measured defaults to be committed on mbp and pulled on the server. Individual arms still use shell overrides, which take precedence. Use the wrapper for subsequent serving commands. This preparation does not change the running container.

Baseline Pi 0.85.1 with the current extension and xhigh passed 8/8 tasks in 280.0 seconds, with 16,409 generated tokens and 63 tool calls. Concurrency 1; each task starts fresh, and observed prompt lengths vary with its tool turns. This is the comparison baseline for complete tasks.

MTP2 started at 12:52:42 UTC and became healthy after approximately four minutes. Startup logs verify `num_speculative_tokens: 2` and 114,062 KV tokens, up 2,553 from MTP3. All other serving parameters are unchanged. SearXNG was not restarted. The command used the new wrapper:

```bash
ssh vllm 'cd /home/chris/Code/llm-server && env MTP_TOKENS=2 bash scripts/compose.sh --profile a-int4draft up -d --no-deps vllm-a-int4draft'
bash scripts/bench-arm.sh mtp2
```

The first code repetition at 8,254 actual input tokens, 768 generated tokens, concurrency 1 and thinking off measured 72.8 tok/s. No conclusion is drawn from this single repetition; the six-repetition screening is running.

The MTP2 six-repetition code result at 8,254 input tokens is 71.2 tok/s (sd 1.11), versus MTP3 84.3 tok/s (sd 2.45) at 8,251 tokens. Both use concurrency 1, thinking off, 768 generated tokens and cached prefixes. Higher aggregate acceptance, 87.1% versus 81.4%, does not compensate for removing the third speculative token. Remaining workloads are still running.
