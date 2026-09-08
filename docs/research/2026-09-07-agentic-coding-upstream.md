# Qwen3.8-27B agentic coding: upstream audit

Checked 2026-09-07. This is source research, not a server experiment. No engine, model, driver, or serving configuration changed during this audit. Local measurements below come from existing experiment logs.

## Recommendation

Keep the current GPTQ checkpoint, 16-bit KV profile, thinking, and single-request serving as the quality baseline. Existing logs call this BF16 KV; live inspection found `--dtype float16 --kv-cache-dtype auto`, so the attention cache follows FP16. First verify that the coding client sends the intended sampling settings, preserves reasoning across tool calls, and keeps conversation prefixes stable. Then compare complete coding tasks, including failures and retries. The next optional throughput experiment is the cookbook's INT4 draft overlay. A newer engine deserves a separate maintenance experiment, but no upstream source establishes that a version change improves this exact workload without regression.

This order follows the local evidence: at a 32K prompt and concurrency one, prefix caching reduced time to first token from 19.5 seconds to 1.1 seconds. The existing task suite passed seven coding tasks plus a direct vision check; it is a functional baseline with limited coverage of difficult repository work. See [decode versus context](../log/2026-09-07-decode-versus-context.md) and [task suite baseline](../log/2026-09-07-task-suite-baseline.md).

## Client behavior comes first

