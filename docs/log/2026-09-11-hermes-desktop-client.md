# Hermes Desktop client validation

Status: concluded
Profile: ad hoc
Author: agent thread on mbp

## Hypothesis

Hermes Desktop 0.21.1 can use the existing OpenAI-compatible vLLM endpoint for model discovery and structured tool calls when its custom provider has the real context limit and uses non-streaming requests.

## Configuration

No server setting changed. The following client configuration was added on mbp, relative to Hermes's prior `auto` provider using `anthropic/claude-opus-4.6`:

```yaml
model:
  default: qwen38
  provider: vllm-server
  base_url: http://100.103.136.98:8000/v1
  key_env: HERMES_CUSTOM_VLLM_SERVER_API_KEY
  streaming: false

providers:
  vllm-server:
    name: vLLM Server
    base_url: http://100.103.136.98:8000/v1
    model: qwen38
    discover_models: true
    context_length: 98304
    key_env: HERMES_CUSTOM_VLLM_SERVER_API_KEY
    models:
      qwen38:
        context_length: 98304
```

`~/.hermes/.env` holds `HERMES_CUSTOM_VLLM_SERVER_API_KEY`, copied from `API_KEY` in the server's private `compose/.env`. The secret is not in the repository.

Non-streaming was selected because the server runs `--tool-call-parser qwen3_xml` with `--reasoning-parser qwen3`. Hermes 0.21.1 documents a failure mode in which this combination's streaming path emits tool-call markup as plain text and returns no structured `tool_calls`.

The verification command was:

```bash
~/.hermes/hermes-agent/venv/bin/python ~/.hermes/hermes-agent/hermes \
  --ignore-rules --reasoning none -t terminal \
  -z 'Use the terminal tool to run printf HERMES_TOOL_OK, then reply with exactly the command output and nothing else.'
```

Baseline for comparison: none. Hermes had no custom endpoints before this change.

## Measurements

| Metric | Baseline | This run |
|---|---:|---:|
| Models returned by endpoint validation | not configured | 1 (`qwen38`) |
| Terminal tool-call pass count, concurrency 1, reasoning off | not configured | 1/1 |
| End-to-end one-shot wall time | not configured | 11.6 s |

Decode rate, time to first token, prefill rate, peak VRAM and MTP acceptance were not measured. The one-shot command reports only total wall time.

## What happened

Hermes's endpoint validation reached `GET http://100.103.136.98:8000/v1/models` with the configured bearer key and discovered `qwen38`. Saving the endpoint made `vllm-server` the default for new chats. Desktop showed `custom:vllm-server: qwen38` with the gateway ready.

The one-shot request asked the model to invoke Hermes's terminal tool. Hermes ran `printf HERMES_TOOL_OK`, returned the command result to the model and printed exactly `HERMES_TOOL_OK`.

## Outcome

Confirmed for endpoint discovery and one structured terminal tool round trip. This does not validate image input, long-context compaction, tool reliability across a longer task or quality at Hermes's normal reasoning setting.

## Consequences

Hermes Desktop now uses `vllm-server/qwen38` by default on mbp with non-streaming model requests. The durable current state was added to `STATUS.md`, and `clients/hermes/README.md` records setup and verification.
