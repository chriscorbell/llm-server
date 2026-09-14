# 2026-09-13 Two checkpoint profiles

Status: in progress
Profile: `a-int4draft` and `original-int4draft`
Author: agent thread on mbp

## Hypothesis

Giving the kernelogic and SergiioB checkpoints separate Compose profiles will make model selection deterministic while preserving the validated FP8 KV, INT4 draft, MTP4 and 131,072-token serving configuration.

## Configuration

Replace the shared `MODEL_DIR` selection with one fixed model directory per profile, add `original-int4draft`, and remove `a-bf16kv`, `a-fp8kv`, `a-nospec` and `turbo-gguf` from the runnable Compose configuration.

```diff
-MODEL_DIR=/home/chris/models/Qwen3.8-27B-Uncensored-GPTQ-Int4-sym-G128-MTP-BF16
+UNCENSORED_MODEL_DIR=/home/chris/models/Qwen3.8-27B-Uncensored-GPTQ-Int4-sym-G128-MTP-BF16
+ORIGINAL_MODEL_DIR=/home/chris/models/Qwen3.8-27B-GPTQ-Int4-sym-G128-MTP-BF16
```

Both retained profiles use the same engine image and flags. Only the read-only `/model` bind mount differs.

Baseline for comparison: [abliterated checkpoint deployment](2026-09-13-uncensored-gptq.md) and [original checkpoint 128K validation](2026-09-12-context-128k.md).

## Measurements

No runtime measurements yet. Configuration rendering, profile inventory, startup health and authenticated model discovery will be checked for both profiles before this entry is concluded.

## What happened

Both checkpoint directories were present on `vllm` before the change. The active `a-int4draft` container was healthy with zero restarts and mounted the kernelogic checkpoint.

## Outcome

In progress.

## Consequences

No deployed state has changed yet.
