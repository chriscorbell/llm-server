# Status

Last updated: 2026-09-11. Rewrite the affected lines whenever reality changes. This file describes the present, never the past.

## Current state

The September 11 optimization campaign is complete. The server is healthy on the committed MTP4 default, original pinned engine and unrestricted CPUs. Identical requests confirm a 6.6% warm code-decode gain at 8,240 input tokens, 768 generated tokens, concurrency 1 and thinking off; reasoning throughput is unchanged within the observed spread. [Exact-request confirmation](docs/log/2026-09-11-mtp-fixed-prompt-confirmation.md). The 0.29.0 image and one-CCX CPU pin did not provide material speed gains and were not retained. Pi remains at xhigh by default; `pi --thinking medium` is documented for small edits after two 8/8 task runs at each effort. [Effort comparison](docs/log/2026-09-11-pi-reasoning-effort.md).

Profile `a-int4draft` serves Qwen3.8-27B with the INT4 draft overlay, MTP4, vision, tool calling and thinking at 98,304 context. The final container started on September 11 at 14:38:02 UTC and has zero Docker restarts. It has 109,067 KV tokens and empty CPU affinity metadata, with all 64 CPUs available. Final smoke checks pass; the fresh xhigh suite passes 8/8. The API is at `http://100.103.136.98:8000/v1`, with its key in the server's private `compose/.env`. The unquantized-draft rollback profile is `a-bf16kv` with `MTP_TOKENS=3`.

The original image remains pinned at `sha256:f01e24f6c7ff01f1e0662234255a1372297d1dbd89d003cf13c8fad3eab1ba4f`. The September 11 campaign preserves the 98,304-token limit, utilization 0.95, 8,192 batched tokens and one sequence. XPU graphs were already enabled before tuning. `compose/tuning.env` records the validated defaults; the running container uses them without shell overrides.

Pi 0.85.1 on mbp passes all eight tasks, including image input. The previous OpenCode/API baseline also passed eight of eight capabilities. [Pi validation](docs/log/2026-09-07-pi-client-validation.md), [earlier baseline](docs/log/2026-09-07-task-suite-baseline.md)

The repaired recovery watchdog is enabled and active, rechecked September 11 after the experiments. It requires three failed health checks and a GPU fault, saves diagnostics, allows ten minutes for initialization and stops after two recovery attempts per incident. Five offline recovery checks passed. Recovery from a new physical GPU failure has not yet been observed. [repair and deployment](docs/log/2026-09-07-watchdog-repair.md)

Pi 0.85.1 is configured on mbp with xhigh thinking, explicit Qwen sampling, a 98,304-token window and automatic compaction above 57,344 estimated tokens. It preserves reasoning through tool calls and remembered an early requirement after automatic compaction at 62,578 tokens. Run `pi` from a project directory, or `pi -c` to continue. The `llm-server` extension in `clients/pi/extensions/` shows time to first token and the prefix-cache share per request, warms the cache after compaction and thinking changes, diagnoses server outages, and adds `/vllm`, `/warm` and `/handoff`. Its `web_search` and `web_fetch` tools use a SearXNG container on `vllm` (port 8080, Tailscale only, no API keys), added 2026-09-08 and pinned by digest in `compose/.env.example`. [SearXNG and web tools](docs/log/2026-09-08-searxng-web-tools.md) Every profile now passes `--enable-prompt-tokens-details`, so `usage.prompt_tokens_details.cached_tokens` is reported; cache blocks are coarse, and a repeated 3,519-token prompt reported 2,496 cached while a 619-token one reported 0. [launch guide](clients/pi/README.md), [validation](docs/log/2026-09-07-pi-client-validation.md), [extension and warm-up](docs/log/2026-09-07-pi-quality-of-life.md)

