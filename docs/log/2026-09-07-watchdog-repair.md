# 2026-09-07 Watchdog recovery repair

Status: concluded
Profile: A, existing live engine unchanged

## Hypothesis

Correcting the GPU signature expression and retaining an incident across health checks prevents false restarts while allowing recovery after three failed checks.

## Configuration

Recovery implementation is the variable. Baseline: [false-trigger investigation](2026-09-07-watchdog-false-triggers.md). The candidate removes empty regex alternatives, persists pending faults and attempt counters, captures diagnostics, waits up to 600 seconds for initialization and limits recovery to two attempts per incident.

```bash
shellcheck watchdog/xpu-wedge-watchdog.sh watchdog/install.sh
scp watchdog/xpu-wedge-watchdog.sh vllm:/tmp/xpu-wedge-watchdog-candidate.sh
ssh vllm 'chmod +x /tmp/xpu-wedge-watchdog-candidate.sh && /tmp/xpu-wedge-watchdog-candidate.sh --self-test'
```

## Measurements

- Four offline scenarios passed on Linux in 12.6 seconds: healthy no-op, unrelated network message ignored after three failures, one pending GPU fault causing exactly one recovery at threshold, and recovery attempts stopping at the configured limit.
- The successful fake recovery produced exactly one diagnostics file.
- Inference speed and memory were not measured; these tests use a temporary local HTTP server and a fake recovery command.

## What happened

The old expression matches arbitrary text because each leading `|` creates an empty alternative. The repaired expression requires a listed GPU fault. Persistent fault state retains a one-time reset until health failures reach the threshold. Persistent attempt state survives watchdog process restarts.

## Outcome

Candidate passes the offline checks. Deployment remains pending final review.

Final review moved the attempt limit into the shared recovery function so health-only mode obeys it too. Diagnostic commands now have 15-second limits and the recovery command has a 60-second limit, preventing a stuck GPU query or Docker command from blocking recovery indefinitely. Journal snapshots retain monotonic timestamps so a repeated fault message is distinguishable from an earlier occurrence. Five offline scenarios passed on Linux at 01:09 UTC, including the added health-only limit check. ShellCheck, Bash syntax and whitespace checks passed.

## Consequences

Updated the script, systemd state/log directories and installer restart behavior. The currently running watchdog is still the old version; inference has not been restarted.

Deployment update: committed as `2367484`, pushed from mbp, pulled on vllm and installed with `bash watchdog/install.sh`. All five checks passed again before installation. The unit became active at 2026-09-08 01:13:19 UTC, bootstrapped a 500-line snapshot in `/var/lib/xpu-wedge-watchdog/kernel.snapshot`, and is enabled for boot. The installed script matches the repository copy. Qwen remained healthy with its original `StartedAt=2026-09-08T00:31:21.980018882Z`. No new physical GPU failure has occurred to validate real recovery; the tests exercise detection and control flow with a temporary HTTP server.
