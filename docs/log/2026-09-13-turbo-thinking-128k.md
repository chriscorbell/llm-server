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
