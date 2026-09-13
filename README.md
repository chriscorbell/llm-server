# llm-server

Cookbook for a single-GPU inference server that hosts Qwen3.8-27B on an Intel Arc Pro B70 for agentic coding from a MacBook.

The goal is model quality first, then usable context, then decode speed, for one user at a time. This repository holds the configuration that achieves that, the measurements that justify it, and the record of everything that failed on the way.

## Start here

- [`STATUS.md`](STATUS.md) is the current truth. What is running, what is measured, what is broken.
- [`AGENTS.md`](AGENTS.md) is how to work in this repository, including the duty to record findings.
- [`CONTEXT.md`](CONTEXT.md) is the glossary.
- [`clients/pi/`](clients/pi/README.md) is the checked MacBook client configuration and launch guide.
- [`docs/log/`](docs/log/) is one file per Experiment, oldest to newest.
- [`docs/research/`](docs/research/) holds the background research the plan was built on.

## Hardware

Threadripper 3970X, 64 GB DDR4, one Intel Arc Pro B70 with 32 GB GDDR6, Ubuntu Server 26.04 with the in-tree `xe` driver. The card has no native FP8 in its matrix engines, which shapes every quantization decision here.

## Running it

On the server, once:

```bash
ssh <hostname> 'bash -s' < scripts/setup-server.sh
```

Then copy `compose/.env.example` to `compose/.env`, fill in the render group id, an API key and a SearXNG secret, and start one Profile. SearXNG, which backs Pi's web search, has no profile and starts alongside whichever engine you pick:

```bash
ssh <hostname> 'cd ~/Code/llm-server && bash scripts/compose.sh --profile a-int4draft up -d'
```

First start takes several minutes while the engine compiles kernels. Watch it with `docker logs -f qwen38`.

`scripts/compose.sh` loads the server's private `compose/.env`, then `compose/model.env` for the selected vLLM checkpoint, `compose/tuning.env` for vLLM settings and `compose/turbo.env` for the alternative GGUF engine. Configuration changes are committed on the MacBook and pulled on the server; credentials stay in `.env`. Shell variables can override one setting for an experiment. Use this wrapper for subsequent Compose commands so an older value in `.env` cannot silently undo a measured optimization.

## Abliterated GPTQ checkpoint

