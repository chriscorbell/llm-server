# Pi against this server

Pi runs on the MacBook and uses its local tools to read, edit and test code. The model request goes over Tailscale to Qwen on `vllm`.

## Install the checked configuration

Pi 0.85.1 from `@earendil-works/pi-coding-agent` is the validated client version. Keep the API key in the environment; do not copy it into JSON.

```bash
npm install -g @earendil-works/pi-coding-agent@0.85.1
mkdir -p ~/.pi/agent
cp clients/pi/models.json ~/.pi/agent/models.json
cp clients/pi/settings.json ~/.pi/agent/settings.json
test -n "$LLM_SERVER_API_KEY"
pi --list-models qwen38
```

The model declares the server's real 98,304-token window. Pi begins compaction above 57,344 estimated context tokens, reserving 32,768 for the response plus 8,192 tokens of headroom.

Sampling is explicit because Qwen's thinking preset and MTP acceptance both depend on it. The model supports low, medium and xhigh effort. xhigh is the daily-driver default; unsupported Pi levels are hidden.

## Run it

From a project directory:

```bash
pi
```

The MacBook is already configured. Keep Tailscale connected, open a terminal in the project you want to work on, and run `pi`. Describe the change and ask it to run the project's checks. Use `pi -c` to continue the most recent session in that directory. `/compact` summarizes a long conversation; automatic compaction is also enabled.

For a one-shot check:

```bash
pi --model llm-server/qwen38 --thinking xhigh --tools read,ls -p \
  "Use your tools to read README.md, then describe this project in one sentence."
```

Pi's tools run on the MacBook. A shell command requested by Qwen therefore runs in the current MacBook directory, never on `vllm`, unless the command itself uses SSH.

Keep the thinking level at xhigh for normal work. In the checked conversation, cached tool follow-ups at about 23K input tokens started in 0.9 to 1.0 seconds. The first request after compaction took 12.3 seconds at 22.6K input tokens. A pause after adding a large file or compacting is expected; these timings measure the first reasoning token at concurrency 1, not the final answer.

## Why these compatibility settings

- vLLM's Qwen template expects a system role rather than an OpenAI developer role.
- The running vLLM accepts `reasoning_effort` and maps it into the Qwen template.
- The server streams thinking as `reasoning`; Pi 0.85.1 retains that field name and sends it back with assistant tool calls.
- `max_tokens` is known to work on the running endpoint.
- Provider retries stay off so Pi's visible three-attempt retry loop handles transient errors once rather than nesting two retry loops.

If the server profile changes, update `contextWindow` here and in the installed `~/.pi/agent/models.json` together.
