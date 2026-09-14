# 2026-09-13 Two checkpoint profiles

Status: concluded
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

| Check | `a-int4draft` | `original-int4draft` |
|---|---|---|
| Resolved `/model` mount | `/home/chris/models/Qwen3.8-27B-Uncensored-GPTQ-Int4-sym-G128-MTP-BF16` | `/home/chris/models/Qwen3.8-27B-GPTQ-Int4-sym-G128-MTP-BF16` |
| Cold-start health | healthy by the 24th 10-second poll | healthy by the 25th 10-second poll |
| Container restarts | 0 | 0 |
| GPU KV cache | 205,391 tokens | 205,391 tokens |
| Authenticated model discovery | `qwen38` | `qwen38` |
| Authenticated completion | `ABLITERATED_PROFILE_OK` | `ORIGINAL_PROFILE_OK` |

`docker compose config --profiles` returned exactly `a-int4draft` and `original-int4draft`. No decode, prefill, TTFT, acceptance-rate or peak-VRAM benchmark was run because the serving flags did not change and both checkpoints already have separate performance and quality measurements.

## What happened

Both checkpoint directories were present on `vllm` before the change. The active `a-int4draft` container was healthy with zero restarts and mounted the kernelogic checkpoint.

Commit `97afe70` was pulled onto a clean server worktree. Compose rendered each retained profile with the expected fixed model directory. The SergiioB profile then started cleanly, applied the runtime INT4 draft patches, exposed a 205,391-token KV cache and completed an authenticated request. The abliterated profile was restored and passed the same checks. Its replacement container started at `2026-09-14T02:45:36.155238727Z` and remained healthy with zero restarts.

## Outcome

Confirmed. Each retained profile selects its intended checkpoint without a mutable shared `MODEL_DIR`, both start with the same validated serving settings, and the four unwanted profile names are absent from Compose's profile inventory.

## Consequences

The server now has two runnable inference profiles: `a-int4draft` and `original-int4draft`. The abliterated profile is active. Pi and OpenCode retain one `qwen38` model entry because both profiles expose the same API alias. The removed profile definitions and the obsolete `qwen38-turbo` client entries are no longer part of current configuration. Model weights were not deleted.
