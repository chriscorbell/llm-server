# 2026-09-11 CPU affinity with the INT4 draft

Status: concluded, unrestricted CPUs retained
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

The original image was restored through the committed wrapper configuration. Its container started at 14:11:27 UTC, with MTP4 and no shell overrides. The affinity comparison is queued behind a successful health check and will run sequentially with no competing inference requests.

The first alternating pair completed with two measured warm repetitions per arm, 768 output tokens, thinking off and concurrency 1. Unrestricted CPUs measured 89.9 tok/s at 8,251 actual input tokens; pinned CPUs measured 89.9 tok/s at 8,253. TTFT was 0.910 and 0.913 s respectively. Docker inspection verified the pin. The remaining two pairs are still running; this first pair does not support a gain.

### Clearing affinity failed and was corrected

The first run stopped before its second unrestricted block with the exact message `Affinity override did not apply`. Docker accepted `docker update --cpuset-cpus '' qwen38` but left both `HostConfig.CpusetCpus` and the cgroup's `cpuset.cpus.effective` at `0-3,32-35`. The exit trap hit the same behavior. No supposedly unrestricted benchmark was recorded under the leftover pin.

The active container was immediately restored with `docker update --cpuset-cpus 0-63 qwen38`. Both Docker inspection and `/sys/fs/cgroup/cpuset.cpus.effective` then reported `0-63`, matching all online CPUs. Raw evidence is in `cpu-affinity-restore.log`. This is a Docker update limitation, not an inference failure.

The corrected script uses the host's online CPU list for the unrestricted arm and cleanup, and checks the effective cgroup mask as well as Docker's configured value. Empty Docker metadata will be restored by recreating the container through the committed Compose defaults. The interrupted measurements are retained separately; the full three-pair comparison is restarted in a new directory:

```bash
mkdir -p eval/results/2026-09-11-tuning/cpu-retry
cp eval/results/2026-09-11-tuning/corpus.txt eval/results/2026-09-11-tuning/cpu-retry/corpus.txt
bash scripts/bench-affinity.sh eval/results/2026-09-11-tuning/cpu-retry
```

### Completed comparison

Six measured repetitions per arm, across three alternating pairs, warm code output, thinking off, 768 generated tokens and concurrency 1. Both Docker's configured value and the effective cgroup mask were checked for every block. The completed pairs use the same corpus and per-pair seeds but retain the earlier benchmark's fresh session nonce per block.

| Arm | Actual input tokens | Decode median (sd), tok/s | TTFT, s | Acceptance | Peak global VRAM, GiB |
|---|---:|---:|---:|---:|---:|
| unpinned | 8249-8251 | 90.3 (3.69) | 0.918 | 73.9% | 30.224 |
| pinned | 8252-8254 | 89.6 (2.26) | 0.910 | 72.8% | 30.224 |

Per-pair decode medians were 87.2 versus 87.5, 92.5 versus 91.6, and 93.0 versus 89.1 tok/s, unrestricted then pinned. Pinning changes these by +0.3%, -1.0% and -4.2%. It does not demonstrate a repeatable improvement and is rejected. No cold-prefill or task-quality arm is needed for this rejected setting.

Cleanup restored both Docker and the effective cgroup to all online CPUs, `0-63`. The next container recreation will restore empty Docker metadata through the committed default. A Finding in `STATUS.md` records that this specific CCX pin does not help; it does not rule out every possible CPU optimization.

The benchmark now accepts an explicit warm `--prompt-id` and records complete request hashes. Future affinity pairs use a shared identifier to remove session-prefix variation. The results above predate that refinement and are retained as measured; no small positive gain is promoted from them.

The empty-update behavior was observed with Docker client and server 29.1.3. The subsequent MTP3 container recreation restored empty `HostConfig.CpusetCpus`, while `cpuset.cpus.effective` remained `0-63`, confirming the intended unrestricted runtime state.
