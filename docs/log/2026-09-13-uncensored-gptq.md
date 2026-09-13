# 2026-09-13 Deploy the abliterated GPTQ checkpoint

Status: in progress
Profile: a-int4draft, FP8 KV, MTP4

## Hypothesis

The pinned kernelogic abliterated checkpoint can replace the original SergiioB checkpoint under the existing vLLM profile while retaining tools, vision, xhigh thinking, prefix caching and the 131,072-token window.

## Configuration

Change only the model checkpoint. Source: `kernelogic/Qwen3.8-27B-Uncensored-GPTQ-Int4-sym-G128-MTP-BF16`, revision `bd3f8d56b9dc617c995ec5a3ececa486d1d064be`. Keep engine digest `sha256:f01e24f6c7ff01f1e0662234255a1372297d1dbd89d003cf13c8fad3eab1ba4f`, GPTQ INT4, runtime INT4 draft, MTP4, FP8 KV, 131,072 context, vision, prefix caching, one sequence, 8,192 batched tokens and utilization 0.95. API alias stays `qwen38`.

```bash
# Proposed model selection after download and verification:
MODEL_DIR=/home/chris/models/Qwen3.8-27B-Uncensored-GPTQ-Int4-sym-G128-MTP-BF16 bash scripts/compose.sh --profile a-int4draft up -d --no-deps vllm-a-int4draft

# Original model rollback, after capturing diagnostics:
MODEL_DIR=/home/chris/models/Qwen3.8-27B-GPTQ-Int4-sym-G128-MTP-BF16 bash scripts/compose.sh --profile a-int4draft up -d --no-deps vllm-a-int4draft
```

Run server commands through `ssh vllm` from mbp. Changes are committed and pushed from mbp, then pulled into `/home/chris/Code/llm-server`. Original weights remain installed. Baseline: [original profile restoration](2026-09-13-restore-original-profile.md) and [FP8/128K validation](2026-09-12-context-128k.md). Candidate selection evidence is in the [research note](../research/2026-09-13-abliterated-qwen38-gptq.md).

## Measurements

No candidate inference measurements yet. Preflight confirms the original container `ff4da06641021d44bc7b468d8ee8fbb17bec4944914f240fe9fc6e8ae765939c` is healthy with zero restarts. Server checkout is clean at `c5777d6`; model filesystem has 1.6 TB available.

## What happened

Chris requested setup after the candidate recommendation. Execution host is mbp/Darwin; target is vllm/Linux. The local worktree contains unrelated client and status edits, which will be preserved. Download preparation is in progress while the original model continues serving.

## Outcome

Pending download, startup and validation.

## Consequences

No serving configuration has changed yet. Benchmark and diagnostic artifacts will be retained under `eval/results/2026-09-13-uncensored/` on mbp and the server.

### Pinned download preparation

`compose/uncensored-model.json` pins all 15 published model files by size and SHA-256, using the Hugging Face revision API for large-file hashes and hashing the small files fetched from that exact revision. The existing resumable downloader now accepts `--manifest`; its default Turbo behavior is unchanged.

```bash
ssh vllm 'cd /home/chris/Code/llm-server && git pull --ff-only && python3 scripts/download-turbo.py --manifest compose/uncensored-model.json'
```
