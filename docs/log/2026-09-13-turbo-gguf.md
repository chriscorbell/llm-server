# 2026-09-13 Turbo Q6_K GGUF on the B70

Status: in progress
Profile: turbo-gguf

## Hypothesis

DavidAU's Turbo fine-tune in Q6_K GGUF can serve text, tools and images on the B70 through llama.cpp Vulkan with a 65,536-token context window.

## Configuration

This is initial deployment of another engine and checkpoint, not a controlled speed comparison with vLLM. The existing `a-int4draft` profile remains the daily driver. No kernel or host driver changes are planned.

- Engine: `ghcr.io/ggml-org/llama.cpp@sha256:09800bdcf619dbea87cd22194c3210ebbb80c943e5d93fb27e4e5bb6f6e7b1ce`, linux/amd64 manifest resolved from upstream `server-vulkan` on September 13.
- Model repository: [DavidAU Turbo GGUF](https://huggingface.co/DavidAU/Qwen3.8-27B-TURBO-Fable-Cold-Fusion-735-882-Heretic-Uncensored-NEO-CODER-MAX-MTP-GGUF), revision `0b4bc07a8c549be631ed8f5fd78b68fb0e80eced`.
- Weights: `Qwen3.8-27B-TurboFCFusion-735-882-Here-Uncen-NEO-CODER-MAX-MTP-Q6_K.gguf`, 24,033,703,456 bytes, SHA-256 `ac011aabe685edbdf542e49351eb6c76c0e5531408f2507f2235ab10931e23a5`.
- Vision: `mmproj-F16.gguf`, 927,606,976 bytes, SHA-256 `82e620db8cb83267e9775e5aad3e8d8aa5af7ace825e94c52d3d730eb35af88a`.
- All model layers on `Vulkan0`, one sequence, F16 KV, flash attention on, batch 2,048 and microbatch 512. MTP initially disabled, although the selected file includes its head. MTP needs its own follow-up experiment.
- Same private API key and Tailscale-only published port 8000; model alias `qwen38-turbo`.

```bash
ssh vllm 'cd ~/Code/llm-server && python3 scripts/download-turbo.py'
ssh vllm 'cd ~/Code/llm-server && bash scripts/compose.sh --profile turbo-gguf pull llama-turbo'
# Capture the current service before stopping it.
ssh vllm 'cd ~/Code/llm-server && bash scripts/gpu-health.sh'
ssh vllm 'docker stop qwen38 && docker rm qwen38'
ssh vllm 'cd ~/Code/llm-server && bash scripts/compose.sh --profile turbo-gguf up -d --no-deps llama-turbo'
```

Restore the daily driver with the same stop/remove sequence, then `bash scripts/compose.sh --profile a-int4draft up -d --no-deps vllm-a-int4draft` on the server. Do not use `down`, which would also stop SearXNG.

Baseline: [validated 128K vLLM deployment](2026-09-12-context-128k.md). Different engine, quantization and model mean any throughput difference cannot be attributed to the fine-tune alone.

## Measurements

Inference not yet measured. Repository metadata gives 22.383 GiB of weights plus 0.864 GiB of projector. F16 KV at 65,536 tokens is approximately 4 GiB before runtime buffers and recurrent state. These are capacity estimates, not measured peak VRAM.

The unchanged vLLM daily driver was measured before the switch with:

```bash
python3 scripts/bench.py --base-url http://vllm:8000 --model qwen38 \
  --prompt-tokens 4096 --gen 256 --workload code --corpus-file scripts/bench.py \
  --warm --prompt-id turbo-profile-comparison -n 2 \
  --json scratch/turbo/vllm-reference.json
```

At concurrency 1, thinking off and exactly 4,199 actual input tokens, the two warm repetitions produce 256 tokens each at 82.8 and 93.5 tok/s, median 88.2 tok/s, median TTFT 1.339 s and MTP acceptance 72.0%. Both report 1,664 cached tokens. This is a small reference sample, not a quality or controlled engine comparison.

## What happened

### Temporary switch for validation

The current service's diagnostics are saved in `scratch/turbo/before-switch-health.log` on both machines. A one-second VRAM sampler writes to `scratch/turbo/vram.jsonl` on mbp. The daily-driver container ID is `ff4da06641021d44bc7b468d8ee8fbb17bec4944914f240fe9fc6e8ae765939c`.

For this initial test, preserve its writable layer and compiled kernels instead of removing it:

```bash
ssh vllm 'docker stop qwen38 && docker rename qwen38 qwen38-before-turbo'
ssh vllm 'cd ~/Code/llm-server && bash scripts/compose.sh --profile turbo-gguf up -d --no-deps llama-turbo'
# After collecting evidence and finishing Turbo tests:
ssh vllm 'docker stop qwen38 && docker rm qwen38 && docker rename qwen38-before-turbo qwen38 && docker start qwen38'
```

### Preparation

The pinned image identifies itself as llama.cpp `b10920`, revision `eafe15a5e3d87dd68ae33acf6a7cbd9415a0ac5e`, built September 12 at 05:55:29 UTC. `--list-devices` detects `Vulkan0: Intel(R) Graphics (BMG G31)` with 32,656 MiB total memory while vLLM remains healthy. Docker Compose validation passes on the server. The MacBook has no Docker CLI, so Compose checks run through SSH.

The downloaded file's header reports GGUF v3, architecture `qwen35`, 866 tensors, 65 blocks including one next-token prediction block, and native context 262,144. Its embedded general name is `Qwen3.8 27B Brainwaves NM HERETIC BR LOA1`, which differs from the filename. The pinned repository file and SHA-256, rather than that inherited display metadata, identify this deployment.

The server was healthy with zero swap use, about 51 GiB available RAM and 1.7 TiB free storage. Both clones were on `main`; the server was clean. The MacBook has pre-existing client and documentation edits, which are outside this change. The two original hardware/engine research reports were read before selecting Vulkan. The upstream Docker documentation lists `server-vulkan`, and its Dockerfile bundles Mesa inside the container. The host's kernel and drivers therefore stay unchanged.

The publisher recommends Q6 for tool calling. Its Q8 MTP file is 28.162 GiB before the 0.864 GiB projector, KV and buffers, so Q6 leaves a more useful context budget. Published quality and speed claims have not been verified here.

## Outcome

Pending model download and live verification.

## Consequences

Added a separate Compose profile, a pinned model manifest and a resumable SHA-256-verifying download script. The current vLLM profile's tuning is unchanged.
