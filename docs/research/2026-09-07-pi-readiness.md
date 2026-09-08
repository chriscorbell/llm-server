# Making the B70 server a dependable coding backend for Pi

Checked 2026-09-07 from mbp. Chris's priorities are coding quality, responsive tool use, and a server that requires little maintenance. This is an assessment and proposed setup, not an installation or an inference tuning run.

Implementation update: the MacBook now uses Pi 0.85.1 from `@earendil-works/pi-coding-agent`, with a different configuration schema from the 0.73.1 proposal below. Use the [installed configuration and launch guide](../../clients/pi/README.md). All eight tasks and the reasoning/compaction check passed. The watchdog repair is deployed. See [Pi validation](../log/2026-09-07-pi-client-validation.md) and [watchdog repair](../log/2026-09-07-watchdog-repair.md).

## Decision

Keep the B70, the pinned Qwen3.8-27B GPTQ checkpoint, the current 98,304-token limit, MTP4, prefix caching, and one active generation. Keep thinking at xhigh initially. Fix automatic recovery before trying a different engine or weight format. Connect Pi directly to the existing API, then judge quality on real repository tasks.

Pi runs on the MacBook, reads and edits local files, and executes local tools. The server receives model requests and returns reasoning, tool calls, and text. Pi executes the requested tools and sends their results back. A working connection does not establish equal coding ability to the models Chris uses through hosted agents.

## Current state and the reliability gap

The server is healthy. Its container started at `2026-09-08T00:31:21.980018882Z`, has Docker restart policy `unless-stopped`, and binds only to the Tailscale IP. The watchdog is enabled and active. No service restart occurred during this assessment.

The watchdog's GPU matcher accepts arbitrary kernel messages. The journal shows network interface messages used as recovery triggers. In the inspected interval beginning 23:00 UTC there were 21 recovery commands, 19 timeout messages, and two successful recoveries. Real GPU errors also exist, so those counts do not mean all restarts were unnecessary. The reproduction, exact logs, and additional source findings are in [watchdog false triggers](../log/2026-09-07-watchdog-false-triggers.md).

The first repair should:

1. Remove empty alternatives from the GPU signature patterns.
2. Remember a genuine fault through the configured three failed health checks, clearing it after healthy recovery.
3. Save kernel, GPU, and container diagnostics before restarting.
4. Allow model initialization to finish and bound repeated recovery attempts.
5. Verify ordinary logs never trigger recovery and a one-time real fault followed by three failed checks triggers exactly one recovery. Use an offline fake recovery command, then observe ordinary service startup without causing a GPU fault.

The reproducible configuration also needs correction before handoff. `compose/.env.example` still declares 131,072 tokens and utilization 0.92, while the working instance uses 98,304 and 0.95. Copying the example does not reproduce the working server. Existing logs call this the BF16 KV profile; its actual flags are `--dtype float16 --kv-cache-dtype auto`, so the attention KV dtype follows FP16. Preserve profile names as historical identifiers and correct prose rather than silently changing the runtime dtype.

## Quality and latency evidence

The current suite passed seven small coding tasks through OpenCode, plus one direct API vision check. Task 07 searched a 76,686-byte generated file and read selected regions. That is useful repository navigation, but it does not validate a 96K conversation or recovery after compaction. No repeated quality comparison for the exact GPTQ artifact against full precision is available here. See [baseline](../log/2026-09-07-task-suite-baseline.md) and its saved transcript under `eval/results/2026-09-07-profile-a-baseline/07-long-context.log`.

Recorded cold versus cached TTFT at a nominal 32,768-token prompt, one concurrent request, was 19.52 versus 1.11 seconds. The corresponding decode rates were 37.2 and 45.7 tok/s. At a nominal 90,000-token cold prompt, TTFT was 81.80 seconds. These are prior measurements, not a Pi forecast. [Context experiment](../log/2026-09-07-decode-versus-context.md)

Measurement caveat: `scripts/bench.py` currently approximates prompt length from characters and reports the requested length rather than the API's actual `usage.prompt_tokens`. It also reports prefill as nominal input length divided by TTFT. Treat those context labels and prefill rates as approximate until actual token counts are recorded. The tool-call and final-answer latencies of a thinking model also differ from first reasoning-token latency.

For a useful quality baseline, replay 10 to 20 representative tasks from Chris's repositories in isolated checkouts, including multi-file features, non-obvious bugs, preservation of existing behavior, and a session continued after compaction. Run repeated attempts with the same limits. Record first-attempt passes, regressions, retries, total task seconds, time to first tool call, cold/warm TTFT, actual prompt tokens, completion tokens, and cache hits. Keep the existing suite as a quick regression check. This evaluation is proposed, not implemented or run.

## Pi integration checked against a specific release

`pi` was not found on mbp's PATH and `~/.pi/agent` was absent. The npm registry returned `@mariozechner/pi-coding-agent` version `0.73.1`, git commit `781152fc24841dc54b22284514604048ebe5e2c9`, requiring Node >=20.6.0. Source inspection used that commit, not an assumption about the website's latest documentation.

