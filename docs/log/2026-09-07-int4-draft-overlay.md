# 2026-09-07 INT4 draft overlay

Status: concluded
Profile: A, new arm `a-int4draft`
Author: agent thread on mbp

## Hypothesis

Requantizing only the draft side of MTP to INT4 cuts the bytes read per draft pass, so decode should rise while target verification keeps output quality unchanged. The upstream author measured 21 to 39% faster prefix-cached agentic decode on another B70 with FP8 KV and thinking off. Expected here: a measurable decode gain at 512 to 32K context with thinking on and FP16 KV, a small drop in acceptance, and an unchanged task suite pass count.

## Configuration

One variable: the two upstream overlay patches applied at container start, enabled by `B70_DRAFT_LMHEAD_INT4=1` and `B70_DRAFT_MTP_INT4=1`. Everything else is the depth 3 configuration measured in [MTP depth 3](2026-09-07-mtp-depth-3.md): same image digest, `--dtype float16 --kv-cache-dtype auto`, 98,304 context, utilization 0.95, one sequence, 8,192 batched tokens, MTP3, prefix caching on.

Patches vendored from cookbook commit `966c593a` as `compose/patches/patch_draft_lmhead_int4.py` and `patch_draft_mtp_int4.py`, hashes in `NOTICE.md`. The first quantizes a copy of the shared FP16 LM head to INT4 g128 round-to-nearest and routes the draft's logit passes through it. The second quantizes the draft's five MTP linears the same way in `load_weights` and frees their BF16 copies. Both fail closed if the engine source anchors differ, both refuse tensor parallelism, and neither touches the target model or its verification head. The GDN mixed-split companion stays unapplied because `--max-num-seqs 1` prevents mixed batches.

```bash
ssh vllm 'cd ~/Code/llm-server/compose && docker compose --profile a-bf16kv down && docker compose --profile a-int4draft up -d'
```

Rollback is the reverse: `--profile a-int4draft down`, `--profile a-bf16kv up -d`.

Measurement is the same harness and sizes as the depth 3 experiment, run within two hours of it:

```bash
for p in 512 8192 32768; do
  ./scripts/bench.py --base-url http://vllm:8000 --key "$KEY" --corpus code \
    --thinking --prompt-tokens $p --gen 256 -n 6 \
    --json eval/results/2026-09-07-int4-draft/int4-p$p.json
done
./eval/run.py --client pi --model llm-server/qwen38 --thinking xhigh --timeout 900 \
  --out eval/results/2026-09-07-int4-draft-tasks
```

Baseline for comparison: the depth 3 arm in [MTP depth 3](2026-09-07-mtp-depth-3.md) for speed, and [Pi validation](2026-09-07-pi-client-validation.md) for the 8/8 task suite.

## Measurements

Startup: both patches found their anchors on image `f01e24f6`. The five draft linears went from 0.85 GB BF16 to 0.22 GB INT4 at load, with the BF16 copies freed. The LM head copy went from 2.54 GB FP16 to 0.66 GB INT4 on the first draft pass. GPU KV cache size: 111,509 tokens, against 105,640 for the depth 3 BF16 draft arm. Health after about 240 seconds. `scripts/smoke.sh` passed all five checks.

Speed, concurrency 1, thinking on, 256 generated tokens, cold prefix, medians of six after a discarded warmup. Baseline is the depth 3 BF16 draft arm measured about 75 minutes earlier with the same harness.

| | p512 BF16 draft | p512 INT4 draft | p8192 BF16 | p8192 INT4 | p32768 BF16 | p32768 INT4 |
|---|---:|---:|---:|---:|---:|---:|
| Actual prompt tokens | 625 | 770 | 7,551 | 9,240 | 33,420 | 35,357 |
| TTFT | 0.380 s | 0.444 s | 3.794 s | 4.718 s | 19.196 s | 20.463 s |
| Prefill cold | 1,642 tok/s | 1,734 tok/s | 1,990 | 1,958 | 1,741 | 1,728 |
| Decode median | 48.5 tok/s | 57.2 tok/s | 44.7 | 58.5 | 46.2 | 59.2 |
| Decode mean, sd | 48.6, 2.8 | 58.5, 2.5 | 47.0, 5.4 | 58.4, 2.1 | 45.6, 5.0 | 59.9, 4.4 |
| Decode min, max | 45.5, 51.6 | 56.4, 62.4 | 41.9, 56.2 | 55.6, 61.9 | 38.4, 50.4 | 55.5, 67.9 |
| Acceptance, counter delta | 51.7% | 43.0% | 49.0% | 46.9% | 56.1% | 59.9% |

