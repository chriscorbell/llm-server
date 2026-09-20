# 2026-09-11 Pi browser extension on agent-browser

Status: concluded
Profile: A (a-int4draft), client-side change only

## Hypothesis

Pi 0.85.1 accepts image blocks in tool results and qwen38 declares image input, so a tool that screenshots a real browser should let the model inspect a running web app visually, and an accessibility snapshot with refs should let it interact without screenshots for most steps. Wrapping the `agent-browser` CLI rather than embedding Playwright keeps the extension dependency-free and reuses its daemon, snapshot-and-ref system and annotated screenshots.

## Configuration

New extension `clients/pi/extensions/browser/index.ts` (one file, no npm dependencies), symlinked to `~/.pi/agent/extensions/browser`. Tools: `browser_open`, `browser_snapshot`, `browser_act`, `browser_screenshot`, `browser_console`, `browser_eval`; command `/browser [close]`. Session per working directory, headed by default, viewport 1280x800, JPEG quality 80. Screenshots become `{ type: "image" }` blocks when `ctx.model.input` includes `image`, else a path.

```bash
brew install agent-browser        # 0.37.1
agent-browser install             # Chrome 153.0.8010.36 for mac-arm64, 182 MB
ln -sfn "$PWD/clients/pi/extensions/browser" ~/.pi/agent/extensions/browser
```

Candidates considered before building: pi-agent-browser-native (screenshots as file paths, large tool schema), pi-chrome (companion Chrome extension plus authorization gates), pi-browser-harness (40 tools over CDP), pi-chrome-use (one free-form `browser_execute` tool), pi-playwright (a skill over playwright-cli driven through bash), pi-browser-use (chrome-devtools-mcp, about 18K tokens of schema). None returned inline images with a small typed surface.

Baseline for comparison: none; first browser capability for this client.

## Measurements

Harness run (fake Pi, real CLI) against a local demo page: open 1,125 ms including browser launch, fill 74 ms, click 80 ms, snapshot 33 ms, annotated screenshot 203 ms (57 KB JPEG at 1280x800).

One-shot `pi --thinking low` with qwen38, tools `read` plus the five browser tools, task: open the page, fill a name, click Greet, screenshot, report the greeting text, the background colour and console errors.

| Request | Prompt tokens | Cached | Time to first token | Stop |
|---|---|---|---|---|
| 1 open | 6,065 | 0 | 3.05 s | tool |
| 2 fill | 6,221 | 4,992 | 0.71 s | tool |
| 3 click | 6,388 | 4,992 | 0.78 s | tool |
| 4 console | 6,534 | 4,992 | 0.87 s | tool |
| 5 screenshot | 6,750 | 4,992 | 1.00 s | tool |
| 6 answer | 10,110 | 5,824 | 3.32 s | stop |

Prompt growth from request 5 to 6 is 3,360 tokens; the console and screenshot tool calls and text account for roughly 300, so one 1280x800 JPEG costs about 3,000 tokens on this model. The answer named the greeting "Hello Ada" and described the background as a very dark navy, which matches the page's `#1e1e2e`; it listed the `boom` error and the warning and log lines. Its claim that the error fires on submit is wrong (it fires 100 ms after load), a model inference not a tool fault.

Provider check: the six tool schemas plus guidelines add 6,065 minus 4,743 equals about 1,300 prompt tokens on an empty project (the earlier one-shot with `read` only measured 4,743).

## What happened

Two CLI behaviours needed workarounds. `errors --clear` returns `success` but leaves the buffer intact in 0.37.1, so `browser_console` tracks a per-session cursor of errors already reported and clears only the console buffer. A command other than `open` at cold daemon start fails with "Daemon process exited during startup with no error output"; the extension rewrites that to "No browser page is open for this project. Call browser_open with a URL first." Once the daemon is warm, a snapshot without `open` returns `about:blank`, which is clear enough.

The type check (tsc 5.9 against Pi's bundled types) reports no errors for the extension.

## Outcome

Confirmed. The model interacts through refs and only pays for images when it asks for them, and the same extension degrades to file paths for text-only models such as gpt-5.3-codex-spark.

## Consequences

`clients/pi/README.md` gains "The browser extension" with install steps and environment variables; `STATUS.md` Pi line updated. `agent-browser` and Chrome for Testing are installed on mbp under Homebrew and `~/.agent-browser/browsers/`. No server change.
