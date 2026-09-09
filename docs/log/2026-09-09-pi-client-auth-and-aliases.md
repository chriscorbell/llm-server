# 2026-09-09 Client key moves into Pi's auth store, agent shell loses zsh aliases

Status: concluded
Profile: ad hoc
Author: agent thread on mbp

## Hypothesis

Two client-side changes, neither of them a performance experiment. First, a desktop app launched from the Dock does not read `.zshrc`, so an API key that lives only in an exported shell variable is invisible to it; Pi's own `auth.json` is read by every launch mode. Second, importing interactive zsh aliases into the agent's `bash` tool makes standard commands behave unexpectedly for the model.

## Configuration

Key: `~/.pi/agent/auth.json` gains `{"llm-server": {"type": "api_key", "key": "..."}}`. The `apiKey` field leaves `clients/pi/models.json`, the `export LLM_SERVER_API_KEY` line leaves `.zshrc`. `scripts/bench.py` and `eval/vision_check.py` default their `--key` to the same auth entry, the opencode client uses opencode's own auth store, and `.pi/prompts/bench.md` drops the env var from its command.

Aliases: `shellCommandPrefix` removed from `clients/pi/settings.json` and the installed copy.

```
-  "shellCommandPrefix": "shopt -s expand_aliases\neval \"$(grep '^alias ' ~/.zshrc)\""
```

Baseline for comparison: none, no numbers measured.

## What happened

With the prefix in place, a Pi session in the desktop client ran `ls` inside the bash tool and got empty output. `ls` is aliased to `eza -al --icons=always` in `.zshrc`, and eza prints an empty listing when it is given no path and no terminal. Qwen noticed, spent six tool calls diagnosing the alias, and finished the task with `eza -al .`. The same thing happens in the Pi TUI, since both use the same bash tool.

The key move was verified by starting `pi --mode rpc` with `LLM_SERVER_API_KEY` removed from the environment: the model resolved and the extension loaded.

## Outcome

Concluded. Not measured, by design.

## Consequences

Repository: `clients/pi/models.json`, `clients/pi/settings.json`, `clients/pi/README.md`, `clients/opencode/`, `scripts/bench.py`, `eval/vision_check.py`, `.pi/prompts/bench.md`. Supersedes the alias note in [2026-09-07-pi-quality-of-life.md](2026-09-07-pi-quality-of-life.md). The `notify.ts` module of the extension also skips its macOS notification when `ctx.mode` is `rpc`, because the desktop client posts its own. No Finding promoted.
