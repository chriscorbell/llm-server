# 2026-09-07 Larger prefill chunks buy nothing

Status: concluded
Profile: A, BF16 KV
Author: agent thread on mbp

## Hypothesis

Time to first token reaches 82 seconds at 90K context. Prefill runs in chunks of `--max-num-batched-tokens`, default 8,192 here, so a 90K prompt is eleven chunks. Fewer, larger chunks should amortise per-chunk overhead and cut that wait.

## Configuration

One variable: `MAX_BATCHED_TOKENS`. Everything else as in `STATUS.md`.

The first attempt did not start at all. Doubling the chunk to 16,384 while holding context at 98,304 pushed the KV cache over budget and vLLM refused:

```
ValueError: To serve at least one request with the model's max seq len (98304),
7.39 GiB KV cache is needed, which is larger than the available KV cache memory
```

So the lever costs context before it does anything else. Context was lowered to 81,920 to let it boot and be measured.

## Measurements

| | Chunk 8,192, 96K context | Chunk 16,384, 80K context |
|---|---|---|
| KV cache capacity | 103,326 tokens | 86,121 tokens |
| Time to first token, 32K prompt | 19.52 s | 19.38 s |
| Time to first token, 64K prompt | 46.73 s | 46.75 s |
| Prefill rate, 64K prompt | 1,402 tok/s | 1,402 tok/s |
| Decode, 32K prompt | 37.2 tok/s | 40.5 tok/s |

## Outcome

Refuted. Prefill throughput is identical to three significant figures at 64K, and time to first token differs by 20 milliseconds on a 47-second operation. Doubling the chunk changed nothing except taking 17,205 tokens of context away.

Prefill is not chunk-bound on this card. At roughly 1,400 to 1,700 tok/s it is limited by the per-token work itself, not by how the work is grouped, which is consistent with the same rate appearing at every prompt size measured today.

## Consequences

`MAX_BATCHED_TOKENS` stays at 8,192. The finding is recorded so nobody spends another hour on it. The 82-second cold start at 90K remains, and prefix caching remains the only measure that has actually moved it, from 19.5 seconds to 1.1 at 32K.
