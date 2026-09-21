# Pi against this server

Pi runs on the MacBook and uses its local tools to read, edit and test code. The model request goes over Tailscale to Qwen on `vllm`, or to any other provider Pi is logged into; the checked extension loads for every provider and decides per selected model what applies (see "Other providers" below).

The server has `a-int4draft` and `original-int4draft` profiles. Both expose the same `qwen38` API model, so switching checkpoints does not require a client configuration change. Selecting a model in Pi does not switch the server profile.

## Install the checked configuration

Pi 0.85.1 from `@earendil-works/pi-coding-agent` is the validated client version. The API key lives in `~/.pi/agent/auth.json`, which Pi reads for custom providers and creates with mode 0600. Do not copy it into `models.json`, which is checked in.

```bash
npm install -g @earendil-works/pi-coding-agent@0.85.1
mkdir -p ~/.pi/agent/extensions ~/.config/rpiv-todo
cp clients/pi/models.json ~/.pi/agent/models.json
cp clients/pi/settings.json ~/.pi/agent/settings.json
cp clients/pi/web-search.json ~/.pi/agent/web-search.json
cp clients/pi/rpiv-todo.json ~/.config/rpiv-todo/config.json
cp clients/pi/pi-goal-x-settings.json ~/.pi/agent/pi-goal-x-settings.json
ln -sfn "$PWD/clients/pi/extensions/llm-server" ~/.pi/agent/extensions/llm-server
pi install npm:pi-agent-browser-native@0.6.15
pi install npm:pi-web-access@0.30.0
pi install npm:@juicesharp/rpiv-ask-user-question@2.10.1
pi install npm:@juicesharp/rpiv-todo@2.10.1
pi install npm:pi-goal-x@0.31.6
```

For a fresh installation with no `auth.json`, write the server key once, replacing the placeholder, then confirm the model is available. If the file already exists, add the `llm-server` entry to it and preserve the other provider credentials:

```bash
umask 077
cat > ~/.pi/agent/auth.json <<'EOF'
{ "llm-server": { "type": "api_key", "key": "change-me" } }
EOF
pi --list-models qwen38
```

The symlink keeps the installed extension identical to the checked one; edit it here and restart Pi. On mbp, `~/.pi/agent/AGENTS.md` is a separate symlink to `~/Code/AGENTS.md/AGENTS.md`, the shared global instructions repository. There are no separate global Pi skill, prompt or theme directories configured beyond package-provided resources. Credentials, session history, generated caches and the `lastChangelogVersion` runtime marker stay outside this repository. The `.pi/prompts/` templates in the repository root load only when Pi runs from this repository and the project is trusted.

The model declares the server's validated 131,072-token window. Pi begins compaction above 106,496 estimated context tokens, reserving 16,384 for the response plus 8,192 tokens of headroom. The reserve was 40,960 until 2026-09-20; the largest response in a 201-turn session was under 4K tokens, so the old reserve only shortened the usable window. `maxTokens` and `reserveTokens` move together: vLLM rejects a request whose prompt plus `max_tokens` exceeds the window.

Sampling is explicit because Qwen's thinking preset and MTP acceptance both depend on it. The model supports low, medium and xhigh effort. Medium is the default since 2026-09-20; select xhigh per session with `--thinking xhigh` or `/thinking` for hard repository work. Unsupported Pi levels are hidden. Retained reasoning was 75% of context growth in the session that motivated the change, so the effort level is the main lever on how often Pi compacts. [Context pressure](../../docs/log/2026-09-20-pi-context-pressure.md)

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

`clients/pi/extensions/llm-server/` is one Pi extension in nine modules, with no npm runtime dependencies. Everything it does follows from measurements in `docs/log/`: prefix reuse is worth 12 seconds per request at 23K tokens, the window is small, and the server is a single box that sometimes goes away.

Pi loads the extension for every provider, so each module checks the selected model at runtime. Three modules act only while the model's provider is `llm-server` (`LOCAL_PROVIDER` in `shared.ts`, override with `PI_LOCAL_PROVIDER`): cache warm-up, the thinking guard and server diagnosis. Two scale with the window: the tool-output cap and the system-prompt constraints block. The rest apply to any model. Since 2026-09-11; [rework entry](../../docs/log/2026-09-11-pi-extension-provider-agnostic.md).

