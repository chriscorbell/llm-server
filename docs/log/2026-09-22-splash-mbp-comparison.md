# 2026-09-22 Inco Splash on the MacBook versus vLLM on the B70

Status: concluded
Profile: ad hoc (mbp), `a-int4draft` (server, unchanged)
Author: agent thread on mbp

## Hypothesis

Inco Splash on the M5 Pro MacBook should decode Qwen3.8-27B at roughly the 74 tok/s Inco reports for a 48 GB M5 Pro with medium reasoning, close to the server's 67.9 to 87.1 tok/s, but prefill should be several times slower than the B70 because Inco reports 363 tok/s at 32K.

## Configuration

Nothing on the server changed. The MacBook gained a second, independent engine.

MacBook: `mbp`, Apple M5 Pro, 48 GB unified memory, macOS 26.6.2, AC power.

```
brew install incoai/tap/splash          # Splash 1.0.2, bottle arm64_tahoe
splash serve --model incoai/Qwen3.8-27B-Splash --no-webui   # 127.0.0.1:8000, auto memory and context
```

`incoai/Qwen3.8-27B-Splash` is Inco's own 4-bit package of the original Qwen3.8-27B with a DFlash 2 draft model. It is not the kernelogic abliterated checkpoint the server runs; see the server's September 13 comparison for how little that changed speed.

Both engines receive the same benchmark matrix, `scripts/bench-compare.sh`, at concurrency 1, with the fixed corpus `eval/results/2026-09-11-tuning/corpus.txt`:

```
scripts/bench-compare.sh vllm-b70 http://100.103.136.98:8000 qwen38 --presence-penalty 0 --off-effort none
scripts/bench-compare.sh splash-mbp http://127.0.0.1:8000 incoai/Qwen3.8-27B-Splash --key none --presence-penalty 0 --off-effort none
```

The matrix is three repetitions of warm 384-token generation at about 4K input (code with thinking off, code at xhigh, prose summary with thinking off), the same code request at about 32K input, then two cold prefill repetitions at about 8K and 32K with 32 generated tokens. Each row discards one warm-up request first.

Raw results: `eval/results/2026-09-22-splash-mbp/`.

Baseline for comparison: [uncensored GPTQ deployment](2026-09-13-uncensored-gptq.md), re-measured today with the same matrix.

## Measurements

All rows are concurrency 1 with identical request bodies on both engines. Decode is the median of three repetitions, excluding time to first token. Speeds from the server are measured from mbp over Tailscale. Both engines report the same prompt token count for each identical request.

| Test | B70, vLLM | M5 Pro, Splash | Mac as share of server |
|---|---|---|---|
| Warm code decode, thinking off, 4,174 input, 384 output | 91.3 tok/s | 62.6 tok/s | 69% |
| Same request, sustained 30 repetitions, heavy thermal pressure | not run | 58.3 tok/s (54.6 to 64.2) | 64% |
| Warm code decode, xhigh, 4,214 input, 384 output (all reasoning) | 68.9 tok/s | 51.9 tok/s | 75% |
| Warm prose summary decode, thinking off, 4,012 input | 64.3 tok/s (147 output) | 35.7 tok/s (116 output) | 56% |
| Warm code decode, thinking off, 32,567 input, 384 output | 81.6 tok/s | 58.8 tok/s | 72% |
| Inco-style: code, medium reasoning, 651 input, 1,024 output | 90.3 tok/s | 55.8 tok/s | 62% |
| Cached TTFT, about 4.2K input | 1.340 s (1,664 cached) | 0.217 s (4,160 cached) | 6.2 times faster |
| Cached TTFT, 32,567 input | 2.388 s (29,952 cached) | 0.271 s (32,544 cached) | 8.8 times faster |
| Cold TTFT, 8,090 input | 4.297 s | 21.502 s | 5.0 times slower |
| Cold TTFT, 32,431 input | 21.224 s | 101.683 s | 4.8 times slower |
| Effective cold prefill, 8K / 32K | 1,883 / 1,528 tok/s | 376 / 319 tok/s | 20% / 21% |
| Draft acceptance, 4K code, thinking off | 72.8% (MTP4) | 61.9% (DFlash 2) | not comparable |
| Memory peak | 30.263 GiB VRAM, September 13 sample | 25.0 GiB (`splash_memory_peak_bytes` 26,860,650,496) after the 32K rows | |

Acceptance is accepted over drafted tokens on both engines, but MTP4 and DFlash draft different block sizes, so the percentages do not rank the drafters. Cold rows generate only 32 tokens; their decode figures are not used.

Thermal behaviour on the Mac, all at AC power, `powermode 0` (automatic):

