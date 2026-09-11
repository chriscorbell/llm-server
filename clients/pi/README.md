# Pi against this server

Pi runs on the MacBook and uses its local tools to read, edit and test code. The model request goes over Tailscale to Qwen on `vllm`.

## Install the checked configuration

Pi 0.85.1 from `@earendil-works/pi-coding-agent` is the validated client version. The API key lives in `~/.pi/agent/auth.json`, which Pi reads for custom providers and creates with mode 0600. Do not copy it into `models.json`, which is checked in.

```bash
npm install -g @earendil-works/pi-coding-agent@0.85.1
mkdir -p ~/.pi/agent/extensions
cp clients/pi/models.json ~/.pi/agent/models.json
cp clients/pi/settings.json ~/.pi/agent/settings.json
ln -sfn "$PWD/clients/pi/extensions/llm-server" ~/.pi/agent/extensions/llm-server
(cd clients/pi/extensions/llm-server && npm install)
```

Write the server key into Pi's auth file once, replacing the placeholder, then confirm the model is available:

```bash
umask 077
cat > ~/.pi/agent/auth.json <<'EOF'
{ "llm-server": { "type": "api_key", "key": "change-me" } }
EOF
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

For small edits with clear checks, run `pi --thinking medium`. Two eight-task runs finished in 132.9 and 145.9 seconds; xhigh took 199.6 and 222.7 seconds. Every run passed 8/8, at concurrency 1 with per-task maximum prompts from 7.1K to 12.7K tokens. Xhigh remains the default for harder repository work because these fixtures do not test complex changes or compaction. [Effort measurements](../../docs/log/2026-09-11-pi-reasoning-effort.md).

Choose the thinking level before starting a task, because changing it invalidates the cached prefix. In the checked conversation, cached tool follow-ups at about 23K input tokens started in 0.9 to 1.0 seconds. The first request after compaction took 12.3 seconds at 22.6K input tokens. A pause after adding a large file or compacting is expected; these timings measure the first reasoning token at concurrency 1, not the final answer.

## The llm-server extension

`clients/pi/extensions/llm-server/` is one Pi extension in nine modules. Everything it does follows from measurements in `docs/log/`: prefix reuse is worth 12 seconds per request at 23K tokens, the window is small, and the server is a single box that sometimes goes away.

- **Request numbers in the footer.** After every response the status line shows time to first token, the share of the prompt served from vLLM's prefix cache, and how many tokens remain before automatic compaction. A prompt of 8K tokens or more that hits the cache below 50% raises a warning with the cold-prefill time. The cache share needs vLLM started with `--enable-prompt-tokens-details`, which the compose file passes; without it the line shows the prompt size only.
- **Warm-up after compaction.** `session_compact` fires, and once Pi is idle the extension sends the compacted context with `max_tokens` 1 so vLLM prefills it while you type. `/warm` does the same by hand. The next real request is compared with the warm-up payload and a mismatch is reported, so a silent cache miss cannot hide. Measured effect is in [the log entry](../../docs/log/2026-09-07-pi-quality-of-life.md).
- **Thinking-level guard.** Changing effort rewrites Qwen's template and invalidates the prefix. Pi cannot block the change, so the extension states the cost in seconds and warms the cache with the new level if Pi is idle.
- **Server diagnosis.** A request that ends in an error triggers a `/health` check. If the engine answers, the message says the error was request-level. If not, the extension watches `/health` every 10 seconds for up to 15 minutes and says when it is back. `/vllm` shows health plus the container state over SSH; `/vllm logs 60` tails the engine log. Output appears in the transcript and is not sent to the model.
- **Notification.** A run longer than 15 seconds posts a macOS notification when Pi is waiting for input.
- **Handoff.** `/handoff <goal>` is Pi's example handoff extension unchanged: it writes a focused prompt from the current conversation and opens a new session with it in the editor. Prefer it over `/compact` when switching tasks; the new session prefills in a second or two instead of 12.
- **Web search and fetch without keys.** `web_search` queries the SearXNG container on `vllm` (`compose/docker-compose.yml`, service `searxng`, JSON on port 8080 over Tailscale) and returns numbered results with title, URL, snippet and the engines that agreed. `web_fetch` downloads a page, reduces it to its article with Readability, converts it to markdown with absolute links, and returns text, JSON and markdown bodies as-is; GitHub blob URLs are rewritten to the raw file. Both outputs share the 24 KB budget. `SEARXNG_URL` overrides the endpoint. The two npm dependencies live in the extension's own `package.json`, hence the `npm install` in the install steps. SearXNG runs without a rate limiter because it is single-user behind Tailscale; upstream engines occasionally refuse a query, and the result list shows which engines answered.
- **System prompt additions.** The web tools carry `promptSnippet` and `promptGuidelines`, so they appear in Pi's "Available tools" list and add two guideline bullets: search for anything version-, date- or error-specific instead of answering from memory, and fetch a specific page rather than an index. A `before_agent_start` handler appends a static "Server constraints" block naming the window and compaction threshold, the tool-output cap, and that a compaction summary is prior work rather than new instructions. Together they cost 246 prompt tokens (3,975 to 4,221 on an empty project). The block never changes within a session, so it stays inside vLLM's cached prefix; editing its text invalidates every cached prefix on the server.
- **Tool output budget.** `read` and `bash` results are cut to 24 KB or 600 lines instead of Pi's 50 KB or 2000. `read` keeps the head and tells the model to page with offset and limit; `bash` keeps the tail. Override with `PI_TOOL_BUDGET_KB` and `PI_TOOL_BUDGET_LINES`.

Set `PI_LLM_SERVER_LOG=/path/file.jsonl` to have the extension append one JSON line per response and warm-up with token counts and timings. It never records prompt text. `eval/pi_warmup.py` uses this to measure the warm-up.

## Prompt templates for this repository

From the repository root, Pi offers three templates that encode the recording duty in `AGENTS.md`:

- `/log <topic-slug> [hypothesis]` copies `docs/log/TEMPLATE.md` to a dated entry and fills in the hypothesis and configuration section.
- `/status <what changed>` rewrites the stale lines of `STATUS.md` and links the entry.
- `/bench [sizes] [--thinking]` runs `scripts/bench.py` at each prompt size and reports a table against the current Findings without writing a log entry.

## Settings worth knowing

`quietStartup` hides the banner and `showCacheMissNotices` prints Pi's own notice on a large cache miss. The `bash` tool runs a plain non-interactive shell with no aliases from `~/.zshrc`; an earlier `shellCommandPrefix` that imported them was removed on 2026-09-09 because display aliases such as `ls` to `eza --icons` print nothing outside a terminal and cost the model a turn of confusion. `hideThinkingBlock` is off; turn it on in `~/.pi/agent/settings.json` if xhigh output is too noisy.

## Why these compatibility settings

- vLLM's Qwen template expects a system role rather than an OpenAI developer role.
- The running vLLM accepts `reasoning_effort` and maps it into the Qwen template.
- The server streams thinking as `reasoning`; Pi 0.85.1 retains that field name and sends it back with assistant tool calls.
- `max_tokens` is known to work on the running endpoint.
- Provider retries stay off so Pi's visible three-attempt retry loop handles transient errors once rather than nesting two retry loops.

If the server profile changes, update `contextWindow` here and in the installed `~/.pi/agent/models.json` together.