| | |
|---|---|
| Server | `vllm`, reachable as `ssh vllm` |
| GPU | Intel Arc Pro B70, Battlemage G31, PCI `4c:00.0`, device id `0xe223` |
| Usable VRAM | 31.9 GiB (`0x7f9000000` after stolen memory) |
| Driver | in-tree `xe`, kernel 7.0.0-31-generic, Ubuntu 26.04.1 |
| Userspace | Level Zero and OpenCL runtime 26.05.37020.3 from the Ubuntu archive |
| Host | Threadripper 3970X, 32 cores, 60 GiB usable RAM, 1.7 TB free on NVMe |
| Network | two Intel I211 gigabit ports, Tailscale at `100.103.136.98`, LAN `10.0.0.10` |
| Engine | vLLM XPU, image pinned by digest in `compose/.env.example` |
| Model | `SergiioB/Qwen3.8-27B-GPTQ-Int4-sym-G128-MTP-BF16` at revision `9d189a60` |

## Findings

Each Finding cites the Experiment that produced it. Do not add a Finding without one.

- **Medium effort cuts completed-task time on the small fixture suite.** At concurrency 1, with per-task maximum prompts from 7,138 to 12,689 actual tokens, two runs per effort averaged 139.4 s for medium versus 211.15 s for xhigh. Both passed 16/16 task instances. This does not establish parity on difficult repository changes or compaction; xhigh remains the default, with `pi --thinking medium` documented for routine edits. [Effort comparison](docs/log/2026-09-11-pi-reasoning-effort.md)

- **Pinning to `0-3,32-35` does not improve this workload.** Three alternating pairs with six measured warm code repetitions per arm, about 8.3K input, 768 generated tokens, thinking off and concurrency 1 gave 90.3 tok/s unrestricted versus 89.6 pinned. Pair changes were +0.3%, -1.0% and -4.2%. Unrestricted CPUs remain selected. Docker update ignores an empty cpuset, so restore all online CPUs explicitly during live experiments and recreate to restore empty metadata. [CPU affinity](docs/log/2026-09-11-cpu-affinity.md)

- **vLLM 0.29.0 is compatible but provides no material measured speed gain here.** Its default XPU V2 runner executes both INT4 draft conversions and passes 18/18 short checks and 8/8 Pi tasks. At concurrency 1, warm code/tool/reasoning decode overlaps the old image's spread, cached TTFT falls about 30 ms, and cold 32.6K TTFT is 18.550 versus 18.606 s. It still needs four patches and holds 1,435 fewer KV tokens. The original digest remains selected. [Serving comparison](docs/log/2026-09-11-vllm029-serving.md)

- **MTP4 improves code throughput with the INT4 draft.** With all six complete request hashes matching across depths, warm code at exactly 8,240 input tokens and 768 generated tokens measures 90.1 tok/s versus MTP3's 84.5, a 6.6% gain, thinking off and concurrency 1. Xhigh reasoning at 8,282 input tokens is 65.0 versus 65.7 tok/s, inside the observed spread. Earlier 32K/57K code and 8K tool screening also favored MTP4 but used differing session nonces. Cold and cached TTFT are unchanged. Short checks pass 18/18 and corrected Pi tasks 8/8; no broader quality claim is established. [Exact-request confirmation](docs/log/2026-09-11-mtp-fixed-prompt-confirmation.md), [initial depth sweep](docs/log/2026-09-11-int4-mtp-depth.md)

Historical `scripts/bench.py` context labels used a character-based estimate. Their timings are measured, but those input lengths and derived prefill rates are approximate. New benchmark output records `usage.prompt_tokens`. [measurement correction](docs/log/2026-09-07-ttft-actual-token-counts.md)

