# 2026-09-07 Hardware survey and stack choice

Status: concluded
Profile: none yet
Author: agent thread on mbp

## Hypothesis

Not an experiment in the measurement sense. This entry records the starting state of the machine and why the stack was chosen, so later entries have a baseline to refer to.

## What the machine actually is

Probed over SSH on 2026-09-07.

```
Ubuntu 26.04.1 LTS, kernel 7.0.0-31-generic
AMD Ryzen Threadripper 3970X, 32 cores / 64 threads
60 GiB usable RAM, 1.8 TB NVMe with 1.7 TB free
4c:00.0 Intel Battlemage G31, device id 0xe223, driver xe
  BAR: 32 GB prefetchable, so Resizable BAR is active
  VRAM usable excluding stolen: 0x7f9000000 = 31.9 GiB
  SR-IOV PF mode, display version 14.01 stepping C0
Docker 29.1.3, overlayfs, runc
intel-opencl-icd 26.05.37020.3, libze-intel-gpu1 26.05.37020.3
user chris in groups docker and render, passwordless sudo
eno1 and a second Intel I211, both gigabit
```

Two corrections to prior assumptions. The server has gigabit networking, not 10 GbE; the fleet document's 10 GbE line belongs to the MacBook. And Resizable BAR is already enabled, which matters because community reports put compute throughput at roughly half without it.

## Why this stack

Full reasoning in the two reports under `docs/research/`. The short chain:

1. **The card has no native FP8.** Xe2 XMX supports FP16, BF16, INT8, INT4 and INT2. FP8 checkpoints run through a dequantization path, and oneDNN's 2026 notes carry an open issue about sporadically wrong FP8 matmul results on Arc B-series. So the obvious "least lossy" choice, Qwen's official FP8 release, is the wrong one here.
2. **INT4 is the fast path and appears not to cost quality on this model.** Quesma's published evals of Qwen3.8-27B put BF16, Q8_0 and Q4_K_M within noise of each other on GPQA Diamond, IFBench and Terminal-Bench 2.1. Kaitchup's work on the previous generation shows the loss concentrates in the linear-attention projections, which the chosen checkpoint keeps at higher precision.
3. **The engine choice is between vLLM XPU and llama.cpp.** SGLang XPU lacks speculative decoding, OpenVINO's Qwen3.8 support is nightly-only with a weaker INT4 recipe, Ollama has no Intel path, and IPEX-LLM was archived by Intel in January 2026.
4. **vLLM wins on the numbers that matter here.** GGUF conversion strips the MTP head, so llama.cpp cannot use the model's own speculative decoding, and 8-bit GGUF weights leave too little VRAM for the target context. Published single-B70 measurements for this exact checkpoint under vLLM: 83.7 tok/s decode with MTP4 at 512-token prompts, 56.3 tok/s at 131K context, about 1,750 tok/s cold prefill.

## Decisions

| Decision | Value | Why |
|---|---|---|
| Engine | vLLM XPU, image pinned by digest | Only stack with MTP, vision and measured numbers on this card |
| Weights | GPTQ INT4 G128 sym, MTP head and GDN projections in BF16 | Integer-first hardware, published quality parity |
| KV cache | BF16 as baseline, FP8 as an experiment | KV precision is the one place we have not seen quality data |
| Vision | on, by omitting `--language-model-only` | Requirement. Costs ~0.92 GiB |
| Concurrency | `--max-num-seqs 1` | Holds MTP acceptance near 95% and avoids a known crash |
| Thinking | on, `xhigh` | Quality is the stated priority |
| Exposure | Tailscale address only, static API key | Single user, no reason to be reachable otherwise |

## Consequences

Repository scaffolded: `AGENTS.md`, `CONTEXT.md`, `STATUS.md`, compose profiles, helper scripts, and the two research reports. The three upstream patches are vendored under `compose/patches/` with their hashes recorded.

Next: Experiment 2, find the largest `--max-model-len` that BF16 KV actually fits. The arithmetic suggests 131,072 will not fit and the real ceiling is nearer 64K to 96K.
