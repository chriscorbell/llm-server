# 2026-09-21 Pi advisor through Anthropic OAuth

Status: concluded
Profile: client configuration on mbp

## Hypothesis

Replacing pi-claude-bridge with pi-anthropic-auth and routing advisor calls through Pi's configured provider will let Qwen consult Fable 5.1 with native token usage and the selected reasoning effort.

## Configuration

Baseline: [advisor through claude-bridge](2026-09-21-pi-advisor-flow.md). Pi is already 0.86.1 on mbp; this experiment does not upgrade it. The installed advisor effort is `high`, while the previous repository example says `xhigh`; preserve the installed choice.

Installed migration:

```bash
pi install npm:@gotgenes/pi-anthropic-auth@3.0.1
pi remove npm:pi-claude-bridge@0.8.0
node clients/pi/patch-advisor.mjs
```

Advisor changes from `claude-bridge/claude-fable-5-1` to `anthropic/claude-fable-5-1`. Keep the executor, gates and per-session opt-in unchanged. Back up the existing client configuration and obsolete bridge extension before removal.

## Measurements

All 8 installed extensions load with 0 errors through Pi 0.86.1's `DefaultResourceLoader`. The auth diagnostics command and `ask_advisor` are registered. Applying the transport patch a second time succeeds without changes. No inference measurements yet. Pi has no Anthropic credential in its auth store; interactive `/login anthropic` has been requested before live validation.

## What happened

Upstream's [architecture documentation](https://github.com/gotgenes/pi-anthropic-auth/blob/main/docs/architecture.md) identifies a coverage gap: direct pi-ai compatibility calls bypass the registered OAuth wrapper. pi-advisor-flow 0.7.0 uses that path in `src/model-stream.ts`. Pi 0.86.1 exposes `ctx.modelRegistry.streamSimple`, which uses the configured provider and accepts the advisor's provider-neutral reasoning option. The installed correction is a version-checked patch to the advisor package, without replacing the global Anthropic API registry.

## Outcome

Confirmed by the final live validation below. Both consultation paths use the new OAuth wrapper and report token usage.

## Consequences

No inference server changes. Prior uncommitted advisor setup files are present and form the migration baseline.

### Installation checkpoint

The replacement is installed, the old bridge is uninstalled, and both installed and repository advisor configurations select Anthropic Fable 5.1 at high effort. The old bridge config and shim were backed up to `~/.pi/backups/2026-09-21-anthropic-auth-195135/` and removed from the active setup. The patch modifies both `src/model-stream.ts` and `dist/index.js`, so source inspection matches the executed bundle. No global API registry override is installed.

### Print-mode manual command limitation

After Chris completed `/login anthropic`, Pi lists `anthropic/claude-fable-5-1` with a 1M-token context window. A print-mode attempt using `pi --no-session --mode json -p '/advisor-manual ...'` exited before sending an Anthropic request. The command starts background UI work, and Pi disposes the print session before that work finishes:

```text
Error: This extension ctx is stale after session replacement or reload. Do not use a captured pi or command ctx after ctx.newSession(), ctx.fork(), ctx.switchSession(), or ctx.reload(). For newSession, fork, and switchSession, move post-replacement work into withSession and use the ctx passed to withSession. For reload, do not use the old ctx after await ctx.reload().
```

The stack points to `CommandRuntime.requestManualRender` in advisor's bundle. This attempt does not measure the Anthropic transport. The next live check activates `/advisor` and asks Qwen to call `ask_advisor`, whose tool execution is awaited.

### Live consultation checkpoint

The Qwen tool round trip passes 1/1. Qwen sent exactly one `ask_advisor` call, Fable answered the arithmetic question with the requested marker, and Qwen relayed it. A temporary fetch observer saw model `claude-fable-5-1`, `thinking.type: adaptive`, `output_config.effort: high`, the OAuth billing system header, and HTTP 200. The tool reported 4 uncached input tokens, 669 cache-write tokens and 30 output tokens. Qwen's two requests used 1,432 and 1,591 input tokens at medium thinking, concurrency 1.

A separate SDK check kept the manual consultation alive and received `MANUAL_ADVISOR_OK` with 461 input and 156 output tokens, also HTTP 200 with the billing header and high effort. Its first test runner disposed the session on `agent_end`, before Pi finished handling its custom message, and hit the same stale-context error during teardown. The runner must await `session.waitForIdle()` before disposing. This error followed a successful answer and is separate from the request transport.

### Final validation

The manual SDK check now waits for `session.waitForIdle()` after receiving the answer. It exits 0 with empty stderr. The final live checks pass 2/2:

| Check | Context and concurrency | Result | Advisor usage |
|---|---|---|---|
| Qwen `ask_advisor` round trip | Qwen 1,432 then 1,591 input tokens, medium; advisor 673 total input tokens, high; concurrency 1 | One tool call, arithmetic answer 42 and `AUTH_ADVISOR_OK` relayed by Qwen | 4 uncached input, 669 cache-write, 30 output tokens |
| Manual consultation in a persistent SDK session | Advisor 461 input tokens, high; Qwen continuation 47 input tokens; concurrency 1 | `MANUAL_ADVISOR_OK`, then Qwen continuation; complete in 4.918 s including Qwen | 461 input, 178 output tokens |

Both outgoing Anthropic requests specify `claude-fable-5-1`, adaptive thinking and `output_config.effort: high`. Both include the `x-anthropic-billing-header` system block and receive HTTP 200. Provider usage is nonzero in both tool/message details. No decode speed, TTFT, prefill, VRAM or MTP measurements were taken; the test changes only the hosted advisor client path.

Reproduce the tool check from an empty directory after installing the pinned packages, applying the patch and completing `/login anthropic`:

```bash
pi --model llm-server/qwen38 --thinking medium \
  --no-session --no-context-files --no-skills --tools ask_advisor --mode json -p \
  '/advisor' \
  'Call ask_advisor exactly once with this question: What is 17 plus 25? Answer in one sentence and include AUTH_ADVISOR_OK. Then return the advisor answer. This is a read-only integration check; do not inspect files, plan changes, or call other tools.'
```

The manual check creates an in-memory SDK session, loads the installed extensions, subscribes to `advisor-manual-result` and `agent_end`, sends `/advisor-manual Answer exactly MANUAL_ADVISOR_OK.`, awaits the result and `session.waitForIdle()`, then disposes. A temporary fetch observer checks only the model, thinking configuration, billing-header presence and HTTP status. Test artifacts for this run are under `/tmp/pi-anthropic-advisor-verify/`.

The installed package list and advisor JSON match their repository copies. Qwen remains the default executor at medium, Fable 5.1 is the advisor at high, and `alwaysOn` remains false. Syntax checks pass for the patch script and patched bundle; `git diff --check` passes. The patch also succeeds when reapplied.

The finding about the configured-provider path is promoted to `STATUS.md`. The README pins Pi 0.86.1 and documents installation, login, patch reapplication and the headless-command limitation. Automatic gate frequency, long-session behavior and the terminal dialog rendering were not measured.

### Update behavior clarification

The installed Pi 0.86.1 `pi update --help` confirms that plain `pi update` updates Pi only. Upstream package documentation says version-pinned npm packages are skipped by `pi update --extensions` and `pi update --all`. Advisor is pinned to 0.7.0, so those routine commands leave the installed patch in place. Explicitly reinstalling advisor can replace the patched files; rerun `node clients/pi/patch-advisor.mjs` afterward. Changing advisor to another version requires patch review, and a future Pi API change could also require a compatibility fix. No update or inference check was run for this clarification.
