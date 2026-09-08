// A thinking-level change rewrites Qwen's chat template, so the cached prefix no
// longer matches and the next request prefills cold (12.6 s at 23K tokens in
// docs/log/2026-09-07-pi-client-validation.md). Pi's thinking_level_select event
// is notification-only, so this cannot block the change. It explains the cost and
// asks cache-warmup.ts to prefill with the new level while the user is still typing.
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { estimateColdSeconds, fmtTokens } from "./shared.ts";

export default function thinkingGuard(pi: ExtensionAPI) {
	pi.on("thinking_level_select", async (event, ctx) => {
		if (!event.previousLevel || event.level === event.previousLevel) return;
		const usage = ctx.getContextUsage();
		const tokens = usage?.tokens ?? 0;
		if (tokens < 1000) return;
		const estimate = Math.max(1, Math.round(estimateColdSeconds(tokens)));
		if (ctx.isIdle()) {
			ctx.ui.notify(
				`Thinking ${event.previousLevel} -> ${event.level} changes Qwen's prompt template, so the ${fmtTokens(tokens)}-token cached prefix is stale. Warming it with the new level now, about ${estimate} s; the footer clears when done.`,
				"warning",
			);
			pi.events.emit("llm-server:warm", { reason: `thinking ${event.level}`, thinkingLevel: event.level });
		} else {
			ctx.ui.notify(
				`Thinking ${event.previousLevel} -> ${event.level} changes Qwen's prompt template. The next request prefills ${fmtTokens(tokens)} tokens cold, about ${estimate} s.`,
				"warning",
			);
		}
	});
}
