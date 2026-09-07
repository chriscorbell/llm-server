# Agent instructions for llm-server

This repository is the cookbook for `vllm`, a bare-metal inference server that hosts Qwen3.8-27B on a single Intel Arc Pro B70. It exists because agent context is ephemeral and this hardware is poorly documented. Anything you learn here that a future agent would have to rediscover belongs in a file, not in your reply.

## Where you run

You run on `mbp` (the MacBook). The server is `vllm`, reachable as `ssh vllm` over Tailscale. Never assume you are on the server. Every server command goes through SSH.

The working clone on the server is `/home/chris/Code/llm-server`. Changes flow one way: commit and push from `mbp`, then `ssh vllm 'cd ~/Code/llm-server && git pull'`. Do not edit files directly on the server. If you find uncommitted changes there, commit them from the server with an explanatory message rather than discarding them.

## The recording duty

This is the primary obligation of any agent working in this repository. It is not optional and it is not something to do "at the end if there is time".

Write to the log **as you go**, not once at the end of your turn. A thread that dies mid-experiment must leave behind enough for the next agent to continue.

Three files carry state:

- `STATUS.md` is the current truth. What is running right now, which profile, which flags, which measured numbers, what is known broken. A fresh agent should be able to read only this file and act correctly. Rewrite the affected lines whenever reality changes. Never let it describe a past state.
- `docs/log/YYYY-MM-DD-topic.md` is one Experiment per file, append-only in spirit. Never edit an old entry to make it agree with a newer result. Write a new entry that supersedes it and link back.
- `CONTEXT.md` is the glossary. Add a term the moment you find yourself explaining it twice.

### When to write a log entry

Write one for every one of these, without being asked:

- A configuration change that you measured, whether it helped or not.
- A failure, crash, hang, or wrong output, with the exact error text and the fix or the workaround.
- A version bump of the engine image, the model, the driver, or the kernel, with before and after numbers.
- A dead end. Negative results are the most valuable thing here because they stop the next agent repeating the work.

A tuning idea you had but did not test is not an Experiment. Put it in `STATUS.md` under open questions.

### Experiment entry format

Copy `docs/log/TEMPLATE.md`. Every entry states, in this order: the hypothesis, the exact configuration as a copy-pasteable diff or command, the measurements as numbers with units, the outcome, and what changed as a result. If you did not measure it, say so explicitly rather than implying a result.

Numbers that matter and how to get them: decode tokens per second, time to first token, prefill tokens per second, peak VRAM, MTP acceptance rate, and for evals the pass count out of total. `scripts/bench.sh` produces the first four. Never report a speed without saying at what context length and concurrency it was measured, because both dominate the result on this hardware.

### Promoting a Finding

When an Experiment produces a conclusion that should outlive it, copy the conclusion into `STATUS.md` as a Finding with a link to the entry. A Finding is a durable claim about this hardware or this model. An Experiment is the evidence for it.

## Working rules for this machine

Read `STATUS.md` and the two reports in `docs/research/` before proposing a configuration change. Most obvious ideas have already been tried by the community on this exact card, and the reports say which ones failed.

Change one variable per Experiment. Batching three flag changes into one run produces a number you cannot attribute.

Pin versions. The engine image is pinned by digest in `compose/`. Do not move to `:latest` to fix a problem. Bump the pin deliberately, in its own Experiment, and record both digests.

The Arc Pro B70 fails in ways NVIDIA hardware does not. Before diagnosing a model or engine bug, check `dmesg` on the server for `xe` engine resets and Level Zero errors, and check whether the container survived. `scripts/gpu-health.sh` collects this.

Do not restart the service to "see if that fixes it" without first capturing the logs and GPU state that would explain the failure. That state is gone after the restart and it is exactly what the log entry needs.

## Boundaries

Safe without asking: reading anything, running benchmarks and evals, starting and stopping the inference container, pulling images, downloading model weights, editing files in this repository.

Ask Chris first: rebooting the server, changing the kernel or GPU driver, changing SSH, firewall or Tailscale configuration, deleting model weights, and anything that would expose the API beyond the Tailscale interface.

## Prose

Follow the global instructions in `~/.claude/CLAUDE.md`. Concrete over promotional, sentence case headings, no emoji, no em dashes. In this repository specifically: write down the number, not the adjective. "Decode fell to 56 tok/s at 131k context" is useful. "Performance degraded significantly at long context" is not.
