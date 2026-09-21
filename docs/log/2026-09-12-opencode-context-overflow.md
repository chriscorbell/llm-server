# 2026-09-12 OpenCode overflows during presentation research

Status: concluded
Profile: ad hoc client diagnosis, server unchanged

## Hypothesis

The reported context overflow came from accumulated tool results during the task, rather than the short initial user message.

## Configuration

T3 Code 0.0.40, OpenCode 1.18.30, `llm-server/qwen38` at xhigh, context 131,072 and configured output limit 32,768. Captured requests in the preceding experiments use an effective `max_tokens` of 32,000. No setting has changed for this diagnosis.

Inspect the read-only OpenCode SQLite database at `~/.local/share/opencode/opencode.db`, session `ses_f6784251cffezVy1dWKoKpoEPI`, directory `/Users/chris/Code/ai-builders`. T3 thread `30d330ff-3951-41af-9ea3-b20bbf4ed233` contains the reported error. The user supplied one 241-character instruction to create deck2 about llm-server, Pi, OpenCode and Pier.

```sql
SELECT id, time_created, data
FROM message
WHERE session_id = 'ses_f6784251cffezVy1dWKoKpoEPI'
ORDER BY time_created;

SELECT message_id, data
FROM part
WHERE session_id = 'ses_f6784251cffezVy1dWKoKpoEPI'
ORDER BY time_created;
```

Baseline: [working reasoning mapping](2026-09-12-t3-opencode-reasoning-fix.md). This diagnosis concerns context growth, not reasoning-option transport.

## Measurements

| Observation | Value |
|---|---:|
| First request input, uncached plus cached | 24,022 tokens |
| Eleventh completed model call input, uncached plus cached | 98,237 tokens |
| Eleventh call output | 624 tokens |
| Effective output reservation | 32,000 tokens |
| Input budget with that reservation | 99,072 tokens |
| Rejected request's reported input lower bound | 99,073 tokens |
| Automatic compaction input | 15,057 tokens |
| Automatic compaction output | 7,927 tokens |
| Stored summary text | 12,397 characters |

No throughput, TTFT, prefill, peak VRAM, MTP acceptance or task-quality comparison was performed.

## What happened

The first request at 2026-09-13T01:57:29Z fit. Qwen made successive tool calls, including a 39,598-character read of deck1, a 41,642-character recursive directory listing, a 28,652-character STATUS read and three research reports totalling 42,763 characters. After the eleventh model response, another three tool results added 5,269 characters.

At 02:01:17Z, the next request failed with the exact error reported by Chris:

```text
This model's maximum context length is 131072 tokens. However, you requested 32000 output tokens and your prompt contains at least 99073 input tokens, for a total of at least 131073 tokens. Please reduce the length of the input prompt or the number of requested output tokens. (parameter=input_tokens, value=99073)
```

OpenCode created an automatic overflow-compaction message immediately afterward. At 02:03:17Z, it completed the summary, emitted `session.compacted`, added a synthetic continuation message and started another build response. The task was already continuing while diagnosis was in progress. No interruption or retry was issued by this investigation.

`ssh vllm 'cd ~/Code/llm-server && ./scripts/gpu-health.sh'` returned a healthy API and captured GPU/container state to `/tmp/qwen-context-error-health.txt`. The inference container was not restarted.

## Outcome

The transcript confirms that accumulated agent context caused the rejection. The initial user message was accepted. Inspection of compaction timing is still in progress.

## Consequences

No configuration changes. Do not increase the server context limit or reduce reasoning effort solely because the original user message was short; the failing request already contained many tool results. Investigate earlier compaction and output reservation before changing the server.

## Compaction timing reproduction

The 30 tool calls before the first failure produced 214,412 characters of completed output. The last completed model response reported 98,861 total tokens, only 211 below OpenCode's effective 99,072-token threshold. Its following tool results added 5,269 characters that were absent from that count.

OpenCode 1.18.30's `session/overflow.ts` computes `context - maxOutputTokens` when `model.limit.input` is absent. In that branch, `compaction.reserved` is not subtracted. With an explicit input limit, it instead subtracts the default 20,000-token compaction buffer from that limit. Merely increasing the global `compaction.reserved` setting would not fix this model's current branch. [Pinned source](https://github.com/anomalyco/opencode/blob/v1.18.30/packages/opencode/src/session/overflow.ts).

A loopback fixture drives the installed OpenCode CLI through a file-read tool call. Its scripted response reports exactly the real failing run's last successful usage, 98,237 input and 624 output tokens, then permits a local fixture read. The next request is classified as compaction or a normal build request. The fixture uses a dummy credential, no MCP, and permission only for reading its temporary file. It does not replay Chris's presentation task or contact vllm.

```bash
python3 /tmp/t3-qwen-reasoning-inspection/check_compaction.py
```

Baseline result: two model requests, both normal build requests, `max_tokens: 32000`, exit code 0. The assertion reports exactly `FAIL: next build request is sent without compaction`. This reproduces the late-compaction decision rather than simulating GPU inference or relying on token estimates. Artifact: `/var/folders/5p/9fk78x3d20gd_yln3r0_m4k00000gn/T/qwen-compaction-check-xnd6619f/requests.json`.

The T3 UI still marked the real thread Failed after displaying the compaction summary. The OpenCode database nevertheless records a subsequent successful build response with 56,229 input tokens and 690 output tokens by 02:05:55Z. Thus the first automatic recovery worked; the visible Failed label did not mean the backend had stopped. No continuation message was sent by this investigation.

## Final outcome

The initial prompt was accepted. File and tool results accumulated until the next request could not fit alongside the 32,000-token output allowance. The error's 99,073 figure is a lower bound, so it does not establish that the request exceeded the limit by only one token.

The installed CLI fixture reproduces the late-compaction decision. A separate [input-budget experiment](2026-09-12-opencode-compaction-headroom.md) tests and installs earlier compaction. The server, model and reasoning picker are not the cause of this overflow. T3's stale Failed state during OpenCode's automatic recovery remains a separate client behavior; this repository does not contain T3's application source.
