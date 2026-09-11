# Upstream optimization candidates for the B70

Checked 2026-09-11 against release notes, tagged source and GitHub APIs. This is source research, not an Experiment. No server command, benchmark or configuration change was made. It updates the version recommendations in the [September 7 audit](2026-09-07-agentic-coding-upstream.md).

The baseline remains image `sha256:f01e24f6c7ff01f1e0662234255a1372297d1dbd89d003cf13c8fad3eab1ba4f`, vLLM `0.27.2rc1.dev77`, XPU kernels `0.1.12.3`, GPTQ INT4 target, INT4 draft overlay and MTP3. The strongest upstream candidate is a pinned vLLM 0.29.0 comparison. Existing graph coverage and CPU dispatch deserve profiling. Neither has a verified speedup for this server.

## Candidate 1: compare the released 0.29.0 engine

vLLM 0.29.0 was released September 9 and publishes `vllm/vllm-openai-xpu:v0.29.0`. Its default changes to Model Runner V2, and it adds per-request speculative acceptance reporting. These are reasons to investigate CPU work per generated token and improve measurements; the release does not establish a speedup for single-card Qwen3.8-27B GPTQ with the local draft overlay. [Release](https://github.com/vllm-project/vllm/releases/tag/v0.29.0)

The tagged requirements pin this pair:

| Package | Version |
|---|---|
| PyTorch | `2.13.0` |
| Triton | `3.7.2+xpu` |
| XPU kernels | `0.1.14.1` |
| AutoRound library | `0.14.2` |

These are source requirements, not an inspection of a downloaded container. Resolve the image digest and inspect its installed packages before testing. [Tagged requirements](https://github.com/vllm-project/vllm/blob/v0.29.0/requirements/xpu.txt)

Kernels 0.1.14 fix mixed speculative/non-speculative GDN execution and convolution-state indexing. The low-level GDN ops change to separate speculative and non-speculative interfaces, so an old source patch cannot be assumed compatible. [Kernel release](https://github.com/vllm-project/vllm-xpu-kernels/releases/tag/v0.1.14)

There is a release-note inconsistency: the `0.1.14.1` page claims the 0.1.13 codebase, but the GitHub tag API resolves both `0.1.14.1` and `v0.1.14` to commit `6d92b1bfbf32767ecda8e819613eb151e70030ad`. The tag evidence supports a shared 0.1.14 source revision; actual wheel contents still need inspection. [0.1.14.1 release](https://github.com/vllm-project/vllm-xpu-kernels/releases/tag/0.1.14.1), [0.1.14.1 tag](https://api.github.com/repos/vllm-project/vllm-xpu-kernels/git/ref/tags/0.1.14.1), [0.1.14 tag](https://api.github.com/repos/vllm-project/vllm-xpu-kernels/git/ref/tags/v0.1.14)

XPU has an explicit V2 runner implementation, although configuration can fall back for unsupported features. Check the selected runner in startup logs. Revalidate the INT4 draft patches against that runner before comparing speed. [XPU worker](https://github.com/vllm-project/vllm/blob/v0.29.0/vllm/v1/worker/xpu_worker.py#L112-L138), [runner selection](https://github.com/vllm-project/vllm/blob/v0.29.0/vllm/config/vllm.py#L645-L677)

Keep graph mode, model revision, quantization, MTP depth, KV dtype, context limit, 8,192-token prefill chunks and concurrency fixed for the engine comparison. Measure real code generation and repeated tool turns, with acceptance and correctness alongside latency. The new `--per-request-spec-decode-metrics summary` can supply acceptance counts; streaming requires `stream_options.include_usage: true`. Its implementation was validated upstream on NVIDIA with n-gram speculation, so XPU MTP reporting needs a local check. [Metrics implementation](https://github.com/vllm-project/vllm/pull/48915)

## Candidate 2: profile existing graph coverage and CPU dispatch

The current compose configuration already sets `VLLM_XPU_ENABLE_XPU_GRAPH=1`. The September 11 live inspection recorded PIECEWISE capture for mixed prefill/decode and FULL capture for decode. Graph enablement is therefore already in the baseline. Profile remaining CPU dispatch, synchronization and work outside captured graphs before proposing another change. A busy engine thread alone does not identify the bottleneck. [Compose configuration](../../compose/docker-compose.yml), [current inspection](../../STATUS.md), [earlier CPU observation](../log/2026-09-07-decode-versus-context.md)

The 0.29.0 XPU platform still calls graphs experimental and supports only single-GPU execution. Preserve graph settings during an engine comparison, and use eager execution as a separate correctness control when changing the engine or MTP depth. [Tagged platform source](https://github.com/vllm-project/vllm/blob/v0.29.0/vllm/platforms/xpu.py)

Open issue 54785 reports incorrect, varying logits with captured MTP4 on two B70s, Qwen3.8-27B FP8, TurboQuant KV, vLLM `0.21.1.dev0` and kernels `0.1.8.3.dev0`. The reporter found MTP1 through MTP3 and eager MTP4 clean; short prompts reproduced the error most clearly. This differs from our single-GPU GPTQ/MTP3 configuration and does not prove it affected. Include repeated short-prompt correctness checks against eager execution, plus long-context and tool-call checks, when changing captured execution or trying MTP4. [Issue and reproduction](https://github.com/vllm-project/vllm/issues/54785), [short-prompt addendum](https://github.com/vllm-project/vllm/issues/54785#issuecomment-5497862084)

## Changes that do not justify an immediate switch

- The release's fused GDN MTP head-ratio optimization is a CUDA kernel with NVIDIA measurements. Qwen's XPU implementation takes `forward_xpu`; this headline is not evidence of a B70 gain. [PR 52539](https://github.com/vllm-project/vllm/pull/52539), [XPU dispatch](https://github.com/vllm-project/vllm/blob/v0.29.0/vllm/model_executor/layers/mamba/gdn/qwen_gdn_linear_attn.py#L389-L401)
- The new INC W4A8 selector applies to INC linear layers, with W4A16 fallback below 512 tokens. It is not a switch for the current GPTQ path and its published workloads differ. [PR 50501](https://github.com/vllm-project/vllm/pull/50501)
- Kernel sampler changes landed after 0.1.14, including per-row RNG support on September 10. They are absent from the tagged pair. The latter's B60 microbenchmark shows almost no benefit at batch one and does not establish a gain for this speculative workload. No kernel release newer than 0.1.14/0.1.14.1 was listed by the release API during this check. [Sampler PR 590](https://github.com/vllm-project/vllm-xpu-kernels/pull/590), [release API](https://api.github.com/repos/vllm-project/vllm-xpu-kernels/releases?per_page=6)
