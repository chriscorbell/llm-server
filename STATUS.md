# Status

Last updated: 2026-09-07. Rewrite the affected lines whenever reality changes. This file describes the present, never the past.

## Current state

Nothing is serving yet. The repository has been scaffolded and the plan agreed. Next action is Experiment 1: bring up Profile A and find the largest context that BF16 KV actually fits.

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

None yet. Each Finding below cites the Experiment that produced it. Do not add a Finding without one.

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

- Does BF16 KV fit at 131,072 tokens? The arithmetic is tight and probably says no. Weights and vision tower take 19.1 GiB of 31.9 GiB usable. BF16 KV costs 64 KiB per token, so 131,072 tokens is 8.0 GiB, leaving 4.8 GiB for activations, XPU graphs and speculative buffers. Published runs on this card at FP8 KV and the same context left only about 870 MiB free, which suggests overhead near 7.9 GiB and therefore a BF16 ceiling closer to 64K or 96K. Measure it, do not assume it. This is Experiment 1.
- Is FP8 KV distinguishable from BF16 KV on the task suite? If not, spend the saving on context up to 262,144.
- What does `xhigh` reasoning effort buy over `medium` on the task suite, and at what wall-clock cost?
- Does prefix caching help or hurt here? Upstream measured 91% hit rate single-stream but no decode gain, and the recipe disables it. It is enabled in this repository's compose because an agent client re-sends a growing conversation, which is the case prefix caching exists for.
- The optional INT4 draft overlay raises decode from 83.7 to 112.7 tok/s but changes draft logits. Off, and staying off until the baseline is characterized.
- Intel's `llm-scaler-vllm` image would remove the need for vendored patches once it lists Qwen3.8. Re-check at each release.

## Known hazards on this hardware

- The `xe` driver can reset a compute engine under sustained load and wedge the context. Capture `scripts/gpu-health.sh` output before restarting anything.
- oneDNN's 2026 release notes carry a known issue that FP8 matmul may sporadically produce incorrect results on Arc B-series. This is one reason the plan avoids FP8 weights.
- Re-packed or locally converted copies of the model can drop the three image-processor JSON files, after which vLLM dies at startup with `Can't load image processor for '/model'`. `scripts/setup-server.sh` checks for them.
