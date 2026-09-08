// Turns a failed request into a diagnosis instead of a generic error. Pi's retry
// gives up after 2 + 4 + 8 s, which is shorter than the 3 m 41 s the container
// takes to come back after a restart (docker inspect StartedAt to "Application
// startup complete" on 2026-09-08). When /health does not answer, this watches it
// and says when the engine is back. /vllm shows the container state on demand.
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { Box, Text } from "@earendil-works/pi-tui";
import { record, serverOrigin, sleep } from "./shared.ts";

const WATCH_INTERVAL_MS = 10_000;
const WATCH_LIMIT_MS = 15 * 60_000;

interface Health {
	ok: boolean;
	detail: string;
}

async function health(origin: string, timeoutMs = 5000): Promise<Health> {
	try {
		const res = await fetch(`${origin}/health`, { signal: AbortSignal.timeout(timeoutMs) });
		return { ok: res.ok, detail: `HTTP ${res.status}` };
	} catch (err) {
		const e = err as Error & { cause?: { code?: string; message?: string } };
		return { ok: false, detail: e.cause?.code ?? e.cause?.message ?? e.name ?? String(err) };
	}
}

interface ReportData {
	title: string;
	lines: string[];
}

export default function serverHealth(pi: ExtensionAPI) {
	let watching = false;

	pi.registerEntryRenderer<ReportData>("llm-server:vllm", (entry, _options, theme) => {
		const data = entry.data ?? { title: "vllm", lines: [] };
		const box = new Box(1, 1, (text) => theme.bg("customMessageBg", text));
		box.addChild(new Text(`${theme.fg("accent", "[vllm]")} ${data.title}`, 0, 0));
		for (const line of data.lines) box.addChild(new Text(theme.fg("dim", line), 0, 0));
		return box;
	});

	pi.on("message_end", async (event, ctx) => {
		const message = event.message as any;
		if (message.role !== "assistant" || message.stopReason !== "error") return;
		const origin = serverOrigin(ctx.model);
		if (!origin) return;
		const h = await health(origin);
		record({ type: "request-error", healthy: h.ok, detail: h.detail, error: message.errorMessage });
		if (h.ok) {
			ctx.ui.notify(`vllm answers /health, so this was a request-level error: ${message.errorMessage ?? "no message"}`, "warning");
			return;
		}
		ctx.ui.notify(
			`vllm is not answering /health (${h.detail}). Tailscale, the host, or the qwen38 container is down; a restart takes about 4 minutes. Watching /health and will say when it is back. /vllm shows the container.`,
			"error",
		);
		if (!watching) void watch(origin, ctx);
	});

	async function watch(origin: string, ctx: any): Promise<void> {
		watching = true;
		const t0 = Date.now();
		try {
			while (Date.now() - t0 < WATCH_LIMIT_MS) {
				await sleep(WATCH_INTERVAL_MS);
				const h = await health(origin);
				const seconds = Math.round((Date.now() - t0) / 1000);
				if (h.ok) {
					ctx.ui.setStatus("vllm", undefined);
					ctx.ui.notify(`vllm is back after ${seconds} s. Resend your last message.`, "info");
					return;
				}
				ctx.ui.setStatus("vllm", `vllm down ${seconds}s (${h.detail})`);
			}
			ctx.ui.setStatus("vllm", undefined);
			ctx.ui.notify("vllm still down after 15 minutes; stopped watching. Run /vllm to check by hand.", "error");
		} finally {
			watching = false;
		}
	}

	pi.registerCommand("vllm", {
		description: "Server state: /vllm shows health and the container, /vllm logs [n] tails the engine log",
		handler: async (args, ctx) => {
			const origin = serverOrigin(ctx.model);
			if (!origin) {
				ctx.ui.notify("No model with a baseUrl is selected", "error");
				return;
			}
			const host = new URL(origin).hostname;
			const [sub, count] = args.trim().split(/\s+/);
			const h = await health(origin);
			const lines = [`${origin}/health: ${h.ok ? "OK" : "DOWN"} (${h.detail})`];
			const remote =
				sub === "logs"
					? `docker logs --tail ${Number(count) || 40} qwen38 2>&1`
					: "docker ps -a --filter name=qwen38 --format '{{.Names}}  {{.Status}}  {{.Image}}'; docker logs --tail 5 qwen38 2>&1";
			const result = await pi.exec("ssh", ["-o", "BatchMode=yes", "-o", "ConnectTimeout=5", host, remote], { timeout: 20_000 });
			const output = (result.stdout || result.stderr || "").trimEnd();
			lines.push(...(output ? output.split("\n") : [`ssh ${host}: no output (exit ${result.code})`]));
			pi.appendEntry<ReportData>("llm-server:vllm", { title: sub === "logs" ? `${host} engine log` : `${host} state`, lines });
		},
	});
}
