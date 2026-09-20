// Tighter tool-output cap than Pi's built-in 50 KB / 2000 lines for models with a
// small window. On a 96K window with compaction at 57K, one 50 KB read is about a
// fifth of the usable context. Larger windows keep Pi's defaults unless
// PI_TOOL_BUDGET_KB or PI_TOOL_BUDGET_LINES force a cap (shared.ts, toolBudget).
// read keeps the head (the model can page with offset/limit); bash keeps the tail.
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { formatSize, truncateHead, truncateTail } from "@earendil-works/pi-coding-agent";
import { toolBudget } from "./shared.ts";

export default function toolOutputBudget(pi: ExtensionAPI) {
	pi.on("tool_result", async (event, ctx) => {
		if (event.toolName !== "read" && event.toolName !== "bash") return;
		const budget = toolBudget(ctx.model);
		if (!budget) return;
		const index = event.content.findIndex((c) => c.type === "text");
		if (index < 0) return;
		const text = (event.content[index] as { text: string }).text;
		if (Buffer.byteLength(text, "utf8") <= budget.maxBytes && text.split("\n").length <= budget.maxLines) return;

		const truncation = event.toolName === "read" ? truncateHead(text, budget) : truncateTail(text, budget);
		if (!truncation.truncated) return;

		const kept = `${truncation.outputLines} of ${truncation.totalLines} lines (${formatSize(truncation.outputBytes)} of ${formatSize(truncation.totalBytes)})`;
		const advice =
			event.toolName === "read"
				? "Read further with offset and limit; the context window is small, so read only the ranges you need."
				: "Rerun with grep, tail or head to see the part you need; the context window is small.";
		const note = `\n\n[kept ${kept}. ${advice}]`;
		const content = event.content.slice();
		content[index] = { type: "text", text: truncation.content + note };
		return { content };
	});
}
