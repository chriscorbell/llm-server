# Status

Last updated: 2026-09-07. Rewrite the affected lines whenever reality changes. This file describes the present, never the past.

## Current state

Profile A is running and healthy on `vllm`, serving Qwen3.8-27B with vision, tool calling and thinking at 96K context. Reachable at `http://100.103.136.98:8000/v1` with the API key in `compose/.env` on the server.

Pi 0.85.1 on mbp passes all eight tasks, including image input. The previous OpenCode/API baseline also passed eight of eight capabilities. [Pi validation](docs/log/2026-09-07-pi-client-validation.md), [earlier baseline](docs/log/2026-09-07-task-suite-baseline.md)

The repaired recovery watchdog is enabled and active as of 2026-09-08 01:13 UTC. It requires three failed health checks and a GPU fault, saves diagnostics, allows ten minutes for initialization and stops after two recovery attempts per incident. Five offline recovery checks passed. Recovery from a new physical GPU failure has not yet been observed. [repair and deployment](docs/log/2026-09-07-watchdog-repair.md)

Pi 0.85.1 is configured on mbp with xhigh thinking, explicit Qwen sampling, a 98,304-token window and automatic compaction above 57,344 estimated tokens. It preserves reasoning through tool calls and remembered an early requirement after automatic compaction at 62,578 tokens. Run `pi` from a project directory, or `pi -c` to continue. [launch guide](clients/pi/README.md), [validation](docs/log/2026-09-07-pi-client-validation.md)

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

Historical `scripts/bench.py` context labels used a character-based estimate. Their timings are measured, but those input lengths and derived prefill rates are approximate. New benchmark output records `usage.prompt_tokens`. [measurement correction](docs/log/2026-09-07-ttft-actual-token-counts.md)

