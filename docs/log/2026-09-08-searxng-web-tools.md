# 2026-09-08 SearXNG and keyless web tools for Pi

Status: concluded
Profile: a-int4draft, engine unchanged
Author: agent thread on mbp

## Hypothesis

A self-hosted SearXNG next to the engine gives Pi web search with no API keys or quotas, and a Readability-based fetch keeps page content inside the 24 KB tool budget, so Qwen can look things up without a hosted search provider.

## Configuration

Server variable: a `searxng` service added to `compose/docker-compose.yml` with no profile, so it runs alongside any engine Profile. Image pinned by digest (`searxng/searxng@sha256:1dab138e…`, upstream version 2026.9.7-3e454637f), bound to `${BIND_ADDR}:8080`, `compose/searxng/settings.yml` mounted read-only with `search.formats: [html, json]` and `server.limiter: false`. `SEARXNG_SECRET` generated with `openssl rand -hex 32` into `compose/.env`.

```bash
ssh vllm 'cd ~/Code/llm-server/compose && docker compose --profile a-int4draft up -d searxng'
```

Client: `web_search` and `web_fetch` in `clients/pi/extensions/llm-server/web.ts`, with `@mozilla/readability`, `linkedom` and `turndown` as the extension's own npm dependencies. OpenCode's `websearch`, the alternative considered, is a client for Exa's hosted MCP endpoint and was not ported.

Baseline for comparison: none; there was no web tool in Pi before this.

## Measurements

From mbp over Tailscale, one run each unless stated:

| Call | Result | Time |
|---|---|---|
| `web_search` "vllm automatic prefix caching" | 30 results, engines startpage, google cse, brave | not timed (curl) |
| `web_search` "vllm enable-prompt-tokens-details cached_tokens" | 5 of 30 results returned, top hit the vLLM forum thread on that flag | 0.81 s |
| `web_fetch` vLLM APC docs page | 632,118 bytes HTML to 2,442 characters of markdown, Readability path | 0.16 s |
| `web_fetch` GitHub blob README | rewritten to raw.githubusercontent.com, 5,706 bytes text/plain | 0.16 s |

Container start to `Listening at: http://:::8080` took under 8 seconds. SearXNG logs two engine load errors at start, `ahmia` and `torch`, both Tor engines that need a Tor proxy; they are harmless.

End to end through Pi (`pi -p --tools web_search,web_fetch`, xhigh, concurrency 1), asked which vLLM flag exposes `cached_tokens`: two `web_search` calls (0.81 s and 0.62 s, 8 of 49 and 8 of 42 results), one `web_fetch` of the vLLM CLI reference (742,002 bytes, 0.19 s), correct answer `--enable-prompt-tokens-details` with the docs URL, 24 s in total across three model requests.

## What happened

The first `web_fetch` implementation re-parsed Readability's article HTML with linkedom's `parseHTML("<body>…</body>")` to strip scripts and navigation. linkedom turns a bare fragment into a document whose `body.innerHTML` is empty, so every HTML fetch returned a title and nothing else. In the first Pi smoke run the model compensated by fetching eight pages in a row, each adding about 100 tokens. Turndown parses the string with its own DOM, so the cleanup now uses `turndown.remove([...])` and the markdown came back at 2,442 characters for the same page.

That end-to-end run recorded every hook twice. Adding a `package.json` with a `"pi": {"extensions": [...]}` manifest to the extension directory made Pi load it as a package in addition to discovering `index.ts` in `~/.pi/agent/extensions/llm-server/`, so every tool and handler registered twice. The manifest key is gone; the `package.json` now only carries the dependencies, and a rerun recorded each hook once.

A Pi run started through `zsh -lic` from a backgrounded shell stopped on terminal access and never launched; the rerun used a non-interactive shell with the key read from the server's `.env`, the same way `scripts/experiment.sh` does.

## Outcome

Confirmed. Search and fetch work without keys, search answers in under a second, and fetch output fits the budget. Result quality on hard queries and how often upstream engines refuse SearXNG are unmeasured.

## Consequences

`searxng` runs on `vllm` and is part of every `docker compose up`. `compose/.env.example` documents `SEARXNG_IMAGE`, `SEARXNG_PORT` and `SEARXNG_SECRET`. The extension gains two tools and a `package.json`; the install steps in `clients/pi/README.md` add `npm install`. `/vllm` now lists the searxng container. STATUS.md's Pi paragraph links here.
