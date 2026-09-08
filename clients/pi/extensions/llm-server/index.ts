// Pi quality-of-life extension for the llm-server setup (Qwen on vllm over Tailscale).
// Install by symlinking this directory into ~/.pi/agent/extensions/ and running npm install
// here for web.ts's dependencies; see clients/pi/README.md.
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import cacheWarmup from "./cache-warmup.ts";
import handoff from "./handoff.ts";
import notify from "./notify.ts";
import requestStats from "./request-stats.ts";
import serverHealth from "./server-health.ts";
import thinkingGuard from "./thinking-guard.ts";
import toolOutputBudget from "./tool-output-budget.ts";
import web from "./web.ts";

export default function (pi: ExtensionAPI) {
	requestStats(pi);
	cacheWarmup(pi);
	thinkingGuard(pi);
	serverHealth(pi);
	notify(pi);
	handoff(pi);
	toolOutputBudget(pi);
	web(pi);
}
