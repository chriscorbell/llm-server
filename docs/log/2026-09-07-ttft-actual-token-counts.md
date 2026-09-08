# 2026-09-07 TTFT with actual token counts

Status: concluded
Profile: A, existing live engine unchanged

## Hypothesis

Prefix caching remains the largest available reduction in response startup time on this configured server.

## Configuration

Only cache state changes between runs. The engine, Qwen checkpoint and server flags remain unchanged. `scripts/bench.py` now reads `usage.prompt_tokens` instead of using the requested character-based estimate in its prefill calculation. Earlier nominal context sizes and prefill rates in [decode versus context](2026-09-07-decode-versus-context.md) are approximate; their client-side timing measurements remain valid.

```bash
python3 scripts/bench.py --base-url http://vllm:8000 \
  --prompt-tokens 32768 --gen 128 -n 3 --thinking \
  --json eval/results/2026-09-07-ttft-cold.json
python3 scripts/bench.py --base-url http://vllm:8000 \
  --prompt-tokens 32768 --gen 128 -n 3 --thinking --warm \
  --json eval/results/2026-09-07-ttft-warm.json
```

Concurrency 1, code corpus, thinking enabled with the server's default xhigh effort, temperature 1.0, top_p 0.95, top_k 20. Each command discards one warmup. Cold runs use a unique prefix each time; warm runs reuse one exact prompt. Warm prefill throughput is effective input processing including cache reuse, not GPU prefill throughput.

The benchmark reads the key from `LLM_SERVER_API_KEY` by default.

## Measurements

Cold result, concurrency 1, three scored repetitions after a discarded warmup: median 33,419 actual prompt tokens, 19.211 seconds TTFT, 52.1 output tokens/second, 1,739.6 effective prefill tokens/second and 56.6% MTP acceptance (acceptance includes warmup). Each response generated 128 tokens. Warm measurement follows. Peak VRAM is not measured in this experiment.

Completed comparison:

| Metric, concurrency 1 | Cold | Cached |
|---|---:|---:|
| Actual prompt tokens, median | 33,419 | 33,422 |
| First reasoning/content token, median | 19.211 s | 0.811 s |
| Decode, median | 52.1 tok/s | 41.9 tok/s |
| Effective prefill, median | 1,739.6 tok/s | 41,207.3 tok/s |
| MTP acceptance, including warmup | 56.6% | 51.6% |
| Scored repetitions | 3 | 3 |
| Output length per repetition | 128 tokens | 128 tokens |

Raw cold TTFT values: 19.20, 19.21 and 19.22 seconds. Raw cached values: 0.83, 0.81 and 0.81 seconds. Prompt-token differences come from the random prefix. Sampled outputs and acceptance differ between repetitions, so this run does not establish a decode-speed effect from caching.

## What happened

The old benchmark claimed to report actual input token counts but returned the requested approximate length. Corrected the result and added `prompt_tokens_target` for reproducibility plus explicit concurrency metadata.

## Outcome

Confirmed for this workload: caching reduced median TTFT by 23.7 times at about 33.4K actual input tokens. The measured benefit concerns the first streamed token, including reasoning, not the time to a completed answer. Keep prefix caching, one active request and stable session settings. No engine change is justified by this result.

## Consequences

The benchmark now reports actual prompt tokens and uses them for effective prefill rate. No serving configuration changed.
