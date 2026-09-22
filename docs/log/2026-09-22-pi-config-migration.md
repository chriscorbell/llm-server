# 2026-09-22 Move the MacBook Pi configuration into pi-config

Status: concluded
Profile: Pi on mbp

## Hypothesis

A dedicated repository containing the actual installed Pi configuration can replace `clients/pi` without changing Pi's available models, extensions, prompts, or preferences.

## Configuration

Chris requested that everything about the MacBook's Pi setup, including the local-server model definition and extension, move into a private `chriscorbell/pi-config` repository. The target checkout is `/Users/chris/Code/pi-config`.

The existing client directory and project prompts were backed up under `~/.pi/backups/2026-09-22-pi-config-*` or the local-date `2026-09-21-pi-config-*` directory before migration. That backup includes the source repository's uncommitted diff. Installed configuration takes precedence over stale checked copies: the advisor executor is currently `openai-codex/gpt-5.6-sol`, while the old client copy selected Qwen.

Credentials, session transcripts, generated model catalogs, caches, browser profiles, and project goal/task state remain local. Shared global instructions and skills retain their existing ownership; the new repository records those dependencies.

## Measurements

| Check | Before | After |
|---|---|---|
| Loaded extensions | 11 | 11 |
| Registered extension tools | 17 | 17 |
| Shared skills | 37 | 37 |
| Server-project prompt templates | 3 | 3 |
| Extension-loading errors | 0 | 0 |

Pi's resource loader returned identical tool/command names, skill paths, prompt contents, and global prompt additions before and after moving the installed links. A second-directory check confirmed the server templates stayed project-scoped. The configuration comparison passes. A temporary-home installer check confirms backups, preservation of credentials and runtime markers, expected symlinks, and idempotence. The two affected evaluation scripts compile and resolve the new configuration paths.

No inference or browser performance measurements have been run.

## What happened

The client files were copied into the new checkout before changing installed paths. The installed llm-server extension and APPEND_SYSTEM.md now point into pi-config. JSON preferences and Orca-generated files remain writable copies with capture/check/install commands in the new repository. The server's prompt sources moved into `pi-config/projects/llm-server/prompts`; their installed symlinks remain in the server checkout's ignored `.pi/prompts` directory. `eval/pi_contract.py` and `eval/pi_warmup.py` now read `~/Code/pi-config/agent`, with `PI_CONFIG_REPO` as an override.

## Outcome

Installation and offline resource-equivalence checks pass. The complete configuration is committed as `41851d4` and pushed to the private [chriscorbell/pi-config repository](https://github.com/chriscorbell/pi-config). GitHub reports visibility `PRIVATE` and default branch `main`.

## Consequences

The server repository retains inference deployment configuration and historical experiments. Current Pi setup instructions point to pi-config, and `clients/pi/README.md` is the migration pointer. Restart existing Pi sessions so later module loads use the new checkout.
