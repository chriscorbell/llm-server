# 2026-09-21 Pi advisor flow with Fable 5.1 through claude-bridge

Status: concluded
Profile: client configuration on mbp against `a-int4draft`
Author: agent thread on mbp

## Hypothesis

pi-advisor-flow can keep Qwen3.8 as the Executor and route consequential decisions to a frontier model, first an OpenAI Codex model and then Claude Fable 5.1 through pi-claude-bridge, without changing the server.

## Configuration

```bash
pi install npm:pi-advisor-flow@0.7.0
pi install npm:pi-claude-bridge@0.8.0
cp clients/pi/advisor.json ~/.pi/agent/advisor.json
cp clients/pi/claude-bridge.json ~/.pi/agent/claude-bridge.json
ln -sfn "$PWD/clients/pi/extensions/claude-bridge-api" ~/.pi/agent/extensions/claude-bridge-api
```

`advisor.json`: Executor `llm-server/qwen38` at medium, Advisor `claude-bridge/claude-fable-5-1` at xhigh, all gates on, ten calls per session, `gateFailureMode` `block-tool`, git context `summary`, secret redaction on, Herdr off, `alwaysOn` false. `claude-bridge.json`: AskClaude tool off, `plan` `max`, strict MCP, auto-memory off. Claude Code CLI 2.1.278 is installed at `~/.local/bin/claude`; the account has an OAuth login and extra usage off.

Smoke test: one-shot `pi -p` from an empty directory in a temporary agent directory with `alwaysOn` true, asking the Executor to call `ask_advisor` once with a one-sentence question and echo the answer.

## Measurements

| Configuration | Prompt tokens, first request |
|---|---|
| Five packages after the 2026-09-20 trim | 13,254 |
| Plus pi-advisor-flow, flow off | 14,168 |
| Plus pi-advisor-flow, `alwaysOn` | 14,142 |
| Plus pi-claude-bridge, AskClaude off | 14,168 |

| Advisor | Result | Wall time of the one-shot |
|---|---|---|
| `openai-codex/gpt-6-astra` | answered; provider usage 373 in, 107 out, cost 0.009 | 12.5 s |
| `claude-bridge/claude-fable-5-1`, no shim | `No API provider registered for api: claude-bridge` | 13.9 s |
| `claude-bridge/claude-fable-5-1`, shim without isolation | `prompt-capture: no capture for this 1194-char system prompt` | 16.4 s |
| `claude-bridge/claude-fable-5-1`, shim with `cacheRetention: "none"` | answered and named itself Fable 5.1; bridge spawn to done 5.2 s; usage reported as zero | 12.5 s |

## What happened

The Codex advisor worked on the first try. The bridge worked as Pi's main model (`--model claude-bridge/claude-fable-5-1` returned `BRIDGE_OK`) but not as the Advisor, for two reasons found in the sources:

1. Pi's `registerProvider` keeps an extension's `streamSimple` inside the session's provider composer (`core/provider-composer.js`) and never registers it in pi-ai's api-provider registry. pi-advisor-flow's `model-stream.ts` calls `stream()` from `@earendil-works/pi-ai/compat`, which resolves the api from that registry and throws.
2. The bridge's normal path resolves the call's system prompt against prompts it captured from Pi's own agent (`prompt-capture.ts`). The Advisor's 1,194-character prompt matches nothing, so the bridge refuses rather than send Claude Code a prompt with none of Pi's context.

The bridge routes any call marked `cacheRetention: "none"` to `isolatedStreamFn`: a fresh Claude Code process with `tools: []`, `persistSession: false`, `maxTurns: 1` and `systemPrompt: context.systemPrompt`, reading the last user message as the prompt. The Advisor sends one user message, so that path fits. The shim in `clients/pi/extensions/claude-bridge-api/index.ts` reads the bridge's stream function from `globalThis[Symbol.for("claude-bridge:activeStreamSimple")]`, wraps it to add the marker, and registers it with `registerApiProvider` at load and again on `session_start` in case the bridge loads later.

An `-e` probe extension observed earlier loads before directory extensions; the same applies here, which is why registration is retried on `session_start`.

## Outcome

Confirmed. Qwen consults Fable 5.1 through `ask_advisor`. Two limits of the isolated path: the bridge reports zero usage for these calls, so Pi's `/cost` cannot account for them, and `advisorEffort` is not forwarded, so Claude Code decides its own thinking. Neither blocks the workflow.

## Consequences

Both packages are pinned in `clients/pi/settings.json` and installed. `clients/pi/advisor.json`, `clients/pi/claude-bridge.json` and the shim extension are checked in; the README's install block and a new "Advisor flow with Fable 5.1" section describe them. STATUS.md lists the packages. The flow is opt-in per session with `/advisor`. Not measured: how often the plan, failure and completion gates fire on a real coding session and what they cost in wall time on the single-sequence server.
