# 2026-09-23 Claude Code effort override

Status: concluded
Profile: a-int4draft (unchanged)
Author: agent thread on mbp

Follows [Claude Code as a client](2026-09-23-claude-code-client.md).

## Hypothesis

`claude-qwen --effort medium` selects medium effort, as the client guide claimed.

## Configuration

Before: the launcher exported `CLAUDE_CODE_EFFORT_LEVEL=xhigh`. After: it passes `--effort ${CLAUDE_QWEN_EFFORT:-xhigh}` unless the arguments already contain `--effort`.

```diff
-export CLAUDE_CODE_EFFORT_LEVEL="${CLAUDE_QWEN_EFFORT:-xhigh}"
-exec claude "$@"
+for arg in "$@"; do
+  case "$arg" in
+    --effort|--effort=*) exec claude "$@" ;;
+  esac
+done
+exec claude --effort "${CLAUDE_QWEN_EFFORT:-xhigh}" "$@"
```

## Measurements

Claude Code 2.1.280, interactive, startup banner read in tmux. No model requests were timed.

| Invocation | Before | After |
|---|---|---|
| `claude-qwen` | xhigh | xhigh |
| `claude-qwen --effort medium` | xhigh | medium |
| `claude-qwen --effort=low` | not tested | low |
| `/effort`, one step up from low | not tested | medium for the session |
| `claude-qwen mcp list` | not tested | exit 0 |

## What happened

The claim was wrong. `CLAUDE_CODE_EFFORT_LEVEL` overrides `--effort`, as the Claude Code environment variable reference states, so the flag was silently ignored.

`/effort` inside a session also writes `modelSettings.qwen38.effortLevel` to `~/.claude/settings.json`. The test created that entry and it was removed afterwards. The global `effortLevel: "high"` was not changed. The launcher's `--effort` flag overrides the saved value at the next launch, so a saved `qwen38` value has no effect under `claude-qwen`.

## Outcome

Confirmed after the change: the default stays xhigh, and `--effort` and `/effort` now take effect.

## Consequences

Updated `clients/claude-code/claude-qwen`, its README and the `STATUS.md` current-state line.
