# Pi against this server

Pi runs on the MacBook and uses its local tools to read, edit and test code. The model request goes over Tailscale to Qwen on `vllm`.

## Install the checked configuration

Pi 0.85.1 from `@earendil-works/pi-coding-agent` is the validated client version. Keep the API key in the environment; do not copy it into JSON.

```bash
npm install -g @earendil-works/pi-coding-agent@0.85.1
mkdir -p ~/.pi/agent/extensions
cp clients/pi/models.json ~/.pi/agent/models.json
cp clients/pi/settings.json ~/.pi/agent/settings.json
ln -sfn "$PWD/clients/pi/extensions/llm-server" ~/.pi/agent/extensions/llm-server
test -n "$LLM_SERVER_API_KEY"
pi --list-models qwen38
```

The symlink keeps the installed extension identical to the checked one; edit it here and restart Pi. The `.pi/prompts/` templates in the repository root load only when Pi runs from this repository and the project is trusted.

The model declares the server's real 98,304-token window. Pi begins compaction above 57,344 estimated context tokens, reserving 32,768 for the response plus 8,192 tokens of headroom.

Sampling is explicit because Qwen's thinking preset and MTP acceptance both depend on it. The model supports low, medium and xhigh effort. xhigh is the daily-driver default; unsupported Pi levels are hidden.

## Run it

From a project directory:

```bash
pi
```

The MacBook is already configured. Keep Tailscale connected, open a terminal in the project you want to work on, and run `pi`. Describe the change and ask it to run the project's checks. Use `pi -c` to continue the most recent session in that directory. `/compact` summarizes a long conversation; automatic compaction is also enabled.

For a one-shot check:

```bash
pi --model llm-server/qwen38 --thinking xhigh --tools read,ls -p \
  "Use your tools to read README.md, then describe this project in one sentence."
```

Pi's tools run on the MacBook. A shell command requested by Qwen therefore runs in the current MacBook directory, never on `vllm`, unless the command itself uses SSH.

Keep the thinking level at xhigh for normal work. In the checked conversation, cached tool follow-ups at about 23K input tokens started in 0.9 to 1.0 seconds. The first request after compaction took 12.3 seconds at 22.6K input tokens. A pause after adding a large file or compacting is expected; these timings measure the first reasoning token at concurrency 1, not the final answer.

## The llm-server extension

`clients/pi/extensions/llm-server/` is one Pi extension in seven modules. Everything it does follows from measurements in `docs/log/`: prefix reuse is worth 12 seconds per request at 23K tokens, the window is small, and the server is a single box that sometimes goes away.

- **Request numbers in the footer.** After every response the status line shows time to first token, the share of the prompt served from vLLM's prefix cache, and how many tokens remain before automatic compaction. A prompt of 8K tokens or more that hits the cache below 50% raises a warning with the cold-prefill time. The cache share needs vLLM started with `--enable-prompt-tokens-details`, which the compose file passes; without it the line shows the prompt size only.
- **Warm-up after compaction.** `session_compact` fires, and once Pi is idle the extension sends the compacted context with `max_tokens` 1 so vLLM prefills it while you type. `/warm` does the same by hand. The next real request is compared with the warm-up payload and a mismatch is reported, so a silent cache miss cannot hide. Measured effect is in [the log entry](../../docs/log/2026-09-07-pi-quality-of-life.md).
- **Thinking-level guard.** Changing effort rewrites Qwen's template and invalidates the prefix. Pi cannot block the change, so the extension states the cost in seconds and warms the cache with the new level if Pi is idle.
- **Server diagnosis.** A request that ends in an error triggers a `/health` check. If the engine answers, the message says the error was request-level. If not, the extension watches `/health` every 10 seconds for up to 15 minutes and says when it is back. `/vllm` shows health plus the container state over SSH; `/vllm logs 60` tails the engine log. Output appears in the transcript and is not sent to the model.
- **Notification.** A run longer than 15 seconds posts a macOS notification when Pi is waiting for input.
- **Handoff.** `/handoff <goal>` is Pi's example handoff extension unchanged: it writes a focused prompt from the current conversation and opens a new session with it in the editor. Prefer it over `/compact` when switching tasks; the new session prefills in a second or two instead of 12.
- **Tool output budget.** `read` and `bash` results are cut to 24 KB or 600 lines instead of Pi's 50 KB or 2000. `read` keeps the head and tells the model to page with offset and limit; `bash` keeps the tail. Override with `PI_TOOL_BUDGET_KB` and `PI_TOOL_BUDGET_LINES`.

Set `PI_LLM_SERVER_LOG=/path/file.jsonl` to have the extension append one JSON line per response and warm-up with token counts and timings. It never records prompt text. `eval/pi_warmup.py` uses this to measure the warm-up.

## Prompt templates for this repository

From the repository root, Pi offers three templates that encode the recording duty in `AGENTS.md`:

- `/log <topic-slug> [hypothesis]` copies `docs/log/TEMPLATE.md` to a dated entry and fills in the hypothesis and configuration section.
- `/status <what changed>` rewrites the stale lines of `STATUS.md` and links the entry.
- `/bench [sizes] [--thinking]` runs `scripts/bench.py` at each prompt size and reports a table against the current Findings without writing a log entry.

## Settings worth knowing

`quietStartup` hides the banner, `showCacheMissNotices` prints Pi's own notice on a large cache miss, and `shellCommandPrefix` loads the aliases from `~/.zshrc` into the non-interactive shell Pi uses for `bash`. `hideThinkingBlock` is off; turn it on in `~/.pi/agent/settings.json` if xhigh output is too noisy.

## Why these compatibility settings

- vLLM's Qwen template expects a system role rather than an OpenAI developer role.
- The running vLLM accepts `reasoning_effort` and maps it into the Qwen template.
- The server streams thinking as `reasoning`; Pi 0.85.1 retains that field name and sends it back with assistant tool calls.
- `max_tokens` is known to work on the running endpoint.
- Provider retries stay off so Pi's visible three-attempt retry loop handles transient errors once rather than nesting two retry loops.

If the server profile changes, update `contextWindow` here and in the installed `~/.pi/agent/models.json` together.
