// Prefill the current context while the user is idle so the next real request
// hits vLLM's prefix cache. After compaction the first request measured 12.3 s at
// 22.6K tokens cold against 0.9 s warm (docs/log/2026-09-07-pi-client-validation.md).
//
// The warm-up sends the same system prompt, messages and tools through the same
// pi-ai serializer the agent uses, with max_tokens 1. Sampling and max_tokens do
// not affect the prompt; reasoning_effort does, so it is passed explicitly. The
// next real request is compared against the warm-up payload and a mismatch is
// reported, so a silent cache miss cannot hide.
//
// Triggers: compaction when idle (or once the run settles), /warm, and the
// "llm-server:warm" bus event from thinking-guard.ts.
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { convertToLlm } from "@earendil-works/pi-coding-agent";
import { fmtTokens, record } from "./shared.ts";

interface WarmRequest {
	reason: string;
	thinkingLevel?: string;
}

export default function cacheWarmup(pi: ExtensionAPI) {
	let pending: WarmRequest | undefined;
	let running: AbortController | undefined;
	let lastWarmPayload: any;
	let lastCtx: any;

	pi.on("session_start", async (_event, ctx) => {
		lastCtx = ctx;
		lastWarmPayload = undefined;
	});
	pi.on("session_before_switch", async () => running?.abort());
	pi.on("session_shutdown", async () => running?.abort());

	pi.on("session_compact", async (event, ctx) => {
		lastCtx = ctx;
		// Overflow recovery re-sends the aborted turn immediately; nothing to gain.
		if (event.willRetry) return;
		const request = { reason: `${event.reason} compaction` };
		// ctx.isIdle() is false inside this event: Pi still holds the compaction controller
		// until the handler returns. Check again shortly after; a mid-run compaction stays
		// pending until agent_settled.
		pending = request;
		setTimeout(() => {
			if (pending !== request || !ctx.isIdle()) return;
			pending = undefined;
			void warm(ctx, request);
		}, 500);
	});

	pi.on("agent_settled", async (_event, ctx) => {
		lastCtx = ctx;
		if (!pending) return;
		const request = pending;
		pending = undefined;
		void warm(ctx, request);
	});

	pi.events.on("llm-server:warm", (data: WarmRequest) => {
		if (lastCtx) void warm(lastCtx, data);
	});

	pi.registerCommand("warm", {
		description: "Prefill the current context on vllm so the next request hits the prefix cache",
		handler: async (_args, ctx) => {
			lastCtx = ctx;
			await warm(ctx, { reason: "manual" });
		},
	});

	pi.on("before_provider_request", async (event, ctx) => {
		lastCtx = ctx;
		verify(event.payload, ctx);
	});

	async function warm(ctx: any, request: WarmRequest): Promise<void> {
		if (running) return;
		const model = ctx.model;
		if (!model) return;
		const messages = convertToLlm(ctx.sessionManager.buildSessionContext().messages);
		if (messages.length === 0) return;

		const definitions = new Map(pi.getAllTools().map((t) => [t.name, t]));
		const tools = pi
			.getActiveTools()
			.map((name) => definitions.get(name))
			.filter((t) => t !== undefined)
			.map((t) => ({ name: t.name, description: t.description, parameters: t.parameters }));
		const level = request.thinkingLevel ?? ctx.thinkingLevel ?? pi.getThinkingLevel();

		running = new AbortController();
		const t0 = performance.now();
		ctx.ui.setStatus("warm", `warming prefix cache (${request.reason})`);
		try {
			const response = await ctx.modelRegistry.complete(
				model,
				{ systemPrompt: ctx.getSystemPrompt(), messages, tools },
				{
					maxTokens: 1,
					reasoningEffort: level === "off" ? undefined : level,
					signal: running.signal,
					onPayload: (payload: any) => {
						lastWarmPayload = payload;
						return payload;
					},
				},
			);
			const seconds = (performance.now() - t0) / 1000;
			const usage = response.usage ?? {};
			const prompt = (usage.input ?? 0) + (usage.cacheRead ?? 0) + (usage.cacheWrite ?? 0);
			record({ type: "warmup", reason: request.reason, seconds, prompt, cached: usage.cacheRead ?? 0, stopReason: response.stopReason });
			if (response.stopReason === "error") {
				ctx.ui.notify(`Warm-up failed: ${response.errorMessage ?? "unknown error"}`, "warning");
			} else {
				ctx.ui.notify(`Prefix cache warm: ${fmtTokens(prompt)} tokens in ${seconds.toFixed(1)} s (${request.reason}).`, "info");
			}
		} catch (err) {
			if (!running.signal.aborted) {
				record({ type: "warmup-error", reason: request.reason, error: String(err) });
				ctx.ui.notify(`Warm-up failed: ${err instanceof Error ? err.message : String(err)}`, "warning");
			}
		} finally {
			running = undefined;
			ctx.ui.setStatus("warm", undefined);
		}
	}

	/** Compare the next real request with the warm-up payload. The real request appends the new user turn, so only the warm-up's prefix must match. */
	function verify(payload: any, ctx: any): void {
		if (!lastWarmPayload) return;
		const warmPayload = lastWarmPayload;
		lastWarmPayload = undefined;
		const warmMessages: any[] = warmPayload.messages ?? [];
		const realMessages: any[] = payload.messages ?? [];
		let mismatch: string | undefined;
		if (JSON.stringify(warmPayload.tools ?? null) !== JSON.stringify(payload.tools ?? null)) mismatch = "tools";
		else if (warmPayload.reasoning_effort !== payload.reasoning_effort) mismatch = `reasoning_effort ${warmPayload.reasoning_effort} vs ${payload.reasoning_effort}`;
		else {
			for (let i = 0; i < warmMessages.length; i++) {
				if (JSON.stringify(warmMessages[i]) !== JSON.stringify(realMessages[i])) {
					mismatch = `messages[${i}] of ${warmMessages.length} (real request has ${realMessages.length})`;
					break;
				}
			}
		}
		record({ type: "warmup-verify", mismatch: mismatch ?? null, warmMessages: warmMessages.length, requestMessages: realMessages.length });
		if (mismatch) {
			ctx.ui.notify(`Warm-up prefix differs from the real request at ${mismatch}; the prefix cache will miss. Record this in the log.`, "warning");
		}
	}
}
