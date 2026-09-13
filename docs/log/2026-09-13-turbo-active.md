# 2026-09-13 Activate Turbo on the server

Status: in progress
Profile: turbo-gguf

## Hypothesis

The previously validated Turbo profile can become the persistent active service with its existing xhigh thinking, 131,072-token context, Q8_0 KV, Q6_K weights, MTP2 and vision settings.

## Configuration

Change the active profile from `a-int4draft` to `turbo-gguf` at Chris's request. Keep all pinned model, engine, kernel and driver versions unchanged. Preserve the stopped vLLM container as `qwen38-vllm-standby` so its compiled kernels remain available for rollback.

```bash
ssh vllm 'cd ~/Code/llm-server && mkdir -p scratch/turbo-active && bash scripts/gpu-health.sh > scratch/turbo-active/before-switch.log 2>&1 && docker logs --tail 120 qwen38 > scratch/turbo-active/vllm-before-switch.log 2>&1'
ssh vllm 'docker stop qwen38 && docker rename qwen38 qwen38-vllm-standby && cd ~/Code/llm-server && bash scripts/compose.sh --profile turbo-gguf up -d --no-deps llama-turbo'
```

Baseline: [128K thinking validation](2026-09-13-turbo-thinking-128k.md) and [installed Pi/OpenCode checks](2026-09-13-turbo-clients.md). This is an activation, not a tuning comparison. The API remains on the Tailscale address and existing key; its model ID changes to `qwen38-turbo`.

## Measurements

Pending health, model/context discovery and a short reasoning request. No throughput benchmark or task suite is repeated.

## What happened

Execution host is mbp/Darwin; all server commands use SSH to `vllm`. The server checkout is clean at `09dd6c0`. The original `a-int4draft` service is healthy before switching. Existing unrelated MacBook edits are preserved.

## Outcome

Pending startup verification.

## Consequences

Leave Turbo active after validation. Its `restart: unless-stopped` policy retains it across host/Docker restarts. The stopped standby stays stopped. The watchdog continues to follow the shared container name `qwen38`. Client entries already exist; select `llm-server/qwen38-turbo` in Pi or OpenCode.

To roll back this preserved standby after capturing GPU diagnostics:

```bash
ssh vllm 'cd ~/Code/llm-server && bash scripts/gpu-health.sh > scratch/turbo-active/before-rollback.log 2>&1'
ssh vllm 'docker stop qwen38 && docker rm qwen38 && docker rename qwen38-vllm-standby qwen38 && docker start qwen38'
```
