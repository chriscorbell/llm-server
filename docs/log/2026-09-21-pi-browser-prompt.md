# 2026-09-21 Pi browser mode and persistent profile instructions

Status: concluded
Profile: Pi client on mbp

## Hypothesis

A global prompt addition can direct Pi to use headless browsing for independent work and one persistent headed profile when Chris needs to interact, across sessions and projects.

## Configuration

The only behavioral configuration change is the global prompt addition in [clients/pi/APPEND_SYSTEM.md](../../clients/pi/APPEND_SYSTEM.md). Previously no global or project `APPEND_SYSTEM.md` existed. Install on mbp from the repository root:

```bash
ln -s "$PWD/clients/pi/APPEND_SYSTEM.md" ~/.pi/agent/APPEND_SYSTEM.md
mkdir -p ~/.pi/browser-profiles/headed
chmod 700 ~/.pi/browser-profiles/headed
```

The instructions select `agent_browser` from the existing pi-agent-browser-native 0.6.15 package. Headed launches use `--headed --profile /Users/chris/.pi/browser-profiles/headed --session pi-headed`. Subsequent calls select that same session. Headless work remains separate.

An absolute profile directory is required: [upstream session documentation](https://agent-browser.dev/sessions#persistent-profiles) distinguishes persistent directories from named Chrome profiles, which are copied temporarily and never written back. The [Chrome engine documentation](https://agent-browser.dev/engines/chrome) identifies `--profile` as the browser's `--user-data-dir`. A shared named session prevents separate Pi projects from deliberately launching competing browser processes against one profile. Agents still need to coordinate active use.

## Measurements

| Check | Result |
|---|---|
| Pi 0.86.1 discovers the global addition from two working directories | 2/2 pass |
| Built-in prompt retained and addition appears exactly once | 2/2 pass |
| Added text | 177 words, 1,140 bytes |

Checks used Pi's installed `DefaultResourceLoader` with `SettingsManager.inMemory({packages: []})` and extensions, skills, prompt templates, themes, and context files disabled. After `reload()`, `getAppendSystemPrompt()` returned the exact installed file once from both `/Users/chris/Code/llm-server` and `/Users/chris/Code/fleet`. `getSystemPrompt()` returned no replacement. Rendering with `buildSystemPrompt({cwd, appendSystemPrompt: additions.join("\n\n")})` retained Pi's built-in preamble and added the text inside `<addendum>`.

No model request, browser launch, persistence test, tokenization, or performance measurement was run.

## What happened

The requested behavior is expressed in the global prompt addition. The symlink is installed and the persistent profile directory is created with mode 0700. The installed browser package and native CLI are unchanged.

## Outcome

Global prompt discovery and assembly are confirmed. Actual agent adherence and browser extensions/history persistence have not been tested.

## Consequences

The prompt source is tracked in the client configuration. Browser profile data stays outside the repository. Existing Pi sessions need `/reload` or a restart to read the new prompt file.

## Subsequent relocation

On September 22 the prompt source moved to `~/Code/pi-config/agent/APPEND_SYSTEM.md`; the installed global symlink now points there. The original client path above records its initial installation. [Migration](2026-09-22-pi-config-migration.md).
