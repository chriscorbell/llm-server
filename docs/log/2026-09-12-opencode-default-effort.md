# 2026-09-12 Correct OpenCode's default effort key

Status: concluded
Profile: ad hoc client configuration, server unchanged

## Hypothesis

Using the adapter's camel-case default-effort key will explicitly send xhigh when no variant is selected, while a selected low variant will still take precedence.

## Configuration

Baseline: the [installed three-level variant map](2026-09-12-t3-opencode-reasoning-fix.md). Change one key in the model options in both `clients/opencode/opencode.jsonc` and `~/.config/opencode/opencode.jsonc`:

```diff
-            "reasoning_effort": "xhigh"
+            "reasoningEffort": "xhigh"
```

The initial configuration backup is `~/.config/opencode/opencode.jsonc.backup-reasoning-20260912-214853`.

## Measurements

Pending two outgoing-request checks, one without `--variant` and one with `--variant low`. No model speed or quality comparison is planned.

## What happened

The previous diagnosis captured no outgoing effort from the snake-case option. The API adapter consumes `reasoningEffort` and emits `reasoning_effort`.

## Outcome

Pending.

## Consequences

The client will explicitly declare its existing xhigh default instead of relying on the server fallback. No server change is required.

## Verification and final outcome

Both configuration files now use `options.reasoningEffort: "xhigh"`. `python3 /tmp/t3-qwen-reasoning-inspection/capture_default_effort.py` reran the original loopback request recorder against the installed model configuration:

| Selection | Outgoing `reasoning_effort` | Requests | Exit code |
|---|---|---:|---:|
| no `--variant` argument | xhigh | 1 | 0 |
| `--variant low` | low | 1 | 0 |

Both checks pass, 2/2. The default now reaches the API and does not override an explicit selection. Other captured sampling and output parameters match the preceding experiment. Results: `/var/folders/5p/9fk78x3d20gd_yln3r0_m4k00000gn/T/qwen-variant-capture-9hq6hsv8/results.json`.

No inference, decode throughput, TTFT, prefill throughput, peak VRAM, MTP acceptance or task-quality measurements were performed. The client and repository template are corrected. The setup guide and `STATUS.md` record the explicit xhigh default and the [verified picker](2026-09-12-t3-opencode-reasoning-fix.md).