Pi's release source accepts streamed `reasoning_content`, `reasoning`, or `reasoning_text` and remembers the received field name in the thinking block. It writes that field back on later assistant messages. The running vLLM normalizes either reasoning alias for Qwen's template. This supports a direct connection; an actual Pi tool round trip remains the acceptance check. [Pi receive and replay source](https://github.com/badlogic/pi-mono/blob/781152fc24841dc54b22284514604048ebe5e2c9/packages/ai/src/providers/openai-completions.ts#L309-L335), [Pi replay](https://github.com/badlogic/pi-mono/blob/781152fc24841dc54b22284514604048ebe5e2c9/packages/ai/src/providers/openai-completions.ts#L812-L836), [local parser inspection](../log/2026-09-07-agent-client-contract.md).

Use the standard `openai` thinking format with `supportsReasoningEffort: true` on this engine. The `qwen-chat-template` branch in Pi 0.73.1 sends `enable_thinking` and `preserve_thinking` but omits the selected effort. The standard branch sends the mapped effort, and the installed vLLM converts it into template controls. Hide Pi's unsupported `minimal` and `high` levels rather than passing invalid values. For the initial thinking-only configuration, hide `off` too; a non-thinking mode needs its own sampling preset. [Pi effort mapping](https://github.com/badlogic/pi-mono/blob/781152fc24841dc54b22284514604048ebe5e2c9/packages/ai/src/providers/openai-completions.ts#L553-L585), [model configuration](https://github.com/badlogic/pi-mono/blob/781152fc24841dc54b22284514604048ebe5e2c9/packages/coding-agent/docs/models.md#thinking-level-map).

The proposed `~/.pi/agent/models.json` for **Pi 0.73.1** is:

```json
{
  "providers": {
    "llm-server": {
      "baseUrl": "http://vllm:8000/v1",
      "api": "openai-completions",
      "apiKey": "LLM_SERVER_API_KEY",
      "compat": {
        "supportsStore": false,
        "supportsDeveloperRole": false,
        "supportsReasoningEffort": true,
        "supportsUsageInStreaming": true,
        "maxTokensField": "max_tokens",
        "thinkingFormat": "openai"
      },
      "models": [{
        "id": "qwen38",
        "name": "Qwen3.8-27B on vllm",
        "reasoning": true,
        "thinkingLevelMap": {
          "off": null,
          "minimal": null,
          "low": "low",
          "medium": "medium",
          "high": null,
          "xhigh": "xhigh"
        },
        "input": ["text", "image"],
        "contextWindow": 98304,
        "maxTokens": 32768
      }]
    }
  }
}
```

The bare `LLM_SERVER_API_KEY` name is the environment-variable syntax in this release. Set that variable securely to the existing server key. The current website documents newer `$ENV_VAR` interpolation and `samplingParams`; neither should be copied into a pinned release without verifying support. Pi 0.73.1's inspected model schema and API provider do not contain `samplingParams`. [Pinned value resolution docs](https://github.com/badlogic/pi-mono/blob/781152fc24841dc54b22284514604048ebe5e2c9/packages/coding-agent/docs/models.md#value-resolution), [current website](https://pi.dev/docs/latest/models).

The running server already loads temperature 1.0, top_p 0.95, and top_k 20 from the model's generation config. Let the initial Pi connection inherit those defaults, and verify the outgoing request does not override them. `preserve_thinking` defaults true in the pinned template. No proxy is indicated by the source inspection.

Proposed `~/.pi/agent/settings.json` additions:

```json
{
  "defaultProvider": "llm-server",
  "defaultModel": "qwen38",
  "defaultThinkingLevel": "xhigh",
  "compaction": {
    "enabled": true,
    "reserveTokens": 40960,
    "keepRecentTokens": 20000
  }
}
```

The 40,960-token reserve is an initial choice, not a measured optimum. It allows 32,768 output tokens plus 8,192 tokens of headroom. Pi's threshold calculation would start compaction above 57,344 tokens of estimated context. Large tool results can still require special handling, so verify a session near the limit. Keep the declared model window accurate; do not use the model's native 262K limit. [Pinned compaction calculation](https://github.com/badlogic/pi-mono/blob/781152fc24841dc54b22284514604048ebe5e2c9/packages/coding-agent/src/core/compaction/compaction.ts#L217-L222), [settings](https://github.com/badlogic/pi-mono/blob/781152fc24841dc54b22284514604048ebe5e2c9/packages/coding-agent/docs/settings.md).

Before adopting this configuration: capture a synthetic tool round trip, confirm xhigh and medium requests differ as intended, verify reasoning survives replay, run a file-edit task and screenshot task, and continue a session through compaction. These checks have not run during this assessment.

## Optional performance work after readiness

Keep stable instructions, tool definitions, reasoning effort, and earlier messages within a session so prefix caching can reuse them. Prefer focused file searches and bounded tool output over repeatedly inserting whole repositories. Do not disable thinking to chase a lower initial delay without measuring task success and total time.

The best optional throughput candidate is the INT4 draft overlay, which reduces the cost of proposing speculative tokens while retaining target-model verification. The author's cached agentic measurements on another B70 improved decode from 48.04 to 66.99 tok/s at 8K, 54.40 to 65.92 at 16K, and 44.83 to 56.20 at 64K, all concurrency one with 128 generated tokens. Quality evidence is only 12/15 on both arms of a small comparison. This is a reason to test the overlay, not a promised improvement on this server. [Upstream audit and original sources](2026-09-07-agentic-coding-upstream.md)

A new engine/kernel pair could reduce patch maintenance, but vLLM 0.28.0 alone does not establish that the newer mixed-GDN fixes are included. Keep immutable pins and compare a complete compatible stack in a separate experiment. Do not mix an engine upgrade, draft change, and cache change. CPU governor and prefill chunk tuning already produced null results locally; they are not priorities.

FP8 KV is a capacity option only if longer sessions prove necessary. Prior measurements found slower cold prefill and no clear decode benefit. Exact-model coding quality with FP8 KV remains untested. No evidence from this assessment justifies purchasing hardware or changing kernel/driver versions now.

## Readiness criteria

The server is ready for ordinary use when recovery behaves correctly, one documented configuration reproduces it, Pi completes multi-turn tool use with reasoning intact, a session survives compaction, and repeated representative coding tasks meet Chris's quality expectations. Freeze the working versions at that point. Optional speed experiments should have a measured benefit and an immediate rollback to that baseline.