Qwen recommends the following complete presets. Its default effort is `xhigh`; supported levels are `xhigh`, `medium`, and `low`. It recommends retaining prior thinking and warns that lower effort can increase total task time through failed attempts and retries. Its example accepts both response aliases, then supplies both aliases on subsequent assistant messages. Source: [official model card](https://huggingface.co/Qwen/Qwen3.8-27B/blob/1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0/README.md).

| Request setting | Thinking | Non-thinking |
|---|---:|---:|
| `temperature` | 1.0 | 0.7 |
| `top_p` | 0.95 | 0.80 |
| `top_k` | 20 | 20 |
| `min_p` | 0.0 | 0.0 |
| `presence_penalty` | 0.0 | 1.5 |
| `repetition_penalty` | 1.0 | 1.0 |

For a quality-first coding client, start with thinking enabled, `xhigh`, and `preserve_thinking: true`. Treat these as the baseline to evaluate, not a guarantee of maximal task success. Measure `medium` on complete tasks before selecting it to save time.

The pinned quantized checkpoint's template is byte-identical to the official template retrieved in this audit, 8,952 bytes. It validates the three effort levels. `xhigh` and `low` insert different instructions near the beginning of the prompt; `medium` omits that extra instruction. Effort is prompt conditioning, not a hard token budget. The template reads historical `message.reasoning_content` and preserves it by default. Sources: [pinned quantized template](https://huggingface.co/SergiioB/Qwen3.8-27B-GPTQ-Int4-sym-G128-MTP-BF16/blob/9d189a60e4c0ad7f9f47cd94bfa393ca10b3924e/chat_template.jinja), [official template](https://huggingface.co/Qwen/Qwen3.8-27B/blob/1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0/chat_template.jinja).

There is no demonstrated server alias bug from that template alone. At the pinned vLLM source commit `ac7509e2b`, the request validator converts incoming `reasoning_content` to `reasoning`. The message parser then populates both names for the template. A client may therefore send either name on this version. It must actually retain and resend the content. Sources: [request normalization, lines 524-547](https://github.com/vllm-project/vllm/blob/ac7509e2b/vllm/entrypoints/openai/chat_completion/protocol.py#L524-L547), [template conversation construction, lines 1840-1872](https://github.com/vllm-project/vllm/blob/ac7509e2b/vllm/entrypoints/chat_utils.py#L1840-L1872).

Practical verification for Pi or another client:

1. Record one tool-call round trip through a local mock endpoint. Verify outgoing sampling fields, assistant reasoning, tool-call IDs, and tool results.
2. Confirm `reasoning_effort` reaches the rendered prompt, using `chat_template_kwargs` if the provider does not pass the top-level field. The [vLLM Qwen recipe](https://recipes.vllm.ai/Qwen/Qwen3.8-27B#thinking-modes) documents template controls.
3. Keep effort constant within a task initially. Changing it changes the beginning of the rendered prompt and can invalidate a long cached prefix. This is an inference from the template and prefix matching mechanism, not a local measurement.
4. Keep stable instructions and tool definitions at the beginning. Append tool outputs and new turns. Avoid changing early timestamps or rewriting old messages on each request.

Do not infer that omission of `top_k` currently means unrestricted sampling. The recipe says the checkpoint generation config contains `top_k: 20`. Compare the live engine's effective defaults with the client request before attributing a speed difference to omission. The existing local experiment remains evidence for its recorded requests and conditions.

## Prefix caching works for the installed hybrid model

The local 32K result is more useful than a general claim about GDN support. vLLM's [automatic prefix caching documentation](https://docs.vllm.ai/en/latest/features/automatic_prefix_caching/) explains that reuse saves prefill computation; it does not accelerate the generation of new tokens. Measure cache-hit tokens and time to first token, not only decode speed.

The [hybrid cache design document](https://docs.vllm.ai/en/latest/design/hybrid_kv_cache_manager/) still calls Mamba prefix caching work in progress, but explicitly says it describes an older commit. The newer [vLLM 0.28.0 release](https://github.com/vllm-project/vllm/releases/tag/v0.28.0) enables Mamba prefix caching by default. These documents should not override observed cache reuse on the installed Qwen build.

Preserved reasoning increases stored conversation length. Its expected benefit is better continuity during tool use; caching can reduce the cost of reading that history again. The quality and total-time tradeoff still needs a task comparison. Disabling preservation solely to shorten prompts would change both the model's available information and its prompt prefix.

## INT4 draft is the strongest optional speed candidate

The cookbook's optional overlay quantizes a copy of the draft LM head and five draft MTP linears with INT4 round-to-nearest. The target model and verification head remain unchanged. It targets the same `f01e24f6` image digest and MTP4 as this repository. Its 15-task quality comparison, thinking off at temperature zero, passed 12/15 on both arms. That small suite does not establish parity on difficult agentic coding. Source: [draft overlay at cookbook commit 966c593a](https://github.com/SergiioB/intel-arc-pro-b70-inference-cookbook/blob/966c593a8b375c4df5173d8d07b6be4db7835fdb/docs/qwen38-27/DRAFT-INT4-S-M1.md).

More relevant than its synthetic 112.65 tok/s headline are these prefix-cached agentic measurements from 2026-08-19. Each used one request at a time, MTP4, FP8 KV, the same pinned image, and a configured 230 W cap. Rates are client-observed decode after the first token.

| Starting prompt / generation | BF16 draft | INT4 draft | Repetitions |
|---|---:|---:|---|
| 8K / 128 tokens | 48.04 tok/s | 66.99 tok/s | 3 sessions, 15 turns |
| 16K / 128 tokens | 54.40 tok/s | 65.92 tok/s | 2 sessions, 8 turns |
| 64K / 128 tokens | 44.83 tok/s | 56.20 tok/s | 2 sessions, 4 turns |

These are the author's measurements on another B70, not forecasts for this server. The 128K cold-turn comparison was slower with INT4 draft and had only one observation. Source: [cookbook prefix-on campaigns](https://github.com/SergiioB/intel-arc-pro-b70-inference-cookbook/blob/966c593a8b375c4df5173d8d07b6be4db7835fdb/docs/qwen38-27/QWEN38-VLLM-XPU.md#prefix-on-agentic-2026-08-19-run-43).

A local experiment should hold the target, KV dtype, effort, sampling, concurrency, and context fixed. Compare pass counts, retries, wall-clock completion time, decode, first-token latency, acceptance by draft position, and peak VRAM. Run harder repository tasks as well as the current suite. Keep the overlay optional until that evidence exists.

MTP depth 1, 2, and 4 is a smaller experiment if the real coding workload rejects later draft positions. There is no locally measured optimal depth for that workload. Sweep only depth, after choosing whether to evaluate the draft overlay; do not change both together.

## New engine versions change the maintenance choice

The old statement that Intel does not list Qwen3.8 is stale. Intel's [README at 2ac6a6f6, 2026-09-07](https://github.com/intel/llm-scaler/blob/2ac6a6f68f58a7789e6f3652fe5d083047457339/vllm/README.md) lists Qwen3.8-27B and its FP8 variant. The MTP section still names Qwen3.6 and Gemma models as verified, so the exact GPTQ checkpoint plus preserved BF16 MTP path remains unverified here. Intel's [0.26.0-b1 release, September 2](https://github.com/intel/llm-scaler/releases/tag/vllm-0.26.0-b1) claims better Qwen first-token latency, Qwen accuracy fixes, and faster FP8 KV. It gives no before/after numbers for this server's combination.

Upstream vLLM [0.28.0, August 26](https://github.com/vllm-project/vllm/releases/tag/v0.28.0) publishes an XPU image and describes reduced CPU/GPU synchronization. Those changes are relevant to investigating the busy engine thread, but their impact on this workload is unknown. Its named B70 Mamba SSU tuning is not evidence of faster Qwen GDN. The release changes the default prefill batch size to 16,384; preserve this repository's explicit 8,192 during a version comparison.

The mixed speculative/non-speculative GDN issue has an upstream fix. [XPU kernels 0.1.14, August 31](https://github.com/vllm-project/vllm-xpu-kernels/releases/tag/v0.1.14) describes the mixed-batch and convolution-state fixes. [Issue 510](https://github.com/vllm-project/vllm-xpu-kernels/issues/510) was closed September 2 after the paired kernel and vLLM changes landed. This is a reason to evaluate a supported engine/kernel pair for reduced patch maintenance, especially before enabling multiple in-flight requests.

Do not assume `v0.28.0` contains that kernel release. Its [pinned XPU requirements](https://github.com/vllm-project/vllm/blob/v0.28.0/requirements/xpu.txt) name `vllm_xpu_kernels==0.1.13.2`. Inspect the candidate image's actual packages and source before choosing it. Current [XPU installation guidance](https://docs.vllm.ai/en/latest/getting_started/installation/gpu/#intel-xpu) recommends compute runtime 26.18 or newer from kernels 0.1.10 onward. The recorded host runtime is 26.05; first identify the userspace runtime actually loaded inside the image. A host driver change requires Chris's approval and should be a separate experiment.

For a server that needs little maintenance, an upgrade candidate must meet these conditions before becoming the default:

- Record the immutable image digest, vLLM commit/version, XPU kernel version, PyTorch version, model revision, and required runtime versions.
- Audit every vendored patch against that image. Remove a patch only when its behavior exists upstream and the relevant check passes. Do not blindly apply old source rewrites to a new release.
- Reproduce tool calling, reasoning preservation, vision, and cold/warm long-context requests at the same settings. Pass the current suite and a repeated set of harder coding tasks.
- Measure total task time, first-token latency, decode, acceptance, memory, and failures against the current digest. Keep the current digest and profile available for rollback.
- If concurrency is wanted, separately verify staggered prefill plus speculative decode. A single-user agent can still issue overlapping requests, but concurrency is not automatically beneficial on one card.

## Quality claims that remain unproven

The existing report's GGUF Q4-versus-BF16 results do not establish parity for this exact GPTQ artifact, quantization exclusions, and XPU kernels. The draft-overlay author also explicitly leaves target GPTQ quality against a BF16 teacher untested. There is no source-backed promise here that a different quantization, engine, or reduced reasoning effort improves coding quality.

The useful decision metric is successful repository tasks per unit of wall-clock time, with first-attempt success and regressions visible. The current eight-capability suite can detect broken integrations; it cannot reliably rank close quality differences. Keep engine tuning behind the client correctness checks and a more demanding task baseline.
