# 2026-09-20 Pi package suite

Status: complete
Profile: client configuration on mbp

## Hypothesis

The seven requested packages can add MCP connectivity, structured questions, session todos, background jobs, language tooling, persistent goals and side conversations alongside the existing browser and web packages on Pi 0.85.1.

## Configuration

Pinned registry releases inspected on 2026-09-20:

```bash
pi install npm:pi-mcp-adapter@2.34.0
pi install npm:@juicesharp/rpiv-ask-user-question@2.10.1
pi install npm:@juicesharp/rpiv-todo@2.10.1
pi install npm:pi-background-tasks@2.5.0
pi install npm:pi-lens@4.2.1
pi install npm:pi-goal-x@0.31.6
pi install npm:@narumitw/pi-btw@0.60.3
```

Preserve the existing local Qwen model, browser and account-free web settings. Back up installed and repository settings and npm manifests under `~/.pi/backups/2026-09-20-package-suite/`. Resolve the shared Ctrl+Shift+T shortcut by moving rpiv-todo to Alt+T. No shared or Pi MCP configuration currently exists; install the adapter without inventing server connections.

Additional settings: todo uses 8 widget rows and Alt+T; goal auditing defaults to local Qwen at medium thinking; side questions inherit the main model and start at low thinking; Lens keeps LSP, linting, formatting and autofix defaults, uses compact rendering, and disables automatic test runs so checks remain task-specific. No automatic goal was started. Background/Fusion defaults inherit the current model. MCP has no server connections yet.

npm 12 blocked the `@ast-grep/cli@0.45.3` postinstall until reviewed. The script links/copies the already-installed platform binary; approved that exact package with `npm install-scripts approve @ast-grep/cli`, then rebuilt it with `npm rebuild @ast-grep/cli`.

## Measurements

All seven `pi install` commands exited 0, taking 2.65, 1.19, 0.96, 0.73, 2.50, 0.96 and 1.86 seconds in the order above. Each reported zero npm audit vulnerabilities. Runtime validation: all 11 extension entrypoints load with 0 errors in 4,845 ms. Session-start/shutdown handlers report 0 errors. The adapter reports 0 configured servers. Todo create/update/list succeeds; a mocked RPC dialog returns the expected structured answer. A real background shell job launches in 11 ms, completes with exit 0 after about 1 second, and its log contains `PI_BACKGROUND_OK`. Goal status correctly reports no active goal. Lens resolves the installed config, outlines 2 TypeScript symbols in 1,286 ms and returns the expected TypeScript LSP hover in 4,185 ms.

The first `symbol_search` returned `Word index is building in the background for this workspace — retry this query shortly.` after 4 ms. This is not a clean search result; retry validation is pending. A standalone SDK transport check failed with `Error: Theme not initialized. Call initTheme() first.` because the mocked UI did not initialize Pi's theme. The check now calls `initTheme("dark")` before creating its session. The real Pi terminal opens the BTW manager and displays local Qwen, low thinking and remembered changes off; the corrected MCP check passes: connection in 79 ms, tool discovery in 1 ms, and an echo round trip in 2 ms against a temporary local stdio server. No test server is added to the global configuration. Repeated symbol search now returns the expected TypeScript file in 2 ms with complete one-file coverage.

The real BTW side-thread call failed before inference with `Error: modelRegistry.streamSimple is not a function`. Published 0.60.1 through 0.60.3 contain that call; 0.60.0 uses the Pi AI completion function instead. Replaced only BTW with pinned 0.60.0. A fresh Pi terminal side thread then returned exactly `BTW_SETUP_OK` from local Qwen at low thinking. This is 1/1 successful model round trips; no precise inference timing was collected. The other package versions remain unchanged. No goal execution or completion-auditor run has been claimed. Package metadata declares Pi versions below 0.85 for pi-background-tasks 2.5.0 and pi-goal-x 0.31.6. Pi's package manager deliberately omits host peer resolution; live loading and focused calls will determine compatibility with 0.85.1.

## Outcome

All seven requested packages are installed and pinned. The final BTW pin is **0.60.0**, superseding the initially tested 0.60.3 command above. No package source was patched. Both settings files preserve the existing browser/web pins and default local Qwen model.

Validated 11 extension entrypoints with no load errors, actual MCP stdio connection/tool call, todo create/update/list, mocked RPC question selection, real background command completion/log retrieval, goal status, Lens effective configuration/AST outline/symbol search/TypeScript LSP hover, and a real terminal BTW answer. The RPC question test validates host-dialog fallback, not Pier's actual display. The real terminal `/goal-settings` panel confirms inherited `llm-server/qwen38` at medium thinking. Full goal continuation/auditing, delegation and Fusion model runs were not exercised. Package peer ranges for background tasks and goals still omit Pi 0.85; these checks establish the tested paths only.

## Consequences

Final assertions pass: all nine pinned versions match their installed package manifests, all five checked config copies match, the main model remains local Qwen at xhigh, and `git diff --check` reports no errors. The global install and repository pin the same nine total packages. Added checked config files for todo, Lens, goal auditing and BTW, copied to their documented global locations. Existing browser and account-free web configuration remain unchanged. No new external account or API key was added; no persistent goal or production background task was started.

Use `/mcp setup` to connect chosen servers later. The test stdio server exists only under `/tmp/pi-package-setup-20260920/workspace/`. Use `/todos`, `/bg`, `/jobs`, `/logs`, `/lens-health`, `/goal`, `/goal-status`, `/goal-pause`, `/goal-resume` and terminal-only `/btw`. Keep the BTW 0.60.0 pin until an upgrade passes a real model request.

The background package also installs its Anthropic OAuth attribution provider; non-Anthropic routes are unchanged. This package restricts its Anthropic path to subscription OAuth rather than metered API credentials. Fusion defaults to the current model and can queue multiple requests against the single-sequence local server. No Fusion model override was added.

Restart Pi, or quit and reopen Pier, to load the new extensions. The README and STATUS.md record the setup. Backups are under `~/.pi/backups/2026-09-20-package-suite/`; validation scripts/results are under `/tmp/pi-package-setup-20260920/`.
