# 2026-09-20 Pi context pressure and the fixed prompt prefix by package

Status: in progress, fixes applied, full-session re-measurement pending
Profile: client configuration on mbp against `a-int4draft`
Author: agent thread on mbp

## Hypothesis

Pi compacts every few turns because the usable window is consumed by three things that are not the server's context limit: retained reasoning from every prior turn, a large fixed system prompt from the nine installed packages, and compaction summaries that grow with each compaction. Measuring the prefix per package should show which packages are worth removing.

## Configuration

Session analysed: `~/.pi/agent/sessions/--Users-chris-Code-personal-blog--/2026-09-20T20-59-34-964Z_*.jsonl`, 13 user turns, 201 assistant turns, 20 compactions, xhigh thinking, window 131,072, `reserveTokens` 40,960, `keepRecentTokens` 20,000.

Prefix measurement: `eval/pi_prefix_by_package.py`. It builds a temporary agent directory under `PI_CODING_AGENT_DIR` that symlinks the installed `npm`, `extensions`, `models.json`, `auth.json` and `AGENTS.md`, rewrites `settings.json` with a different `packages` list per run, and sends one `pi -p --mode json --thinking off --no-session "Reply with only the word OK."` from an empty directory. The reported prompt size is `usage.input + usage.cacheRead` of the first assistant message, which is the server's own prompt token count. Runs are killed after 150 s; the first attempt hung for ten minutes because the server was busy with an interactive xhigh generation at `--max-num-seqs 1`.

## Measurements

Session analysis, characters accumulated across the whole session:

| Content | Characters | Share |
|---|---|---|
| Thinking blocks | 1,710,969 | 75% |
| Tool results | 495,651 | 22% |
| Assistant text | 75,994 | 3% |

Per compaction segment, the ratio of accumulated characters to the server-reported prompt growth was 2.2 to 7.7, consistent with 3 to 5 characters per token only if thinking is sent back. The checkpoint's chat template keeps `reasoning_content` for every prior assistant turn when `preserve_thinking` is unset (`preserve_thinking is undefined or preserve_thinking is true or loop.index0 > ns.last_query_index`), and the Pi extension does not set it.

Compaction summaries grew from 12,256 characters at the first compaction to 56,351 at the twentieth. Segment start sizes rose from 24,001 tokens to 57K, 68K and 76K, so the last segments had 15K to 30K tokens of room before the 90,112 threshold. The largest single assistant output in the session was under 4K tokens against a 32,768 `maxTokens` reserve.

Prompt prefix, tokens reported by the server for the first request from an empty directory, thinking on (the `off` level maps to the template default):

| Configuration | Prompt tokens |
|---|---|
| All nine packages (current) | 22,681 |
| All nine packages, `-nc` | 20,761 |
| No packages, extension loaded | 5,667 |
| No packages, `-ne` | 5,631 |

Per package, cost when it is the only package installed, and saving when only it is removed. The two columns agree within a few tokens, and the sum of the per-package costs (17,014) equals the gap between all and none.

| Package | Alone minus none | Removed from all |
|---|---|---|
| pi-background-tasks 2.5.0 | 4,975 | 4,975 |
| pi-agent-browser-native 0.6.15 | 3,488 | 3,488 |
| pi-lens 4.2.1 | 3,266 | 3,266 |
| pi-web-access 0.30.0 | 2,498 | 2,498 |
| pi-mcp-adapter 2.34.0 | 1,186 | 1,186 |
| rpiv-todo 2.10.1 | 917 | 917 |
| pi-goal-x 0.31.6 | 411 | 411 |
| rpiv-ask-user-question 2.10.1 | 273 | 273 |
| pi-btw 0.60.0 | 0 | 0 |

Raw event streams: scratchpad `runs/*.jsonl` for this thread only; not retained.

## What happened

The nine packages add 17,014 tokens to every request, three times the 5,667-token floor. The global `AGENTS.md` adds about 1,900. The blog session's first request was 24,001 tokens, which is the 22,681 measured here plus the project `AGENTS.md` and the goal seed. Thinking, not tool output, is the dominant growth term between compactions.

## Outcome

Confirmed. The server window is not the constraint; roughly a quarter of the usable window is fixed prefix, and three quarters of the growth is retained reasoning.

## Consequences

Applied on 2026-09-20 to both the installed configuration and the checked copies under `clients/pi/`:

- Removed pi-background-tasks, pi-lens, pi-mcp-adapter and pi-btw with `pi remove`. Re-measured with the same harness: the prefix fell from 22,681 to 13,254 tokens (9,427 saved, matching the per-package sum of 9,427). The floor without packages is unchanged at 5,667.
- Added `thinking-history.ts` to the llm-server extension. It returns the payload with `chat_template_kwargs.preserve_thinking: false` from `before_provider_request` for local-server models, and `cache-warmup.ts` applies the same kwargs to the warm-up payload. A probe extension loaded after llm-server confirmed the outgoing payload carries the kwargs, a 16,384 `max_tokens` and medium effort, and the server answered. An `-e` probe loads before directory extensions and sees the unmodified payload, so verify with a discovered extension.
- `compaction.reserveTokens` 40,960 to 24,576 and `maxTokens` 32,768 to 16,384, so the threshold moves from 90,112 to 106,496 and prompt plus `max_tokens` stays under the 131,072 window.
- `defaultThinkingLevel` xhigh to medium.
- `clients/pi/pi-lens.json` and `pi-btw.json` deleted; README and STATUS rewritten.

`eval/pi_prefix_by_package.py` is added so the measurement can be repeated after package changes.

Still open:

1. Re-measure a full session with the new settings: compactions per 100 assistant turns, segment start size, and the accumulated-characters-to-prompt-growth ratio. The session analysis in this entry is the baseline.
2. If summaries still grow toward 50K characters, investigate whether Pi's summary prompt re-embeds the previous summary and whether a length control exists.
