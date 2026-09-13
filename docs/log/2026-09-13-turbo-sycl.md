# 2026-09-13 Turbo Q6_K backend comparison

Status: in progress
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

SYCL not yet measured. Vulkan's completed warm-up generates 256 tokens at 3.95 tok/s after an 8.644 s prefill of 4,199 input tokens, thinking off, concurrency 1. The next warm request still measures 3.95 tok/s. CPU consumption during that request is 27% of one core; GPU memory is 26.7 GiB. No new GPU fault appears.

## What happened

The Intel image is also b10920 at revision `eafe15a5e3d87dd68ae33acf6a7cbd9415a0ac5e`, built September 12 at 06:42:58 UTC. It detects `SYCL0: Intel(R) Arc(TM) Pro B70 Graphics`, 32,656 MiB total. Both backend images therefore use the same llama.cpp source revision.

The completed Vulkan benchmark records 3.9 tok/s median, 0.491 s median TTFT, 4,199 input tokens and 4,195 cached tokens for both measured 256-token code responses, thinking off and concurrency 1. Raw data: `scratch/turbo/vulkan-nospec-warm.json` on mbp.

The existing benchmark and repeated short suite reproduce the low throughput. All 18 short checks pass, so the issue being investigated is performance. Ranked explanations before changing the backend:

1. Vulkan's kernel path for these weights and this hybrid architecture is slow. Prediction: SYCL improves the same steady-state workload.
2. Some operations fall back to CPU. Prediction: CPU activity or backend diagnostics reveal substantial CPU computation. Observed 27% of one core makes a sustained CPU bottleneck less likely, but does not rule out small fallbacks.
3. Compilation dominates short requests. Prediction: repeated requests speed up. The completed warm-up and subsequent request remain at 3.95 tok/s, contradicting this explanation for steady decode.

The performance feedback loop is `scripts/bench.py` with `--warm --prompt-id turbo-profile-comparison --corpus-file scripts/bench.py --prompt-tokens 4096 --gen 256 --workload code -n 2`. A full run takes minutes at 4 tok/s; the recurring server timing at 100 generated tokens gives the same rate. No synthetic unit test can verify this GPU/backend behavior, so the live benchmark and existing correctness checks are the regression checks.

## Outcome

Pending the SYCL run.

## Consequences

Added an explicit backend device setting to the profile. The final default is not selected yet.
