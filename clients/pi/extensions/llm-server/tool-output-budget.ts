// Tighter tool-output cap than Pi's built-in 50 KB / 2000 lines. On a 96K window
// with compaction at 57K, one 50 KB read is about a fifth of the usable context.
// read keeps the head (the model can page with offset/limit); bash keeps the tail.
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { formatSize, truncateHead, truncateTail } from "@earendil-works/pi-coding-agent";

const MAX_BYTES = Number(process.env.PI_TOOL_BUDGET_KB || 24) * 1024;
const MAX_LINES = Number(process.env.PI_TOOL_BUDGET_LINES || 600);

export default function toolOutputBudget(pi: ExtensionAPI) {
	pi.on("tool_result", async (event) => {
		if (event.toolName !== "read" && event.toolName !== "bash") return;
		const index = event.content.findIndex((c) => c.type === "text");
		if (index < 0) return;
		const text = (event.content[index] as { text: string }).text;
		if (Buffer.byteLength(text, "utf8") <= MAX_BYTES && text.split("\n").length <= MAX_LINES) return;

		const options = { maxBytes: MAX_BYTES, maxLines: MAX_LINES };
		const truncation = event.toolName === "read" ? truncateHead(text, options) : truncateTail(text, options);
		if (!truncation.truncated) return;

		const kept = `${truncation.outputLines} of ${truncation.totalLines} lines (${formatSize(truncation.outputBytes)} of ${formatSize(truncation.totalBytes)})`;
		const advice =
			event.toolName === "read"
				? `Read further with offset and limit; the context window on this server is small, so read only the ranges you need.`
				: `Rerun with grep, tail or head to see the part you need; the context window on this server is small.`;
		const note = `\n\n[llm-server: kept ${kept}. ${advice}]`;
		const content = event.content.slice();
		content[index] = { type: "text", text: truncation.content + note };
		return { content };
	});
}