- **The 16-bit KV profile cannot reach 128K on this card.** vLLM's own estimate is 109,824 tokens at 0.96 utilization, and the running configuration uses 98,304. The real cost is 76 KiB per token rather than the 64 KiB the layer arithmetic predicts, because speculative decoding buffers and the Gated DeltaNet recurrent state also come out of that budget. [first boot](docs/log/2026-09-07-profile-a-first-boot.md)
- **FP8 KV costs prefill and buys capacity. Decode is a wash.** Repeated across four prompt sizes, decode differences sit inside run-to-run spread, but FP8 prefills 15 to 27% slower, which worsens the dominant cost of long context. It holds 181,484 KV tokens against 103,326, so it is the only route past a 96K window. An earlier claim that FP8 is simply slower was drawn from a single noisy pair and is withdrawn. [FP8 KV at long context](docs/log/2026-09-07-fp8-kv-at-long-context.md)
- **The running server defaults to Qwen's thinking sampling preset.** Live generation config and startup logs confirm temperature 1.0, top_p 0.95, and top_k 20. An earlier 512-token, concurrency-one experiment associated explicit top_k 20 with higher acceptance and decode, but omission must not be assumed to disable top_k on this instance. Verify the effective request before attributing an effect. [client contract inspection](docs/log/2026-09-07-agent-client-contract.md), [earlier experiment](docs/log/2026-09-07-decode-speed-and-mtp-acceptance.md)
- **A larger prefill chunk buys nothing and costs context.** Doubling `MAX_BATCHED_TOKENS` to 16,384 left prefill identical at 1,402 tok/s at 64K and took 17,205 tokens of KV capacity. Prefill is limited by per-token work, not by how it is grouped. Do not retry this. [prefill chunk size](docs/log/2026-09-07-prefill-chunk-size.md)
- **The `performance` CPU governor changes nothing.** Boost already holds cores at 4.34 GHz under load. Left at schedutil. [governor and pinning](docs/log/2026-09-07-cpu-governor-and-pinning.md)
- **oneCCL needs `/dev/dri` bind mounted, not just device mapped.** Without it the engine dies at startup with `opendir failed: could not open device directory`, even on a single GPU. [first boot](docs/log/2026-09-07-profile-a-first-boot.md)
- **Decode speed is set by how predictable the output is, not the prompt.** Free prose gives 44.8 tok/s at 40% draft acceptance, writing new code gives 56.3 at 56%, and reproducing a file verbatim gives 85.2 at 100%. Swapping the prompt between code, prose and nonsense moves it by about 2 tok/s. [what drives decode speed](docs/log/2026-09-07-what-actually-drives-decode-speed.md)
- **Long context costs time to first token, not decode.** Decode falls gently with context: 42.8 tok/s at 512 prompt tokens, 37.2 at 32K, 28.4 at 90K, with acceptance flat near 40%. That tracks memory bandwidth. Time to first token is the real cost, reaching 82 seconds at 90K. The earlier claim of 18 tok/s at 28K was an artifact of an engine counter that includes prefill time. [decode versus context](docs/log/2026-09-07-decode-versus-context.md)
- **Prefix caching is the main defence against long context.** At 33.4K actual prompt tokens, thinking on, concurrency 1 and 128 generated tokens, cached TTFT is 0.811 seconds versus 19.211 cold (medians of three repetitions). Pi's cached tool follow-ups also started in 0.9 to 1.0 seconds at about 23K input tokens. Compaction and changed reasoning settings can require a fresh prefill. [current benchmark](docs/log/2026-09-07-ttft-actual-token-counts.md), [Pi check](docs/log/2026-09-07-pi-client-validation.md)
- **The prefix cache works in 832-token blocks and is now reported per request.** With `--enable-prompt-tokens-details`, `usage.prompt_tokens_details.cached_tokens` is populated, and every observed value is a multiple of 832: a repeated 3,519-token prompt reports 2,496 cached, a 619-token one reports 0. Pi shows it as `R` in the footer and the llm-server extension as a cache share. [extension and warm-up](docs/log/2026-09-07-pi-quality-of-life.md)
- **Warming the compacted context while idle removes the cold post-compaction request.** After a manual compaction at 21.8K to 31.3K tokens the next request started in 1.03 s with 29,952 tokens cached, against 11.71 s cold without the warm-up, one run per arm at concurrency 1 and xhigh. Threshold compaction that fires mid-run is unaffected, because the cold request follows before the client can act. [extension and warm-up](docs/log/2026-09-07-pi-quality-of-life.md)
- **The INT4 draft overlay is worth 26 to 31% decode at no measured quality cost.** Six repetitions per size, thinking on, identical prompts: 45.5 to 57.2 tok/s at 512 tokens, 45.6 to 58.5 at 8K, and 46.2 to 59.2 at 32K with a slightly different corpus. Per-position acceptance fell from 0.716, 0.494, 0.358 to 0.679, 0.472, 0.326. The eight-task Pi suite passed 8 of 8 in 202 seconds against 362 at the earlier baseline. Quality parity on hard repository work is unmeasured on both arms. [INT4 draft overlay](docs/log/2026-09-07-int4-draft-overlay.md)
- **MTP depth 3 beat depth 4 with the unquantized draft.** At six repetitions per size with thinking on and concurrency 1, decode medians were 48.5 against 45.3 tok/s at about 625 actual prompt tokens, and inside noise at about 7.6K and 33.4K. Per-position acceptance for the first three drafts barely moved (0.716, 0.494, 0.358), and removing the fourth draft returned KV capacity from 103,326 to 105,640 tokens. This comparison predates the INT4 draft overlay; it does not establish the best depth for the current profile. The later INT4 sweep separately measured depths 2, 3 and 4. [MTP depth 3](docs/log/2026-09-07-mtp-depth-3.md)
- **Decode runs about 30% under the bandwidth ceiling, and one CPU thread is pegged.** The vLLM engine core loop holds 99.5% of one core while the GPU stays at its 2800 MHz boost clock. That single-threaded loop is normal for vLLM, but on this XPU stack it may be the limiter. [decode versus context](docs/log/2026-09-07-decode-versus-context.md)
- **opencode 1.18.27 cannot send images to this server.** It attaches files with mime `text/plain`, so the model receives a text file and correctly says it cannot see an image. Vision itself works: score it with `eval/vision_check.py`, which sends a proper image part. Also note `--file` is a greedy option, so the message must come before `--file=<path>`. [task suite](docs/log/2026-09-07-task-suite-baseline.md)
- **This build returns thinking in `message.reasoning`.** Not `message.reasoning_content`. A client reading only the older field sees empty reasoning and a correct answer. [first boot](docs/log/2026-09-07-profile-a-first-boot.md)
- **Pi 0.85.1 works with the existing server.** All eight coding/image tasks passed. A separate ten-request check confirmed sampling, reasoning replay, medium/xhigh effort and requirement retention after automatic compaction. This validates the client contract and small-task behavior, not broad coding quality. [Pi validation](docs/log/2026-09-07-pi-client-validation.md)
- **The watchdog's false-trigger bug is repaired.** The old expression accepted arbitrary text. The installed version rejects unrelated network messages, remembers a single fault through the failure threshold and bounds recovery attempts. Five offline scenarios passed on Linux; the inference container was not restarted during deployment. [repair](docs/log/2026-09-07-watchdog-repair.md), [original evidence](docs/log/2026-09-07-watchdog-false-triggers.md)

