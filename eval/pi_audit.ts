// Opt-in request metadata for evals. Never record headers, prompts or reasoning text.
import { appendFileSync } from "node:fs";

export default function (pi: any) {
  const path = process.env.PI_EVAL_AUDIT;
  if (!path) throw new Error("PI_EVAL_AUDIT must name a local results file");
  let started = 0;
  let first = false;
  let request = 0;
  const record = (value: object) => appendFileSync(path, JSON.stringify(value) + "\n");
  pi.on("before_provider_request", (event: any) => {
    started = performance.now();
    first = false;
    request++;
    const p = event.payload;
    const assistants = (p.messages ?? []).filter((m: any) => m.role === "assistant");
    record({
      type: "request", request, model: p.model,
      reasoning_effort: p.reasoning_effort, max_tokens: p.max_tokens,
      temperature: p.temperature, top_p: p.top_p, top_k: p.top_k,
      assistant_tool_calls: assistants.filter((m: any) => m.tool_calls?.length).length,
      replayed_reasoning: assistants.filter((m: any) => m.reasoning || m.reasoning_content).length,
      image_parts: (p.messages ?? []).flatMap((m: any) => Array.isArray(m.content) ? m.content : [])
        .filter((p: any) => p.type === "image_url").length,
    });
  });
  pi.on("message_update", (event: any) => {
    if (!first && event.assistantMessageEvent?.type?.endsWith("_delta")) {
      first = true;
      record({ type: "first_delta", request, seconds: (performance.now() - started) / 1000 });
    }
  });
  pi.on("message_end", (event: any) => {
    if (event.message.role === "assistant") {
      record({ type: "response", request, usage: event.message.usage,
        stopReason: event.message.stopReason, seconds: (performance.now() - started) / 1000 });
    }
  });
}
