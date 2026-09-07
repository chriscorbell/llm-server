# 2026-09-07 Task suite baseline for Profile A

Status: concluded
Profile: A, BF16 KV at 98,304, MTP4, thinking on at xhigh
Author: agent thread on mbp

## Hypothesis

Profile A, at 4-bit weights, would behave well enough on real agentic coding work to serve as a daily driver, and the suite would show where it does not.

## Configuration

Server as in `STATUS.md`. Client is opencode 1.18.27 on mbp through the `llm-server` provider, temperature 1.0, top_p 0.95, top_k 20, reasoning effort xhigh. Each task runs in a fresh copy of its fixture, and the verdict comes from the task's verifier.

```bash
./eval/run.py --model llm-server/qwen38 --timeout 2700 \
  --out eval/results/2026-09-07-profile-a-baseline
```

## Measurements

| Task | Result | Seconds |
|---|---|---|
| 01 ts add feature | pass | 33.1 |
| 02 ts fix bug | pass | 32.6 |
| 03 ts refactor | pass | 113.0 |
| 04 py add feature | pass | 51.1 |
| 05 py fix bug | pass | 22.9 |
| 06 multifile trace | pass | 40.8 |
| 07 long context | pass | 61.5 |
| 08 vision css | see below | |

Seven of seven scorable tasks passed on the first attempt, including the refactor that is checked both for behaviour and for actually removing the duplication, and the long-context task that requires finding one non-conforming handler among 240.

Engine telemetry during the run, which is the first realistic-traffic measurement of this machine:

| Metric | Value |
|---|---|
| Draft acceptance on real coding traffic | 66 to 69% |
| Generation throughput, short context | 57.7 tok/s |
| Generation throughput at about 28K context | 18.0 tok/s |
| Prefix cache hit rate across the run | 85.2% |

## The vision task

It failed, and then failed again after I fixed my own harness bug, and the second failure was not the model's.

The first failure was mine. `opencode run -f <path> <prompt>` treats `--file` as a greedy array option, so the prompt was consumed as a second filename and the run died in 0.4 seconds with `File not found`. The `--file=<path>` form takes one value, and the message must come before it.

With that fixed, the model replied that it could not see an image. Debug logging showed why:

```
level=INFO run=fc725741 message=file mime=text/plain
```

opencode 1.18.27 attaches the PNG as `text/plain`. The model receives a text file, not an image. It then tried to read the pixels by shelling out to Python and PIL, which is a reasonable move for something told a file exists that it cannot see, and it is not vision.

So the vision requirement was scored against the API instead, using the same screenshot as a proper image part and the same headless layout verifier. The model named the defect correctly from the image alone:

> The fixed sidebar is removed from normal flow but `.content` has no left offset to compensate, so the main content starts at the left edge of the viewport and gets hidden behind the fixed sidebar.

It returned a corrected stylesheet, and the verifier passed. Vision works.

## Outcome

Confirmed. Eight of eight capabilities pass, seven through the real client and vision through the API.

## Consequences

`eval/vision_check.py` added. `eval/run.py` now skips any task carrying a screenshot and says why, rather than reporting a client defect as a model failure. Set `EVAL_CLIENT_SENDS_IMAGES=1` to re-enable that path once opencode sends the right mime type.

Two Findings promoted to `STATUS.md`: the opencode image limitation, and the realistic-traffic throughput figures that supersede the synthetic benchmark numbers from earlier today.
