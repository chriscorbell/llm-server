# 2026-09-07 What actually drives decode speed here

Status: concluded, supersedes the speed conclusions in [the earlier entry](./2026-09-07-decode-speed-and-mtp-acceptance.md)
Profile: A
Author: agent thread on mbp

## Hypothesis

Earlier today I guessed that decode measured near 50 tok/s, against a published 84, because my benchmark filled prompts with a repeated pangram, and that realistic prompt text would close the gap. That guess was wrong, and this entry replaces it.

## Configuration

Same server, unchanged. Two experiments. First, the same benchmark run against three prompt corpora at 512 prompt tokens and 128 generated, five repetitions. Second, three requests that differ only in how predictable the generated text is, three repetitions, 200 tokens each.

## Measurements

Changing the prompt text changes almost nothing:

| Prompt corpus | Decode tok/s | Acceptance |
|---|---|---|
| This repository's code | 44.3 | 40.1% |
| This repository's Markdown | 45.6 | 44.8% |
| Repeated pangram | 46.6 | 40.6% |

Changing what the model is asked to generate changes everything:

| Generation task | Decode tok/s | Acceptance |
|---|---|---|
| Summarise something in a paragraph | 44.8 | 39.9% |
| Write a new Python function | 56.3 | 56.5% |
| Reproduce a given source file verbatim | 85.2 | 100.0% |

## Outcome

The speculative head's acceptance rate tracks the predictability of the output, not the input. Prompt content is nearly irrelevant.

That also explains the published 83.7 tok/s. At 85.2 tok/s and 100% acceptance, verbatim reproduction reproduces the headline figure almost exactly, which means the published number describes a maximally predictable generation. This machine is not underperforming. It was being asked a different question.

The number that matters for the actual workload sits in the middle. Writing new code gives 56.3 tok/s, and the task suite running real agentic work measured 57.7 tok/s with 66 to 69% acceptance. Those agree, and they are the honest figure to plan around.

## Consequences

Findings in `STATUS.md` corrected: the machine does about 56 tok/s on code generation, not "50 and unexplained". The open question about prompt realism is closed. The corpus switch added to `scripts/bench.py` stays, because it costs nothing and rules the variable out permanently, but the default benchmark prompt should be understood as measuring free-prose generation, which is the pessimistic end of the range.

Remaining speed question, unchanged: decode fell to 18.0 tok/s at about 28K context during the task suite. That curve is worth mapping.
