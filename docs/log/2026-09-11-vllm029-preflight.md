# 2026-09-11 vLLM 0.29.0 compatibility preflight

Status: in progress
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

## What happened

Manifest verification succeeded. Download is in progress.

## Outcome

Pending compatibility inspection.

## Consequences

The serving image remains at digest `f01e24f6`; no engine upgrade is selected.
