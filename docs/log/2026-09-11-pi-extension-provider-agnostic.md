# 2026-09-11 Pi extension made provider-agnostic

Status: concluded
Profile: A (a-int4draft), client-side change only

## Hypothesis

The `llm-server` Pi extension loads for every provider Pi knows about, but four of its nine modules assumed the selected model was qwen38 on vllm. With `openai-codex` now logged in on mbp, a hosted model would have received the "Server constraints" block sized for a 98K window, the 24 KB tool cap, a warm-up request after every compaction (billed as a full prompt on a hosted API) and a `/health` probe of vllm after any provider error. Gating each module on the selected model at runtime should make the extension correct for any provider without a second extension or a second install path.

## Configuration

One extension, same directory and symlink. `shared.ts` gains `LOCAL_PROVIDER` (`llm-server`, override `PI_LOCAL_PROVIDER`), `isLocalServer(model)`, `localModel(ctx)` and `toolBudget(model)`; `SMALL_WINDOW_TOKENS` is 131072 (override `PI_SMALL_WINDOW_TOKENS`).

| Module | Before | After |
|---|---|---|
| cache-warmup | warmed after every compaction, `/warm` for any model | returns unless the model's provider is `llm-server`; `/warm` says why |
| thinking-guard | Qwen template warning for any model | `llm-server` only |
| server-health | `/health` probe after any error; `/vllm` needed the local model selected | probe only for `llm-server` errors; `/vllm` finds the server in the model registry |
| context-notes | one static "Server constraints" block, window from whichever model started the session | block per model: window and compaction lines only under 128K, cap line only when a cap applies, compaction-summary line always |
| tool-output-budget | 24 KB / 600 lines for any model | under 128K only, or when `PI_TOOL_BUDGET_KB`/`PI_TOOL_BUDGET_LINES` are set; Pi's 50 KB / 2000 otherwise |
| web | fixed 24 KB cap in the tool description and output | same per-model rule via the execute context |
| request-stats | status key `llm-server`, "prefix cache" wording | status key `request`, provider-neutral wording; works with any provider that reports cached tokens |
| notify, handoff | unchanged | unchanged |

Baseline for comparison: [extension and warm-up](2026-09-07-pi-quality-of-life.md).

## Measurements

One-shot `pi -p` runs from an empty directory with `--tools read`, asking the model to quote the constraints block and list its tools.

| Metric | llm-server/qwen38 (low) | openai-codex/gpt-5.5 |
|---|---|---|
| Prompt tokens | 4,743 | 4,171 |
| Time to first token | 2.39 s | 5.34 s |
| Total | 9.60 s | 11.91 s |
| Constraints block | window, cap and compaction lines, quoted back verbatim | compaction line only (model declined to quote; verified by calling the handler directly) |

Calling the `before_agent_start` handler directly with three model records: qwen38 at 98,304 tokens gets three lines and a 24 KB cap; gpt-5.3-codex-spark at 131,072 and gpt-5.5 at 272,000 get the compaction line and no cap.

## What happened

`openai-codex/gpt-5.4-mini` is rejected by the Codex backend for ChatGPT accounts ("The 'gpt-5.4-mini' model is not supported when using Codex with a ChatGPT account"); the extension logged the error through `request-stats` and, because the provider is not `llm-server`, did not probe vllm. gpt-5.5 answered normally.

The type check (tsc 5.9 against Pi 0.85.1's bundled types) reports no new errors. Five pre-existing ones remain: missing `@types/turndown`, two `AbortSignal | undefined` passes in `web.ts`, and the untyped `pi.events.on` payload in `cache-warmup.ts`. Pi loads extensions through jiti without type checking, so they have no runtime effect.

## Outcome

Confirmed. The same installed extension now serves qwen38 with the small-window behaviour it was written for and leaves a 272K hosted model with Pi's defaults plus the compaction note.

## Consequences

`clients/pi/README.md` describes the gating and adds an "Other providers" section. `STATUS.md` line for Pi updated. No server change.
