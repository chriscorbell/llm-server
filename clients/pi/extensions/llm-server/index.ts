// Pi quality-of-life extension. It loads for every provider: the request footer,
// notifications, handoff and the window-scaled output caps apply to any
// model; cache warm-up, the thinking guard and server diagnosis act only while a
// model from the private server (shared.ts, LOCAL_PROVIDER) is selected.
// Install by symlinking this directory into ~/.pi/agent/extensions/;
// see clients/pi/README.md. Web tools come from the pi-web-access package.
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import cacheWarmup from "./cache-warmup.ts";
import contextNotes from "./context-notes.ts";
import handoff from "./handoff.ts";
import notify from "./notify.ts";
import requestStats from "./request-stats.ts";
import serverHealth from "./server-health.ts";
import thinkingGuard from "./thinking-guard.ts";
import thinkingHistory from "./thinking-history.ts";
import toolOutputBudget from "./tool-output-budget.ts";

export default function (pi: ExtensionAPI) {
	requestStats(pi);
	cacheWarmup(pi);
	thinkingGuard(pi);
	thinkingHistory(pi);
	serverHealth(pi);
	notify(pi);
	handoff(pi);
	toolOutputBudget(pi);
	contextNotes(pi);
}
