# 2026-09-20 Pi repository sync

Status: concluded
Profile: client configuration on mbp

## Hypothesis

The checked Pi configuration and setup instructions can reproduce the installed client without committing credentials, generated state or unrelated client work.

## Configuration

Compare installed Pi settings and model declarations, all five package-specific config files, the local extension symlink and installed package versions against `clients/pi/`. Copy the missing `hideThinkingBlock: true` preference into the checked settings. Keep `lastChangelogVersion` as an installed runtime marker. Expand the primary install instructions to include all nine package pins and every global config copy. Document the separate shared global instructions symlink.

Baseline: [package setup](2026-09-20-pi-package-suite.md), [account-free web routes](2026-09-20-pi-account-free-web.md), [browser migration](2026-09-20-pi-native-browser.md).

## Measurements

The initial comparison found 1 user preference missing from the checked settings: `hideThinkingBlock`. Model declarations and all 5 package config files matched. The installed local extension symlink resolves directly to `clients/pi/extensions/llm-server`; no extra global extension, skill, prompt or theme directories are configured. All 9 package versions were verified during the preceding setup.

Final checks pass: checked settings equal installed settings after excluding the runtime marker; model declarations and all 5 package config files match; all 9 installed package versions match their pins; local links in every staged Markdown file resolve within the staged tree; `git diff --cached --check` reports no whitespace errors. Runtime behavior was validated in the linked setup experiments and is unchanged by this documentation sync.

## Outcome

The repository now captures the installed Pi configuration and its setup steps, including the compatible BTW 0.60.0 pin, account-free web routing, local goal auditor, todo shortcut, Lens defaults and hidden thinking blocks.

## Consequences

The staged commit includes the current Pi extension, package pins, global config templates and Pi experiment history. STATUS.md includes only its Pi changes and update date; unrelated Codex, OpenCode, Hermes and hardware edits remain in the working tree. No inference-server runtime change is required for this client configuration sync.
