# OpenCode against this server

OpenCode reaches the server over Tailscale at `http://vllm:8000/v1`. The server speaks the OpenAI chat completions API with tool calling and image input. The provider ID is `llm-server`, and the API model ID is `qwen38`, displayed as `Qwen3.8-27B GPTQ-INT4`. Its context limit is 131,072 tokens, including input and output.

The server has `a-int4draft` and `original-int4draft` profiles. Both expose the same `qwen38` API model, so switching checkpoints does not require a client configuration change. Selecting a client model does not switch the server profile.

## Install

Merge the `provider` block from `opencode.jsonc` into `~/.config/opencode/opencode.jsonc` on the MacBook. Keep your existing settings and providers. Copy the template's top-level `model` setting only if Qwen should become the default.

Store the API key in OpenCode's own auth file. Run the login flow, choose "Other", enter `llm-server` as the provider ID and paste the key. It lands in `~/.local/share/opencode/auth.json` with mode 0600, and OpenCode uses it for the provider of the same name.

```bash
opencode auth login
```

Remove `provider.llm-server.options.apiKey` if it points to `{env:LLM_SERVER_API_KEY}`. An unset environment variable leaves an empty credential override. The persistent entry in `auth.json` has the form `"llm-server": {"type": "api", "key": "<server key>"}`. Preserve other entries when updating that file. [OpenCode custom-provider documentation](https://opencode.ai/docs/providers/#custom-provider)

Restart an existing OpenCode session after setup. Select `Qwen3.8-27B GPTQ-INT4` under `llm-server (vllm)` in `/models`, or launch it directly:

```bash
opencode -m llm-server/qwen38
```

## Why these settings

- **Reasoning uses explicit low, medium and xhigh variants.** OpenCode config uses camel-case `reasoningEffort`; the adapter sends `reasoning_effort` to the server. Xhigh is the default when no variant is selected. Qwen rejects high, so it is omitted. The installed configuration passes three selection checks and two default/override checks. [Picker fix](../../docs/log/2026-09-12-t3-opencode-reasoning-fix.md), [default-effort check](../../docs/log/2026-09-12-opencode-default-effort.md)
- **Sampling** follows Qwen's thinking preset: temperature 1.0, top_p 0.95, top_k 20. The running server also supplies these defaults, so omission does not establish that top_k is disabled. [Effective server settings](../../docs/log/2026-09-07-agent-client-contract.md)
- **`npm: "@ai-sdk/openai-compatible"`** rather than the plain OpenAI provider, because the server is not OpenAI and the strict provider sends fields vLLM rejects.
- **Context is declared as the server's actual limit**, not the model's 262,144 native window. Update it whenever `MAX_MODEL_LEN` changes on the server.
- **The input budget is 98,304 tokens**, the 131,072-token window minus the declared 32,768-token output allowance. This explicit `limit.input` activates OpenCode 1.18.30's 20,000-token compaction buffer, giving a computed trigger of 78,304 tokens. Without it, compaction waited until 99,072 and a batch of file results overflowed the next request. The installed correction passes the captured-usage reproduction. [Overflow diagnosis](../../docs/log/2026-09-12-opencode-context-overflow.md), [headroom correction](../../docs/log/2026-09-12-opencode-compaction-headroom.md)

## Verifying it works

In T3 Code, use Settings > Providers > Refresh provider status after changing the OpenCode model config. Select Qwen in the composer. Its Reasoning menu should contain only Low, Medium and Xhigh. This refresh was verified in T3 Code 0.0.40 with OpenCode 1.18.30.

An existing T3-managed OpenCode runtime can retain old model limits after that inventory refresh. Restart T3 after active work finishes to load changed context budgets into its runtime. A read-only check during the presentation task confirmed this distinction. [Runtime readback](../../docs/log/2026-09-12-opencode-compaction-headroom.md#active-runtime-readback)

For a standalone OpenCode request, select a level with `--variant`:

```bash
opencode run -m llm-server/qwen38 --variant medium "Reply OK without using tools."
```

```bash
env -u LLM_SERVER_API_KEY opencode models llm-server
opencode run -m llm-server/qwen38 "List the files in this directory using your tools, then say how many there are."
```

The model list should contain `llm-server/qwen38`. Check for an actual completed tool event and a reply that matches the files. A model listing alone does not verify authentication, and prose describing a tool call does not prove it ran.
