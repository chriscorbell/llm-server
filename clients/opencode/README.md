# Opencode against this server

Opencode reaches the server over Tailscale at `http://vllm:8000/v1`. The server speaks the OpenAI chat completions API with tool calling and image input.

## Install

Merge `opencode.jsonc` into `~/.config/opencode/opencode.jsonc` on the MacBook. Keep your existing `permission` and `mcp` blocks; only the `provider` and `model` keys below are ours.

Store the API key in opencode's own auth file rather than the config file or the shell environment. Run the login flow, choose "Other", enter `llm-server` as the provider id and paste the key. It lands in `~/.local/share/opencode/auth.json` with mode 0600, and opencode uses it for the provider of the same name.

```bash
opencode auth login
```

## Why these settings

- **`reasoning_effort: "xhigh"`** matches the server default. Lower it per session when you want speed over depth.
- **Sampling** follows Qwen's own recommendation for thinking mode: temperature 1.0, top_p 0.95, top_k 20. Do not drop `top_k`. Measured on this server, omitting it lowers speculative acceptance from 53% to 43% and costs about a fifth of decode speed.
- **`npm: "@ai-sdk/openai-compatible"`** rather than the plain OpenAI provider, because the server is not OpenAI and the strict provider sends fields vLLM rejects.
- **Context is declared as the server's actual limit**, not the model's 262,144 native window. Opencode uses this to decide when to compact, and overstating it means requests fail at the boundary instead of compacting. Update it whenever `MAX_MODEL_LEN` changes on the server.

## Verifying it works

```bash
opencode run -m llm-server/qwen38 "List the files in this directory using your tools, then say how many there are."
```

A reply that names real files proves tool calling works. A reply that describes what it would do proves the tool parser is misconfigured.
