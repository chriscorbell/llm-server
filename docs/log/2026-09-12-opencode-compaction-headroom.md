# 2026-09-12 Give OpenCode headroom for tool results

Status: concluded
Profile: ad hoc client configuration, server unchanged

## Hypothesis

An explicit Qwen input limit will activate OpenCode's existing compaction buffer and trigger summarization before the overflowing request in the captured presentation run.

## Configuration

Baseline: [context overflow diagnosis](2026-09-12-opencode-context-overflow.md). T3 Code 0.0.40 and OpenCode 1.18.30 on mbp. Change only `limit.input` in the installed OpenCode model and repository template:

```diff
           "limit": {
             "context": 131072,
+            "input": 98304,
             "output": 32768
           },
```

98,304 is the total context minus the declared 32,768-token output allowance. OpenCode's default 20,000-token compaction buffer then gives a computed trigger of 78,304 tokens. Its unchanged effective 32,000-token output allowance leaves 20,768 tokens between that trigger and the server's 99,072-token input budget, for newly appended tool results. The model's total context and output limits remain unchanged.

Test the installed CLI using the loopback fixture from the diagnosis:

```bash
python3 /tmp/t3-qwen-reasoning-inspection/check_compaction.py --input-limit 98304
```

## Measurements

| Check using 98,861 previous-response tokens | Baseline | Explicit input limit |
|---|---|---|
| Next request is compaction | false | true |
| Normal build resumes after summary | no summary performed | true |
| Effective output allowance | 32,000 tokens | 32,000 tokens |
| Reasoning effort | xhigh | xhigh |
| Process exit | 0 | 0 |

The isolated input-limit override passes 1/1 compaction decision check. There are three requests: build, compaction, build. Baseline has two build requests with no intervening compaction. No model inference, throughput, TTFT, prefill, peak VRAM, MTP acceptance or task-quality comparison was performed.

## What happened

The first override fixture omitted the unchanged context and output fields. OpenCode validates each config source before merging, so it exited 1 with no requests:

```text
Error: Configuration is invalid at OPENCODE_CONFIG_CONTENT
Missing key provider.llm-server.models.qwen38.limit.context
Missing key provider.llm-server.models.qwen38.limit.output
```

The corrected override repeats context 131072 and output 32768 while adding input 98304. It exits 0 and reports `PASS: compacts before the next build request`. Artifact: `/var/folders/5p/9fk78x3d20gd_yln3r0_m4k00000gn/T/qwen-compaction-check-bvkfsrj3/requests.json`.

## Outcome

The isolated correction works. Installed configuration and final reproduction are pending.

## Consequences

The planned change is confined to this Qwen provider. Other models and global compaction settings remain as configured. The real presentation task is already recovering, so it will not be restarted or given another prompt.

## Installed verification and outcome

The existing config was backed up as `~/.config/opencode/opencode.jsonc.backup-headroom-20260912-220830`, mode 0600. The installed model and repository template now declare context 131072, input 98304 and output 32768. All three reasoning variants remain present.

Rerunning the original command without an input-limit override now passes 1/1: build request, compaction request, resumed build request, exit code 0. All requests retain `max_tokens: 32000` and `reasoning_effort: "xhigh"`. Artifact: `/var/folders/5p/9fk78x3d20gd_yln3r0_m4k00000gn/T/qwen-compaction-check-cx_don0n/requests.json`.

This verifies the installed client's decision with the captured usage value. The 78,304-token threshold is calculated from the pinned client source, not established by a boundary sweep. A single tool batch larger than the remaining reserve can still overflow; this change provides headroom rather than an absolute guarantee for arbitrary tool output.

The real presentation session has continued with successful model responses after its original compaction. It was not restarted or replayed. This experiment does not establish that an already-running OpenCode instance reloaded the new metadata; new instances do load it. `STATUS.md` and the OpenCode setup guide now record the input budget and its reason. The server and all other providers are unchanged.

## Active runtime readback

Read-only `GET /provider` on the active T3-managed OpenCode service at `http://127.0.0.1:58327`, with `x-opencode-directory: /Users/chris/Code/ai-builders`, returned the old in-memory limit `{ "context": 131072, "output": 32768 }`. `GET /session/status` returned the presentation session as `busy`. This establishes that the current runtime has not loaded `limit.input`; the installed correction applies when that instance is reloaded. Provider inventory refresh alone is not evidence that an active session's model metadata was replaced.

The active process was left running to preserve the presentation work. Reload T3/OpenCode after this task finishes to activate the new budget in that runtime. No restart, task cancellation or duplicate prompt was issued.
