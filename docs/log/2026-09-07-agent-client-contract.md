# 2026-09-07 Agent client request and reasoning contract

Status: concluded for source and request-parser inspection; client round trip untested
Profile: ad hoc, local client inspection against the running Profile A

## Hypothesis

The OpenCode configuration sends Qwen's intended sampling and reasoning settings and preserves reasoning through a tool round trip.

## Configuration

No inference configuration change. Inspect OpenCode 1.18.27 on mbp and the running container through SSH. A local mock endpoint was considered; the investigation changed to Pi after Chris identified it as the intended client. No client request capture was performed.

```bash
opencode --version
ssh vllm 'docker inspect qwen38 --format "{{json .Config.Cmd}}"'
ssh vllm 'docker exec qwen38 cat /model/generation_config.json /model/chat_template.jinja'
```

Baseline: [task suite](2026-09-07-task-suite-baseline.md).

## Measurements

- Client: OpenCode 1.18.27.
- Running engine: vLLM `0.27.2rc1.dev77+gac7509e2b.xpu`, XPU kernels `0.1.12.3`, PyTorch `2.13.0+xpu`, Transformers `5.15.0`.
- Context limit: 98,304 tokens; maximum concurrent sequences: 1; speculative tokens: 4; GPU utilization setting: 0.95; batched tokens: 8,192; KV dtype: `auto` with `--dtype float16`.
- Container health: healthy, zero restarts for this container, started `2026-09-08T00:31:21.980018882Z`.
- No new task pass count, inference latency, throughput, VRAM peak, or MTP acceptance measurement yet.

## What happened

The live checkpoint's generation config sets temperature 1.0, top_p 0.95, and top_k 20. Startup logs confirm vLLM adopted those defaults. The earlier claim that every client must explicitly send top_k 20 needs qualification for this running configuration.

The live chat template supports `reasoning_effort` values `xhigh`, `medium`, and `low`, with `xhigh` as the default. It reads historical assistant reasoning from `message.reasoning_content`. The existing first-boot experiment reports response reasoning in `message.reasoning`. Whether OpenCode bridges these fields is under inspection.

The initial GPU-state command used `rg`, which is absent on the server:

```text
bash: line 1: rg: command not found
```

Re-running with `grep` worked. The kernel log contains a fault storm ending at `2026-09-07T23:30:10+00:00`, before the current container started:

```text
xe 0000:4c:00.0: [drm] Tile0: GT0: Fault response: Unsuccessful -EINVAL
```

This is historical evidence, not proof the currently healthy container is failing. No restart, driver change, or reboot was performed.

## Outcome

The server source bridges incoming reasoning aliases correctly. At the running commit, `ChatCompletionRequest` normalizes `reasoning_content` to `reasoning`, and `chat_utils.py` supplies both names to the template. The apparent naming mismatch does not demonstrate a server bug.

Exercising the installed `ChatCompletionRequest.build_chat_params()` with synthetic messages produced these four results without inference:

| Request effort | Template effort | Template thinking |
|---|---|---|
| low | low | true |
| medium | medium | true |
| xhigh | xhigh | true |
| none | none | false |

Reproduction:

```bash
ssh vllm 'docker exec -i qwen38 python -' <<'PY'
from vllm.entrypoints.openai.chat_completion.protocol import ChatCompletionRequest
for effort in ['low', 'medium', 'xhigh', 'none']:
    req = ChatCompletionRequest(model='qwen38', reasoning_effort=effort,
        messages=[{'role': 'user', 'content': 'Test.'}])
    print(effort, req.build_chat_params(None, 'auto').chat_template_kwargs)
PY
```

Pi 0.73.1 source reads streamed `reasoning` and retains that field name for replay. Its standard `openai` thinking format sends mapped effort levels; its `qwen-chat-template` format only sends the on/off switch and preservation flag, so selecting that format would not transmit medium versus xhigh on this version. See the [Pi readiness report](../research/2026-09-07-pi-readiness.md) for pinned sources and a proposed configuration.

OpenCode's custom model has no `interleaved` declaration. Source inspection found an explicit reasoning replay path gated by that declaration, but no request capture verified whether another path preserves it. Do not call reasoning loss a measured defect in the existing OpenCode runs.

The live defaults and effort mapping are verified. Complete client reasoning preservation, image input, and coding-task success through Pi remain untested.

## Consequences

Investigation notes added and stale current-state claims qualified in `STATUS.md`. No runtime or client configuration change.
