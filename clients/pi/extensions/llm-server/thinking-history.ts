// Qwen3.8's chat template keeps reasoning_content for every earlier assistant
// turn when preserve_thinking is unset. In a 201-turn session that was 75% of all
// context growth (docs/log/2026-09-20-pi-context-pressure.md). Setting it false
// keeps reasoning only for steps after the latest user message, so the current
// tool loop still sees its own chain of thought while older turns lose theirs.
// The prompt only changes at user-turn boundaries, so the cached prefix survives.
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { isLocalServer, withTemplateKwargs } from "./shared.ts";

export default function thinkingHistory(pi: ExtensionAPI) {
	pi.on("before_provider_request", (event, ctx) => {
		if (!isLocalServer(ctx.model)) return;
		return withTemplateKwargs(event.payload as Record<string, unknown>);
	});
}
