# Context

Glossary for this project. Terms only, no implementation detail and no configuration values. If you need to explain a word twice, add it here.

## Profile

A named, runnable server configuration defined as a Docker Compose profile: one engine, one weight format, one set of flags. Exactly one Profile runs at a time, because the GPU holds one model. Profiles are how we A/B engines and quantizations against identical prompts.

## Experiment

One dated entry in `docs/log/` recording a single hypothesis tested against a single changed variable. It holds the exact configuration, the measurements, and the outcome. Experiments are never rewritten after the fact. A later Experiment supersedes an earlier one by linking to it.

## Finding

A durable conclusion promoted out of an Experiment into `STATUS.md`. A Finding is a claim about how this hardware, driver, engine, or model behaves, stated so that a future agent can act on it without reading the log. Every Finding cites the Experiment that produced it.

## Profile A

The daily-driver Profile: vLLM XPU serving Qwen3.8-27B with 4-bit GPTQ weights, keeping the Gated DeltaNet projections and the multi-token prediction head in BF16. Named so that log entries can refer to it without restating the flags.

## MTP

Multi-token prediction. A small head trained into Qwen3.8 that proposes several tokens ahead, which the main model then verifies in one pass. It is speculative decoding using the model's own head rather than a separate draft model. Its value is measured by acceptance rate, the fraction of proposed tokens the main model keeps.

## Acceptance rate

The fraction of MTP-proposed tokens accepted by the verification pass. It falls sharply as concurrency rises, which is why this server is configured for a single user.

## GDN layers

The Gated DeltaNet layers of Qwen3.8's hybrid attention. Forty-eight of the sixty-four layers are GDN and hold a fixed-size recurrent state rather than a growing cache. Only the sixteen full-attention layers contribute to KV cache growth, which is why long context is affordable on 32 GB. Quantizing GDN projections is known to damage quality, so they stay in BF16.

## KV budget

The VRAM left for the key-value cache after weights, activations, and the vision tower. It sets the maximum context length. Every quantization decision is ultimately a trade between weight precision and KV budget.

## Task suite

The fixed set of pass/fail coding tasks in `eval/` used to score a Profile's real behavior, as opposed to its speed. Each task has a test that decides the outcome without human judgment. One task requires reading a screenshot, which exercises vision.

## Thinking

Qwen3.8's extended reasoning mode, on by default in this deployment, controlled per request by a reasoning effort level. Thinking tokens consume context and wall time, so any speed number must state whether thinking was on.
