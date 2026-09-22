# llm-server

Cookbook for a single-GPU inference server that hosts Qwen3.8-27B on an Intel Arc Pro B70 for agentic coding from a MacBook.

The goal is model quality first, then usable context, then decode speed, for one user at a time. This repository holds the configuration that achieves that, the measurements that justify it, and the record of everything that failed on the way.

## Start here

- [`STATUS.md`](STATUS.md) is the current truth. What is running, what is measured, what is broken.
- [`AGENTS.md`](AGENTS.md) is how to work in this repository, including the duty to record findings.
- [`CONTEXT.md`](CONTEXT.md) is the glossary.
- [pi-config](https://github.com/chriscorbell/pi-config) contains the complete MacBook Pi setup, including the local-server model definition and extension. [`clients/pi/`](clients/pi/README.md) records the migration and evaluation paths.
- [`docs/log/`](docs/log/) is one file per Experiment, oldest to newest.
- [`docs/research/`](docs/research/) holds the background research the plan was built on.

## Hardware

Threadripper 3970X, 64 GB DDR4, one Intel Arc Pro B70 with 32 GB GDDR6, Ubuntu Server 26.04 with the in-tree `xe` driver. The card has no native FP8 in its matrix engines, which shapes every quantization decision here.

## Running it

On the server, once:

```bash
ssh <hostname> 'bash -s' < scripts/setup-server.sh
```

Then copy `compose/.env.example` to `compose/.env`, fill in the render group id, an API key and a SearXNG secret, download the abliterated checkpoint, and start one Profile. The setup script downloads the original checkpoint. SearXNG, which provides a fallback for Pi's Exa-first web search, has no profile and starts alongside either model:

```bash
ssh <hostname> 'cd ~/Code/llm-server && python3 scripts/download-turbo.py --manifest compose/uncensored-model.json'
ssh <hostname> 'cd ~/Code/llm-server && bash scripts/compose.sh --profile a-int4draft up -d'
```

First start takes several minutes while the engine compiles kernels. Watch it with `docker logs -f qwen38`.

`scripts/compose.sh` loads the server's private `compose/.env`, then `compose/model.env` for both checkpoint directories and `compose/tuning.env` for measured vLLM settings. Configuration changes are committed on the MacBook and pulled on the server; credentials stay in `.env`. Shell variables can override one setting for an experiment. Use this wrapper for subsequent Compose commands so an older value in `.env` cannot silently undo a measured optimization.

## Checkpoint profiles

Only two Compose profiles are configured. Both expose API model `qwen38` with the same FP8 KV, runtime INT4 draft, MTP4, vision, tool calling, prefix caching and 131,072-token settings. They differ only in the checkpoint mounted at `/model`:

- `a-int4draft` mounts [kernelogic's abliterated Qwen3.8-27B](https://huggingface.co/kernelogic/Qwen3.8-27B-Uncensored-GPTQ-Int4-sym-G128-MTP-BF16). `compose/uncensored-model.json` pins revision `bd3f8d56b9dc617c995ec5a3ececa486d1d064be` and every file checksum.
- `original-int4draft` mounts the preceding [SergiioB checkpoint](https://huggingface.co/SergiioB/Qwen3.8-27B-GPTQ-Int4-sym-G128-MTP-BF16) at revision `9d189a60e4c0ad7f9f47cd94bfa393ca10b3924e`.

Download and verify the approximately 19.6 GB abliterated checkpoint once after the initial setup. Interrupted downloads resume:

```bash
ssh vllm 'cd /home/chris/Code/llm-server && python3 scripts/download-turbo.py --manifest compose/uncensored-model.json'
```

Capture diagnostics before replacing the inference container. Switching interrupts inference and clears the prompt cache. Start the original profile with:

```bash
ssh vllm 'cd ~/Code/llm-server && mkdir -p scratch && bash scripts/gpu-health.sh > scratch/before-original-profile.log 2>&1'
ssh vllm 'docker rm -f qwen38'
ssh vllm 'cd ~/Code/llm-server && bash scripts/compose.sh --profile original-int4draft up -d --no-deps vllm-original-int4draft'
```

Restore the abliterated daily driver with:

```bash
ssh vllm 'cd ~/Code/llm-server && bash scripts/gpu-health.sh > scratch/before-abliterated-profile.log 2>&1'
ssh vllm 'docker rm -f qwen38'
ssh vllm 'cd ~/Code/llm-server && bash scripts/compose.sh --profile a-int4draft up -d --no-deps vllm-a-int4draft'
```

Wait for `docker ps` to show `qwen38` as healthy after either command. Pi, OpenCode and Hermes keep using their existing `qwen38` entry; selecting a client model does not switch the server profile. SearXNG remains up during the switch. See the [two-profile deployment](docs/log/2026-09-13-two-checkpoint-profiles.md), [abliterated validation](docs/log/2026-09-13-uncensored-gptq.md) and [original 128K validation](docs/log/2026-09-12-context-128k.md).

## Credit

The vLLM XPU recipe, the runtime patches and the reference measurements come from SergiioB's [Intel Arc Pro B70 Inference Cookbook](https://github.com/SergiioB/intel-arc-pro-b70-inference-cookbook), MIT licensed. This repository adapts that work to one specific machine and records what changed.
