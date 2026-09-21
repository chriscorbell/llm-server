# 2026-09-20 Codex desktop setup

Status: concluded, desktop UI restart pending
Profile: ad hoc, existing inference service unchanged

## Hypothesis

The desktop-bundled Codex runtime can use the existing Qwen Responses endpoint for local coding tools after configuring a custom provider and Qwen model metadata.

## Configuration

Baseline: [Responses compatibility check](2026-09-20-codex-provider-compatibility.md). The inference service remains unchanged. Test the desktop-bundled Codex 0.155.0-alpha.9.2 before selecting Qwen for new desktop tasks.

## Measurements

First runtime check, desktop-bundled Codex 0.155.0-alpha.9.2, xhigh, concurrency 1, declared context 131,072 tokens:

| Check | Result |
|---|---|
| Read an unpredictable token from a local file | 1/1 exact match |
| Correct subtraction to addition with Codex's patch tool | 1/1 completed file change |
| Execute Node checks | 2/2 passed, exit code 0 |
| Aggregate input across model requests | 53,512 tokens |
| Aggregate cached input | 47,232 tokens |
| Aggregate output | 371 tokens |

These are task totals, not the prompt size of a single request. No speed or TTFT measurements were taken. Vision and compaction remain untested.

## What happened

Current official documentation supports separate `~/.codex/qwen.config.toml` profiles through `codex --profile qwen`. The old top-level `profile` selector is no longer supported. Desktop selection therefore needs separate verification.

Native computer use cannot inspect the app: `Computer Use is not allowed to use the app 'com.openai.codex' for safety reasons.` Configuration and runtime validation will use the supported config files and Codex executable. No attempt will be made to bypass the UI restriction.

Sources:

- [Profiles](https://learn.chatgpt.com/docs/config-file/config-advanced#profiles)
- [Configuration reference](https://learn.chatgpt.com/docs/config-file/config-reference)

Created `~/.codex/qwen.config.toml` with `model = "qwen38"`, provider `vllm`, xhigh effort, 131,072 context, a 90,000-token compaction threshold, disabled hosted web search, and `wire_api = "responses"` at the existing Tailscale endpoint. Authentication uses `/bin/cat ~/.codex/credentials/vllm-api-key`; the credential was copied from the existing OpenCode entry into a mode-0600 file and never printed. The base Codex configuration was not changed during this test.

The temporary fixture `/tmp/codex-qwen-smoke` contains an unpredictable token in `input.txt`, a broken addition function in `sum.js`, and a package file. Test command:

```sh
/Applications/ChatGPT.app/Contents/Resources/codex exec \
  --ignore-user-config --profile qwen --ephemeral --skip-git-repo-check \
  --sandbox workspace-write --disable multi_agent \
  -C /tmp/codex-qwen-smoke --json \
  -o /tmp/codex-qwen-smoke/final.txt \
  'Work only inside /tmp/codex-qwen-smoke. Read input.txt with a tool. Fix sum.js so sum adds its two arguments, then run node to verify sum(2,3) is 5 and sum(-4,1) is -3. Do not delegate or access other files. In your final response, include the exact content of input.txt and state whether both checks passed.'
```

Qwen read the files with a shell command, applied the code patch, ran Node successfully, and returned the exact token. The JSON event log is at `/tmp/codex-qwen-smoke/events.jsonl`. The isolated test omitted user-configured plugins and MCP servers; it verifies the standard Codex tool loop, not every installed integration.

## Outcome

Core coding-tool loop passes. The second check below verifies the catalog and the normal user configuration. The visible desktop UI remains unverified because computer use blocks access to Codex itself.

### Model-list check after the first runtime pass

With the custom provider and model selected but no catalog, a fresh desktop-bundled app-server `model/list` call returned only five built-in OpenAI models. The Qwen runtime worked, but that configuration did not expose Qwen in the list used by the desktop picker. Added `clients/codex/models.json` as a separate configuration variable to declare Qwen and its low, medium and xhigh efforts. This catalog still requires parsing and runtime validation.

The first two catalog parses failed before any model request:

```text
failed to parse model_catalog_json path `/Users/chris/.codex/model-catalogs/qwen.json` as JSON: unknown variant `function`, expected `freeform` at line 27 column 5
failed to parse model_catalog_json path `/Users/chris/.codex/model-catalogs/qwen.json` as JSON: missing field `experimental_supported_tools` at line 26 column 5
```

Removed the optional patch-tool field to retain Codex's default tool behavior and supplied the required empty experimental-tools array.

### Catalog and full configuration pass

The corrected catalog passed parsing. A fresh desktop-bundled app-server returned exactly one visible default model: `qwen38`, displayed as `Qwen3.8-27B (vllm)`, with low, medium and xhigh efforts, default xhigh, and text/image input metadata. Image inference was not exercised by this test.

Repeated the coding fixture in `/tmp/codex-qwen-catalog-smoke`, this time with the catalog and the normal user configuration loaded. The command is the first fixture command with that directory substituted and `--ignore-user-config` omitted. The prompt also prohibited browsing, contacting external services, and reading outside the fixture.

At concurrency 1 and declared context 131,072, the file-read check passes 1/1, code-edit check passes 1/1, and Node assertions pass 2/2. This run used shell editing rather than the patch tool. Aggregate usage across the three model requests is 147,562 input tokens, 46,592 cached input tokens and 503 output tokens. These task totals exceed the per-request context window because they sum repeated prompts. No speed or per-request context measurement is claimed. The event log is `/tmp/codex-qwen-catalog-smoke/events.jsonl`.

The server logs explain developer-role compatibility:

```text
Chat template does not support the 'developer' message role. Converting developer messages to 'system' role.
```

No server configuration change was needed. The normal Codex configuration loaded its plugins and MCP settings, but this check only used local shell tools. It does not validate every plugin.

### Desktop activation

Installed the exact profile captured in `clients/codex/qwen.config.toml.example` and the catalog from `clients/codex/models.json`. Ran:

```sh
python3 clients/codex/select-provider.py qwen
python3 clients/codex/select-provider.py openai
python3 clients/codex/select-provider.py qwen
```

Readback verified Qwen activation, restoration to the previous settings, and final Qwen activation. The restored TOML matched the original parsed configuration except for the deliberately retained `vllm` provider definition. Unrelated plugin, MCP, project and permission settings were preserved. The API key file remains mode 0600.

The selector saves the previous model settings in `~/.codex/qwen-original-settings.json` and changes the corresponding top-level keys in `~/.codex/config.toml`. The final active default is Qwen, with the OpenAI settings available through the `openai` selector. The user must restart the desktop app and start a fresh local task to verify the visible picker. The running app was not interrupted.

## Consequences

Qwen is installed as the Codex default for new tasks, with a separate CLI profile and a reversible provider selector. Added `clients/codex/` setup documentation and updated STATUS.md. The inference engine, its flags and the deployed service were unchanged. Desktop picker interaction, vision and compaction remain untested.
