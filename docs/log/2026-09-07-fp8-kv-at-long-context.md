# 2026-09-07 FP8 KV at long context, and a correction

Status: concluded, corrects a Finding from [the decode speed entry](./2026-09-07-decode-speed-and-mtp-acceptance.md)
Profile: A with `--kv-cache-dtype fp8`, context 98,304
Author: agent thread on mbp

## Hypothesis

FP8 KV halves the bytes each forward pass reads from the cache, and the cache is the only term that grows with context. If decode at long context is bandwidth-bound, FP8 should win there even though an earlier short-prompt measurement said it lost.

## Configuration

One variable against the baseline: `--kv-cache-dtype fp8` instead of `auto`. Same context, same everything else. Two repetitions per point, code corpus, 128 generated tokens.

## Measurements

| Prompt tokens | Decode BF16 | Decode FP8 | TTFT BF16 | TTFT FP8 |
|---|---|---|---|---|
| 512 | 42.8 tok/s | 45.0 tok/s | 0.39 s | 0.39 s |
| 32,768 | 37.2 | 39.3 | 19.52 s | 22.49 s |
| 65,536 | 35.6 | 33.6 | 46.73 s | 59.53 s |
| 90,000 | 28.4 | 35.2 | 81.80 s | 94.67 s |

KV capacity: 181,484 tokens against 103,326.

## Outcome

Half confirmed, and it forces a correction.

**The correction.** This morning I recorded that "FP8 KV is slower here, not just less precise", from a single short-prompt pair, 39.3 against 48.4 tok/s. That does not survive repetition. Today FP8 is slightly faster at the same prompt size, 45.0 against 42.8. Across the four points FP8 is ahead at three and behind at one, by margins that sit inside the run-to-run spread. On decode the two are a wash, and the earlier Finding was drawn from noise. It has been replaced.

**What is real.** FP8 prefills consistently slower, by 15% at 32K, 27% at 64K, and 16% at 90K. Time to first token is the dominant cost of long context, so FP8 makes the thing that actually hurts worse. The extra work of quantizing keys and values as the cache is filled is paid during prefill and is not recovered.

The one place FP8 genuinely wins on decode is the far end, 35.2 against 28.4 tok/s at 90K, which is the bandwidth effect the hypothesis predicted. It arrives too late to matter, because reaching 90K costs 95 seconds of prefill rather than 82.

## Consequences

Baseline stays BF16 KV. FP8 KV is worth choosing for one reason only: it holds 181,484 tokens against 103,326, so it is the route to a context window past 96K. If that is ever wanted, it costs roughly a fifth of prefill speed and an unmeasured amount of precision.

`STATUS.md` corrected. The claim that FP8 is slower is withdrawn; what replaces it is that FP8 costs prefill and buys capacity.