- During the first code-xhigh row: pressure Nominal, GPU 100% active at 1,438 MHz, 34.05 W.
- At the end of the first pass, after the 32K cold row: pressure Heavy.
- A repeat of the 4K thinking-off code row, 30 s after pressure returned to Nominal, gave 54.7 tok/s against the first pass's 62.6, with byte-identical request bodies, identical output text and identical draft counts (311 of 511 accepted). The whole repeat ran at Nominal, so the OS pressure level alone does not predict speed.
- A cold 8K repeat gave 24.052 s TTFT against 21.502 s in the first pass.
- The 30-repetition sustained run spent all 41 samples at Heavy, with GPU 1,462 to 1,599 MHz (median 1,564) and 21.3 to 28.8 W (median 26.4 W). Decode fluctuated between 54.6 and 64.2 tok/s with no steady downward trend.

## What happened

Installation and first start took about four minutes: 2 min 28 s to download 79 files, then 11 s from `Loading` to `Ready`. With no flags Splash chose a 256K context and a 38,321,848,320-byte Metal memory limit, and printed `Kernel policy for GPU family 10 with 16 cores.`

Two request-contract differences forced benchmark changes:

- Splash rejects any nonzero `presence_penalty`, which `scripts/bench.py` sends as 1.5 in thinking-off mode:

  ```
  {"error":{"message":"the requested logits or output transformation is not supported","type":"invalid_request_error","code":"invalid_request_error"}}
  ```

  `presence_penalty: 0.0`, `top_k`, `min_p`, `repetition_penalty: 1.0` and `seed` are accepted.
- Splash ignores `chat_template_kwargs.enable_thinking: false` and still reasons. Only `reasoning_effort: "none"` turns reasoning off. Its default effort matches xhigh: the same seeded prompt produced 56 reasoning tokens with no effort and with xhigh, 36 with low, and 0 with none. vLLM accepts `"none"` too and also returns no reasoning.

`scripts/bench.py` gained `--presence-penalty` and `--off-effort none`, both off by default so earlier request hashes are unchanged, and now reads Splash's `splash_drafted_tokens_total` and `splash_accepted_draft_tokens_total` as the acceptance counters. Both machines ran the matrix with `--presence-penalty 0 --off-effort none`, so every request body except `model` is identical between the two engines. A first server pass with the old 1.5 penalty was stopped after one row and discarded.

The server's own numbers today match its September 13 baseline: 91.3 tok/s versus 87.1 for warm thinking-off code at about 4.2K input, and 68.9 versus 67.9 at xhigh, with this entry's zero presence penalty rather than 1.5.

Inco reports 74 tok/s at short context with medium reasoning on a 48 GB M5 Pro. The closest row here, medium reasoning at 651 input tokens and 1,024 output, measured 55.8 tok/s. The prompts differ (Inco used SPEED-Bench coding tasks), Inco does not state its GPU core count or power mode, and this Mac has a 16-core GPU in automatic power mode, so the gap is not explained by this entry.

## Outcome

Hypothesis partly refuted. Splash works on this MacBook with no configuration, but decode is 56 to 75% of the B70 server at every tested length and effort, not close to it. Prefill is about 5 times slower, as predicted, making a cold 32K prompt take 102 s against 21 s. Splash wins cached TTFT by 6 to 9 times because it reused all but 14 to 23 prompt tokens, while vLLM reused only 1,664 of 4,174 and 29,952 of 32,567. For an agent loop that stays in cache, each Mac turn starts about 1 to 2 s sooner, but it then generates about 30% slower.

The Mac also lost up to 13% decode between identical runs as it heated up, and sustained load settles near 58 tok/s. Quality was not compared: the engines run different 4-bit checkpoints of Qwen3.8-27B.

## Consequences

- Splash 1.0.2 is installed on mbp by Homebrew. The 16 GB model package is in `~/.cache/huggingface/hub/models--incoai--Qwen3.8-27B-Splash`, linked from `~/Library/Application Support/Splash/models/incoai/Qwen3.8-27B-Splash`. Splash revision `9d27070b71f7142c6b6025f03ac011d70a73cb48`. It was started by hand for this entry and is not a service or a client provider.
- `scripts/bench.py` gained `--presence-penalty` and `--off-effort` and reads Splash's acceptance counters. `scripts/bench-compare.sh` runs this matrix against any endpoint.
- Nothing on the server changed. The server remains the faster choice for everything except warm-cache time to first token.
- Finding added to `STATUS.md`.
- Later the same day, Chris decided the speed did not justify keeping it. Splash was stopped, uninstalled with `brew uninstall splash` and `brew untap incoai/tap`, and its 16 GB model cache and `~/Library/Application Support/Splash` were deleted. The benchmark tooling and results remain.
