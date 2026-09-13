# 2026-09-13 Turbo Q6_K backend comparison

Status: concluded
Profile: turbo-gguf

## Hypothesis

The Intel SYCL build of llama.cpp will decode the same Turbo Q6_K checkpoint faster than the Vulkan build on this B70, while preserving short-output correctness.

## Configuration

Change the engine backend from Vulkan to SYCL, including the matching device selector and the Level Zero allocation setting. Keep the model file, context, KV format, batch sizes, flash attention, sampling and disabled speculative decoding fixed. The selected image bundles its own compute userspace; the host kernel and drivers remain unchanged.

- Vulkan baseline image: `ghcr.io/ggml-org/llama.cpp@sha256:09800bdcf619dbea87cd22194c3210ebbb80c943e5d93fb27e4e5bb6f6e7b1ce`, llama.cpp b10920, revision `eafe15a5e3d87dd68ae33acf6a7cbd9415a0ac5e`.
- Intel candidate image: `ghcr.io/ggml-org/llama.cpp@sha256:61606ca6fa74290cca83c0c8c7f0efc4c22c28bbdc9741bff8e6c861dccdd670`, linux/amd64 manifest resolved from upstream `server-intel` on September 13. Build revision to be checked after pulling.

```bash
ssh vllm 'cd ~/Code/llm-server && bash scripts/gpu-health.sh > scratch/turbo/before-sycl-health.log 2>&1'
ssh vllm 'cd ~/Code/llm-server && TURBO_IMAGE=ghcr.io/ggml-org/llama.cpp@sha256:61606ca6fa74290cca83c0c8c7f0efc4c22c28bbdc9741bff8e6c861dccdd670 TURBO_DEVICE=SYCL0 bash scripts/compose.sh --profile turbo-gguf up -d --no-deps llama-turbo'
```

Baseline: [initial Vulkan deployment](2026-09-13-turbo-gguf.md).

## Measurements

The completed SYCL comparison uses identical request hashes to the Vulkan run and the same actual 4,199-token input, 256 generated tokens, thinking off, concurrency 1 and two warm repetitions:

| Metric | Vulkan | SYCL |
|---|---:|---:|
| Median decode | 3.9 tok/s | 19.7 tok/s |
| Median TTFT | 0.491 s | 0.214 s |
| Cached prompt tokens | 4,195 | 4,195 |
| Short checks | 18/18 | 18/18 |
| Startup to listening | 11.613 s | 75.188 s |

SYCL's observed VRAM during the benchmark is 28,768,468,992 bytes, 26.792 GiB. Its cold warm-up processes 4,199 tokens in about 4.7 s before decode. Raw data: `scratch/turbo/sycl-nospec-warm.json` and `scratch/turbo/sycl-nospec-short-checks.json` on mbp. The code corpus is frozen as `scratch/turbo/bench-corpus.py`, SHA-256 `9ae37e8c1bde0e297188695f444c50060e754a8d59dbbd7ff83240a0ddf900bb`, before extending the benchmark's metric parser for llama.cpp.

SYCL not yet measured. Vulkan's completed warm-up generates 256 tokens at 3.95 tok/s after an 8.644 s prefill of 4,199 input tokens, thinking off, concurrency 1. The next warm request still measures 3.95 tok/s. CPU consumption during that request is 27% of one core; GPU memory is 26.7 GiB. No new GPU fault appears.

## What happened

The first SYCL startup takes longer than a 50-second readiness probe. An initial correctness command was inadvertently launched after that probe timed out and received `urllib.error.HTTPError: HTTP Error 503: Service Unavailable`. No inference ran in that attempt. Subsequent checks are gated on successful HTTP 200 readiness. The container remains running with zero restarts and reaches thread-pool initialization at 19.375 s; one CPU core remains busy during initialization. Pre-restart diagnostics are saved in `scratch/turbo/sycl-starting-health.log` on the server. No restart was performed.

The Intel image is also b10920 at revision `eafe15a5e3d87dd68ae33acf6a7cbd9415a0ac5e`, built September 12 at 06:42:58 UTC. It detects `SYCL0: Intel(R) Arc(TM) Pro B70 Graphics`, 32,656 MiB total. Both backend images therefore use the same llama.cpp source revision.

The completed Vulkan benchmark records 3.9 tok/s median, 0.491 s median TTFT, 4,199 input tokens and 4,195 cached tokens for both measured 256-token code responses, thinking off and concurrency 1. Raw data: `scratch/turbo/vulkan-nospec-warm.json` on mbp.

The existing benchmark and repeated short suite reproduce the low throughput. All 18 short checks pass, so the issue being investigated is performance. Ranked explanations before changing the backend:

1. Vulkan's kernel path for these weights and this hybrid architecture is slow. Prediction: SYCL improves the same steady-state workload.
2. Some operations fall back to CPU. Prediction: CPU activity or backend diagnostics reveal substantial CPU computation. Observed 27% of one core makes a sustained CPU bottleneck less likely, but does not rule out small fallbacks.
3. Compilation dominates short requests. Prediction: repeated requests speed up. The completed warm-up and subsequent request remain at 3.95 tok/s, contradicting this explanation for steady decode.

The performance feedback loop is `scripts/bench.py` with `--warm --prompt-id turbo-profile-comparison --corpus-file scripts/bench.py --prompt-tokens 4096 --gen 256 --workload code -n 2`. A full run takes minutes at 4 tok/s; the recurring server timing at 100 generated tokens gives the same rate. No synthetic unit test can verify this GPU/backend behavior, so the live benchmark and existing correctness checks are the regression checks.

## Outcome

Confirmed for this pinned checkpoint and workload. Changing the backend raises steady decode about fivefold and preserves the 18 short checks. This identifies the slow Vulkan deployment path, not an individual kernel or a general defect in all Vulkan models. Image and long-context checks remain for the selected profile.

## Consequences

Selected the pinned SYCL image and `SYCL0` in `compose/turbo.env`. Keep the Vulkan digest above as a functional but slower fallback. No host kernel or driver changed. MTP is the next isolated experiment.
