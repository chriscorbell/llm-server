# 2026-09-07 Decode speed and MTP acceptance below the published numbers

Status: concluded, with an open question
Profile: A
Author: agent thread on mbp

## Hypothesis

Profile A should reproduce roughly the published single-B70 figures for this checkpoint: about 84 tok/s decode at a 512-token prompt with 4 speculative tokens, and about 95% draft acceptance.

## What happened

The first measurement said 17 tok/s. That was a bug in my own harness, not the server. `scripts/bench.py` counted stream chunks and called them tokens, but speculative decoding delivers several accepted tokens in one chunk. Counting chunks understates the rate by roughly the acceptance length. The harness now reads `completion_tokens` from the server's own usage block, requested with `stream_options.include_usage`.

Corrected, decode sits near 50 tok/s and acceptance near 45%, against the published 84 and 95%. The engine reports the shape of the shortfall directly:

```
SpecDecoding metrics: Mean acceptance length: 2.72,
Per-position acceptance rate: 0.707, 0.453, 0.307, 0.253,
Avg Draft acceptance rate: 43.0%
```

The first speculative token is accepted most of the time. The fourth almost never is. The draft is working, it just decays fast.

A second harness defect mattered too. I was not sending `top_k`, so the sampler used the full distribution. Qwen recommends `top_k: 20`, and adding it lifted acceptance from 43% to 53% and decode from 42 to 52 tok/s with nothing else changed. Greedy sampling reached 60.5% and 60.5 tok/s, which brackets the effect.

## Measurements

Prompt 512 tokens, generation 128, one sequence, thinking off, median of three, cold prefix each time.

| Arm | Decode tok/s | Acceptance | KV tokens |
|---|---|---|---|
| BF16 KV, prefix on, no top_k | 53.2 | 44.2% | 103,326 |
| BF16 KV, prefix off, no top_k | 41.7 | 43.0% | 105,640 |
| BF16 KV, prefix off, top_k 20 | 51.7 | 52.9% | 105,640 |
| BF16 KV, prefix off, top_k 1 | 60.5 | 60.5% | 105,640 |
| BF16 KV, prefix on, top_k 20 | 48.4 | 42.6% | 103,326 |
| FP8 KV, prefix on, top_k 20 | 39.3 | 37.3% | 181,484 |

Prefill was flat across every arm at about 1,600 tok/s cold, and time to first token at a 512-token prompt was 0.32 seconds in all six.

## Outcome

Partly refuted, and the harness is not yet good enough to settle the rest.

Two things are established. FP8 KV is slower and accepts fewer draft tokens than BF16 KV on this machine, which inverts the assumption behind the published recipe. Its only argument is capacity: it holds 181,484 tokens where BF16 holds 103,326. And `top_k` matters enough that any speed number measured without it is wrong.

One thing is not established. Run-to-run spread at three repetitions is large enough to swamp the prefix caching comparison, which came out both ways. I am not going to draw a conclusion from it.

The likely reason the absolute numbers trail the published ones is the prompt content. My generator emits a repeated pangram, which is not text this model predicts the way it predicts prose or code. Draft acceptance is highly sensitive to that. The published harness used realistic prompts.

## Consequences

Baseline stays BF16 KV at 98,304 tokens with prefix caching on. `scripts/bench.py` gained usage-based token counting and a `--top-k` flag defaulting to 20.

Open question carried into `STATUS.md`: rerun with realistic prose and code prompts at higher repetition counts before treating any of these absolute figures as this machine's ceiling.
