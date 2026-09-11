# 2026-09-11 Vision task edited the source fixture

Status: concluded, regression and live validation passed
Profile: a-int4draft, MTP4

## Hypothesis

The screenshot's original absolute path led the model to edit the repository's source fixture instead of the disposable task directory, causing a false vision failure and contaminating later runs.

## Configuration

The serving configuration is unchanged. The task runner now copies screenshot attachments beside the temporary editable files. On macOS it also launches the client through `sandbox-exec` with writes to this repository denied. The parent runner can still save results; the agent can write to its temporary working directory. Failed and timed-out task directories are retained for inspection.

```bash
python3 eval/test_isolation.py
python3 eval/run.py --client pi --model llm-server/qwen38 --thinking xhigh \
  --timeout 600 --out eval/results/2026-09-11-tuning/mtp4-tasks-isolated
```

The regression invokes the real `run_task` path with a tiny fake Pi executable that follows the image attachment's directory, reproducing the observed mistake. It checks that the temporary copy is fixed, the original fixture stays broken, and a repository canary cannot be overwritten by the child.

## Measurements

The original MTP4 suite passed 7/8 and reported this exact error for vision:

```text
FAIL: the main content still sits under the fixed sidebar
```

The failing task took 28.4 seconds, generated 1,460 tokens, used eight tool calls and reached 10,891 prompt tokens, concurrency 1 and xhigh. The local isolation regression failed before the fix in 0.188 seconds and passed afterward in 0.229 seconds.

## What happened

The transcript shows correct visual diagnosis and the correct CSS change, `margin-inline-start: var(--sidebar-width)`, but its edit targeted `/Users/chris/Code/llm-server/eval/tasks/08-vision-css/fixture/styles.css`. The model then ran the source fixture's verifier and saw a pass. The outer runner verified its unchanged temporary copy and failed.

The original source fixture's single added line was removed, restoring the intended broken input. No other fixture change appeared in Git. GPU diagnostics were captured before any restart in `eval/results/2026-09-11-tuning/mtp4-vision-failure-health.log`; the container and health endpoint remained healthy. The trace and the fast regression identify the cause directly, so no GPU-reset or model-quality hypothesis experiment is needed for this failure.

## Outcome

The local isolation defect is reproduced and fixed. The original 7/8 result remains recorded but does not establish a vision regression from MTP4. A fresh full suite with the corrected runner is in progress.

## Consequences

Attachments no longer expose source-fixture locations. The model under test cannot write to this repository on mbp. A focused regression protects both properties. No serving setting is promoted on the strength of the invalid vision result.

### Live validation

The corrected MTP4 Pi suite passed 8/8 in 222.7 seconds, generating 13,653 tokens with 49 tool calls, xhigh and concurrency 1. Maximum prompt lengths ranged from 7,621 to 12,689 tokens. This single suite uses fewer generated tokens than the MTP3 run, so its wall-time difference is not a pure engine-speed measurement. No source fixture changed.

### Request-metrics collection correction

The completed task run had no optional `mtp4-isolated-requests.jsonl`. Inspection raised `FileNotFoundError: [Errno 2] No such file or directory`. The extension catches write failures because its logging is best effort. The macOS repository-write rule also blocked this file when the child tried to append to the requested results path.

Hypothesis: collecting child metrics outside the protected repository and copying them back from the parent preserves both isolation and request logging. The runner now redirects `PI_LLM_SERVER_LOG` into a temporary metrics directory for each task. After the client finishes, the parent appends that file to the requested destination. Serving flags are unchanged.

The focused regression now asks its fake Pi to append a metrics record while attempting the forbidden canary write. Before the correction it failed in 0.208 s with `AssertionError: 'prior metrics\\n' != 'prior metrics\\nrequest metrics\\n'`. Afterward it passed in 0.168 s, including the attachment and canary checks. The live missing metrics cannot be recovered. Task pass counts, wall times and token counts from saved Pi transcripts remain valid; no request-level latency claim uses that missing file. Subsequent live suites will verify the corrected metrics path.

Live metrics validation passed during the 0.29.0 suite: its first two passing tasks produced ten response records in the requested repository results file. Records contain numeric prompt/cache counts, TTFT, total response time and stop reason. The parent-copy path works while the repository remains protected.
