# 2026-09-13 Restore the original profile

Status: concluded
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

Health and authenticated discovery pass. The API advertises `qwen38` at 131,072 context; the restored engine has 205,391 KV tokens. A default-thinking arithmetic request passes 1/1 with 69 input tokens, 53 generated tokens, 0.813 s TTFT and 1.310 s total time at concurrency 1. No throughput comparison or full task suite was run.

## What happened

Execution host is mbp/Darwin. The server checkout is clean at `022a2f6`. Turbo is healthy before the switch, and the preserved original container is stopped. Capture GPU diagnostics and logs before stopping Turbo.

## Outcome

The original `a-int4draft` profile is active and healthy. Model discovery, response correctness and returned reasoning are verified. Turbo is stopped.

## Consequences

Leave `a-int4draft` active after validation. Turbo's model weights, saved configuration and client entries remain installed for later use. Client default-model settings are unchanged.

### Restoration verified

The preserved original container started `2026-09-13T19:30:02.908288087Z` and is healthy with zero restarts and `unless-stopped` policy. Target/draft compilation loads from the saved artifacts in 1.07 s and 0.05 s. The watchdog is active. GPU diagnostic message content is unchanged across the switch; no new xe/Level Zero faults appeared.

The smoke request omits all thinking/effort overrides and returns `323` with 149 reasoning characters and a normal stop. Raw diagnostics and API results are in `scratch/restore-original/` on mbp and the server. STATUS.md again describes the original profile as active and its vLLM settings as the configuration in force. Existing unrelated edits remain preserved.
