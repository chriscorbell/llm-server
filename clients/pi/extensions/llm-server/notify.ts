// Desktop notification when a run that took a while has settled. Task-suite turns
// against vllm run 16 to 138 s at xhigh, long enough to tab away.
import { execFile } from "node:child_process";
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

const MIN_SECONDS = 15;

function send(title: string, body: string): void {
	if (process.platform === "darwin") {
		// Notification Center works in every macOS terminal; OSC 777 does not reach Terminal.app.
		execFile("osascript", ["-e", `display notification ${JSON.stringify(body)} with title ${JSON.stringify(title)}`], () => {});
		return;
	}
	if (process.env.KITTY_WINDOW_ID) {
		process.stdout.write(`\x1b]99;i=1:d=0;${title}\x1b\\`);
		process.stdout.write(`\x1b]99;i=1:p=body;${body}\x1b\\`);
		return;
	}
	// Ghostty, WezTerm, iTerm2, rxvt-unicode.
	process.stdout.write(`\x1b]777;notify;${title};${body}\x07`);
}

export default function notify(pi: ExtensionAPI) {
	let started = 0;

	pi.on("agent_start", () => {
		if (!started) started = performance.now();
	});

	// agent_end can be followed by a retry or compaction; agent_settled means Pi is waiting for input.
	pi.on("agent_settled", async (_event, ctx) => {
		if (!started) return;
		const elapsed = (performance.now() - started) / 1000;
		started = 0;
		if (elapsed < MIN_SECONDS || !ctx.hasUI) return;
		const project = ctx.cwd.split("/").filter(Boolean).pop() ?? "pi";
		send("Pi", `Ready after ${Math.round(elapsed)} s in ${project}`);
	});
}
