# 2026-09-13 Turbo xhigh at 128K context

Status: in progress
Profile: turbo-gguf

## Hypothesis

Doubling Turbo's context from 65,536 to 131,072 tokens with the validated Q8_0 KV cache fits the B70 and preserves xhigh reasoning, long-context retrieval, cached continuation, coding and images.

## Configuration

Change only `TURBO_CONTEXT` from 65,536 to 131,072. Keep Q6_K model weights, Q8_0 keys and values, MTP2, xhigh thinking by default, F16 vision projector, flash attention, one sequence, batch 2,048 and microbatch 512. The SYCL b10920 image remains pinned at `sha256:61606ca6fa74290cca83c0c8c7f0efc4c22c28bbdc9741bff8e6c861dccdd670`. Baseline: [Q8_0 at 64K](2026-09-13-turbo-thinking-q8kv.md).

```bash
ssh vllm 'cd ~/Code/llm-server && bash scripts/gpu-health.sh > scratch/turbo-thinking/before-128k.log 2>&1 && docker logs qwen38 > scratch/turbo-thinking/q8-64k-container.log 2>&1 && TURBO_CONTEXT=131072 bash scripts/compose.sh --profile turbo-gguf up -d --no-deps llama-turbo'
python3 scripts/bench.py --base-url http://vllm:8000 --model qwen38-turbo \
  --thinking --effort xhigh --workload code --prompt-tokens 4096 --gen 384 \
  --corpus-file scratch/turbo/bench-corpus.py --warm --prompt-id turbo-thinking-kv \
  -n 2 --json scratch/turbo-thinking/q8-128k-thinking.json
python3 eval/context_check.py --base-url http://vllm:8000 --model qwen38-turbo \
  --engine llama.cpp --thinking --effort xhigh --max-tokens 4096 \
  --prompt-tokens 124000 --out scratch/turbo-thinking/q8-128k-context-thinking.json
```

The retrieval check uses temperature 0 and checks actual returned reasoning as well as exact answers and API token counts. The 124K input target leaves room for reasoning, the answer and a continuation in the same 128K window. It is a context-handling test, not a long-context repository-quality benchmark. A 1 Hz GPU sampler runs throughout validation.

## Measurements

Pending. The 64K Q8_0 baseline measured 34.2 tok/s and 0.226 s cached TTFT with 4,239 input tokens, 384 generated tokens, xhigh and concurrency 1. It passed 18/18 short checks and 2/2 selected Pi xhigh coding/image tasks; sampled peak was 26.506 GiB.

## What happened

Q8_0 passed its separate cache comparison before changing context. The original daily driver remains preserved and stopped as `qwen38-before-turbo`. Capture logs and GPU state before each container replacement.

## Outcome

Pending the 128K run.

## Consequences

The saved context remains 65,536 until the larger window passes. No engine, model, kernel or driver version changes.

### 128K startup and short reasoning benchmark

The model API advertises `qwen38-turbo` with `n_ctx=131072`, Q6_K and native training context 262,144. Docker arguments confirm Q8_0 keys/values, all layers on SYCL0, MTP2 and explicit xhigh thinking. An unauthenticated model-list request returns HTTP 401.

The exact request hashes match the 64K Q8_0 arm. At 4,239 actual input tokens, 4,235 cached, 384 generated tokens and concurrency 1, warm xhigh decode is 34.1 tok/s (34.8 and 33.4), TTFT 0.229 s and MTP acceptance 78.7%. Per-position acceptance is 84.56% and 72.48%. Both outputs contain reasoning, 730 and 443 characters. The two-repetition difference from 34.2 tok/s at 64K is inside the observed spread. Raw evidence: `scratch/turbo-thinking/q8-128k-thinking.json` and `q8-128k-models.json` on mbp. The 124K retrieval check is now running.

### First near-limit retrieval completed

Cold retrieval passes all five exact record lookups and returns reasoning at 123,975 actual input tokens, with only 42 shared template tokens cached. TTFT is 216.848 s, decode 19.4 tok/s, output 937 tokens and reasoning 1651 characters. The request ends normally. Xhigh is enabled, temperature is 0 and concurrency is 1. Cached repeat and continuation are still running.

### Near-limit context validation completed

All three checks pass exact answers, normal stops, matching tokenizer/API prompt counts, and nonempty reasoning. Five record IDs span 3%, 27%, 50%, 73% and 97% of the archive. All requests use xhigh, temperature 0 and concurrency 1.

| Request | Actual input | Cached input | Output | TTFT | Decode | Reasoning characters |
|---|---|---|---|---|---|---|
| retrieval-cold | 123,975 | 42 | 937 | 216.848 s | 19.4 tok/s | 1651 |
| retrieval-repeated | 123,975 | 123,971 | 937 | 1.035 s | 19.4 tok/s | 1651 |
| continuation | 124,943 | 123,971 | 73 | 4.660 s | 18.4 tok/s | 155 |

The first request prefills 123,933 uncached tokens at an effective 571.5 tok/s, including request overhead and time to first streamed text. The 42 reused tokens are common template text; this is effectively a cold archive prompt. The continuation retains the previous assistant reasoning, and reuses 123,971 prompt tokens while reprocessing the generated assistant turn. Raw evidence: `scratch/turbo-thinking/q8-128k-context-thinking.json`. Final selected Pi code/image checks now run with client context 131,072 and a 32,768-token output limit.

### Final Pi and memory validation

Pi 0.85.1 passes 2/2 selected tasks at xhigh, temperature 1.0/top_p 0.95, client context 131,072, output limit 32,768 and concurrency 1:

| Task | Pass | Wall time | Maximum input tokens | Tool calls | Reasoning characters |
|---|---|---|---|---|---|
| 02-ts-fix-bug | 1/1 | 28.6 s | 5469 | 4 | 914 |
| 08-vision-css | 1/1 | 36.3 s | 6943 | 3 | 1437 |

Peak sampled VRAM across 128K initialization, short benchmark, long retrieval and Pi is 29.256 GiB out of 31.891 GiB usable, at 1 Hz. This is sampled global device memory, not an allocation-level peak. The final Turbo container is healthy with zero Docker restarts, and `xpu-wedge-watchdog.service` is active. The sampler is stopped before restoring vLLM so its memory use cannot affect this peak.

Promote `TURBO_CONTEXT=131072` with the validated Q8_0 cache and explicit xhigh default. The unchanged Q6_K weights, projector and pinned SYCL engine pass all requested operating checks. These selected tasks do not establish broad coding-quality parity against another checkpoint. The README now describes the 131,072-token total window, a 32,768-token client output budget and input/compaction headroom. Restore the preserved daily driver after checking that saved defaults match the tested Turbo container.
