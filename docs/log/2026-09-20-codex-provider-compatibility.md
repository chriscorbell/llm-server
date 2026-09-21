# 2026-09-20 Codex provider compatibility

Status: concluded, API smoke check only
Profile: ad hoc, existing inference service unchanged

## Hypothesis

The existing `qwen38` service may accept the Responses API required by current Codex, allowing a custom provider without changing the inference engine.

## Configuration

No configuration changes. Read-only inspection found standalone Codex CLI 0.154.0 and desktop-bundled Codex CLI 0.155.0-alpha.9.2 in ChatGPT app 26.915.31945 on mbp.

```sh
ssh vllm 'curl --fail --silent http://100.103.136.98:8000/openapi.json'
```

The live OpenAPI document advertises `/v1/responses` (POST), `/v1/responses/{response_id}` (GET), `/v1/responses/{response_id}/cancel` (POST), `/v1/chat/completions` (POST), and `/v1/models` (GET). Route registration alone does not establish Qwen request or tool compatibility.

## Measurements

| Check | Result |
|---|---|
| Authenticated streamed Responses request, concurrency 1 | 1/1 HTTP 200, `response.completed` |
| Input tokens | 60 |
| Output tokens | 38 |
| Expected sentinel after stripping surrounding whitespace | 1/1 `CODEx_PROVIDER_OK` |

No speed, TTFT, prefill, VRAM, MTP acceptance, tool calling, image input, compaction, or end-to-end Codex task measurements were taken.

## What happened

The first OpenAPI probe used server loopback and returned `URLError: <urlopen error [Errno 111] Connection refused>`. Repeating it against the documented Tailscale bind address succeeded. This does not indicate an inference-service failure.

Official OpenAI documentation supports custom `model_providers` in user-level `~/.codex/config.toml`. The current configuration reference permits only `wire_api = "responses"`; old examples using `wire_api = "chat"` are obsolete. Project-local configuration cannot override model providers.

Sources checked September 20, 2026:

- [Custom model providers](https://learn.chatgpt.com/docs/config-file/config-advanced#custom-model-providers)
- [Configuration reference](https://learn.chatgpt.com/docs/config-file/config-reference)

The installed desktop bundle `/Applications/ChatGPT.app/Contents/Resources/app.asar` contains explicit custom-provider handling. In `webview/assets/app-initial-a498f911edeb.js`, `hqt` recognizes a configured `model_provider` in `model_providers`; model-list construction passes `isCustomModelProvider` and `modelProvider`; the composer reads `model_provider` from configuration. This supports desktop configuration as a viable path, but is not a completed desktop interaction test.

The authenticated probe sent this JSON to `http://100.103.136.98:8000/v1/responses`, with the existing `API_KEY` read from private `compose/.env` on the server and used as a Bearer token:

```json
{
  "model": "qwen38",
  "input": "Reply with exactly CODEx_PROVIDER_OK.",
  "max_output_tokens": 128,
  "stream": true,
  "store": false
}
```

The request returned HTTP 200, text deltas, and a `response.completed` event with status `completed`. The final text was `\n\nCODEx_PROVIDER_OK`. The credential was never printed or copied into this repository.

## Outcome

Confirmed for a basic streamed text request. The live service already implements the required API, so a Responses-to-Chat-Completions proxy is not needed for this smoke check. Desktop custom-provider code exists in the installed build. Full desktop agent compatibility remains untested, especially tool calls, reasoning replay, and compaction.

## Consequences

No user configuration, server configuration, or service state changed. Added a narrowly scoped Finding to STATUS.md so future setup work starts with the existing Responses endpoint instead of assuming a proxy is required.
