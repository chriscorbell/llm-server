# 2026-09-13 Restore the original profile

Status: in progress
Profile: a-int4draft

## Hypothesis

The preserved original vLLM container can resume serving `qwen38` with its validated xhigh thinking, 131,072-token context, FP8 KV and MTP4 settings.

## Configuration

At Chris's request, stop Turbo and restore the preserved `qwen38-vllm-standby` container. Keep all model weights, profile definitions, client entries and pinned versions. This reverses the [Turbo activation](2026-09-13-turbo-active.md).

```bash
ssh vllm 'cd ~/Code/llm-server && mkdir -p scratch/restore-original && bash scripts/gpu-health.sh > scratch/restore-original/before-switch.log 2>&1 && docker logs --tail 120 qwen38 > scratch/restore-original/turbo-before-switch.log 2>&1'
ssh vllm 'docker stop qwen38 && docker rm qwen38 && docker rename qwen38-vllm-standby qwen38 && docker start qwen38'
```

The restored container is `ff4da06641021d44bc7b468d8ee8fbb17bec4944914f240fe9fc6e8ae765939c`, service `vllm-a-int4draft`. The API remains at the existing Tailscale address with the same key; select `llm-server/qwen38` in Pi or OpenCode.

## Measurements

Pending health, authenticated model discovery and one short reasoning request. No throughput comparison or full task suite is planned.

## What happened

Execution host is mbp/Darwin. The server checkout is clean at `022a2f6`. Turbo is healthy before the switch, and the preserved original container is stopped. Capture GPU diagnostics and logs before stopping Turbo.

## Outcome

Pending startup verification.

## Consequences

Leave `a-int4draft` active after validation. Turbo's model weights, saved configuration and client entries remain installed for later use. Client default-model settings are unchanged.
