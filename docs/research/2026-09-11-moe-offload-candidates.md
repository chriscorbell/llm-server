# MoE candidates with expert weights offloaded to host RAM

Checked September 11, 2026. Source research, not an Experiment. Nothing was downloaded or run. This fills the gap between the [in-VRAM shortlist](2026-09-11-local-model-alternatives.md) and the [DeepSeek V4.1 offload assessment](2026-09-11-deepseek-v41-offload.md): mixture-of-experts models whose attention and shared weights fit the 32 GiB B70 while routed experts live in the 60 GiB of host RAM, or in 192 GB after the upgrade priced in the [hardware assessment](2026-09-11-deepseek-budget-hardware.md).

## Decision

Two candidates are worth an Experiment. Qwen3.8-Flash-Next is the only model that fits today's memory and reports clearly higher agentic scores than Qwen3.8-27B. GLM-5.3-Flash is the strongest model that fits after a 192 GB RAM upgrade. Both require leaving vLLM XPU for llama.cpp, because no Intel serving stack offloads experts. Neither has a published Intel Arc run; the first Experiment is a correctness and speed check, not a quality comparison.

## Runtime: only llama.cpp offloads experts on Intel Arc

| Runtime | Expert offload | Battlemage evidence |
|---|---|---|
| llama.cpp SYCL | Yes, `--n-cpu-moe` and `-ot` are backend-agnostic placement flags | [B60 24 GB + 64 GB RAM, Qwen3.5-35B-A3B Q4 with `-ncmoe 4`, May 2026](https://sanmai.github.io/slop/2026/05/08/llama-cpp-batch-size-arc-b60.html); [B70 resident MoE 54.7 tok/s](https://github.com/PMZFX/intel-arc-pro-b70-benchmarks) |
| llama.cpp Vulkan | Yes, same flags | [3x A770, gpt-oss-120b, `--n-cpu-moe 14`, 14 to 19 tok/s](https://github.com/ggml-org/llama.cpp/discussions/19674); Mesa 26.1 [doubled B70 decode](https://jonathanmann.tech/blog/intel-arc-b70-llama-cpp-benchmarks/). No B-series offload number found. |
| llm-scaler / vLLM XPU | No | [README](https://github.com/intel/llm-scaler/blob/main/README.md) lists GPU-resident models only. Upstream `--cpu-offload-gb` is layer-wise and [reports MoE device errors](https://github.com/vllm-project/vllm/issues/15196). Expert-cache [RFC #38256](https://github.com/vllm-project/vllm/issues/38256) is CUDA-only. |
| ktransformers | Yes by design | [Intel path is beta](https://github.com/kvcache-ai/ktransformers/blob/main/doc/en/xpu.md): A770 and B580 tested, serving unsupported on Intel GPU. |
| SGLang XPU | No | [B580 verified only for small dense models and gpt-oss-20b](https://lmsysorg.mintlify.app/docs/hardware-platforms/xpu). |

Two llama.cpp hazards on this stack. The expert-cache [PR #27861](https://github.com/ggml-org/llama.cpp/pull/27861) is unmerged and reports garbage output on SYCL. The oneDNN flash-attention path in [PR #25222](https://www.techi.com/llama-cpp-intel-battlemage-flash-attention-benchmark/), build b10016 from July 15, gives 4.26x prefill on B70 at 80K context, which matters because TTFT is the dominant cost on this server. Leaving llama.cpp's MTP unsupported also loses the speculative-decoding gain the current profile depends on.

## Candidates

Scores are vendor-reported unless marked. Nobody publishes a verified Terminal-Bench 2.1 or SWE-bench Pro result for any 2026 open model ([llm-stats](https://llm-stats.com/benchmarks/terminal-bench-2.1), [Scale](https://labs.scale.com/leaderboard/swe_bench_pro_public)). Baseline Qwen3.8-27B: Terminal-Bench 2.1 73.0, SWE-bench Pro 61.7, DeepSWE 42.2, NL2Repo 42.3, Artificial Analysis index 34 ([card](https://huggingface.co/Qwen/Qwen3.8-27B), [AA](https://artificialanalysis.ai/models/qwen3-8-27b)).

| Model | Total / active | Agentic scores | 4-bit GGUF | 32 GiB + 60 GiB | 32 GiB + 192 GB |
|---|---|---|---|---|---|
| [Qwen3.8-Flash-Next](https://huggingface.co/Qwen/Qwen3.8-Flash-Next) | 125B + 51B n-gram + 4B MTP / 6B | SWE-Pro 62.5, DeepSWE 58.7, NL2Repo 48.1, no Terminal-Bench; AA 40 | [UD-Q4_K_XL 111 GB, IQ3_XXS 82 GB](https://huggingface.co/unsloth/Qwen3.8-Flash-Next-GGUF) | Tight at Q4, feasible at Q3; n-gram table pages from NVMe | Comfortable |
| [GLM-5.3-Flash](https://huggingface.co/zai-org/GLM-5.3-Flash) | 320B / 18B | Terminal-Bench 2.1 84.3, DeepSWE 63.4, NL2Repo 56.3; AA 42 | [Q4 200 GB, IQ4_XS 157 GB, Q3 148 GB](https://huggingface.co/unsloth/GLM-5.3-Flash-GGUF) | No | Yes at IQ4_XS or Q3 |
| [DeepSeek-V4-Flash-0731](https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash-0731) | 284B / 13B | Terminal-Bench 2.1 82.7, DeepSWE 54.4, NL2Repo 54.2 | [Q4 155 GB, lossless because experts are native FP4](https://unsloth.ai/docs/models/deepseek-v4) | No | Yes, about 60 GiB left for KV |
| [Nex-N2.5-Pro](https://huggingface.co/nex-agi/Nex-N2.5-Pro) | 397B / 17B | Terminal-Bench 2.1 82.7, SWE-Pro 61.2 | No GGUF; base is about 214 GB at Q4 | No | Marginal, 3-bit only |
| [Qwen3-Coder-Next](https://huggingface.co/Qwen/Qwen3-Coder-Next) | 80B / 3B | SWE-Pro 44.3 (card) or 56.2 ([paper](https://arxiv.org/html/2603.00729v1)), Terminal-Bench 2.0 36.2, no thinking | [UD-Q4_K_XL 49.6 GB](https://huggingface.co/unsloth/Qwen3-Coder-Next-GGUF) | Easily | Easily |

Excluded: DeepSeek V4.1 Flash (backbone alone is about 290 GiB at 4-bit), GLM-5.3 753B, Kimi K2.6 and K3, Nex-N2.5-Max, MiniMax M3 (Terminal-Bench 66.0, below baseline), Step 3.7 Flash (59.5), Nemotron 3 Super (Terminal-Bench hard 25.8), gpt-oss-120b (Terminal-Bench 2.0 18.7 independent). Muse Glimmer has no larger variant, and Qwen3.8 has no mid-size MoE other than Flash-Next.

Qwen3-Coder-Next is the only entry where every layer of the stack is already demonstrated on Battlemage, but its scores do not beat the 27B, so it is a runtime rehearsal rather than a capability upgrade.

## Qwen3.8-Flash-Next specifics

- llama.cpp architecture `qwen4exp` merged in [PR #27742](https://github.com/ggml-org/llama.cpp/pull/27742) on August 27; tested on CPU, CUDA, Metal and HIP. No SYCL or Vulkan-on-Intel run is published. Indexer correctness fixes landed September 1 in [PR #27941](https://github.com/ggml-org/llama.cpp/pull/27941); earlier binaries produced garbage on ROCm. Quantized KV cache crashes it. Build 10665 regressed n-gram loading ([issue #28355](https://github.com/ggml-org/llama.cpp/issues/28355)).
- The 51B n-gram table is CPU-only, memory-mapped and reads about 2.7 KB per token at a deterministic address, so it behaves like DeepSeek's Engram and can stay on NVMe. [AtomicChat's split GGUF](https://huggingface.co/AtomicChat/Qwen3.8-Flash-Next-GGUF) isolates it as a 38.4 GB shard and measured about 3 MB/s of random reads from SSD at 36 tok/s on an M5 Max.
- MTP support is [draft PR #28243](https://github.com/ggml-org/llama.cpp/pull/28243), Vulkan-tested on NVIDIA, SYCL untested.
- Closest hardware match: [5070 Ti + 5060 Ti (32 GB) + 64 GB RAM at 23.3 tok/s, and 2x3080 with the n-gram shard on NVMe at 16 to 17 tok/s](https://huggingface.co/unsloth/Qwen3.8-Flash-Next-GGUF/discussions/3). The B70 has less bandwidth than that pair and the Threadripper's four DDR4 channels carry the experts, so treat 15 tok/s as an optimistic ceiling until measured.
- The SWE-bench Pro gain over the 27B is 0.8 points on the vendor's own table. The DeepSWE and NL2Repo gains are 16 and 6 points. Both models were scored in Claude Code at 256K context, which this server cannot reproduce.

## What the first Experiment must establish

Build llama.cpp SYCL from a commit after September 1, load Qwen3.8-Flash-Next UD-IQ3_XXS or Q3_K_XL with the n-gram shard on NVMe and `--n-cpu-moe` sized so the GPU holds attention, shared expert and as many routed experts as fit beside a 64K KV cache. Record: coherent output on the eight-task suite, actual RAM and VRAM peaks, NVMe read rate, cold and cached TTFT at 8K and 32K, decode tok/s with thinking on. Compare against the current 90 tok/s code decode and 18.6 s cold 32K TTFT. If output is garbage on SYCL, retry on Vulkan before concluding anything. Only after that does the 192 GB purchase for GLM-5.3-Flash have evidence behind it.
