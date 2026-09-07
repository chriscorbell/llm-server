# 2026-09-07 Task suite built and self-tested

Status: concluded
Profile: none
Author: agent thread on mbp

## Hypothesis

A suite of pass/fail coding tasks can score a Profile's real behaviour without a human judging prose, and without any network access or package installs.

## Configuration

Eight tasks under `eval/tasks/`, run by `eval/run.py` through `opencode run --dir`. Node 24 with native TypeScript stripping and Python 3 unittest, plus Chrome for the vision task. No dependencies to install.

## What happened

Two defects in the suite itself, both found by self-testing rather than by running a model.

The vision verifier passed on the unfixed fixture. It rendered the page headless and grepped the dumped DOM for `LAYOUT_PASS`, but the dump includes the injected check script, whose source contains both the pass and fail literals. Every run matched. Fixed by matching the rendered `<title>` element instead.

Task 02 was unsolvable. Its fixture used a TypeScript parameter property in a constructor, and Node's strip-only mode rejects that syntax outright, so the suite failed to load regardless of the planted bug. Rewritten with plain field assignments.

Task 07 leaked its own answer: the generator wrote the name of the non-conforming handler to `BROKEN_HANDLER` in the workspace the agent can read. Removed.

## Measurements

Each task was run twice, once on the untouched fixture and once with a known-correct fix applied by script.

| Task | Unfixed | Correctly fixed |
|---|---|---|
| 01 ts add feature | fail | pass |
| 02 ts fix bug | fail | pass |
| 03 ts refactor | fail | pass |
| 04 py add feature | fail | pass |
| 05 py fix bug | fail | pass |
| 06 multifile trace | fail | pass |
| 07 long context | fail | pass |
| 08 vision css | fail | pass |

## Outcome

Confirmed. All eight tasks discriminate in both directions, which is the only property that makes a score meaningful.

## Consequences

The suite is committed and ready to run against Profile A once the server is up. Three verifiers deliberately resist a fix by deletion: task 03 counts occurrences of the rule it asked you to deduplicate, task 07 counts the surviving handlers, task 08 fails if the sidebar is simply removed.
