# 2026-09-07 Profile A first boot and context ceiling

Status: concluded
Profile: A, BF16 KV
Author: agent thread on mbp

## Hypothesis

BF16 KV would not reach 131,072 tokens on 32 GiB, and the real ceiling would land nearer 64K to 96K. Predicted in the previous entry from the arithmetic.

## Configuration

vLLM XPU image `f01e24f6`, model `SergiioB/Qwen3.8-27B-GPTQ-Int4-sym-G128-MTP-BF16` at revision `9d189a60`, MTP with 4 speculative tokens, `--max-num-seqs 1`, vision on, prefix caching on.

## What happened

Three startup failures before the server came up, all worth recording because none were the model's fault.

**oneCCL could not enumerate the GPU.** With only a Compose `devices:` mapping, startup died at

```
RuntimeError: oneCCL: ze_fd_manager.cpp:144 init_device_fds: EXCEPTION: opendir failed: could not open device directory
```

The device mapping exposes the individual nodes but not the directory. oneCCL lists `/dev/dri` at init even on a single GPU. Fixed by bind mounting `/dev/dri:/dev/dri:ro` alongside the device mapping.

**Docker Compose was not installed.** Ubuntu 26.04's Docker packaging does not pull in the Compose plugin. `apt install docker-compose-v2` gave 2.40.3.

**BF16 KV did not fit at 131,072.** vLLM refused with its own arithmetic, which is the cleanest possible confirmation of the prediction:

```
ValueError: To serve at least one request with the model's max seq len (131072),
9.5 GiB KV cache is needed, which is larger than the available KV cache memory
(6.91 GiB). Based on the available memory, the estimated maximum model length is 91520.
```

Raising utilization from 0.92 to 0.96 moved the available KV cache to 8.12 GiB and the estimated ceiling to 109,824. Still short of 131,072, so BF16 KV cannot reach the 128K target on this card at all.

Note that the real cost is 76 KiB per token, not the 64 KiB the layer arithmetic predicts. The extra is the speculative decoding buffers and the Gated DeltaNet recurrent state.

## Measurements

| | |
|---|---|
| Weights loaded | 18.24 GiB |
| Graph capture | 0.15 GiB, 1 second |
| Available KV at 0.92 utilization | 6.91 GiB, ceiling 91,520 tokens |
| Available KV at 0.96 utilization | 8.12 GiB, ceiling 109,824 tokens |
| Chosen setting | 0.95 utilization, `--max-model-len 98304` |
| Allocated KV at that setting | 103,326 tokens |
| Cold start to healthy | about 4 minutes |

## Smoke test

All four capabilities an agent client needs work, verified by `scripts/smoke.sh`:

- Plain text turn returns the expected token.
- Thinking produces reasoning, then the answer.
- Tool calling returns a well-formed `tool_calls` array with the `qwen3_xml` parser.
- Vision answers correctly on a generated solid-red PNG, which also proves the vision tower loaded despite the weights reporting 18.24 GiB.

One API surprise: this build returns the thinking text in `message.reasoning`, not `message.reasoning_content`. The smoke test originally checked only the older name and reported a false failure. It now accepts either.

## Outcome

Confirmed. 96K context at BF16 KV, above the 64K floor and below the 128K target.

## Consequences

`compose/.env` on the server sets `GPU_UTIL=0.95` and `MAX_MODEL_LEN_BF16KV=98304`. The `/dev/dri` bind mount is in the committed compose file. Two Findings promoted to `STATUS.md`.