The selected vLLM checkpoint is [kernelogic's abliterated Qwen3.8-27B](https://huggingface.co/kernelogic/Qwen3.8-27B-Uncensored-GPTQ-Int4-sym-G128-MTP-BF16), GPTQ INT4 with symmetric groups of 128. `compose/uncensored-model.json` pins revision `bd3f8d56b9dc617c995ec5a3ececa486d1d064be` and SHA-256 checksums for all files. `compose/model.env` selects its directory. The API alias remains `qwen38`, so Pi, OpenCode and Hermes use their existing model entries.

Download and verify approximately 19.6 GB once, after the initial server setup. The original SergiioB weights remain available for rollback. The downloader resumes interrupted transfers:

```bash
ssh vllm 'cd /home/chris/Code/llm-server && python3 scripts/download-turbo.py --manifest compose/uncensored-model.json'
```

Capture diagnostics before replacing the inference container, then start the selected checkpoint. This interrupts inference and clears the prompt cache:

```bash
ssh vllm 'cd /home/chris/Code/llm-server && mkdir -p scratch && bash scripts/gpu-health.sh > scratch/before-model-switch.log 2>&1'
ssh vllm 'cd /home/chris/Code/llm-server && bash scripts/compose.sh --profile a-int4draft up -d --no-deps vllm-a-int4draft'
```

Wait for `qwen38` to become healthy. The profile retains 131,072 total context, FP8 KV, runtime INT4 draft, MTP4, vision, tools, prefix caching and xhigh thinking. See the [deployment experiment](docs/log/2026-09-13-uncensored-gptq.md) for measured results and remaining limitations.

To temporarily restore the original checkpoint with the same settings, capture diagnostics again and override only its directory:

```bash
ssh vllm 'cd /home/chris/Code/llm-server && bash scripts/gpu-health.sh > scratch/before-original-restore.log 2>&1'
ssh vllm 'cd /home/chris/Code/llm-server && MODEL_DIR=/home/chris/models/Qwen3.8-27B-GPTQ-Int4-sym-G128-MTP-BF16 bash scripts/compose.sh --profile a-int4draft up -d --no-deps vllm-a-int4draft'
```

For a persistent rollback, change `compose/model.env` on mbp, commit and push, then pull on vllm before recreating. A shell override does not update the saved selection.

## Turbo GGUF profile

`turbo-gguf` serves [DavidAU's Qwen3.8-27B Turbo fine-tune](https://huggingface.co/DavidAU/Qwen3.8-27B-TURBO-Fable-Cold-Fusion-735-882-Heretic-Uncensored-NEO-CODER-MAX-MTP-GGUF) through llama.cpp SYCL. It uses Q6_K weights and the F16 vision projector. The model revision and SHA-256 checksums are in `compose/turbo-model.json`; the engine digest and context are in `compose/turbo.env`. See the [deployment experiment](docs/log/2026-09-13-turbo-gguf.md) and [backend comparison](docs/log/2026-09-13-turbo-sycl.md) for validation and limitations.

The configuration uses a 131,072-token window, Q8_0 KV cache, MTP2, tool calling and image input. Thinking is on by default at xhigh, with no separate reasoning-token cap. The window includes input, reasoning and the final answer. Warm code decode measured 34.1 tok/s at 4,239 input tokens, 384 generated tokens, xhigh and concurrency 1. Retrieval and continuation pass 3/3 with xhigh at 123,975 to 124,943 input tokens. The first request starts in 216.848 s, the cached repeat in 1.035 s, and the continuation in 4.660 s. Selected Pi coding and image tasks pass 2/2 at xhigh; sampled peak VRAM is 29.26 GiB. These checks validate operation on this server; they do not rank overall quality against the daily driver. [Q8 cache comparison](docs/log/2026-09-13-turbo-thinking-q8kv.md), [128K thinking validation](docs/log/2026-09-13-turbo-thinking-128k.md)

Download once on the server, about 25 GB total. Interrupted downloads resume:

```bash
ssh vllm 'cd ~/Code/llm-server && python3 scripts/download-turbo.py'
ssh vllm 'cd ~/Code/llm-server && bash scripts/compose.sh --profile turbo-gguf pull llama-turbo'
```

Only one profile fits on the GPU. Switching interrupts inference and clears the current prompt cache. Capture diagnostics first, then replace only the inference container:

```bash
ssh vllm 'cd ~/Code/llm-server && mkdir -p scratch && bash scripts/gpu-health.sh > scratch/before-profile-switch.log 2>&1'
ssh vllm 'docker stop qwen38 && docker rm qwen38'
ssh vllm 'cd ~/Code/llm-server && bash scripts/compose.sh --profile turbo-gguf up -d --no-deps llama-turbo'
```

Wait for `docker ps` to show `qwen38` as healthy. The API remains `http://vllm:8000/v1` with the existing key; select model `qwen38-turbo` in your client. Set its context window to 131,072 tokens and its output limit to 32,768 tokens. Keep input and tool results within the remaining 98,304 tokens, with compaction headroom below that. Use `reasoning_effort: "xhigh"` when the client exposes an effort setting; a request that omits it inherits the server default. The client's `qwen38` entry describes the vLLM daily driver; Turbo uses the separate model ID `qwen38-turbo`.

Restore the daily driver:

```bash
ssh vllm 'cd ~/Code/llm-server && bash scripts/gpu-health.sh > scratch/before-profile-restore.log 2>&1'
ssh vllm 'docker stop qwen38 && docker rm qwen38'
ssh vllm 'cd ~/Code/llm-server && bash scripts/compose.sh --profile a-int4draft up -d --no-deps vllm-a-int4draft'
```

Use `qwen38` in the client again after startup. SearXNG keeps running during both switches. The recovery watchdog follows the shared container name and health URL.

## Credit

The vLLM XPU recipe, the runtime patches and the reference measurements come from SergiioB's [Intel Arc Pro B70 Inference Cookbook](https://github.com/SergiioB/intel-arc-pro-b70-inference-cookbook), MIT licensed. This repository adapts that work to one specific machine and records what changed.
