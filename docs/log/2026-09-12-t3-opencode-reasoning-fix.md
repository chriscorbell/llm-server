# 2026-09-12 Install Qwen reasoning variants

Status: concluded
Profile: ad hoc client configuration, server `a-int4draft` unchanged

## Hypothesis

Installing explicit low, medium and xhigh variants will make T3 expose Qwen's supported levels and make OpenCode transmit the selected effort.

## Configuration

Baseline: [picker diagnosis](2026-09-12-t3-opencode-reasoning-picker.md), whose four transport checks failed. T3 Code 0.0.40 and OpenCode 1.18.30 on mbp.

Add this model field in both `clients/opencode/opencode.jsonc` and `~/.config/opencode/opencode.jsonc`:

```diff
+          "variants": {
+            "low": { "reasoningEffort": "low" },
+            "medium": { "reasoningEffort": "medium" },
+            "xhigh": { "reasoningEffort": "xhigh" }
+          },
```

The existing default-effort key is left alone for this measurement. Its separate correction will be measured independently. The installed config will be backed up before editing. Other provider settings and credentials stay intact.

## Measurements

Pending the original loopback recorder against the installed configuration, followed by a T3 inventory refresh and picker inspection. No model speed or quality comparison is planned.

## What happened

The previous diagnosis already established the failing request capture and validated this exact map in an isolated process. This experiment installs it for normal use.

## Outcome

Pending.

## Consequences

The repository template and installed OpenCode config will gain the same supported variants. No server change is required.

## Installed mapping results

The installed configuration was backed up to `~/.config/opencode/opencode.jsonc.backup-reasoning-20260912-214853`, mode 0600. The explicit variant map was added to both configurations.

`python3 /tmp/t3-qwen-reasoning-inspection/capture_installed_variants.py` runs the original recorder against the installed model options, overriding only the transport destination, dummy credential, MCP enablement and tool permission in each isolated child process.

| Selection | Outgoing `reasoning_effort` | Requests | Exit code |
|---|---|---:|---:|
| low | low | 1 | 0 |
| medium | medium | 1 | 0 |
| xhigh | xhigh | 1 | 0 |

Transport checks pass 3/3, up from 0/4 before correction. `opencode models llm-server --verbose` lists exactly those three variants. All other captured sampling and output parameters match the baseline. The unsupported high level is absent. Results: `/var/folders/5p/9fk78x3d20gd_yln3r0_m4k00000gn/T/qwen-variant-capture-6rnicexm/results.json`.

T3's picker refresh is pending. No model inference, throughput, TTFT, prefill, peak VRAM, MTP acceptance or task-quality measurements were performed.

## T3 verification and final outcome

Clicked Settings > Providers > Refresh provider status. The OpenCode inventory checked at `2026-09-13T01:49:50.328Z` contains exactly low, medium and xhigh for `llm-server/qwen38`. The composer was then switched to Qwen, and its actual Reasoning menu showed Low, Medium and Xhigh, with Xhigh selected. High is absent. The menu was closed, leaving the empty draft on Qwen at Xhigh; no chat was submitted.

Confirmed: the installed mapping passes 3/3 outgoing-request checks and the refreshed T3 picker shows 3/3 supported choices with no extra level. The separate [default-effort correction](2026-09-12-opencode-default-effort.md) passes two additional checks. No T3 application or inference service restart was needed.

The repository template, installed OpenCode config, setup guide and `STATUS.md` now describe the working configuration. The original configuration backup remains available. The [earlier diagnosis](2026-09-12-t3-opencode-reasoning-picker.md) records the superseded broken state. This experiment does not measure relative task quality or speed between reasoning levels.
