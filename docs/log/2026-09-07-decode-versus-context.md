# 2026-09-07 Decode versus context, and where long context actually hurts

Status: concluded, corrects a wrong Finding in [the task suite baseline](./2026-09-07-task-suite-baseline.md)
Profile: A, BF16 KV at 98,304
Author: agent thread on mbp

## Hypothesis

I reported that decode "fell to 18.0 tok/s at about 28K context". That came from a single ten-second engine log window during the task suite, and vLLM's generation throughput counter divides decoded tokens by wall time in the window, including time spent chunk-prefilling. If the window overlapped a prefill, the figure is an artifact rather than a decode measurement.

## Configuration

Unchanged server. Client-side timing that excludes time to first token, so prefill cannot contaminate the decode figure. Code corpus, 128 generated tokens, three repetitions per point.

## Measurements

| Prompt tokens | Decode tok/s | Time to first token | Prefill tok/s | Acceptance |
|---|---|---|---|---|
| 512 | 42.8 | 0.39 s | 1,326 | 39.4% |
| 4,096 | 50.9 | 1.95 s | 2,101 | 44.4% |
| 16,384 | 41.7 | 9.08 s | 1,805 | 39.1% |
| 32,768 | 37.2 | 19.52 s | 1,678 | 40.5% |
| 65,536 | 35.6 | 46.73 s | 1,402 | 42.9% |
| 90,000 | 28.4 | 81.80 s | 1,100 | 40.7% |

Warm, with the prefix already cached, at 32,768 tokens:

| | Cold | Warm |
|---|---|---|
| Time to first token | 19.52 s | 1.11 s |
| Effective prefill rate | 1,678 tok/s | 29,648 tok/s |
| Decode | 37.2 tok/s | 45.7 tok/s |

## Outcome

Refuted. The 18 tok/s figure was an artifact of the engine counter, exactly as suspected. Real decode at 32K is 37.2 tok/s.

Decode degrades gently: 34% slower at 90K than at 512, with draft acceptance flat near 40% throughout. That decline tracks memory bandwidth almost exactly. Each forward pass reads the 18.2 GiB of weights plus the KV cache, which at 64K adds 4.75 GiB, or 26% more bytes; the measured slowdown over that range is 17%. Long context is not doing anything pathological.

What long context actually costs is time to first token: 82 seconds at 90K. In an agentic session that is the number you feel, not decode.

Prefix caching already answers most of it. At 32K, a cached prefix turns 19.5 seconds into 1.1, an 18-fold improvement, which is why the task suite showed an 85% hit rate and felt responsive. The defence against slow long context is keeping that hit rate high, not tuning decode.

Separately, decode sits about 30% below what raw bandwidth allows. One CPU thread runs at 99.5% during decode while the GPU holds its 2800 MHz boost clock, which is the vLLM engine core loop and is normal, but on this XPU stack it is close enough to being the limiter to be worth an experiment.

## Consequences

The wrong Finding is removed from `STATUS.md` and replaced with this curve. Open questions added for the untested levers: larger prefill chunks, FP8 KV specifically at long context where its smaller cache should help decode, the draft-INT4 overlay, and whether pinning the engine thread buys anything.