- **Request numbers in the footer.** After every response the status line shows time to first token, the share of the prompt served from the provider's prompt cache, and how many tokens remain before automatic compaction. A prompt of 8K tokens or more that hits the cache below 50% raises a warning with the time to first token. The cache share appears once the provider has reported cached tokens at least once; on `vllm` that needs `--enable-prompt-tokens-details`, which the compose file passes. Until then the line shows the prompt size only.
- **Warm-up after compaction (llm-server only).** `session_compact` fires, and once Pi is idle the extension sends the compacted context with `max_tokens` 1 so vLLM prefills it while you type. `/warm` does the same by hand. The next real request is compared with the warm-up payload and a mismatch is reported, so a silent cache miss cannot hide. On another provider the compaction handler returns and `/warm` says so, because a hosted API would bill the warm-up as a full prompt. Measured effect is in [the log entry](../../docs/log/2026-09-07-pi-quality-of-life.md).
- **Thinking-level guard (llm-server only).** Changing effort rewrites Qwen's template and invalidates the prefix. Pi cannot block the change, so the extension states the cost in seconds and warms the cache with the new level if Pi is idle.
- **Server diagnosis (llm-server only).** A request that ends in an error triggers a `/health` check. If the engine answers, the message says the error was request-level. If not, the extension watches `/health` every 10 seconds for up to 15 minutes and says when it is back. Errors from other providers are left to Pi's own message. `/vllm` shows health plus the container state over SSH and works whichever model is selected, because it looks the server up in Pi's model registry; `/vllm logs 60` tails the engine log. Output appears in the transcript and is not sent to the model.
- **Notification.** A run longer than 15 seconds posts a macOS notification when Pi is waiting for input.
- **Handoff.** `/handoff <goal>` is Pi's example handoff extension unchanged: it writes a focused prompt from the current conversation and opens a new session with it in the editor. Prefer it over `/compact` when switching tasks; the new session prefills in a second or two instead of 12.
- **System prompt additions.** A `before_agent_start` handler appends a "Session constraints" block built once per model: the window and compaction threshold when the window is under 128K tokens, the tool-output cap when one applies, and always that a compaction summary is prior work rather than new instructions. The block stays fixed for the selected model so it can remain in the cached prefix.
- **Tool output budget.** For models with a window under 128K tokens (`PI_SMALL_WINDOW_TOKENS`, default 131072), `read` and `bash` results are cut to 24 KB or 600 lines instead of Pi's 50 KB or 2000. `read` keeps the head and tells the model to page with offset and limit; `bash` keeps the tail. Larger windows keep Pi's defaults. Setting `PI_TOOL_BUDGET_KB` or `PI_TOOL_BUDGET_LINES` forces a cap for every model. The pi-web-access package controls its own web-result limits.

Set `PI_LLM_SERVER_LOG=/path/file.jsonl` to have the extension append one JSON line per response and warm-up with token counts and timings. It never records prompt text. `eval/pi_warmup.py` uses this to measure the warm-up.

## The browser package

