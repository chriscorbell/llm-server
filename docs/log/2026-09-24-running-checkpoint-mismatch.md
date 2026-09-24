# 2026-09-24 Running checkpoint does not match STATUS.md

Status: concluded
Profile: `original-int4draft`
Author: agent thread on mbp

## Hypothesis

Not an experiment. A check of what the server was running found that it disagreed with `STATUS.md`. This entry records the mismatch and the correction.

## Configuration

No change was made on the server. The state was read with:

```
ssh vllm 'docker inspect qwen38 --format "{{index .Config.Labels \"com.docker.compose.service\"}} created={{.Created}} started={{.State.StartedAt}} restarts={{.RestartCount}} health={{.State.Health.Status}}"'
ssh vllm 'docker inspect qwen38 --format "{{range .Mounts}}{{.Source}} -> {{.Destination}}{{println}}{{end}}"'
ssh vllm 'docker logs qwen38 2>&1 | grep -E "\[B70\]|GPU KV cache size"'
```

Baseline for comparison: [two-checkpoint profiles](2026-09-13-two-checkpoint-profiles.md), which records the abliterated `a-int4draft` container being restored at `2026-09-14T02:45:36Z`.

## Measurements

| Fact | Recorded in STATUS.md | Observed 2026-09-24 |
|---|---|---|
| Compose service | `vllm-a-int4draft` | `vllm-original-int4draft` |
| `/model` mount | `/home/chris/models/Qwen3.8-27B-Uncensored-GPTQ-Int4-sym-G128-MTP-BF16` | `/home/chris/models/Qwen3.8-27B-GPTQ-Int4-sym-G128-MTP-BF16` |
| Container start | `2026-09-14T02:45:36Z` | `2026-09-14T02:58:10Z` |
| Restarts | 0 | 0 |
| Health | healthy | healthy, up 10 days |
| Engine image | `f01e24f6` | `f01e24f6` |
| KV cache | 205,391 tokens | 205,391 tokens |
| INT4 draft conversions | both | both (LM head and 5 MTP linears) |

No speed, TTFT or quality numbers were measured in this check.

## What happened

The running container is the original SergiioB checkpoint, started 12 minutes 34 seconds after the log recorded the abliterated profile as restored. The Compose labels show it was created from `/home/chris/Code/llm-server/compose`, the tracked configuration. The flags match `a-int4draft` exactly; only the checkpoint differs.

Nothing records why it was switched. There is no commit between `b9baa64` (22:51:54 EDT, September 13) and the next day, no log entry naming `original-int4draft` after the profile change, the watchdog incident directory `/var/log/xpu-wedge-watchdog/` is empty, and the system journal from 22:40 to 23:10 EDT has no watchdog or Compose lines. The server worktree is clean at `a04fea7`.

## Outcome

`STATUS.md` had described the abliterated checkpoint as active for ten days while the original checkpoint served every request.

Every server measurement in log entries dated 2026-09-14 or later ran on the original checkpoint. This includes the [Codex setup](2026-09-20-codex-desktop-setup.md), [Pi context pressure](2026-09-20-pi-context-pressure.md), [Splash comparison](2026-09-22-splash-mbp-comparison.md) and [Claude Code client](2026-09-23-claude-code-client.md) entries. None of those entries names a checkpoint. Their results should not be read as measurements of the abliterated checkpoint.

## Consequences

`STATUS.md` now names `original-int4draft` and the SergiioB checkpoint as running. The abliterated Finding stays, but it no longer claims that checkpoint is selected. The server was not changed. Both checkpoints remain installed.
