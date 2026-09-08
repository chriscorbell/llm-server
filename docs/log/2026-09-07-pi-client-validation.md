# 2026-09-07 Pi client validation

Status: concluded
Profile: A, existing live engine unchanged

## Hypothesis

Pi with explicit Qwen sampling, reasoning replay and early compaction can use the existing 96K server for local coding work without an engine change.

## Configuration

Client variable: Pi 0.85.1 (`@earendil-works/pi-coding-agent`) installed on mbp, replacing OpenCode for this evaluation. Model and settings are recorded in `clients/pi/`. This installed version supersedes the proposed 0.73.1 configuration in the [readiness assessment](../research/2026-09-07-pi-readiness.md).

```bash
./eval/run.py --client pi --model llm-server/qwen38 --thinking xhigh \
  --tasks 02 --timeout 900 --out eval/results/2026-09-07-pi-smoke
```

Baseline: [OpenCode coding and direct API vision](2026-09-07-task-suite-baseline.md).

## Measurements

- Pi read-only tool check completed in 8.4 seconds, calling `ls` and `read` before a correct project description. Two requests used 4,201 and 4,818 actual prompt tokens, with 80 and 150 output tokens. Concurrency 1.
- First coding run took 52.8 seconds and scored 0/1 because the new runner omitted `cwd=workdir`. It edited the tracked source fixture while verification ran in the unchanged temporary copy. This is an invalid model-quality result.
- Decode, TTFT, prefill, MTP acceptance and peak VRAM have not been measured in this experiment.

## What happened

The verification error was `AssertionError [ERR_ASSERTION]: 0 !== 1` at `test/retry.test.ts:38`. The transcript showed the model reading the main repository and repairing `eval/tasks/02-ts-fix-bug/fixture/src/retry.ts` there. Restored its intentional `< options.attempts` bug and added `cwd=workdir` to the agent subprocess. No other fixture changes were present.

## Outcome

Read-only tools work. Coding, image and compaction checks remain in progress.

The corrected isolated bug-fix run passed 1/1 in 16.3 seconds. A full eight-task run is in progress, with transcripts under `eval/results/2026-09-07-pi-baseline/`. Added an opt-in metadata-only Pi extension and RPC check for reasoning replay, sampling, effort and manual compaction using the production settings. These checks run in a temporary project and record no request headers or raw payloads.

Full-suite result: **8/8 passed**, with xhigh thinking and concurrency 1. Individual task times were 45.4, 24.7, 55.1, 25.1, 16.3, 25.7, 138.5 and 31.6 seconds in task order. The longest actual prompt in the first seven tasks was 23,400 tokens (task 07). Vision passed through Pi with the original screenshot attachment. A fresh login shell resolves `LLM_SERVER_API_KEY` without inheriting it from this process. The compaction/request-contract run follows separately with the same production configuration.

The first contract run confirmed xhigh, `max_tokens=32768`, temperature 1.0, top_p 0.95, top_k 20, and historical reasoning alongside assistant tool calls. Automatic compaction succeeded at 62,009 context tokens and reported 12,245 estimated tokens afterward. The test then redundantly requested immediate manual compaction and Pi returned `RuntimeError: Already compacted`. This is a test-runner error after successful automatic compaction. Updated the runner to accept a completed automatic compaction, and use manual compaction only if the threshold was not reached. Rerunning to verify the remembered requirement and medium effort.

Final contract result: **pass**. Ten normal model requests confirmed the sampling preset, xhigh and medium effort, and reasoning replay through tool calls. Automatic compaction triggered at 62,578 context tokens and reported 12,689 estimated tokens afterward. Pi then wrote the exact original `ticket_id,owner,created_utc` header to `report.txt`, without the requirement being repeated or stored in a project file. The request and event records are under `eval/results/2026-09-07-pi-contract-complete/`. The compaction output estimate is a Pi heuristic, not an exact API input count. The suite's eight tasks took 362.4 seconds total, excluding independent verification. These small fixtures establish working tools, images and compaction; they do not establish parity with hosted frontier models on complex repositories.

The first post-compaction request actually used 22,618 input tokens and took 12.264 seconds to its first streamed delta. The next two xhigh tool-follow-up requests used 22,877 and 22,964 tokens and started in 0.901 and 0.974 seconds. Switching to medium then took 12.568 seconds at 23,041 tokens. All were concurrency 1. The effort change alters Qwen's prompt template, so this observation is consistent with losing prefix reuse; there was no separate cache-counter measurement for that request. Keep xhigh stable during a session. TTFT here includes the first reasoning token, not the completed user-visible answer.

## Consequences

Installed `~/.pi/agent/models.json` and merged settings on mbp. The API key is referenced through `LLM_SERVER_API_KEY` and is absent from the JSON. Added Pi support to the task runner with explicit temporary working directories.
