# Opencode against this server

Opencode reaches the server over Tailscale at `http://vllm:8000/v1`. The server speaks the OpenAI chat completions API with tool calling and image input.

## Install

Merge `opencode.jsonc` into `~/.config/opencode/opencode.jsonc` on the MacBook. Keep your existing `permission` and `mcp` blocks; only the `provider` and `model` keys below are ours.

Put the API key in the environment rather than the config file:

```bash
echo 'export LLM_SERVER_API_KEY=...' >> ~/.zshrc
```

## Why these settings

- **`reasoning_effort: "xhigh"`** matches the server default. Lower it per session when you want speed over depth.
- **Sampling** follows Qwen's own recommendation for thinking mode: temperature 1.0, top_p 0.95, top_k 20. Greedy decoding degrades this model noticeably, so do not set temperature 0.
- **`npm: "@ai-sdk/openai-compatible"`** rather than the plain OpenAI provider, because the server is not OpenAI and the strict provider sends fields vLLM rejects.
- **Context is declared as the server's actual limit**, not the model's 262,144 native window. Opencode uses this to decide when to compact, and overstating it means requests fail at the boundary instead of compacting. Update it whenever `MAX_MODEL_LEN` changes on the server.

## Verifying it works

```bash
opencode run -m llm-server/qwen38 "List the files in this directory using your tools, then say how many there are."
```

A reply that names real files proves tool calling works. A reply that describes what it would do proves the tool parser is misconfigured.
