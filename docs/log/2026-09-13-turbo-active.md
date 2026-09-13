# 2026-09-13 Activate Turbo on the server

Status: concluded
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

Container start: `2026-09-13T16:22:57.835661165Z`; model loaded after 76.339 s. Health passes and authenticated discovery advertises `qwen38-turbo` with 131,072 context. A default-thinking arithmetic request passes 1/1 with 69 input tokens, 77 generated tokens, TTFT 2.109 s and total time 4.179 s at concurrency 1. No throughput benchmark or task suite is repeated.

## What happened

Execution host is mbp/Darwin; all server commands use SSH to `vllm`. The server checkout is clean at `09dd6c0`. The original `a-int4draft` service is healthy before switching. Existing unrelated MacBook edits are preserved.

## Outcome

Turbo is active and healthy. Its model/context discovery and short reasoning request pass. Leave it running.

## Consequences

Leave Turbo active after validation. Its `restart: unless-stopped` policy retains it across host/Docker restarts. The stopped standby stays stopped. The watchdog continues to follow the shared container name `qwen38`. Client entries already exist; select `llm-server/qwen38-turbo` in Pi or OpenCode.

To roll back this preserved standby after capturing GPU diagnostics:

```bash
ssh vllm 'cd ~/Code/llm-server && bash scripts/gpu-health.sh > scratch/turbo-active/before-rollback.log 2>&1'
ssh vllm 'docker stop qwen38 && docker rm qwen38 && docker rename qwen38-vllm-standby qwen38 && docker start qwen38'
```

### Activation verified

The API returns the correct `323` answer with 177 reasoning characters and a normal stop when the request omits all thinking/effort overrides. Container arguments verify xhigh defaults, 131,072 context and Q8_0 keys/values. The `llama-turbo` service is healthy with zero restarts and `unless-stopped` policy. `qwen38-vllm-standby` is stopped, and `xpu-wedge-watchdog.service` is active. GPU diagnostic message content is unchanged across the switch, with no new xe/Level Zero faults. Raw evidence is in `scratch/turbo-active/` on mbp and the server.

STATUS.md now identifies Turbo as active, records its actual engine/model/settings, and labels the vLLM settings as the stopped rollback profile. No client default, credential, network, driver or kernel change was made.