- **The 16-bit KV profile cannot reach 128K on this card.** vLLM's own estimate is 109,824 tokens at 0.96 utilization, and the running configuration uses 98,304. The real cost is 76 KiB per token rather than the 64 KiB the layer arithmetic predicts, because speculative decoding buffers and the Gated DeltaNet recurrent state also come out of that budget. [first boot](docs/log/2026-09-07-profile-a-first-boot.md)
- **FP8 KV costs prefill and buys capacity. Decode is a wash.** Repeated across four prompt sizes, decode differences sit inside run-to-run spread, but FP8 prefills 15 to 27% slower, which worsens the dominant cost of long context. It holds 181,484 KV tokens against 103,326, so it is the only route past a 96K window. An earlier claim that FP8 is simply slower was drawn from a single noisy pair and is withdrawn. [FP8 KV at long context](docs/log/2026-09-07-fp8-kv-at-long-context.md)
- **The running server defaults to Qwen's thinking sampling preset.** Live generation config and startup logs confirm temperature 1.0, top_p 0.95, and top_k 20. An earlier 512-token, concurrency-one experiment associated explicit top_k 20 with higher acceptance and decode, but omission must not be assumed to disable top_k on this instance. Verify the effective request before attributing an effect. [client contract inspection](docs/log/2026-09-07-agent-client-contract.md), [earlier experiment](docs/log/2026-09-07-decode-speed-and-mtp-acceptance.md)
- **A larger prefill chunk buys nothing and costs context.** Doubling `MAX_BATCHED_TOKENS` to 16,384 left prefill identical at 1,402 tok/s at 64K and took 17,205 tokens of KV capacity. Prefill is limited by per-token work, not by how it is grouped. Do not retry this. [prefill chunk size](docs/log/2026-09-07-prefill-chunk-size.md)
- **The `performance` CPU governor changes nothing.** Boost already holds cores at 4.34 GHz under load. Left at schedutil. [governor and pinning](docs/log/2026-09-07-cpu-governor-and-pinning.md)
- **oneCCL needs `/dev/dri` bind mounted, not just device mapped.** Without it the engine dies at startup with `opendir failed: could not open device directory`, even on a single GPU. [first boot](docs/log/2026-09-07-profile-a-first-boot.md)
- **Decode speed is set by how predictable the output is, not the prompt.** Free prose gives 44.8 tok/s at 40% draft acceptance, writing new code gives 56.3 at 56%, and reproducing a file verbatim gives 85.2 at 100%. Swapping the prompt between code, prose and nonsense moves it by about 2 tok/s. [what drives decode speed](docs/log/2026-09-07-what-actually-drives-decode-speed.md)
- **Plan around 56 tok/s.** That is what code generation gives, and the task suite running real agentic work measured 57.7 tok/s with 66 to 69% acceptance and an 85% prefix cache hit rate. The published 83.7 figure corresponds to maximally predictable output, which this machine also reproduces at 85.2. It is not underperforming. [what drives decode speed](docs/log/2026-09-07-what-actually-drives-decode-speed.md)
- **Long context costs time to first token, not decode.** Decode falls gently with context: 42.8 tok/s at 512 prompt tokens, 37.2 at 32K, 28.4 at 90K, with acceptance flat near 40%. That tracks memory bandwidth. Time to first token is the real cost, reaching 82 seconds at 90K. The earlier claim of 18 tok/s at 28K was an artifact of an engine counter that includes prefill time. [decode versus context](docs/log/2026-09-07-decode-versus-context.md)
- **Prefix caching is the main defence against long context.** At 33.4K actual prompt tokens, thinking on, concurrency 1 and 128 generated tokens, cached TTFT is 0.811 seconds versus 19.211 cold (medians of three repetitions). Pi's cached tool follow-ups also started in 0.9 to 1.0 seconds at about 23K input tokens. Compaction and changed reasoning settings can require a fresh prefill. [current benchmark](docs/log/2026-09-07-ttft-actual-token-counts.md), [Pi check](docs/log/2026-09-07-pi-client-validation.md)
- **MTP depth 3 beats depth 4 on this workload.** At six repetitions per size with thinking on, decode medians were 48.5 against 45.3 tok/s at 512 prompt tokens, and inside noise at 8K and 32K. Per-position acceptance for the first three drafts did not move (0.716, 0.494, 0.358), so the fourth draft was pure overhead. KV capacity rose from 103,326 to 105,640 tokens. Depth 2 is untested. [MTP depth 3](docs/log/2026-09-07-mtp-depth-3.md)
- **Decode runs about 30% under the bandwidth ceiling, and one CPU thread is pegged.** The vLLM engine core loop holds 99.5% of one core while the GPU stays at its 2800 MHz boost clock. That single-threaded loop is normal for vLLM, but on this XPU stack it may be the limiter. [decode versus context](docs/log/2026-09-07-decode-versus-context.md)
- **opencode 1.18.27 cannot send images to this server.** It attaches files with mime `text/plain`, so the model receives a text file and correctly says it cannot see an image. Vision itself works: score it with `eval/vision_check.py`, which sends a proper image part. Also note `--file` is a greedy option, so the message must come before `--file=<path>`. [task suite](docs/log/2026-09-07-task-suite-baseline.md)
- **This build returns thinking in `message.reasoning`.** Not `message.reasoning_content`. A client reading only the older field sees empty reasoning and a correct answer. [first boot](docs/log/2026-09-07-profile-a-first-boot.md)
- **Pi 0.85.1 works with the existing server.** All eight coding/image tasks passed. A separate ten-request check confirmed sampling, reasoning replay, medium/xhigh effort and requirement retention after automatic compaction. This validates the client contract and small-task behavior, not broad coding quality. [Pi validation](docs/log/2026-09-07-pi-client-validation.md)
- **The watchdog's false-trigger bug is repaired.** The old expression accepted arbitrary text. The installed version rejects unrelated network messages, remembers a single fault through the failure threshold and bounds recovery attempts. Five offline scenarios passed on Linux; the inference container was not restarted during deployment. [repair](docs/log/2026-09-07-watchdog-repair.md), [original evidence](docs/log/2026-09-07-watchdog-false-triggers.md)

