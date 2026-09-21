# 2026-09-12 T3 Code OpenCode reasoning picker

Status: concluded
Profile: ad hoc client inspection, server `a-int4draft` unchanged

## Hypothesis

The reasoning level selected in T3 Code should change the effort sent through OpenCode to `llm-server/qwen38`.

## Configuration

T3 Code 0.0.40, commit `09e8de9c655a`, and OpenCode 1.18.30 on mbp. The installed provider uses `@ai-sdk/openai-compatible`, with `options.reasoning_effort: "xhigh"` and no explicit variants. Its model inventory reports `variants: {}`. T3's cached inventory nevertheless lists Low, Medium, High and Xhigh for this model.

A temporary loopback HTTP recorder replaces only the provider base URL and credential for each child process. It returns a fixed SSE completion, disables MCP and denies tools. It records request fields excluding messages, tools and headers. The installed user configuration is unchanged. Each invocation differs only in `--variant`:

```bash
opencode run --pure --dir "$PROBE_DIR" -m llm-server/qwen38 \
  --variant low --format json --title 'Reasoning transport check' \
  'Reply OK. Do not use tools.'
```

The recorder invocation is `python3 /tmp/t3-qwen-reasoning-inspection/capture_variants.py`. Baseline: [OpenCode authentication check](2026-09-11-opencode-provider-auth.md). This experiment verifies parameter transport, not model quality or speed.

## Measurements

| Selected variant | Requests captured | `reasoning_effort` in request | Exit code |
|---|---:|---|---:|
| low | 1 | absent | 0 |
| medium | 1 | absent | 0 |
| high | 1 | absent | 0 |
| xhigh | 1 | absent | 0 |

The four captured request parameter sets are identical. Selection-to-effort checks pass 0/4. No inference was performed by the recorder. Decode throughput, TTFT, prefill throughput, peak VRAM, MTP acceptance and task-suite quality were not measured.

## What happened

The recorder reports `FAIL: selections did not reach reasoning_effort`. Every request includes model `qwen38`, temperature 1, top_p 0.95, top_k 20, max_tokens 32000 and streaming, with neither `reasoning_effort` nor `chat_template_kwargs`.

Before server inspection, `ssh vllm 'cd ~/Code/llm-server && ./scripts/gpu-health.sh'` reported a healthy container and HTTP 200 health. The captured kernel output shows no GPU reset or Level Zero fault. No restart was performed.

## Outcome

The current picker does not map its four choices to distinct outgoing effort parameters. The exact T3 fallback and OpenCode adapter behavior are still being inspected.

## Consequences

No installed client or server configuration has changed. Request capture results are in `/var/folders/5p/9fk78x3d20gd_yln3r0_m4k00000gn/T/qwen-variant-capture-5ha93f8t/results.json`.

## Source inspection and isolated mapping check

T3's installed `apps/server/dist/bin.mjs`, function `openCodeCapabilitiesForModel`, substitutes `low`, `medium`, `high`, `xhigh` when the model's variant map is empty. Its `session.promptAsync` call forwards the selection as `variant`. T3's cached provider snapshot also reports OpenCode 1.18.30, checked at 2026-09-13T01:27:27.778Z.

OpenCode's variant generator returns an empty map for model IDs containing `qwen`. The OpenAI-compatible adapter consumes camel-case `reasoningEffort` and emits snake-case `reasoning_effort` on the wire. The installed snake-case option does not reach the request. [OpenCode transform source](https://github.com/anomalyco/opencode/blob/v1.18.30/packages/opencode/src/provider/transform.ts), [AI SDK adapter](https://github.com/vercel/ai/blob/main/packages/openai-compatible/src/chat/openai-compatible-chat-language-model.ts).

The same recorder was rerun with one additional configuration field, an explicit variant map, supplied only through the child process's `OPENCODE_CONFIG_CONTENT`:

```json
{
  "provider": {
    "llm-server": {
      "models": {
        "qwen38": {
          "variants": {
            "low": { "reasoningEffort": "low" },
            "medium": { "reasoningEffort": "medium" },
            "xhigh": { "reasoningEffort": "xhigh" }
          }
        }
      }
    }
  }
}
```

