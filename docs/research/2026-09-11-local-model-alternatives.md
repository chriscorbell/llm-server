# Local model alternatives on September 11, 2026

This is source research, not an Experiment. No model or server configuration changed, and no new local quality comparison ran.

## Decision

Qwen3.8-27B remains the justified working default. The evidence does not establish it as the most intelligent model this entire server could run with RAM and NVMe offloading. That broader goal requires testing larger models when a correct runtime exists. A slower model that completes harder tasks can be the better choice. The existing eight-task suite verifies basic operation, not comparative intelligence. [Current state](../../STATUS.md)

## DeepSeek V4.1 Flash changes the shortlist

DeepSeek's official instruct results use maximum reasoning effort 100. Its architecture has 552B backbone parameters and 196B Engram lookup parameters, with 8B active during prefill and 16B during decode. Small active counts describe computation, not all stored weights. [DeepSeek model card](https://huggingface.co/deepseek-ai/DeepSeek-V4.1-Flash)

| Vendor-reported benchmark | Qwen3.8-27B | DeepSeek V4.1 Flash |
|---|---:|---:|
| Terminal-Bench 2.1 | 73.0 | 90.6 |
| DeepSWE 1.1 | 42.2 | 74.2 |
| NL2Repo-Bench | 42.3 | 64.0 |

Sources: [Qwen](https://huggingface.co/Qwen/Qwen3.8-27B), [DeepSeek](https://huggingface.co/deepseek-ai/DeepSeek-V4.1-Flash). These are not controlled local comparisons. Qwen uses Terminus for terminal tasks and Claude Code with 256K context for DeepSWE. DeepSeek uses its own framework for terminal tasks and mini-SWE for DeepSWE with 1M context. Its separate Pi results are 86.1 and 66.2 respectively, still at 1M context. This supports investigating a capability upgrade without promising those results on this server.

The [offload assessment](2026-09-11-deepseek-v41-offload.md) separates successful Engram disk lookup from expert streaming and examines current runtime support. It finds no verified V4.1 deployment for this Intel GPU and host RAM budget. Insufficient GPU residency alone does not rule it out.

## Candidates within a smaller memory budget

**Muse Glimmer-30B** is a credible alternative for general tool use. Meta reports MCP Atlas 75.5 against Qwen3.6-27B's 62.5, but that comparison predates Qwen3.8. Its SWE-bench Pro 51.2 and Terminal-Bench 2.1 51.7 provide no clear reason to replace Qwen for coding. [Meta card](https://huggingface.co/meta-models/Muse-Glimmer-30B). Meta's larger official GGUF is 19.7 GB, with a 1.4 GB vision encoder and optional 1.6 GB drafter. [Artifacts](https://huggingface.co/meta-models/Muse-Glimmer-30B-GGUF)

**Gemma 4 31B-it and 26B-A4B-it** fit the quantized model class worth comparing. Google's larger model reports GPQA 84.3 and LiveCodeBench v6 80.0, below Qwen's reported 89.2 and 90.3. Different evaluation setups prevent treating these as a local ranking. [Google card](https://huggingface.co/google/gemma-4-31B-it), [Qwen card](https://huggingface.co/Qwen/Qwen3.8-27B)

**Nex-N2.5-mini** has 35B parameters and is a plausible INT4 fit, subject to actual loading and context allocation. Nex reports Terminal-Bench 2.1 73.4 and SWE-bench Pro 43.8 using NexAU. Its provider comparison mixes published and internal results. Intel deployment of this exact derivative was not verified. [Nex card](https://huggingface.co/nex-agi/Nex-N2.5-mini)

**GLM-4.7-Flash** is a smaller, older alternative. Its vendor reports SWE-bench Verified 59.2; Verified and Pro are different benchmarks. The newer **GLM-5.3-Flash** has 320B parameters despite its Flash name, requiring separate offload investigation. [GLM-4.7 card](https://huggingface.co/zai-org/GLM-4.7-Flash), [GLM-5.3-Flash card](https://huggingface.co/zai-org/GLM-5.3-Flash)

**Qwen3-Coder-Next** remains a reasonable coding-specific comparison when CPU offload is acceptable. It has 80B total parameters, 3B active, 262K context and no explicit thinking mode. Ideal uniform four-bit weight storage is 37.3 GiB before scales and runtime overhead, already beyond GPU capacity. That arithmetic is not a measured deployment footprint or a quality result. [Qwen card](https://huggingface.co/Qwen/Qwen3-Coder-Next)

Intel's current llm-scaler documentation explicitly lists Qwen3.8-27B, Muse Glimmer, Gemma 4, GLM-4.7-Flash and Qwen3-Coder-Next. Muse and Gemma have documented INT4 support; Coder-Next's table lists FP16/FP8. These establish engine support, not one-B70 performance or quality. This supersedes the September 7 report's statement that Intel does not name Qwen3.8. [Intel documentation](https://github.com/intel/llm-scaler/blob/main/vllm/README.md)

## Other larger candidates

Qwen3.8-Flash-Next improves Qwen's reported DeepSWE score to 58.7, but includes 125B main parameters, 51B n-gram embeddings and 4B MTP. [Qwen card](https://huggingface.co/Qwen/Qwen3.8-Flash-Next). Its vLLM recipe lists 172.78 GiB FP8 weights and explicitly excludes XPU from the initial implementation. It also needs a separate offload feasibility check. [vLLM recipe](https://recipes.vllm.ai/Qwen/Qwen3.8-Flash-Next)