Why this stack was chosen at all, including the engines rejected and the reasoning about Xe2 having no native FP8: [hardware survey and stack choice](docs/log/2026-09-07-hardware-survey-and-stack-choice.md).

## Configuration in force

Defined in `compose/.env` on the server, template in `compose/.env.example`. The decisions behind these values:

Verified live: maximum context 98,304 tokens, GPU utilization 0.95, batched tokens 8,192, one sequence, MTP3, prefix caching on, 105,640 KV tokens. The historical `a-bf16kv` profile actually uses `--dtype float16 --kv-cache-dtype auto`; its attention cache follows FP16. The profile name and old log labels are retained for traceability. The example environment now matches the working context and utilization values. [inspection](docs/log/2026-09-07-agent-client-contract.md)

- **GPTQ INT4, group size 128, symmetric, with selected Gated DeltaNet projections and the fifteen MTP tensors stored in BF16.** This is the working memory and speed choice. Published quality results for other 4-bit artifacts do not establish BF16 parity for this exact GPTQ checkpoint and XPU runtime. [upstream quality audit](docs/research/2026-09-07-agentic-coding-upstream.md)
- **Vision on.** Achieved by omitting `--language-model-only`. Costs about 0.92 GiB for the unquantized F16 vision tower.
- **`--max-num-seqs 1`.** Single-user server. This sidesteps the `gdn_attention` crash on mixed speculative and non-speculative batches, so `patch_gdn_mixed_split_v5.py` stays unapplied. Local coding-suite acceptance was 66 to 69%; output predictability matters, and a single sequence does not guarantee 95% acceptance.
- **MTP with 3 speculative tokens.** Depth 4's fourth draft token was accepted 23 to 25% of the time and cost a step of draft and verification work. Depth 3 measured equal or faster decode at 512, 8K and 32K context and holds 2,314 more KV tokens. [MTP depth 3](docs/log/2026-09-07-mtp-depth-3.md)
- **Thinking on by default at `xhigh` reasoning effort.**
- **`UR_L0_ENABLE_RELAXED_ALLOCATION_LIMITS=1`.** Level Zero rejects single allocations above 4 GiB by default and the KV cache exceeds that.
- **Bound to the Tailscale address only**, with a static API key.

## Open questions

Ideas not yet tested. Move one into `docs/log/` the moment you test it.

- Is the pegged engine thread the limiter? Decode sits about 30% below the bandwidth ceiling. The `performance` governor changes nothing, because boost already holds cores at 4.34 GHz under load. CPU pinning is set up and verified working but was never measured. [governor and pinning](docs/log/2026-09-07-cpu-governor-and-pinning.md)
- How does this setup score on repeated, representative repository tasks beyond the seven small coding fixtures? The Pi compaction check preserves a simple requirement, but complex edits across compaction remain unmeasured. `scripts/bench.py` now records actual API prompt-token counts.
- What does `xhigh` reasoning effort buy over `medium` on the task suite, and at what wall-clock cost?
- Is FP8 KV distinguishable from BF16 KV on the task suite? Only worth answering if you want context past 96K, now that FP8 KV is known to be slower.
- Does the optional INT4 draft overlay improve total coding-task time without lowering pass rate here? Another B70's cached concurrency-one measurements improved decode by about 21 to 39% at 8K/16K and 25% at 64K, generating 128 tokens. Those are upstream measurements; the overlay remains off locally. [sources and conditions](docs/research/2026-09-07-agentic-coding-upstream.md)
- Which pinned engine and XPU-kernel pair reduces patch maintenance without a quality or latency regression? Intel now lists Qwen3.8, but this exact GPTQ+MTP path is unverified. vLLM 0.28.0 pins XPU kernels 0.1.13.2; the mixed-GDN fix is documented in 0.1.14. A version bump alone does not establish compatibility. [upstream audit](docs/research/2026-09-07-agentic-coding-upstream.md)

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
