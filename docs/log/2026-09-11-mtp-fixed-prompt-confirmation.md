# 2026-09-11 MTP confirmation with identical requests

Status: concluded, MTP4 confirmed
Profile: a-int4draft, original engine, all CPUs available

## Hypothesis

MTP4's code-output advantage survives a comparison that uses identical complete requests, including the session identifier, across depths.

## Configuration

The [initial depth sweep](2026-09-11-int4-mtp-depth.md) fixed the corpus and sampling seeds, but each benchmark invocation created a new session nonce. This defeats accidental caching, but also adds avoidable prompt variation between arms. CPU trials showed noticeable variation across prompt/seed blocks, so the final comparison removes that source of variation.

`scripts/bench.py --prompt-id` now fixes the identifier for warm comparisons and records the SHA-256 of each complete request body. Cold requests retain fresh random prefixes; the CLI rejects `--prompt-id` without `--warm`.

Compare MTP4, then MTP3, on the same original engine digest, model revision, patches, FP16 KV, 98,304-token context, utilization 0.95, 8,192 batched tokens, one sequence and unrestricted CPUs. Only effective MTP depth changes. The first arm's Docker affinity metadata is explicitly `0-63` after the CPU test; the following recreated container uses empty metadata, with the same effective `0-63` mask.

```bash
python3 scripts/bench.py --base-url http://100.103.136.98:8000 \
  --corpus-file eval/results/2026-09-11-tuning/corpus.txt --workload code \
  --prompt-tokens 8192 --gen 768 -n 6 --warm \
  --prompt-id mtp-confirm-20260911-code-8192 \
  --json eval/results/2026-09-11-tuning/fixed-mtp4-code.json
```

The reasoning arm adds `--thinking --effort xhigh`, uses 512 output tokens, and identifier `mtp-confirm-20260911-reasoning-8192`. After capturing diagnostics, recreate with `MTP_TOKENS=3` and repeat both requests under `fixed-mtp3` output labels. Compare all six request hashes before attributing a difference to MTP depth.

## Measurements

Pending. Six measured warm repetitions per workload and depth, concurrency 1. Code uses thinking off; the reasoning workload uses xhigh. Report actual input counts, output counts, TTFT, decode spread, acceptance and sampled peak VRAM.

## Outcome

No result yet. The earlier screening remains recorded; this comparison determines the final short-context claim with tighter controls.

## Consequences

MTP4 remains the tracked selection pending confirmation. The final container will use the selected depth and unrestricted CPUs through committed Compose defaults.

### MTP4 control

Six measured warm repetitions per row, concurrency 1. These request bodies will be reused unchanged for MTP3.

| Workload | Actual input tokens | Output tokens | Decode median (sd), tok/s | TTFT, s | Cached tokens | Draft acceptance | Peak global VRAM, GiB |
|---|---:|---:|---:|---:|---:|---:|---:|
| fixed-mtp4-code | 8240 | 768 | 90.1 (4.08) | 0.911 | 6656 | 73.1% | 30.224 |
| fixed-mtp4-reasoning | 8282 | 512 | 65.0 (7.12) | 0.942 | 6656 | 46.0% | 30.224 |

Diagnostics were captured in `pre-fixed-mtp3-health.log` before recreating with MTP3. No conclusion is drawn from this arm alone.

The one-second GPU sampler was continued between measurement arms: its original two-hour process was deliberately stopped after verifying its PID and command, and a new one-hour process appends to the same raw JSONL file. Sampling cadence and kernel counters are unchanged. The old SSH sampler session exited nonzero because of that deliberate stop; the inference service was unaffected.

The MTP3 confirmation container started at 14:29:49 UTC. Docker affinity metadata is empty and the effective mask is `0-63`, equal to the first arm's effective CPU availability. The original engine digest is unchanged.

### MTP3 control and final result

Six measured warm repetitions per row, concurrency 1, same complete requests as MTP4. Every paired request hash matches, for both code and reasoning.

| Workload | Actual input tokens | Output tokens | Decode median (sd), tok/s | TTFT, s | Cached tokens | Draft acceptance | Peak global VRAM, GiB |
|---|---:|---:|---:|---:|---:|---:|---:|
| fixed-mtp3-code | 8240 | 768 | 84.5 (2.47) | 0.908 | 6656 | 80.6% | 29.582 |
| fixed-mtp3-reasoning | 8282 | 512 | 65.7 (5.64) | 0.938 | 6656 | 53.0% | 30.264 |

MTP4 improves the code median from 84.5 to 90.1 tok/s, 6.6%, at exactly 8,240 input tokens, 768 generated tokens, thinking off and concurrency 1. This is the headline gain with identical requests. The earlier screening's 12% comparison used different nonces and should not replace this tighter result.

Reasoning at exactly 8,282 input tokens, 512 generated and xhigh measures 65.7 tok/s (sd 5.64) for MTP3 and 65.0 (sd 7.12) for MTP4. That difference is inside the observed spread. Cached TTFT stays near 0.91 s for code and 0.94 s for reasoning. No reasoning-speed gain is claimed.

Peak global VRAM is the observed maximum during each arm's measured requests; allocator history differs because MTP4 followed the CPU trials and MTP3 was freshly recreated. Use the startup KV capacities, 109,067 versus 111,509 tokens, for the durable capacity comparison. Both retain the 98,304-token context limit.

MTP4 remains selected. Diagnostics were saved in `pre-final-mtp4-health.log` before restoring the committed defaults with no shell overrides. `STATUS.md` now leads with the exact-request 6.6% code gain and links the earlier longer-context screening separately. The CLI guard rejecting a fixed prompt ID on cold runs was also checked locally without sending an inference request.
