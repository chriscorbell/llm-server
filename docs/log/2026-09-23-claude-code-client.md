# 2026-09-23 Claude Code as a client

Status: concluded; effort handling superseded by [2026-09-23 Claude Code effort override](2026-09-23-claude-code-effort-override.md)
Profile: a-int4draft (unchanged)
Author: agent thread on mbp

## Hypothesis

The running vLLM build serves Anthropic's Messages API, so Claude Code 2.1.280 on mbp can use Qwen3.8-27B through `ANTHROPIC_BASE_URL` without a translation proxy.

## Configuration

No server change. Engine reports version `0.27.2rc1.dev77+gac7509e2b`, container `qwen38`, up 9 days and healthy.

Client launcher: [`clients/claude-code/claude-qwen`](../../clients/claude-code/claude-qwen). Final environment:

```
ANTHROPIC_BASE_URL=http://100.103.136.98:8000
ANTHROPIC_AUTH_TOKEN=<API_KEY from compose/.env>
ANTHROPIC_MODEL=qwen38
ANTHROPIC_DEFAULT_OPUS_MODEL=qwen38
ANTHROPIC_DEFAULT_SONNET_MODEL=qwen38
ANTHROPIC_DEFAULT_HAIKU_MODEL=qwen38
CLAUDE_CODE_SUBAGENT_MODEL=qwen38
CLAUDE_CODE_MAX_CONTEXT_TOKENS=131072
CLAUDE_CODE_EFFORT_LEVEL=xhigh
CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1
```

Task for every Claude Code run: a two-file Node project where `add` returns `a - b`; prompt "node test.js fails. Fix the bug in math.js, then run node test.js to confirm." Pass means `node test.js` prints `PASS` afterwards.

## Measurements

All at concurrency 1.

| Check | Result |
|---|---|
| `POST /v1/messages` with `x-api-key` header only | 401 `{"error":"Unauthorized"}` |
| Same with `Authorization: Bearer` | 200 in 0.37 s, thinking block then text, `stop_reason: end_turn` |
| Streaming tool call, one `Read` tool | 200 in 1.11 s, `tool_use` block with `input_json_delta` chunks, `stop_reason: tool_use` |
| Claude Code `-p`, inherited desktop-app environment | 401 after 184 s of retries |
| Claude Code `-p`, clean environment, effort from user settings (`high`) | 500 after 179 s: `Unexpected reasoning effort high. Supported types are xhigh (default), medium, and low.` |
| Claude Code `-p`, clean environment, `--effort medium` | pass, 7 turns, 48.2 s; context window reported as 200,000 |
| Same, xhigh and `CLAUDE_CODE_MAX_CONTEXT_TOKENS=131072` | pass, 6 turns, 30.7 s; context window reported as 131,072 |
| `claude-qwen -p` from the desktop-app environment | pass, 7 turns, 26.5 s |
| `claude-qwen` interactive TUI in tmux, xhigh | pass, 1 min 41 s wall, of which 1 min 24 s thinking before the edit |

Token usage in the 30.7 s run: 12,888 uncached input, 18,304 cache creation, 53,248 cache read, 910 output. Time to first token, decode speed and VRAM were not measured.

## What happened

The Messages route exists on this build and returns structured thinking and tool-use blocks, including when streaming. The Hermes streaming problem with `qwen3_xml` plus the `qwen3` reasoning parser did not appear on this route in one streamed tool call.

Two client-side failures:

1. Launched from inside the Claude desktop app, the child `claude` inherited host-session variables (`CLAUDE_CODE_ENTRYPOINT`, `CLAUDE_CODE_SDK_HAS_HOST_AUTH_REFRESH` and others) and did not send the configured token. The launcher unsets them; with that, the run from the same polluted environment passes.
2. `~/.claude/settings.json` sets `effortLevel: "high"`. Claude Code forwards it for the unrecognized `qwen38` model and the server rejects it, which Claude Code treats as a retryable 500. `CLAUDE_CODE_EFFORT_LEVEL` overrides the setting.

`CLAUDE_CODE_MAX_CONTEXT_TOKENS` is the documented variable for a gateway model whose window differs from Claude Code's assumption (code.claude.com/docs/en/model-config, "Correct the window for a gateway or custom model ID"). Auto-compaction near the limit was not exercised.

## Outcome

Confirmed. Claude Code works against the existing server with environment variables only. Validated: file read, edit, shell execution and a passing test, headless and interactive. Not tested: compaction, subagents, image input, long sessions.

## Consequences

Added `clients/claude-code/` with the launcher and a setup guide. The key lives in `~/.config/llm-server/api-key`, mode 0600, and `~/.local/bin/claude-qwen` links to the launcher. Promoted a Finding to `STATUS.md`. No server change.
