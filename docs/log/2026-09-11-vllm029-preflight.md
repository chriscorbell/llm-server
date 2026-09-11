# 2026-09-11 vLLM 0.29.0 compatibility preflight

Status: concluded, eligible for a separate serving comparison
Profile: isolated container, no GPU or API binding

## Hypothesis

The released vLLM 0.29.0 XPU image can support the current GPTQ checkpoint and INT4 draft patches, making it eligible for a separate latency comparison.

## Configuration

Current serving image: `vllm/vllm-openai-xpu@sha256:f01e24f6c7ff01f1e0662234255a1372297d1dbd89d003cf13c8fad3eab1ba4f`.

Candidate image: `vllm/vllm-openai-xpu@sha256:1db27a8b75ae1d6b3cbf16ebbb88310c2b5548221c8df1335082b2a54dba209a`. `docker manifest inspect --verbose vllm/vllm-openai-xpu:v0.29.0` resolved this Linux amd64 manifest on September 11. Compressed layers total 3.88 GiB. The candidate is pulled by digest, not by a floating tag.

```bash
ssh vllm 'docker pull vllm/vllm-openai-xpu@sha256:1db27a8b75ae1d6b3cbf16ebbb88310c2b5548221c8df1335082b2a54dba209a'
```

The isolated preflight will inspect installed package versions and apply the four current patches to the container's temporary filesystem. It receives no GPU device, model weights or exposed port. The running engine is unchanged by this test. [Candidate source research](../research/2026-09-11-upstream-optimization.md).

## Measurements

No speed, quality or peak-memory measurement. Download started during the MTP2 restart, between timed runs.

Installed packages in the downloaded image: vLLM `0.29.0+xpu`, PyTorch `2.13.0+xpu`, XPU kernels `0.1.14.1`, Triton `3.7.2+xpu`, AutoRound library `0.14.2`. All four patch scripts exited successfully. This checks source anchors only; no model was loaded.

## What happened

Manifest verification succeeded. Download is in progress.

Update: download completed and the isolated preflight passed. The command was equivalent to:

```bash
ssh vllm 'docker run --rm -i --network none \
  -v /home/chris/Code/llm-server/compose/patches:/patches:ro \
  --entrypoint bash \
  vllm/vllm-openai-xpu@sha256:1db27a8b75ae1d6b3cbf16ebbb88310c2b5548221c8df1335082b2a54dba209a -s' <<'BASH'
python -c 'import importlib.metadata as m; print({n:m.version(n) for n in ("vllm","torch","vllm-xpu-kernels","triton","auto-round-lib")})'
failed=0
for patch in patch_mtp_nightly.py patch_mtp_boundary.py patch_draft_lmhead_int4.py patch_draft_mtp_int4.py; do
  python "/patches/$patch" || failed=1
done
exit "$failed"
BASH
```

PyTorch warned `Can't initialize Level Zero Sysman` and `XPU device count is zero!`. That is expected for this container, which deliberately has no GPU devices. The four patch scripts found their source anchors, wrote their helpers and completed. Raw output is in `eval/results/2026-09-11-tuning/v029-preflight.log` on mbp.

## Outcome

The source-anchor preflight passes. This makes the image eligible for a model-load and benchmark experiment; it does not establish runtime compatibility, correctness or a speed gain.

## Consequences

The serving image remains at digest `f01e24f6`; no engine upgrade is selected.
