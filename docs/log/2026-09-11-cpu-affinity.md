# 2026-09-11 CPU affinity with the INT4 draft

Status: in progress, restoring the original engine before measurement
Profile: a-int4draft, MTP4, original pinned engine

## Hypothesis

Restricting the container to one Threadripper CCX reduces migration between L3 caches and improves decode throughput.

## Configuration

The only variable is CPU affinity. Use the original engine digest `sha256:f01e24f6c7ff01f1e0662234255a1372297d1dbd89d003cf13c8fad3eab1ba4f` and the selected MTP4 configuration from the [depth sweep](2026-09-11-int4-mtp-depth.md). Compare unrestricted CPUs with cores `0-3,32-35`, one four-core CCX and its SMT siblings on this 3970X. Kernel, governor, model and serving flags stay fixed.

```bash
bash scripts/bench-affinity.sh
```

The script applies `docker update --cpuset-cpus '0-3,32-35' qwen38` or `docker update --cpuset-cpus '' qwen38`. It asserts the Docker setting after each change, avoiding the [earlier invalid pinning attempt](2026-09-07-cpu-governor-and-pinning.md). It runs three alternating pairs, reversing order in the middle pair, with two measured repetitions per block and a discarded warmup. Each pair uses the same seed sequence. Its exit trap restores unrestricted CPUs.

## Measurements

Pending. Warm code output at approximately 8K actual input tokens, 768 generated tokens, thinking off and concurrency 1. Six measured repetitions per arm, spread across three pairs. A candidate must improve the paired results before further cold-prefill validation or persistence.

## Outcome

No result yet.

## Consequences

The measured default remains unpinned until this comparison is complete.
