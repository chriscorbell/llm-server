# 2026-09-07 INT4 draft overlay

Status: in progress
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

Pending.

## What happened

Pending.

## Outcome

Pending.

## Consequences

Pending.
