// Per-request numbers in the footer: time to first token, prefix-cache hit share,
// and distance to the compaction threshold. Warns when a large prompt missed the cache.
//
// Cache figures need vLLM started with --enable-prompt-tokens-details; without it
// usage.cacheRead is always 0 and the status shows the prompt size only.
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { compactionReserveTokens, fmtTokens, record } from "./shared.ts";

export default function requestStats(pi: ExtensionAPI) {
	const reserve = compactionReserveTokens();
	let started = 0;
	let firstDelta: number | undefined;
	let request = 0;
	let sawCacheRead = false;

	pi.on("before_provider_request", () => {
		started = performance.now();
		firstDelta = undefined;
		request++;
	});

	pi.on("message_update", (event) => {
		if (firstDelta !== undefined || !started) return;
		if (event.assistantMessageEvent?.type?.endsWith("_delta")) {
			firstDelta = (performance.now() - started) / 1000;
		}
	});

	pi.on("message_end", async (event, ctx) => {
		if (event.message.role !== "assistant" || !started) return;
		const message = event.message as any;
		const usage = message.usage ?? {};
		const cached: number = usage.cacheRead ?? 0;
		const prompt: number = (usage.input ?? 0) + cached + (usage.cacheWrite ?? 0);
		const total = (performance.now() - started) / 1000;
		const ttft = firstDelta;
		started = 0;
		if (cached > 0) sawCacheRead = true;

		record({ type: "response", request, prompt, cached, ttft, total, stopReason: message.stopReason });

		const parts: string[] = [];
		if (ttft !== undefined) parts.push(`ttft ${ttft.toFixed(1)}s`);
		if (prompt > 0) {
			parts.push(sawCacheRead ? `cache ${Math.round((100 * cached) / prompt)}% of ${fmtTokens(prompt)}` : `prompt ${fmtTokens(prompt)}`);
		}
		const usageNow = ctx.getContextUsage();
		if (usageNow && usageNow.tokens !== null) {
			const left = usageNow.contextWindow - reserve - usageNow.tokens;
			parts.push(left > 0 ? `${fmtTokens(left)} to compaction` : "compaction due");
		}
		ctx.ui.setStatus("llm-server", parts.join(" · "));

		if (sawCacheRead && prompt >= 8000 && cached < prompt / 2 && message.stopReason !== "error") {
			const when = ttft !== undefined ? ` (${ttft.toFixed(1)} s to first token)` : "";
			ctx.ui.notify(`Prefix cache miss: ${fmtTokens(prompt - cached)} of ${fmtTokens(prompt)} prompt tokens prefilled cold${when}.`, "warning");
		}
	});
}
