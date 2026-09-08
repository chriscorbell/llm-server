# llm-server

Cookbook for `vllm`, a single-GPU inference server that hosts Qwen3.8-27B on an Intel Arc Pro B70 for agentic coding from a MacBook.

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
ssh vllm 'bash -s' < scripts/setup-server.sh
```

Then copy `compose/.env.example` to `compose/.env`, fill in the render group id and an API key, and start one Profile:

```bash
ssh vllm 'cd ~/Code/llm-server/compose && docker compose --profile a-bf16kv up -d'
```

First start takes several minutes while the engine compiles kernels. Watch it with `docker logs -f qwen38`.

## Credit

The vLLM XPU recipe, the runtime patches and the reference measurements come from SergiioB's [Intel Arc Pro B70 Inference Cookbook](https://github.com/SergiioB/intel-arc-pro-b70-inference-cookbook), MIT licensed. This repository adapts that work to one specific machine and records what changed.