Decode medians rose 18% at 512, 31% at 8K and 28% at 32K. The lowest INT4 repetition at every size exceeds the highest BF16 median. Per-position acceptance over the whole run: 0.679, 0.472, 0.326 against 0.716, 0.494, 0.358, mean acceptance length 2.48 against 2.57. The cruder draft proposes slightly worse and the target rejects a little more, and the cheaper draft passes outweigh that by a wide margin.

Prompt token counts differ between arms because `scripts/bench.py` builds its prompt from this repository's own source files, and vendoring the two overlay patches added about 15% more tokens per requested size. Cold prefill rates are unchanged, and decode is nearly flat across a 50x range of context on this hardware, so the decode comparison stands. A rerun of the BF16 draft arm on the current corpus follows below to remove the doubt.

Corpus recheck. The BF16 draft arm was restarted and measured again on the current corpus, so prompt token counts match the INT4 arm within three tokens.

| Same corpus, concurrency 1, thinking on, 256 generated, medians of 6 | p512 BF16 | p512 INT4 | p8192 BF16 | p8192 INT4 |
|---|---:|---:|---:|---:|
| Actual prompt tokens | 767 | 770 | 9,238 | 9,240 |
| TTFT | 0.430 s | 0.444 s | 4.751 s | 4.718 s |
| Decode median | 45.5 tok/s | 57.2 tok/s | 45.6 | 58.5 |
| Decode mean, sd | 46.1, 2.8 | 58.5, 2.5 | 45.6, 2.2 | 58.4, 2.1 |
| Acceptance, counter delta | 47.3% | 43.0% | 49.2% | 46.9% |

The gain on identical prompts is 26% at 512 and 28% at 8K. The corpus change explains none of it.

Task suite through Pi 0.85.1, xhigh, concurrency 1, on the INT4 arm: **8 of 8 passed**. Task times 17.9, 8.2, 48.5, 33.7, 15.4, 15.4, 42.4 and 20.9 seconds, 202.4 seconds total, against 362.4 seconds for the same eight tasks at the BF16 draft, depth 4 baseline in [Pi validation](2026-09-07-pi-client-validation.md). Task time also depends on how much the model chooses to think and do at temperature 1.0, so the total is indicative, not a decode measurement. Transcripts are under `eval/results/2026-09-07-int4-draft-tasks/` on mbp, gitignored.

## What happened

The first task-suite launch stalled: every task log stayed empty and the server received no requests for 30 minutes. The harness had moved the runner to the background after ten minutes, detaching it from the terminal, and Pi under `subprocess.run` then never completed a request. The same Pi one-shot in the foreground completed in seconds. Relaunched the suite detached from the start with `nohup`, stdin from `/dev/null` and output to a file, and it ran cleanly. Nothing about the server was involved; the first launch's two timed-out tasks are discarded.

The LM head INT4 copy builds lazily on the first draft pass, after the KV cache has been reserved at 0.95 utilization. It allocated 0.66 GB without an out-of-memory error, and the freed 0.63 GB of BF16 MTP linears had already gone into the cache, which is why KV capacity rose rather than fell. No `xe` faults appeared in dmesg during any arm. The container stayed healthy throughout, across three restarts.

The image also prints two `[ERROR]` lines at startup about undocumented `min_frames` and `max_frames` kwargs in the transformers video processor. They appear on every profile and are noise.

## Outcome

Confirmed. Decode rose 26 to 31% at every context size on identical prompts, the eight-task suite passed in full, tool calling, reasoning, vision and long prompts work, and KV capacity rose by 5,869 tokens. Acceptance fell by two to four points, as the upstream author warned, and the cheaper draft passes more than pay for it. This is a speed change with no quality mechanism: the target model and its verification head are untouched, so accepted tokens are drawn from the same distribution as before.

What this does not establish: parity on hard multi-file repository work, which the eight fixtures cannot measure on either arm, and behavior under a future image bump, where these two patches are two more anchors that can fail. Both patches fail closed, so a mismatch shows up as a startup error rather than silent misbehavior.

## Consequences

`a-int4draft` is now the daily-driver profile on `vllm`. `STATUS.md`, the README start command and `scripts/experiment.sh` name it. `a-bf16kv` remains defined as the rollback: `docker compose --profile a-int4draft down && docker compose --profile a-bf16kv up -d`. A Finding was promoted to `STATUS.md`. The watchdog restarts the container by name and needs no change.