Why this stack was chosen at all, including the engines rejected and the reasoning about Xe2 having no native FP8: [hardware survey and stack choice](docs/log/2026-09-07-hardware-survey-and-stack-choice.md).

## Configuration in force

Machine-specific values and credentials are in `compose/.env` on the server, template in `compose/.env.example`. `scripts/compose.sh` loads that file followed by the tracked measured defaults in `compose/tuning.env`. Shell environment overrides take precedence for experiments. The decisions behind these values:

Verified live: maximum context 98,304 tokens, GPU utilization 0.95, batched tokens 8,192, one sequence, MTP4, INT4 draft overlay on, prefix caching on, 109,067 KV tokens. The historical `a-bf16kv` profile actually uses `--dtype float16 --kv-cache-dtype auto`; its attention cache follows FP16. The profile name and old log labels are retained for traceability. The example environment now matches the working context and utilization values. [inspection](docs/log/2026-09-07-agent-client-contract.md)

- **GPTQ INT4, group size 128, symmetric, with selected Gated DeltaNet projections and the fifteen MTP tensors stored in BF16.** This is the working memory and speed choice. Published quality results for other 4-bit artifacts do not establish BF16 parity for this exact GPTQ checkpoint and XPU runtime. [upstream quality audit](docs/research/2026-09-07-agentic-coding-upstream.md)
- **Vision on.** Achieved by omitting `--language-model-only`. Costs about 0.92 GiB for the unquantized F16 vision tower.
- **`--max-num-seqs 1`.** Single-user server. This sidesteps the `gdn_attention` crash on mixed speculative and non-speculative batches, so `patch_gdn_mixed_split_v5.py` stays unapplied. Local coding-suite acceptance was 66 to 69%; output predictability matters, and a single sequence does not guarantee 95% acceptance.
- **INT4 draft overlay on, as profile `a-int4draft`.** The draft's LM head copy and its five MTP linears are requantized to INT4 g128 at container start by two vendored, env-gated patches. The target model and its verification head are untouched. Decode 57 to 59 tok/s against 45 to 46 for the BF16 draft on identical prompts at 512 to 32K context, task suite 8 of 8, and 5,869 more KV tokens because the freed BF16 draft weights go to the cache. Single card only; the patches refuse tensor parallelism. [INT4 draft overlay](docs/log/2026-09-07-int4-draft-overlay.md)
- **MTP with 4 speculative tokens for the INT4 draft.** The identical-request comparison gives 90.1 versus 84.5 tok/s for MTP3 at 8,240 input tokens, thinking off, 768 generated and concurrency 1. Reasoning is unchanged within spread. Longer-context screening measured 81.0 tok/s at 32,590 input tokens and 72.3 at 56,909. Cold 32K TTFT is unchanged at about 18.61 s. Use `MTP_TOKENS=3` with the unquantized `a-bf16kv` rollback profile. [Exact-request comparison](docs/log/2026-09-11-mtp-fixed-prompt-confirmation.md), [depth sweep](docs/log/2026-09-11-int4-mtp-depth.md)
- **Thinking on by default at `xhigh` reasoning effort.**
- **`UR_L0_ENABLE_RELAXED_ALLOCATION_LIMITS=1`.** Level Zero rejects single allocations above 4 GiB by default and the KV cache exceeds that.
- **Bound to the Tailscale address only**, with a static API key.