`python3 /tmp/t3-qwen-reasoning-inspection/capture_explicit_variants.py` passed 3/3 transport checks. Each run emitted one request with `reasoning_effort` matching the selected low, medium or xhigh variant, and exited 0. Other recorded parameters matched the baseline. Results are in `/var/folders/5p/9fk78x3d20gd_yln3r0_m4k00000gn/T/qwen-variant-capture-nkudkt51/results.json`. This verifies a candidate mapping without installing it.

The first server template probe failed before rendering because the probe passed `add_generation_prompt` both explicitly and inside the kwargs returned by `build_chat_params`:

```text
jinja2.environment.Template.render() got multiple values for keyword argument 'add_generation_prompt'
```

This is a probe error, not an inference failure. The corrected probe uses the returned kwargs directly. No service changes were needed.

## Server verification

The corrected probe ran inside the current container, vLLM `0.27.2rc1.dev77+gac7509e2b`, using its actual `ChatCompletionRequest` and `/model/chat_template.jinja`:

```bash
ssh vllm 'docker exec -i qwen38 python -' <<'PY'
import hashlib
from pathlib import Path
from jinja2 import Environment
from vllm.entrypoints.openai.chat_completion.protocol import ChatCompletionRequest

def fail(message):
    raise ValueError(message)

env = Environment()
env.globals['raise_exception'] = fail
template = env.from_string(Path('/model/chat_template.jinja').read_text())
for effort in [None, 'low', 'medium', 'high', 'xhigh', 'none']:
    body = {'model': 'qwen38', 'messages': [{'role': 'user', 'content': 'Reply OK.'}]}
    if effort is not None:
        body['reasoning_effort'] = effort
    try:
        request = ChatCompletionRequest(**body)
        kwargs = request.build_chat_params(None, 'auto').chat_template_kwargs or {}
        prompt = template.render(messages=body['messages'], **kwargs)
        print(effort, kwargs, hashlib.sha256(prompt.encode()).hexdigest())
    except Exception as error:
        print(effort, str(error))
PY
```

| Request effort | Template result | Prompt SHA-256, first 12 characters |
|---|---|---|
| absent | thinking on, xhigh instruction | `4539a30696d2` |
| low | thinking on, low instruction | `96647996b800` |
| medium | thinking on, no added effort instruction | `afe2d2404a84` |
| high | rejected | not rendered |
| xhigh | thinking on, xhigh instruction | `4539a30696d2` |
| none | thinking off | `ab1374ac32d1` |

The absent-effort and explicit-xhigh prompts have identical complete hashes. Low, medium and xhigh produce three distinct prompts. High raises exactly:

```text
Unexpected reasoning effort high. Supported types are xhigh (default), medium, and low.
```

All six expected server-mapping checks pass, including rejection of high. No model generation or timing comparison was performed. [Qwen's official supported levels](https://huggingface.co/Qwen/Qwen3.8-27B#api-usage) agree with the installed template.

## Final outcome and consequences

The picker is ineffective with the installed configuration. T3 forwards the selected variant name, but OpenCode has no corresponding variant options and its configured snake-case effort is dropped. The server therefore renders its xhigh default for all four current choices. This conclusion comes from installed T3 source and inventory, four actual OpenCode request captures, and the running server's request parser and template. No interactive T3 chat was submitted during this diagnosis.

The tested correction is the explicit three-level variant map above. A complete configuration cleanup should also replace the ignored `options.reasoning_effort` key with `options.reasoningEffort` for the default. T3 derives its choices from nonempty model variants when it refreshes inventory; a refreshed interactive picker has not been tested.

`STATUS.md` records the defect and the installed OpenCode version. The OpenCode setup guide no longer claims that the current picker lowers effort. No installed client configuration, server configuration, engine image, model, driver or kernel was changed. Existing unrelated working-tree changes were preserved. This diagnosis verifies transport and template behavior, not comparative model reasoning quality.
