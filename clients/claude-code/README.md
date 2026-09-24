# Claude Code against this server

vLLM serves Anthropic's Messages API at `/v1/messages` alongside the OpenAI endpoints, so Claude Code talks to the server directly. No proxy and no server change are needed.

## Install on mbp

```bash
mkdir -p ~/.config/llm-server
ssh vllm 'grep "^API_KEY=" ~/Code/llm-server/compose/.env | cut -d= -f2-' > ~/.config/llm-server/api-key
chmod 600 ~/.config/llm-server/api-key
ln -sf ~/Code/llm-server/clients/claude-code/claude-qwen ~/.local/bin/claude-qwen
```

Then run `claude-qwen` instead of `claude`. Every argument passes through, so `claude-qwen -p "..."` and `claude-qwen --resume` work. Plain `claude` keeps using your Anthropic login.

## What the launcher sets

| Variable | Value | Why |
|---|---|---|
| `ANTHROPIC_BASE_URL` | `http://100.103.136.98:8000` | No `/v1`; Claude Code appends `/v1/messages`. |
| `ANTHROPIC_AUTH_TOKEN` | contents of the key file | Sent as `Authorization: Bearer`, which is what vLLM checks. `x-api-key` gets a 401. |
| `ANTHROPIC_MODEL` and the opus, sonnet, haiku and subagent model variables | `qwen38` | Background tasks and subagents otherwise request Claude model IDs the server does not have. |
| `CLAUDE_CODE_MAX_CONTEXT_TOKENS` | `131072` | Claude Code otherwise assumes 200,000 for an unknown model and compacts too late. |
| `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC` | `1` | No telemetry or update checks for these sessions. |

## Reasoning effort

`claude-qwen` starts at xhigh. It passes `--effort xhigh` unless you give your own `--effort`, so `claude-qwen --effort medium` works. To change the default, set `CLAUDE_QWEN_EFFORT=medium`. Inside a session, `/effort` changes the level for that session. It also saves a `qwen38` entry under `modelSettings` in `~/.claude/settings.json`, but the launcher's flag overrides that saved value at the next launch.

Only `low`, `medium` and `xhigh` work. The server rejects `high` and `max` with a 500, which Claude Code retries for about three minutes. Without the launcher's default, Claude Code would send `high` from your `effortLevel` user setting.

Do not set `CLAUDE_CODE_EFFORT_LEVEL` instead. It overrides both `--effort` and `/effort`, which locks the session to one level.

## Environment

The launcher also unsets `ANTHROPIC_API_KEY`, `CLAUDE_CODE_OAUTH_TOKEN` and the host-session variables that a parent Claude Code session exports. Inherited from the desktop app, they override the token and the server returns 401 after about three minutes of retries.

## Known behavior

- The startup banner warns that claude.ai connectors are disabled. That is expected: a custom token takes precedence over the claude.ai login.
- Costs shown in `/cost` and JSON output use Claude pricing and mean nothing here.
- Thinking blocks carry signatures that the real Anthropic API will not accept. Do not resume a Qwen session with plain `claude`.
- Your global `CLAUDE.md`, skills, plugins and MCP servers load as usual. Cache creation across a short session was 18,304 to 19,968 tokens, so the first request pays a cold prefill. Its time to first token was not measured; for scale, cold TTFT at 32,590 input tokens is about 18.6 s.
- Remote Control and MCP tool search are disabled by Claude Code whenever the base URL is not Anthropic's.
