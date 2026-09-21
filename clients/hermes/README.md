# Hermes Desktop against this server

Hermes Desktop on the MacBook uses the server as an OpenAI-compatible custom endpoint over Tailscale. The current configuration is:

| Setting | Value |
|---|---|
| Name | `vLLM Server` |
| Provider ID | `vllm-server` |
| Endpoint URL | `http://100.103.136.98:8000/v1` |
| Default model | `qwen38` |
| Context | `131072` |
| Use for new chats | enabled |
| Discover models | enabled |

Hermes stores the API key in `~/.hermes/.env` as `HERMES_CUSTOM_VLLM_SERVER_API_KEY`. `~/.hermes/config.yaml` contains only the environment-variable name. The key is the `API_KEY` value from the server's private `compose/.env`; never copy it into this repository.

## Configure Desktop

Open Settings, then Providers, then Custom Endpoints. Enter the values above and the server API key. Test must report one discovered model, `qwen38`, before saving.

Set Hermes to non-streaming requests:

```bash
~/.hermes/hermes-agent/venv/bin/python ~/.hermes/hermes-agent/hermes \
  config set model.streaming false
```

This is a transport workaround, not a display preference. The server runs vLLM with `--tool-call-parser qwen3_xml` and `--reasoning-parser qwen3`. Hermes documents that this combination can leak tool-call markup into plain text on the streaming Chat Completions path. Non-streaming requests preserve structured tool calls. The local vLLM endpoint is exempt from Hermes's implicit non-streaming stale-call detector, so a long prefill is not killed at the ordinary 90-second threshold.

Changing providers later does not restore streaming automatically. Run the same command with `true` after selecting a provider whose streaming tool path is known to work.

## Verify it

The endpoint test checks only `GET /v1/models`. Verify the full agent loop with a harmless terminal call:

```bash
~/.hermes/hermes-agent/venv/bin/python ~/.hermes/hermes-agent/hermes \
  --ignore-rules --reasoning none -t terminal \
  -z 'Use the terminal tool to run printf HERMES_TOOL_OK, then reply with exactly the command output and nothing else.'
```

Expected output:

```text
HERMES_TOOL_OK
```

Hermes tools run on the MacBook. A command reaches the inference server only when it explicitly uses `ssh vllm`.
