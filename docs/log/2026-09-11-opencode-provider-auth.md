# 2026-09-11 OpenCode provider authentication

Status: concluded
Profile: ad hoc client configuration, server `a-int4draft` unchanged

## Hypothesis

Storing the existing server credential in OpenCode's auth file and removing the empty environment override will make `llm-server/qwen38` usable without exporting a key in the launching shell.

## Configuration

OpenCode 1.18.29 on mbp already lists `llm-server/qwen38`, with text and image input, tool calling, xhigh reasoning, a 98,304-token context window and 32,768-token output limit. Its global config references an unset `LLM_SERVER_API_KEY`, and `~/.local/share/opencode/auth.json` has no entry for this provider.

The planned change removes this line from `~/.config/opencode/opencode.jsonc`:

```diff
-        "apiKey": "{env:LLM_SERVER_API_KEY}"
```

The existing credential from `~/.pi/agent/auth.json` will be copied into OpenCode's private auth file under `llm-server`, using OpenCode's `{"type":"api","key":"<server key>"}` format and mode 0600. Other credentials and settings stay intact. The key is never printed or recorded in the repository.

Baseline: the provider template and setup guide in `clients/opencode/`, plus the [previous client checks](2026-09-07-task-suite-baseline.md). This is an authentication check, not a model performance comparison.

## Measurements

| Check | Before change |
|---|---|
| `opencode models llm-server` | 1 model, `llm-server/qwen38` |
| `GET /v1/models` without authentication | HTTP 401 |
| `GET /v1/models` with the existing Pi server credential | HTTP 200 |
| Live API model ID and context limit | `qwen38`, 98,304 tokens |

Decode throughput, time to first token, prefill throughput, peak VRAM, MTP acceptance and task-suite pass count were not measured.

## What happened

The hostname `vllm` resolves to `100.103.136.98` on mbp. Unauthenticated discovery returns exactly:

```json
{"error":"Unauthorized"}
```

The existing Pi credential successfully authenticates to the configured server URL. OpenCode's provider listing alone does not establish that requests will authenticate.

## Outcome

Pending an OpenCode request with `LLM_SERVER_API_KEY` absent.

## Consequences

No server changes are required. Local authentication installation and an isolated tool-call smoke check are next.

## Authentication installed

The existing Pi credential was copied to `~/.local/share/opencode/auth.json` under `llm-server` with type `api`, and the file's mode was verified as 0600. The environment override was removed from the global config. Both files were backed up beside their originals with suffix `.backup-20260911-232844`, also mode 0600. The current default model was not changed.

An OpenCode smoke check is running in a temporary directory with `LLM_SERVER_API_KEY` removed from its environment. It must read a file containing a random marker through a tool and return the marker exactly. The file is isolated from the working repository.

## Verification result

The smoke check completed with exit code 0 in 16.26 seconds at concurrency 1. OpenCode emitted a completed `read` tool event for `provider-check.txt`, then returned its exact marker, `OPENCODE_QWEN_OK_1888bb11`, with only surrounding whitespace. There were no stderr errors. The check passed 1/1; the eight-task evaluation suite was not rerun.

OpenCode reported 18,704 input tokens and 93 output tokens for the tool-call step. The final step reported 1,435 uncached input tokens, 17,472 cached input tokens and 88 output tokens. These are client-reported counts; this check did not capture request-level TTFT or decode throughput. Reasoning was configured as xhigh; the client reported zero reasoning tokens, which does not establish that server thinking was disabled.

The invocation was equivalent to:

```bash
env -u LLM_SERVER_API_KEY opencode run \
  --dir /var/folders/5p/9fk78x3d20gd_yln3r0_m4k00000gn/T/opencode-qwen-check-qfalspfv \
  -m llm-server/qwen38 --format json --title 'Qwen provider verification' \
  'Read provider-check.txt using your file-reading tool. Reply with only the exact contents of that file. Do not modify any files, run shell commands, delegate work, or access external services.'
```

The temporary directory contains `stdout.jsonl` and `stderr.log` for this run. Authentication and a streamed tool round trip work with the installed OpenCode 1.18.29 client and current server. This supersedes the pending outcome above. `STATUS.md` now records the configured client, and `clients/opencode/README.md` explains persistent authentication and model selection.