## Open questions

Ideas not yet tested. Move one into `docs/log/` the moment you test it.

- Does INT4 draft depth 5 improve on depth 4 while preserving reasoning throughput and the 98,304-token window? The current sweep stops at depth 4; use identical request hashes and check complete task quality before expanding the depth.
- Would persisting the engine compile cache across container recreation shorten configuration changes? Both image trials compile inside the container; no persistent-cache configuration has been tested. Ordinary container restarts retain their writable layer.

- How does this setup score on repeated, representative repository tasks beyond the seven small coding fixtures? The Pi compaction check preserves a simple requirement, but complex edits across compaction remain unmeasured. `scripts/bench.py` now records actual API prompt-token counts.
- Does the extension's 24 KB tool-output budget omit information needed for harder repository edits? The September 11 eight-task suite passes with the extension loaded, but broad quality under truncation remains unmeasured. [current task results](docs/log/2026-09-11-int4-mtp-depth.md), [extension and warm-up](docs/log/2026-09-07-pi-quality-of-life.md)
- Is FP8 KV distinguishable from BF16 KV on the task suite? Only worth answering if you want context past 96K, now that FP8 KV is known to be slower.
- Is the INT4 draft overlay still a win at 64K to 96K context? Measured only to 32K here. The upstream author saw the gain shrink to 18% at 96K and invert on a single cold 128K turn. [INT4 draft overlay](docs/log/2026-09-07-int4-draft-overlay.md)

## Setup gotchas

These break a fresh install and are handled by `scripts/setup-server.sh`. Recorded because each one cost time. [setup gaps](docs/log/2026-09-07-setup-script-gaps.md)

- Ubuntu 26.04 ships Docker without the Compose plugin. Install `docker-compose-v2` or every command fails with `docker: unknown command: docker compose`.
- The API is published on the Tailscale address only, so `http://127.0.0.1:8000` does not answer even on the server itself. Use the hostname.
- The `huggingface_hub` 1.x package dropped the `[cli]` extra and its entry point is not on `PATH` for a mapped container uid. Download through the Python API, which is what the setup script does.
- The checkpoint ships only `processor_config.json`, not the three image-processor files the upstream cookbook lists. Vision works with just that one.

## Known hazards on this hardware

- The `xe` driver can reset a compute engine under sustained load and wedge the context. Capture `scripts/gpu-health.sh` output before restarting anything.
- oneDNN's 2026 release notes carry a known issue that FP8 matmul may sporadically produce incorrect results on Arc B-series. This is one reason the plan avoids FP8 weights.
- Re-packed or locally converted copies of the model can drop the three image-processor JSON files, after which vLLM dies at startup with `Can't load image processor for '/model'`. `scripts/setup-server.sh` checks for them.
