# 2026-09-20 Pi native browser package

Status: concluded
Profile: ad hoc, client configuration on mbp

## Hypothesis

The published `pi-agent-browser-native` package can replace the custom six-tool browser extension on Pi 0.85.1 while retaining browser navigation, form interaction and screenshots with the installed agent-browser 0.37.1.

## Configuration

Replace only the browser extension. Keep the existing llm-server extension and its SearXNG web tools. Pin the package to `npm:pi-agent-browser-native@0.6.15`. The package requires Pi 0.84.0 or newer, Node 22.19.0 or newer and agent-browser 0.35.0 or newer; mbp has Pi 0.85.1, Node 26.8.2 and agent-browser 0.37.1.

```sh
pi install npm:pi-agent-browser-native@0.6.15
```

Before removing the old extension, save its source and the installed Pi settings outside the extension discovery directory. Remove the `~/.pi/agent/extensions/browser` symlink after the native package loads successfully.

Baseline: [custom browser extension](2026-09-11-pi-browser-extension.md). Package source and installation instructions: [pi-agent-browser-native](https://pi.dev/packages/pi-agent-browser-native).

## Measurements

Package doctor passes all 3 checks. Pi loads the new `agent_browser` tool and the retained `web_search` and `web_fetch` tools with zero extension errors. The corrected local browser check passes all 9 operations: open, snapshot, fill, click, read changed page text, screenshot, console, eval and close. The screenshot is returned as both text and an image block, and its PNG file is 11,711 bytes. No inference throughput comparison is planned.

A live Qwen check at low thinking completed the form-and-screenshot task in 27.065 seconds, concurrency 1, with 8 `agent_browser` calls. It returned `Hello Native` and a dark navy background description. Visual inspection of the saved PNG confirms the greeting. The reported approximate hex color was `#1e293b`; the fixture CSS is `#182638`, so this establishes screenshot delivery and a broad color description, not exact color measurement. Prompt-token counts and inference rates were not measured. One incomplete `get text` call was followed by `get text body` and the task completed.

## What happened

Inspected the published npm manifest, extension entry point, process launcher and package preparation script. The npm package contains built JavaScript and uses cross-spawn 7.0.6 as its single runtime dependency. Its optional web-search tool has a distinct name; it is not required for this migration.

The first local form check opened and snapshotted correctly, but the temporary fixture used unescaped quotes in an inline HTML event attribute. The click left its output at `Waiting`, so the assertion failed:

```text
AssertionError [ERR_ASSERTION]: The expression evaluated to a falsy value:
  assert(text.text.includes('Hello Chris'))
```

Replaced the fixture's inline event attribute with an `addEventListener` script. No package or production code change was needed. Browser cleanup succeeded after the failed check.

## Outcome

Confirmed for the checked workflows. Package doctor passes, both extensions load without errors, all 9 direct browser operations pass, and Qwen completes the form-and-screenshot task through the new tool. Full upstream CLI coverage and authenticated profile workflows were not tested.

## Consequences

Installed the pinned npm package globally in `~/.pi/agent/settings.json`, added it to `clients/pi/settings.json`, and removed the old browser symlink and source file. The source and original installed settings are retained at `~/.pi/backups/2026-09-20-native-browser/`. Updated the client guide and current status. The llm-server extension, SearXNG configuration, models and server are unchanged. Existing Pi/Pier processes need a full restart to load the new tool; no active user session was terminated.

Temporary validation scripts and their result files are under `/tmp/pi-browser-native.7ez7Jr/`.
