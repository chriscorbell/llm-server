# 2026-09-13 Turbo in Pi and OpenCode on mbp

Status: in progress
Profile: turbo-gguf, client configuration

## Hypothesis

Adding `qwen38-turbo` to the existing `llm-server` provider in both installed clients enables the validated Turbo profile with xhigh thinking, tools, images and the 131,072-token context window using existing authentication.

## Configuration

Execution and client target: mbp, Darwin. Installed versions: Pi 0.85.1 and OpenCode 1.18.30. Server: `vllm` over SSH, initially healthy on `a-int4draft`.

Add a model called `Qwen3.8-27B Turbo Q6_K`, API ID `qwen38-turbo`, to `clients/pi/models.json`, `clients/opencode/opencode.jsonc`, and their installed files `~/.pi/agent/models.json` and `~/.config/opencode/opencode.jsonc`. Reuse the existing `llm-server` authentication. Preserve existing models, defaults, provider options, extensions and unrelated local edits.

Pi copies the current Qwen compatibility and sampling settings: text/image input, reasoning enabled, low/medium/xhigh effort mapping, context 131,072 and output 32,768. The installed default effort is xhigh and compaction reserve is 40,960, leaving a 90,112-token estimated trigger.

OpenCode uses explicit low/medium/xhigh `reasoningEffort` variants and `options.reasoningEffort: "xhigh"`, text/image modalities, tool calls, context 131,072, input 98,304 and output 32,768. Its existing 20,000-token input compaction buffer gives a 78,304-token trigger. No API key is added to either model file.

```bash
pi --list-models qwen38
opencode models llm-server
pi --model llm-server/qwen38-turbo --thinking xhigh
opencode -m llm-server/qwen38-turbo --variant xhigh
```

Only one model fits on the server at once. Client selection does not switch Compose profiles. Capture diagnostics, preserve the daily driver, load `turbo-gguf` for actual client requests, then restore the daily driver after validation.

Baseline: [Turbo 128K/xhigh validation](2026-09-13-turbo-thinking-128k.md). Configuration references: Pi 0.85.1's installed `docs/models.md`, [OpenCode model options](https://opencode.ai/docs/models/#configure-models) and [custom provider configuration](https://opencode.ai/docs/providers/#custom-provider).

## Measurements

Pending client model listings and authenticated tool round trips. No engine tuning or throughput comparison is planned.

## What happened

Both auth stores already have the `llm-server` provider. Pi's installed extension is symlinked to this repository and gates local-server features by provider, so the additional model uses the same handlers. Installed config files are backed up beside their originals with `.backup-turbo-` timestamp suffix and mode 0600; paths are in `scratch/turbo-clients/backups.json` on mbp. Existing uncommitted client and STATUS edits are saved for preservation checks and excluded from this task's commits.

## Outcome

Pending live validation.

## Consequences

Both clients have a separate Turbo selection. Existing default-model settings are retained. Restart OpenCode to reload its global config; Pi reloads `models.json` when `/model` opens. Server switch instructions remain in the root README.

### Installed model listings

Pi lists both `qwen38` and `qwen38-turbo`, each with 131.1K context, 32.8K max output, thinking and images. OpenCode lists both `llm-server/qwen38` and `llm-server/qwen38-turbo`. This confirms the installed configuration parses; authentication and actual model requests are checked next.

### Effort transport and temporary server switch

The installed OpenCode model passes 2/2 loopback transport checks. With no variant, the outgoing model is `qwen38-turbo` and `reasoning_effort` is `xhigh`; selecting low sends `low`. Both requests carry temperature 1.0, top_p 0.95, top_k 20 and streaming usage. OpenCode caps the request output at 32,000 tokens, below the model declaration of 32,768. The recorder uses a dummy loopback key, does not capture messages/tools, and writes `scratch/turbo-clients/opencode-effort.log`.

Server diagnostics were captured in `scratch/turbo-clients/before-switch.log` before stopping and renaming the daily driver to `qwen38-before-turbo`. The unchanged validated `turbo-gguf` profile is starting for one real file-read/marker check per installed client. Pi uses its existing global config and extensions; OpenCode uses its existing model/auth config with external MCP disabled and only file-reading permission for the test process. Both checks omit an explicit effort override to exercise the default.
