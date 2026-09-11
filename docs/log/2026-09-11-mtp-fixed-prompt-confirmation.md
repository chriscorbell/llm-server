# 2026-09-11 MTP confirmation with identical requests

Status: in progress
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
