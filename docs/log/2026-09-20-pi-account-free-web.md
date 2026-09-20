# 2026-09-20 Account-free Pi web routes

Status: complete
Profile: ad hoc, client configuration on mbp

## Hypothesis

Exa's keyless MCP search, the existing SearXNG service, DuckDuckGo HTML search and Jina Reader can provide search and page extraction without provider accounts, while local Qwen and unpdf handle page answers and PDFs.

## Configuration

Initial configuration tested with pinned pi-web-access 0.30.0 in `clients/pi/web-search.json` and `~/.pi/agent/web-search.json`:

- Replace the explicit SearXNG provider with ordered Exa, SearXNG and DuckDuckGo routing.
- Allow only those three search providers, including explicit per-call choices.
- Use direct HTTP then Jina for readable page extraction, opting into hosted fetching.
- Default page-answer requests to `llm-server/qwen38` and PDF extraction to `unpdf`.
- Keep `workflow: "none"`, prefer local Qwen at low thinking if summaries are explicitly requested, and leave browser-cookie access off.
- Limit inline content to 20,000 characters; retain full stored content for retrieval.

Back up both existing config files under `~/.pi/backups/2026-09-20-account-free-web/`. Baseline: [package migration](2026-09-20-pi-web-access.md).

Final configuration after the Jina check below:

```json
{
  "webSearch": {
    "allowedProviders": [
      "exa",
      "searxng",
      "duckduckgo"
    ]
  },
  "searchRouting": {
    "providers": [
      "exa",
      "searxng",
      "duckduckgo"
    ],
    "fallbackOn": [
      "transient",
      "quota",
      "network",
      "invalid-response",
      "unsupported"
    ]
  },
  "searxngBaseUrl": "http://100.103.136.98:8080",
  "fetchRouting": {
    "providers": [
      "http"
    ],
    "allowRemoteHostedProviders": false
  },
  "fetch": {
    "defaultMode": "readable",
    "answerProvider": "llm-server",
    "answerModel": "qwen38"
  },
  "pdf": {
    "provider": "unpdf"
  },
  "workflow": "none",
  "summaryModel": "llm-server/qwen38:low",
  "maxInlineContentChars": 20000,
  "allowBrowserCookies": false,
  "ssrf": {
    "allowRanges": [
      "100.103.136.98/32"
    ]
  }
}
```

## Measurements

Live Pi SDK calls load all three extensions without errors. Search checks ran concurrently against the same query, `TypeScript narrowing handbook`, requesting 3 results each:

| Check | Elapsed | Result |
|---|---:|---|
| Automatic Exa MCP search | 2,199 ms | 3 results, no Authorization header |
| Explicit SearXNG search | 3,030 ms | 3 results, no Authorization header |
| Explicit DuckDuckGo search | 777 ms | 3 results, no Authorization header |
| Inject Exa HTTP 503, keep fallback real | 2,832 ms | Exa then SearXNG, 3 results |
| Explicit OpenAI search | 1 ms | Rejected by provider allowlist before network access |
| Local unpdf extraction | 189 ms | 1-page W3C dummy PDF, Markdown contains `Dummy PDF file` |
| Readable TypeScript narrowing page | 310 ms | 36,352 characters stored, inline result truncated near 20,000 |
| Page answer with default model | 10,752 ms | Correctly answered that `typeof null` returns `"object"` |
| Final HTTP-only page extraction | 199 ms | 36,352 characters stored |
| Stored-content paging | <1 ms | Returned 1,200 characters at offset 20,000, no further network request |

These are individual tool wall times, not model throughput benchmarks. A subsequent Jina check failed, as recorded below.

The original `https://example.com/` readable-page and page-answer fixtures failed in 340 ms and 142 ms with `Error: Extracted content appears incomplete`. Both attempted HTTP then Jina. The substantial TypeScript documentation page passed both paths listed above. A Jina-only temporary routing configuration still issued ordinary HTTP requests. Source inspection explains why: `extract.ts` runs an HTTP gate first for remote URLs even when another provider is first. Those successful documentation-page runs therefore did not validate Jina. The follow-up injects a direct-HTTP failure within the test process and leaves the actual installed routing intact.

## What happened

Inspected the installed routing, credential, PDF and summary code. No Exa, Jina, Gemini or Perplexity API keys are present in the current process environment. Exa uses MCP without a key, and Jina Reader supports anonymous requests. The summary model setting is a preference, not a strict model allowlist: failed local summary attempts can continue to registered hosted models. The default workflow stays off, so ordinary search does not invoke that path. Per-call answer-model overrides remain an explicit package feature.

## Outcome

Anonymous Jina Reader is unavailable from this network. The actual HTTP response was 401 with the exact body:

```text
AuthenticationRequiredError: You have been blocked from performing anonymous queries due to bad network reputation (AS7018). Please authenticate.
```

Injecting an HTTP 503 for the TypeScript URL and leaving Jina real failed after 219 ms. The package suppressed the Jina authentication message and returned the earlier `HTTP 503:` error with generic configuration suggestions. Removed Jina after this measurement. Final page routing is direct HTTP only, with `allowRemoteHostedProviders: false`; the installed `agent_browser` tool is the account-free option for interactive or JavaScript-dependent pages. This is a separate tool the agent chooses, not an automatic `fetch_content` fallback.

Search, direct page extraction, local PDF extraction and local answers pass. Page-answer request tracing confirms the only inference request went to `http://vllm:8000/v1/chat/completions`.

## Consequences

Installed and repository configurations match. Keep `EXA_API_KEY` unset to use Exa MCP without an account. Search providers outside the three-item allowlist are rejected. No new accounts or external API credentials were added. Restart Pi, or quit and reopen Pier, to apply the saved configuration to existing processes.

The local model and SearXNG fallback need Tailscale. Exa and DuckDuckGo remain external account-free services subject to their availability and anonymous limits. Direct HTTP does not render JavaScript; the installed browser tool covers interactive browsing when selected by the agent. Jina is excluded until anonymous access works from this network.

Validation artifacts are under `/tmp/pi-account-free-web.lPwwIS/`. Configuration backups are under `~/.pi/backups/2026-09-20-account-free-web/`. The client README and STATUS.md describe the final configuration; the earlier migration log remains historical.
