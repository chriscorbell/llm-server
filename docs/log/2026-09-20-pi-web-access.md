# 2026-09-20 Pi web access package

Status: concluded
Profile: ad hoc, client configuration on mbp

## Hypothesis

The published pi-web-access package can replace the custom web.ts module while retaining search through the existing SearXNG service and readable page fetching.

## Configuration

Pin `npm:pi-web-access@0.30.0` on Pi 0.85.1. Set its default provider to `searxng`, using `http://100.103.136.98:8080`, the vllm server's Tailscale address. Allow that single `/32` address through the package's request guard. Keep the default noninteractive search workflow. Remove the custom `web_search` and `web_fetch` registrations before loading the replacement package.

```sh
pi install npm:pi-web-access@0.30.0
```

Back up the existing llm-server extension and Pi settings to `~/.pi/backups/2026-09-20-web-access/`. The native browser package remains installed.

Baseline: [custom SearXNG tools](2026-09-08-searxng-web-tools.md). Package source and documentation: [pi-web-access](https://pi.dev/packages/pi-web-access).

## Measurements

All three extensions load with zero errors, and exactly one extension registers `web_search`. The first search returned 3 TypeScript documentation results in 3.032 seconds. Fetching the narrowing page succeeded in 0.336 seconds, stored 36,352 characters, and returned a bounded inline slice. Inference throughput is not being compared.

The corrected three-operation check passes: search returns 3 results in 3.023 seconds; fetch returns the article in 0.245 seconds; stored-content lookup finds 19 `typeof` matches in 0.001 seconds. The temporary check uses the installed Pi SDK and actual registered tools, with no inference calls. A separate Qwen check at low thinking passes in 21.988 seconds, concurrency 1. It makes one `web_search` call through the configured default and one `fetch_content` call, both with successful tool-result metadata, then explains the null-narrowing behavior with the official source URL. Prompt-token counts and inference rates were not measured.

## What happened

Inspected the npm package manifest, extension registration and SearXNG adapter. The package contains built JavaScript and has no installation lifecycle script. SearXNG requests and redirects use the package's address validation; the existing private endpoint requires a narrow address allowance.

The temporary check initially required the page title to appear in the extracted article body:

```text
AssertionError [ERR_ASSERTION]: The expression evaluated to a falsy value:
  assert(page.text.includes('Narrowing'))
```

The package correctly returned `Documentation - Narrowing` in `details.title`, while article text began with the `padLeft` example. Changed the check to validate the title field, successful-fetch count and article text. No package modification was needed.

## Outcome

Confirmed for search, readable page fetches and stored-content lookup on the existing SearXNG route. All three extensions load without conflicts, and Qwen completes the search/fetch task. Source-check artifacts, optional paid providers, video, authenticated fetching and curator UI were not exercised.

## Consequences

Installed and pinned the package in global and repository Pi settings. Added `clients/pi/web-search.json` and copied it to `~/.pi/agent/web-search.json`. Removed `web.ts` and its registration from the llm-server extension, and removed its Readability, linkedom and Turndown dependencies with npm. The retained extension has no npm runtime dependencies. Updated the client guide and current status. Browser automation, model settings and the server services are unchanged.

Prior extension files and global settings are under `~/.pi/backups/2026-09-20-web-access/`. Temporary validation scripts and result files are under `/tmp/pi-web-access.sRJcKL/`. Existing Pi/Pier sessions need a restart to load the replacement; no active user session was terminated.
