# Status

Last updated: 2026-09-07. Rewrite the affected lines whenever reality changes. This file describes the present, never the past.

## Current state

Profile A is running and healthy on `vllm`, serving Qwen3.8-27B with vision, tool calling and thinking at 96K context. Reachable at `http://100.103.136.98:8000/v1` with the API key in `compose/.env` on the server.

The task suite passes eight of eight capabilities: seven coding tasks through opencode, and vision through the API. See the [baseline](docs/log/2026-09-07-task-suite-baseline.md).

Next action: map decode speed against context length, and settle the prefix caching question with a multi-turn prompt.

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

- **BF16 KV cannot reach 128K on this card.** vLLM's own estimate is 109,824 tokens at 0.96 utilization, and the running configuration uses 98,304. The real cost is 76 KiB per token rather than the 64 KiB the layer arithmetic predicts, because speculative decoding buffers and the Gated DeltaNet recurrent state also come out of that budget. [first boot](docs/log/2026-09-07-profile-a-first-boot.md)
- **FP8 KV costs prefill and buys capacity. Decode is a wash.** Repeated across four prompt sizes, decode differences sit inside run-to-run spread, but FP8 prefills 15 to 27% slower, which worsens the dominant cost of long context. It holds 181,484 KV tokens against 103,326, so it is the only route past a 96K window. An earlier claim that FP8 is simply slower was drawn from a single noisy pair and is withdrawn. [FP8 KV at long context](docs/log/2026-09-07-fp8-kv-at-long-context.md)
- **Omitting `top_k` costs real throughput.** Adding Qwen's recommended `top_k: 20` lifted draft acceptance from 43% to 53% and decode from 42 to 52 tok/s. Any client that does not send it is leaving speed on the table. [decode speed](docs/log/2026-09-07-decode-speed-and-mtp-acceptance.md)
- **oneCCL needs `/dev/dri` bind mounted, not just device mapped.** Without it the engine dies at startup with `opendir failed: could not open device directory`, even on a single GPU. [first boot](docs/log/2026-09-07-profile-a-first-boot.md)
- **Decode speed is set by how predictable the output is, not the prompt.** Free prose gives 44.8 tok/s at 40% draft acceptance, writing new code gives 56.3 at 56%, and reproducing a file verbatim gives 85.2 at 100%. Swapping the prompt between code, prose and nonsense moves it by about 2 tok/s. [what drives decode speed](docs/log/2026-09-07-what-actually-drives-decode-speed.md)
- **Plan around 56 tok/s.** That is what code generation gives, and the task suite running real agentic work measured 57.7 tok/s with 66 to 69% acceptance and an 85% prefix cache hit rate. The published 83.7 figure corresponds to maximally predictable output, which this machine also reproduces at 85.2. It is not underperforming. [what drives decode speed](docs/log/2026-09-07-what-actually-drives-decode-speed.md)
- **Long context costs time to first token, not decode.** Decode falls gently with context: 42.8 tok/s at 512 prompt tokens, 37.2 at 32K, 28.4 at 90K, with acceptance flat near 40%. That tracks memory bandwidth. Time to first token is the real cost, reaching 82 seconds at 90K. The earlier claim of 18 tok/s at 28K was an artifact of an engine counter that includes prefill time. [decode versus context](docs/log/2026-09-07-decode-versus-context.md)
- **Prefix caching is the main defence against long context.** At 32K a cached prefix cuts time to first token from 19.5 seconds to 1.1, and the task suite sustained an 85% hit rate. Protecting that hit rate matters more than any decode tuning. [decode versus context](docs/log/2026-09-07-decode-versus-context.md)
- **Decode runs about 30% under the bandwidth ceiling, and one CPU thread is pegged.** The vLLM engine core loop holds 99.5% of one core while the GPU stays at its 2800 MHz boost clock. That single-threaded loop is normal for vLLM, but on this XPU stack it may be the limiter. [decode versus context](docs/log/2026-09-07-decode-versus-context.md)
- **opencode 1.18.27 cannot send images to this server.** It attaches files with mime `text/plain`, so the model receives a text file and correctly says it cannot see an image. Vision itself works: score it with `eval/vision_check.py`, which sends a proper image part. Also note `--file` is a greedy option, so the message must come before `--file=<path>`. [task suite](docs/log/2026-09-07-task-suite-baseline.md)
- **This build returns thinking in `message.reasoning`.** Not `message.reasoning_content`. A client reading only the older field sees empty reasoning and a correct answer. [first boot](docs/log/2026-09-07-profile-a-first-boot.md)

## Configuration in force

Defined in `compose/.env` on the server, template in `compose/.env.example`. The decisions behind these values:

- **GPTQ INT4, group size 128, symmetric, with the Gated DeltaNet projections and the fifteen MTP tensors kept in BF16.** Xe2 XMX is integer-first and has no native FP8, so 4-bit integer weights are both the fastest and, on published evals of this model, not measurably worse than BF16. See `docs/research/2026-09-07-engines-on-battlemage.md`.
- **Vision on.** Achieved by omitting `--language-model-only`. Costs about 0.92 GiB for the unquantized F16 vision tower.
- **`--max-num-seqs 1`.** Single-user server. This holds MTP acceptance near 95%, where concurrency drops it to 43 to 56%, and it sidesteps the `gdn_attention` crash on mixed speculative and non-speculative batches, so `patch_gdn_mixed_split_v5.py` stays unapplied.
- **MTP with 4 speculative tokens.** Roughly 2.5x decode throughput at 95% acceptance on published single-stream measurements.
- **Thinking on by default at `xhigh` reasoning effort.**
- **`UR_L0_ENABLE_RELAXED_ALLOCATION_LIMITS=1`.** Level Zero rejects single allocations above 4 GiB by default and the KV cache exceeds that.
- **Bound to the Tailscale address only**, with a static API key.

## Open questions

Ideas not yet tested. Move one into `docs/log/` the moment you test it.

- Is the pegged engine thread the limiter? Decode sits about 30% below the bandwidth ceiling. Worth testing a `performance` governor and CPU pinning before concluding anything.
- The cookbook's optional INT4 draft overlay claims decode from 83.7 to 112.7 tok/s. Untested here, and it changes draft logits, so it needs the task suite run alongside it.
- Does prefix caching help or hurt? Three repetitions was too noisy to tell and the comparison came out both ways. Needs a deterministic harness and a realistic multi-turn prompt, which is the case prefix caching exists for.
- What does `xhigh` reasoning effort buy over `medium` on the task suite, and at what wall-clock cost?
- Is FP8 KV distinguishable from BF16 KV on the task suite? Only worth answering if you want context past 96K, now that FP8 KV is known to be slower.
- The optional INT4 draft overlay raises decode from 83.7 to 112.7 tok/s but changes draft logits. Off, and staying off until the baseline is characterized.
- Intel's `llm-scaler-vllm` image would remove the need for vendored patches once it lists Qwen3.8. Re-check at each release.

## Known hazards on this hardware

- The `xe` driver can reset a compute engine under sustained load and wedge the context. Capture `scripts/gpu-health.sh` output before restarting anything.
- oneDNN's 2026 release notes carry a known issue that FP8 matmul may sporadically produce incorrect results on Arc B-series. This is one reason the plan avoids FP8 weights.
- Re-packed or locally converted copies of the model can drop the three image-processor JSON files, after which vLLM dies at startup with `Can't load image processor for '/model'`. `scripts/setup-server.sh` checks for them.