Browser automation uses [pi-agent-browser-native](https://pi.dev/packages/pi-agent-browser-native), pinned to 0.6.15 in `clients/pi/settings.json`. It replaces the custom `clients/pi/extensions/browser/` extension. Pi 0.85.1 and the installed agent-browser 0.37.1 meet the package's runtime requirements.

```bash
brew install agent-browser
agent-browser install
pi install npm:pi-agent-browser-native@0.6.15
```

The package exposes one tool, `agent_browser`, for navigation, accessibility snapshots, form actions, page JavaScript, console output and screenshots. The checked screenshot call returns an inline image block as well as a saved artifact path. It manages browser sessions, rejects stale refs and limits large results with spill files. Read the installed package's `docs/COMMAND_REFERENCE.md` for command details.

```json
{"args":["open","https://example.com"]}
{"args":["snapshot","-i"]}
{"args":["screenshot","/tmp/pi-browser.png"]}
{"args":["close"]}
```

The former `browser_open`, `browser_snapshot`, `browser_act`, `browser_screenshot`, `browser_console`, `browser_eval` and `/browser` command are removed. The new tool uses agent-browser's headless default. To watch a browser window, request `{"args":["--headed","open","https://example.com"],"sessionMode":"fresh"}` on launch. The old `PI_BROWSER_*` settings do not configure this package.

The pi-web-access package supplies `web_search` through account-free Exa, SearXNG and DuckDuckGo routes, plus `fetch_content`. The browser package's optional `agent_browser_web_search` needs separate Exa or Brave credentials and is not configured by this setup.

After installing or updating the package, fully restart Pi, or quit and reopen Pier so it starts fresh Pi processes. The package warns that `/reload` can retain previously loaded JavaScript. The read-only setup check is:

```bash
node ~/.pi/agent/npm/node_modules/pi-agent-browser-native/scripts/doctor.mjs
```

Migration and validation: [native browser package](../../docs/log/2026-09-20-pi-native-browser.md). The original implementation and prior installed settings are backed up outside Pi's extension directory at `~/.pi/backups/2026-09-20-native-browser/`.

## The web access package

Search and page fetching use [pi-web-access](https://pi.dev/packages/pi-web-access), pinned to 0.30.0. It replaces the custom `web.ts` module and its Readability, linkedom and Turndown dependencies in the llm-server extension.

```bash
pi install npm:pi-web-access@0.30.0
cp clients/pi/web-search.json ~/.pi/agent/web-search.json
```

The checked configuration searches through Exa's keyless MCP endpoint first, then the existing SearXNG service at `http://100.103.136.98:8080`, then DuckDuckGo HTML search. Fallback covers transient errors, quota limits, network failures, invalid responses and unsupported requests. `webSearch.allowedProviders` restricts both automatic and explicit search choices to those three providers. No external account or API key is configured. Keep `EXA_API_KEY` unset to retain the keyless Exa route.

SearXNG needs Tailscale; Exa and DuckDuckGo do not. `ssrf.allowRanges` permits only the server's `/32` address through the package's private-address guard. Page fetching uses direct HTTP. Hosted extraction is disabled because anonymous Jina Reader returned HTTP 401 from this network. Use `agent_browser` for JavaScript-dependent or interactive pages; the agent must choose that tool separately.

- `web_search` supports one query or a batch, result counts, recency and domain filters. Its argument names now include `numResults` and `recencyFilter`.
- `fetch_content` replaces `web_fetch`. It returns readable pages and supports additional content types through the package. GitHub URLs can invoke its repository clone or issue/PR handlers.
- `get_search_content` retrieves stored results or finds passages by text without fetching again.
- `source_check` gathers sources and passages into a claim-checking artifact. It does not establish semantic truth automatically.

Page-answer mode defaults to the local `llm-server/qwen38` model, and PDF extraction uses local `unpdf`. Browser-cookie access is off. Search returns results directly with `workflow: "none"`, leaving ordinary synthesis to the selected Pi model. `summaryModel` prefers local Qwen at low thinking if a summary is explicitly requested, but the package can fall back to other registered models in that optional workflow. It is not a strict model allowlist. Per-call answer-model overrides also remain available.

The package registers `/websearch`, `/search`, `/curator` and `/google-account`. Search curation does not open automatically with the checked workflow. The browser package's optional Exa/Brave search is not configured.

The old `SEARXNG_URL` setting and custom web-output caps no longer apply. The replacement uses `searxngBaseUrl` in `~/.pi/agent/web-search.json`, or `SEARXNG_BASE_URL` in the environment. The checked inline-content limit is 20,000 characters; longer content stays available through `get_search_content`, which supports text search and paging without another network request.

Restart Pi, or quit and reopen Pier, to load changes in existing sessions. The old implementation and original Pi settings are backed up at `~/.pi/backups/2026-09-20-web-access/`; the prior web configuration is under `~/.pi/backups/2026-09-20-account-free-web/`. [Migration](../../docs/log/2026-09-20-pi-web-access.md), [account-free route validation](../../docs/log/2026-09-20-pi-account-free-web.md).

## Additional packages

The global installation and `clients/pi/settings.json` pin these packages:

| Package | Version | Use |
|---|---|---|
| [rpiv-ask-user-question](https://pi.dev/packages/@juicesharp/rpiv-ask-user-question) | 2.10.1 | `ask_user_question` presents structured choices in terminal or supported RPC dialogs. |
| [rpiv-todo](https://pi.dev/packages/@juicesharp/rpiv-todo) | 2.10.1 | `todo` tracks the current session's tasks; `/todos` lists them; Alt+T toggles the panel. |
| [pi-goal-x](https://pi.dev/packages/pi-goal-x) | 0.31.6 | `/goal <objective>` plans persistent work; `/goal-pause`, `/goal-resume` and `/goal-status` control it. |

The todo panel has eight rows and uses Alt+T to avoid the goal dashboard's Ctrl+Shift+T binding. Todos track the current conversation; goals save longer-running objectives and plans across sessions. No goal is started by installation. Goal auditing defaults to local Qwen at medium thinking. Automatic continuation keeps the package default; `/goal-pause` stops it, and `/goal-settings` can set an autonomous-run allowance.

pi-mcp-adapter, pi-background-tasks, pi-lens and pi-btw were installed on 2026-09-20 and removed the same day: together they cost 9,427 tokens of system prompt on every request, and the session that prompted the measurement used background tasks twice in 201 turns and the others not at all. Each package's cost is in the [context pressure entry](../../docs/log/2026-09-20-pi-context-pressure.md); `eval/pi_prefix_by_package.py` repeats the measurement. Their earlier compatibility notes remain in the [package suite entry](../../docs/log/2026-09-20-pi-package-suite.md).

To reproduce the added configuration after installing the pinned packages:

```bash
mkdir -p ~/.config/rpiv-todo
cp clients/pi/rpiv-todo.json ~/.config/rpiv-todo/config.json
cp clients/pi/pi-goal-x-settings.json ~/.pi/agent/pi-goal-x-settings.json
```

Restart Pi, or quit and reopen Pier, after installing. [Measurements and compatibility notes](../../docs/log/2026-09-20-pi-package-suite.md).

## Other providers

Hosted-provider credentials live in `~/.pi/agent/auth.json`; `pi --list-models` shows available models and `/model` selects one. `models.json` defines the local server, and `settings.json` sets it as the default. The llm-server extension gates server-specific behavior on the selected provider. Browser and web packages load alongside it for other models too. The SearXNG fallback and local page-answer model need Tailscale whichever model answers the main conversation.

## Prompt templates for this repository

From the repository root, Pi offers three templates that encode the recording duty in `AGENTS.md`:

- `/log <topic-slug> [hypothesis]` copies `docs/log/TEMPLATE.md` to a dated entry and fills in the hypothesis and configuration section.
- `/status <what changed>` rewrites the stale lines of `STATUS.md` and links the entry.
- `/bench [sizes] [--thinking]` runs `scripts/bench.py` at each prompt size and reports a table against the current Findings without writing a log entry.

## Settings worth knowing

`quietStartup` hides the banner and `showCacheMissNotices` prints Pi's own notice on a large cache miss. The `bash` tool runs a plain non-interactive shell with no aliases from `~/.zshrc`; an earlier `shellCommandPrefix` that imported them was removed on 2026-09-09 because display aliases such as `ls` to `eza --icons` print nothing outside a terminal and cost the model a turn of confusion. `hideThinkingBlock` is on, matching the installed setup; reasoning still runs at the selected level, but its text is hidden in the UI.

## Why these compatibility settings

- vLLM's Qwen template expects a system role rather than an OpenAI developer role.
- The running vLLM accepts `reasoning_effort` and maps it into the Qwen template.
- The server streams thinking as `reasoning`; Pi 0.85.1 retains that field name and sends it back with assistant tool calls.
- The extension adds `chat_template_kwargs.preserve_thinking: false` to every request to the local server (`thinking-history.ts`). Without it Qwen's template renders the reasoning of every earlier assistant turn into the prompt; with it only steps after the latest user message keep theirs. The warm-up sends the same kwargs so its cached prefix matches.
- `max_tokens` is known to work on the running endpoint.
- Provider retries stay off so Pi's visible three-attempt retry loop handles transient errors once rather than nesting two retry loops.

If the server profile changes, update `contextWindow` here and in the installed `~/.pi/agent/models.json` together.
