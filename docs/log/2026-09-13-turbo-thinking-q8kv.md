# 2026-09-13 Turbo xhigh thinking and Q8 KV

Status: in progress
Profile: turbo-gguf

## Hypothesis

Q8_0 KV cache can preserve working xhigh reasoning, tools and images on the pinned SYCL engine while freeing enough VRAM to increase Turbo's context beyond 65,536 tokens.

## Configuration

The controlled change is KV precision, F16 to Q8_0 for both keys and values, initially at the same 65,536-token window. Retain Q6_K model weights, MTP2, flash attention, one sequence, batch 2,048, microbatch 512, and the pinned SYCL b10920 image `sha256:61606ca6fa74290cca83c0c8c7f0efc4c22c28bbdc9741bff8e6c861dccdd670`.

Thinking was already on by default in the GGUF template. The previous 34.8 tok/s benchmark disabled it per request; the two earlier Pi tasks used medium thinking. Make the existing xhigh server default explicit with `--chat-template-kwargs '{"enable_thinking":true,"reasoning_effort":"xhigh"}' --reasoning-budget -1`. API requests can still select a supported effort. This is not a finite reasoning-token cap.

```bash
# Initial F16 control after preserving the daily driver and capturing GPU health.
ssh vllm 'cd ~/Code/llm-server && bash scripts/compose.sh --profile turbo-gguf up -d --no-deps llama-turbo'
python3 scripts/bench.py --base-url http://vllm:8000 --model qwen38-turbo \
  --thinking --effort xhigh --workload code --prompt-tokens 4096 --gen 384 \
  --corpus-file scratch/turbo/bench-corpus.py --warm --prompt-id turbo-thinking-kv \
  -n 2 --json scratch/turbo-thinking/f16-64k-thinking.json
# Then change only cache precision.
ssh vllm 'cd ~/Code/llm-server && bash scripts/gpu-health.sh > scratch/turbo-thinking/before-q8.log 2>&1 && TURBO_KV_TYPE=q8_0 bash scripts/compose.sh --profile turbo-gguf up -d --no-deps llama-turbo'
```

Baseline deployment: [Q6_K MTP2 at 64K](2026-09-13-turbo-mtp.md). That file's speed numbers use thinking off and are not the reasoning baseline for this comparison.

## Measurements

Not yet measured. The Q8_0 attention-cache payload is approximately 53.125% of F16, before recurrent state and buffers. Doubling context should therefore cost approximately the same KV memory as the prior F16 window. This is an estimate, not a validated capacity.

## What happened

The previous two hardware/engine reports and current status were read. The server starts healthy on `a-int4draft`, with a clean checkout; existing MacBook client and documentation edits remain outside this work. The pinned source includes Q8_0/Q8_0 SYCL flash-attention instantiations for head dimension 256. The older Xe2 iGPU corruption report in [llama.cpp issue 19276](https://github.com/ggml-org/llama.cpp/issues/19276) is a reason to test this exact build and B70, not evidence that it works.

`eval/context_check.py` now accepts thinking effort and a larger output budget, checks that reasoning is actually returned, and preserves the repeated response's reasoning on continuation. Default arguments retain the earlier non-thinking path.

## Outcome

Pending the cache comparison. A context increase will be a separate experiment after this cache format passes.

## Consequences

The profile has an explicit xhigh thinking default and a configurable KV type. The saved KV/context defaults remain F16 and 65,536 until validation succeeds. No model, engine, kernel or host driver change is planned.
