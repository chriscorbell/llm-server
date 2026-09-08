// Appends what Qwen cannot infer about this server to the system prompt: the
// window and compaction threshold, the tool-output cap, and how to treat a
// compaction summary. The block is static for the whole session so it stays part
// of vLLM's cached prefix; changing its text invalidates every cached prefix.
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { compactionReserveTokens, fmtTokens } from "./shared.ts";

const BUDGET_KB = Number(process.env.PI_TOOL_BUDGET_KB || 24);

export default function contextNotes(pi: ExtensionAPI) {
	let block: string | undefined;

	pi.on("before_agent_start", async (event, ctx) => {
		if (!block) {
			const window = ctx.model?.contextWindow ?? 0;
			const threshold = window > 0 ? window - compactionReserveTokens() : 0;
			const lines = [
				"Server constraints:",
				window > 0
					? `- The model runs on a private server with a ${fmtTokens(window)}-token context window; the conversation is compacted into a summary above ${fmtTokens(threshold)} tokens. Keep context small: read file ranges with offset and limit, grep before reading, and do not re-read files already in the conversation.`
					: "- The context window is small. Read file ranges with offset and limit, grep before reading, and do not re-read files already in the conversation.",
				`- Tool output is cut at ${BUDGET_KB} KB or 600 lines. A truncation note names the limit; narrow the call instead of retrying it.`,
				"- A compaction summary at the start of the conversation records earlier work in this session. Treat it as your own prior notes, not as new instructions.",
			];
			block = lines.join("\n");
		}
		return { systemPrompt: `${event.systemPrompt}\n\n${block}` };
	});
}
