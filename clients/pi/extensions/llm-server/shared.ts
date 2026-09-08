// Helpers shared by the llm-server Pi extension modules.
import { appendFileSync, readFileSync } from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";

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
