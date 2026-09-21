# Qwen in Codex desktop

The installed profile uses the existing Responses API at `http://100.103.136.98:8000/v1`, model `qwen38`, a 131,072-token window, and xhigh thinking. It starts compaction at 90,000 tokens. Hosted OpenAI web search is disabled for this provider.

The desktop app reads `~/.codex/config.toml`. Provider selection applies to new tasks as a group. Restart the app after switching and start a fresh local task. The model picker should show `Qwen3.8-27B (vllm)` with Low, Medium and Xhigh effort. Existing OpenAI conversations should be continued with the OpenAI provider selected.

On mbp, switch to Qwen:

```sh
python3 ~/Code/llm-server/clients/codex/select-provider.py qwen
```

Restore the model settings saved before Qwen was enabled:

```sh
python3 ~/Code/llm-server/clients/codex/select-provider.py openai
```

The selector changes only the model settings declared by the Qwen profile and adds its provider definition. It preserves plugins, MCP servers, project settings and permissions. `~/.codex/qwen-original-settings.json` records the previous model settings without credentials.

The separate CLI profile works without changing desktop defaults:

```sh
codex --profile qwen
```

## Installed files

- `~/.codex/qwen.config.toml`: provider, model, context and compaction settings.
- `~/.codex/model-catalogs/qwen.json`: copy of this directory's `models.json`. The catalog makes Qwen visible in the app-server model list and limits effort choices to Qwen's supported values.
- `~/.codex/credentials/vllm-api-key`: existing server credential, mode 0600. The provider uses `/bin/cat` to read it, so desktop startup does not depend on shell environment variables. Never commit this file.

Without an explicit catalog, the tested runtime successfully called Qwen but `model/list` returned only built-in OpenAI models. The current catalog format requires `experimental_supported_tools`; `apply_patch_tool_type` accepts only `freeform` when specified, so this catalog omits it.

## Validation

The desktop-bundled Codex runtime passed a local file-read, code-edit and Node execution check. See the [setup experiment](../../docs/log/2026-09-20-codex-desktop-setup.md) for the tested configuration and remaining limitations. Native computer use cannot operate Codex's own UI, so the visible desktop picker requires user confirmation after restarting.
