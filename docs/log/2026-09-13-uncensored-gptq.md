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

### Original model baseline

The original model remains active while the pinned files download. `xpu-wedge-watchdog.service` is active and enabled. Before the benchmark, server metrics report zero running and zero queued requests. GPU state and startup logs are saved in `original-health.txt`.

Warm code generation, thinking off, concurrency 1, 4,201 actual input tokens and 384 generated tokens: median decode 87.0 tok/s across three measured repetitions, standard deviation 0.90 tok/s, median TTFT 1.337 s, 1,664 cached tokens, aggregate MTP acceptance 70.7%. This is a short sample, not a broad performance baseline.

```bash
python3 scripts/bench.py --base-url http://100.103.136.98:8000 --corpus-file scratch/turbo/bench-corpus.py --workload code --prompt-tokens 4096 --gen 384 -n 3 --warm --prompt-id uncensored-sept13 --json eval/results/2026-09-13-uncensored/original-code.json
# Repeat with --thinking --effort xhigh and original-thinking.json.
```

The frozen corpus has SHA-256 `9ae37e8c1bde0e297188695f444c50060e754a8d59dbbd7ff83240a0ddf900bb`. The candidate runs will reuse it, the prompt ID and seeds; saved request hashes establish whether complete API requests match.

The original model's xhigh thinking sample measures 73.6 tok/s median, range 65.3 to 80.4 tok/s and standard deviation 7.56 tok/s, at 4,241 input tokens, 384 generated tokens and concurrency 1. Median TTFT is 1.372 s, cached input 1,664 tokens and MTP acceptance 54.6%. All output tokens in these capped requests are reasoning; this measures throughput rather than completed-task quality.

### Saved model selection prepared

`compose/model.env` now selects the candidate directory, loaded after private `.env` by `scripts/compose.sh`. The server still runs the original model until the download finishes and the explicit Compose recreation occurs. No credential or client model-ID change is required. The root README documents initial download, activation and temporary/persistent rollback.
