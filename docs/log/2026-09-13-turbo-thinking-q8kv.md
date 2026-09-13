# 2026-09-13 Turbo xhigh thinking and Q8 KV

Status: concluded
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

### F16 control completed

F16 at 65,536 context, concurrency 1, xhigh, temperature 1.0 and top_p 0.95: warm code decode is 35.6 tok/s (35.4 and 35.8), TTFT 0.225 s, 4,239 actual input tokens, 4,235 cached, 384 output tokens per repetition. MTP acceptance is 82.4%, with per-position acceptance 88.62% and 75.52%. Both outputs include reasoning (730 and 443 characters); the fixed output budget truncates the requested full module, so this is a speed check. Sampled peak VRAM so far is 28.064 GiB at 1 Hz. Startup reports model loaded after 73.705 s.

An API request omitting all thinking/effort options returned the correct `7/22` probability, 536 reasoning characters, 210 generated tokens and a normal stop; 83 input tokens, TTFT 1.198 s. The model template explicitly defaults to xhigh. The CLI prints the harmless warning `Setting 'enable_thinking' via --chat-template-kwargs is deprecated. Use --reasoning on / --reasoning off instead.` The requested setting still works.

Raw evidence: `scratch/turbo-thinking/f16-64k-thinking.json`, `f16-default-thinking.json`, `f16-props.json`, and `vram.jsonl` on mbp. The watchdog is `xpu-wedge-watchdog.service` and is active; there is no `llm-gpu-watchdog.timer`.

Next, capture GPU state and replace only F16 KV with Q8_0 at the same 65,536-token window.

### Q8_0 at 64K speed check

The exact two request SHA-256 values match the F16 arm. At the same 4,239 input tokens, 4,235 cached, 384 generated, xhigh and concurrency 1, Q8_0 decode is 34.2 tok/s (33.9 and 34.5), TTFT 0.226 s and MTP acceptance 79.2%; per-position acceptance is 87.54% and 70.37%. Reasoning is present in both outputs (1,652 and 443 characters). Sampled peak during the measured requests is 26.412 GiB. This is 3.9% lower decode over two repetitions; it is not a claim about task-completion speed because generated text differs. Code and image checks are next.

### Q8_0 at 64K correctness completed

Short arithmetic, Python, lowercase, JSON and declared-tool checks pass 18/18, with thinking disabled only for this fixed regression suite. Pi 0.85.1 passes both selected tasks with xhigh reasoning and temperature 1.0/top_p 0.95:

| Task | Pass | Wall time | Maximum input tokens | Tool calls | Reasoning characters |
|---|---|---|---|---|---|
| 02-ts-fix-bug | 1/1 | 25.2 s | 6517 | 5 | 604 |
| 08-vision-css | 1/1 | 39.3 s | 7950 | 4 | 1573 |

Sampled peak across Q8_0 at 64K is 26.506 GiB. Raw evidence is `scratch/turbo-thinking/q8-64k-short.json` and `q8-64k-pi/` on mbp. The isolated Pi provider uses a temporary 0600 auth file and removes it after each run.

The cache comparison supports promoting `TURBO_KV_TYPE=q8_0`: these selected tasks retain correct reasoning, tool use and image input, while freeing VRAM for a separate [128K context experiment](2026-09-13-turbo-thinking-128k.md). It does not establish identical logits or broad quality parity with F16. Capture final GPU state before changing context.
