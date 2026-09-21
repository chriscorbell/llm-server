// Helpers shared by the Pi extension modules. The extension loads for every
// provider Pi knows about; the helpers below decide per selected model which
// behaviour applies.
import { appendFileSync, readFileSync } from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";

type ModelLike = { provider?: string; id?: string; baseUrl?: string; contextWindow?: number } | undefined;

/**
 * Provider id of the private server in models.json. Modules that depend on vLLM's
 * prefix cache, its /health endpoint or the container (cache-warmup, thinking-guard,
 * server-health) act only while a model from this provider is selected.
 */
export const LOCAL_PROVIDER = process.env.PI_LOCAL_PROVIDER ?? "llm-server";

export function isLocalServer(model: ModelLike): boolean {
	return model?.provider === LOCAL_PROVIDER;
}

/** "openai-codex/gpt-5.5" for messages that explain why a module stayed quiet. */
export function describeModel(model: ModelLike): string {
	return model ? `${model.provider ?? "?"}/${model.id ?? "?"}` : "no model";
}

/** The first model of the private server in Pi's registry, whichever model is selected. */
export function localModel(ctx: { modelRegistry?: { getAll(): Array<{ provider: string }> } }): { provider: string; baseUrl?: string } | undefined {
	return ctx.modelRegistry?.getAll().find((m) => m.provider === LOCAL_PROVIDER);
}

/**
 * Windows below this are "small": the tighter tool-output cap and the context
 * advice in the system prompt apply. 98,304 qualifies; the current 131,072-token Qwen window does not.
 */
export const SMALL_WINDOW_TOKENS = Number(process.env.PI_SMALL_WINDOW_TOKENS || 131072);

export interface ToolBudget {
	maxBytes: number;
	maxLines: number;
}

/**
 * Tool-output cap for the selected model. PI_TOOL_BUDGET_KB or PI_TOOL_BUDGET_LINES
 * force a cap for every model; otherwise a small window gets 24 KB / 600 lines and
 * larger windows keep Pi's own 50 KB / 2000 lines (undefined here).
 */
export function toolBudget(model: ModelLike): ToolBudget | undefined {
	const forced = process.env.PI_TOOL_BUDGET_KB || process.env.PI_TOOL_BUDGET_LINES;
	const window = model?.contextWindow ?? 0;
	if (!forced && !(window > 0 && window < SMALL_WINDOW_TOKENS)) return undefined;
	return {
		maxBytes: Number(process.env.PI_TOOL_BUDGET_KB || 24) * 1024,
		maxLines: Number(process.env.PI_TOOL_BUDGET_LINES || 600),
	};
}

/**
 * Cold prefill rate on the Arc Pro B70 with Profile A. 33.4K prompt tokens took
 * 19.2 s cold, 64K ran at 1,402 tok/s. See docs/log/2026-09-07-ttft-actual-token-counts.md
 * and docs/log/2026-09-07-prefill-chunk-size.md. Used only for user-facing estimates.
 */
export const COLD_PREFILL_TOK_S = 1700;

export function estimateColdSeconds(tokens: number): number {
	return tokens / COLD_PREFILL_TOK_S;
}

export function fmtTokens(n: number): string {
	return n < 1000 ? `${Math.round(n)}` : `${(n / 1000).toFixed(1)}k`;
}

/** Append a JSON line to $PI_LLM_SERVER_LOG when set. Used by eval/pi_warmup.py. Never records prompt text. */
export function record(value: Record<string, unknown>): void {
	const path = process.env.PI_LLM_SERVER_LOG;
	if (!path) return;
	try {
		appendFileSync(path, `${JSON.stringify({ time: Date.now(), ...value })}\n`);
	} catch {
		// Logging is best effort.
	}
}

/**
 * chat_template_kwargs sent with every request to the local server. The warm-up
 * in cache-warmup.ts applies the same values so its rendered prompt matches.
 */
export const TEMPLATE_KWARGS: Record<string, unknown> = { preserve_thinking: false };

export function withTemplateKwargs<T extends Record<string, unknown>>(payload: T): T {
	const existing = (payload.chat_template_kwargs as Record<string, unknown> | undefined) ?? {};
	return { ...payload, chat_template_kwargs: { ...existing, ...TEMPLATE_KWARGS } };
}

/** Pi does not expose settings to extensions, so read the same global file it reads. */
export function compactionReserveTokens(): number {
	const dir = process.env.PI_CODING_AGENT_DIR ?? join(homedir(), ".pi", "agent");
	try {
		const settings = JSON.parse(readFileSync(join(dir, "settings.json"), "utf8"));
		const reserve = settings?.compaction?.reserveTokens;
		if (typeof reserve === "number" && reserve > 0) return reserve;
	} catch {
		// Fall through to Pi's default.
	}
	return 16384;
}

/** "http://vllm:8000" from the model's baseUrl, or undefined when no model is selected. */
export function serverOrigin(model: { baseUrl?: string } | undefined): string | undefined {
	if (!model?.baseUrl) return undefined;
	try {
		return new URL(model.baseUrl).origin;
	} catch {
		return undefined;
	}
}

export function sleep(ms: number, signal?: AbortSignal): Promise<void> {
	return new Promise((resolve) => {
		const timer = setTimeout(resolve, ms);
		signal?.addEventListener("abort", () => {
			clearTimeout(timer);
			resolve();
		});
	});
}
