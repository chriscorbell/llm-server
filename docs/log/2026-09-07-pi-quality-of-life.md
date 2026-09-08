# 2026-09-07 Pi quality-of-life extension and cached-token reporting

Status: concluded
Profile: a-int4draft, live engine
Author: agent thread on mbp

## Hypothesis

Two client-side changes make the measured cost of long context visible and cheaper without touching the engine: reporting vLLM's cached prompt tokens to Pi, and prefilling the compacted context while Pi is idle so the first post-compaction request hits the prefix cache instead of paying the 12.3 s cold prefill recorded in [Pi client validation](2026-09-07-pi-client-validation.md).

## Configuration

Server variable: `--enable-prompt-tokens-details` added to every profile in `compose/docker-compose.yml`, nothing else changed. Container recreated with `docker compose --profile a-int4draft up -d`.

Client: `clients/pi/extensions/llm-server/` symlinked into `~/.pi/agent/extensions/`, `clients/pi/settings.json` gains `quietStartup`, `showCacheMissNotices` and `shellCommandPrefix`, and `.pi/prompts/` gains `/log`, `/status` and `/bench`. The warm-up is measured with:

```bash
python3 eval/pi_warmup.py --arm baseline --out eval/results/2026-09-07-warmup-baseline
python3 eval/pi_warmup.py --arm warm --out eval/results/2026-09-07-warmup-warm
```

Both arms run the same flow as `eval/pi_contract.py`: prompts that read generated notes, a compaction, then one short prompt whose time to first streamed delta is the measurement. The warm arm loads the extension and waits for its warm-up record before sending the timed prompt. `--reads 3` trips threshold compaction mid-run; the default two reads stay under the threshold and the script compacts manually while Pi is idle. Each arm ran once, concurrency 1, xhigh thinking, on the live a-int4draft engine after the flag restart.

Baseline for comparison: the 12.264 s first post-compaction request at 22,618 input tokens in [Pi client validation](2026-09-07-pi-client-validation.md), measured on a-bf16kv.

## Measurements

Restart with the new flag: container started 03:32:03 UTC, `Application startup complete` at 03:35:47, 3 m 44 s.

Cached-token reporting, direct API, thinking off, `max_tokens` 4, same prompt sent repeatedly:

| Prompt tokens | Run | `cached_tokens` | Wall time |
|---|---|---|---|
| 619 | 1st and 2nd | 0 | not timed |
| 3,519 | 1st | 0 (`created_cache_tokens` 2,496) | 2.09 s |
| 3,519 | 2nd and 3rd | 2,496 | 0.60 s, 0.59 s |

Every cached count observed in the Pi runs below is a multiple of 832 (10,816; 19,968; 20,800; 29,952; 31,616; 40,768). The hybrid GDN model's prefix cache works in 832-token blocks, so a prompt under 832 tokens never reports a hit and the tail of every prompt below the next block boundary is always recomputed.

First request after compaction, time to first streamed delta:

| Compaction | Extension | Prompt tokens | Cached | First delta |
|---|---|---|---|---|
| threshold, mid-run (3 reads) | off | 22,494 | 0 | 12.16 s |
| threshold, mid-run (3 reads) | on | 31,594 | 0 | 17.93 s |
| manual, idle (2 reads) | off | 21,763 | 0 | 11.71 s |
| manual, idle (2 reads) | on | 31,290 | 29,952 | 1.03 s |

The idle warm-up itself took 17.6 s for 31,271 tokens at 0 cached, paid while Pi was waiting for input. The warm-up after the mid-run threshold compaction took 1.3 s with 29,952 already cached, because the post-compaction request had just prefilled the same prefix. In both extension runs the next real request matched the warm-up payload across all 11 shared messages, tools and `reasoning_effort` (`warmup-verify` records in `eval/results/2026-09-07-warmup-warm/extension.jsonl` and `eval/results/2026-09-07-warmup-idle-warm/extension.jsonl`).

Thinking-level change, driven over RPC with one 400-line read in context: `set_thinking_level medium` triggered a warm-up of 9,125 tokens at medium effort in 4.6 s while idle; the next request carried `reasoning_effort: medium`, matched the warm-up across all 5 shared messages, and started in 0.94 s with 7,488 tokens cached. Without the warm-up the validation run measured 12.6 s for the same switch at 23K tokens.

Cold prefill implied by the four cold rows: 1,750 to 1,860 tok/s, consistent with the 33.4K cold measurement in [actual token counts](2026-09-07-ttft-actual-token-counts.md).

The tool-output budget changed the runs' shape: with the extension on, each 750-line notes file cost about 10,800 prompt tokens instead of 21,200, so more turns survived compaction and the post-compaction context was 31K instead of 22K.

## What happened

The first version of the measurement counted requests with a substring that matched every audit line, so the baseline summary recorded nulls; the numbers above come from `requests.jsonl` directly and the script was fixed.

The first idle warm run produced no warm-up at all. Pi's `isIdle()` is false inside the `session_compact` handler because the compaction abort controller is still set until the handler returns, so the extension parked the warm-up until an `agent_settled` that never follows a manual compaction. The handler now re-checks idleness 500 ms later and the rerun warmed within a second of compaction.

Pi's threshold compaction runs between turns of the same run when a tool result crosses the threshold, and the request that follows it is cold no matter what a client does; in the three-read runs the user's next prompt was already warm (0.66 s and 0.77 s) because that request had prefilled the compacted prefix. The idle warm-up only pays off when compaction ends a run: manual `/compact`, a threshold trip after a final answer, or a thinking-level change, which the guard module also routes through the warm-up.

vLLM 0.27.2rc1 reports `prompt_tokens_details: null` without `--enable-prompt-tokens-details`; with the flag it reports `cached_tokens` and `created_cache_tokens`. Pi maps `cached_tokens` to `usage.cacheRead` and subtracts it from `input`, which is why the footer's `R` counter and the extension's cache share now populate.

## Outcome

Confirmed for the idle case: 11.7 s to 1.0 s at 22K to 31K tokens, one run per arm. Refuted for mid-run threshold compaction, where the cold request follows before any client-side warm-up can run. The cache-hit reporting works at 832-token granularity. Quality effects of the 24 KB tool budget are unmeasured; the task suite has not been rerun with the extension loaded.

## Consequences

`--enable-prompt-tokens-details` is on every profile in `compose/docker-compose.yml` and live on a-int4draft. `clients/pi/extensions/llm-server/` is installed on mbp by symlink, `clients/pi/settings.json` carries `quietStartup`, `showCacheMissNotices` and `shellCommandPrefix`, and `.pi/prompts/` adds `/log`, `/status` and `/bench` for work in this repository. `eval/pi_warmup.py` reproduces the measurement. Findings promoted to STATUS.md: the 832-token cache block and the idle warm-up numbers. Open question added: does the tighter tool budget change task-suite results.
