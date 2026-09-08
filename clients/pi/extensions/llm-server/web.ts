// web_search and web_fetch without API keys. Search goes to the SearXNG instance
// that runs next to the engine on vllm (compose/docker-compose.yml, service
// searxng); fetch pulls a page and reduces it to markdown with Readability.
// Both outputs are cut to the same budget as tool-output-budget.ts because the
// context window on this server is small.
import { Readability } from "@mozilla/readability";
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { formatSize, truncateHead } from "@earendil-works/pi-coding-agent";
import { parseHTML } from "linkedom";
import TurndownService from "turndown";
import { Type } from "typebox";
import { record } from "./shared.ts";

const SEARXNG_URL = (process.env.SEARXNG_URL || "http://vllm:8080").replace(/\/$/, "");
const MAX_BYTES = Number(process.env.PI_TOOL_BUDGET_KB || 24) * 1024;
const MAX_LINES = Number(process.env.PI_TOOL_BUDGET_LINES || 600);
const FETCH_TIMEOUT_MS = 20_000;
const MAX_BODY_BYTES = 3 * 1024 * 1024;
const USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36";

interface SearxResult {
	title?: string;
	url?: string;
	content?: string;
	engine?: string;
	engines?: string[];
	publishedDate?: string | null;
}

interface SearxResponse {
	results?: SearxResult[];
	answers?: Array<string | { answer?: string; url?: string }>;
	infoboxes?: Array<{ infobox?: string; content?: string; id?: string }>;
	suggestions?: string[];
}

function clip(text: string, max: number): string {
	const oneLine = text.replace(/\s+/g, " ").trim();
	return oneLine.length > max ? `${oneLine.slice(0, max - 1)}…` : oneLine;
}

function budget(text: string, advice: string): { text: string; truncated: boolean } {
	const truncation = truncateHead(text, { maxBytes: MAX_BYTES, maxLines: MAX_LINES });
	if (!truncation.truncated) return { text, truncated: false };
	const kept = `${truncation.outputLines} of ${truncation.totalLines} lines (${formatSize(truncation.outputBytes)} of ${formatSize(truncation.totalBytes)})`;
	return { text: `${truncation.content}\n\n[llm-server: kept ${kept}. ${advice}]`, truncated: true };
}

/** GitHub file pages render badly through Readability; the raw file is what the model wants. */
function rewriteUrl(raw: string): string {
	const m = raw.match(/^https?:\/\/github\.com\/([^/]+)\/([^/]+)\/blob\/(.+)$/);
	return m ? `https://raw.githubusercontent.com/${m[1]}/${m[2]}/${m[3]}` : raw;
}

async function readBody(res: Response): Promise<string> {
	const reader = res.body?.getReader();
	if (!reader) return "";
	const chunks: Uint8Array[] = [];
	let total = 0;
	while (total < MAX_BODY_BYTES) {
		const { done, value } = await reader.read();
		if (done) break;
		chunks.push(value);
		total += value.byteLength;
	}
	await reader.cancel().catch(() => {});
	return Buffer.concat(chunks).toString("utf8");
}

function htmlToMarkdown(html: string, url: string): { title: string; markdown: string; readable: boolean } {
	const { document } = parseHTML(html);
	const title = document.querySelector("title")?.textContent?.trim() ?? "";
	let readable = false;
	let root: string;
	try {
		const article = new Readability(document as any, { charThreshold: 200 }).parse();
		if (article?.content && article.textContent && article.textContent.trim().length > 200) {
			readable = true;
			root = article.content;
		} else {
			root = document.body?.innerHTML ?? html;
		}
	} catch {
		root = document.body?.innerHTML ?? html;
	}
	// Turndown parses the string with its own DOM; linkedom cannot re-parse a bare fragment.
	const turndown = new TurndownService({ headingStyle: "atx", codeBlockStyle: "fenced", bulletListMarker: "-" });
	turndown.remove(["script", "style", "noscript", "svg", "iframe", "nav", "footer", "form"] as any);
	turndown.addRule("absoluteLinks", {
		filter: "a",
		replacement: (content, node) => {
			const href = (node as HTMLAnchorElement).getAttribute("href");
			const label = content.trim();
			// Heading permalinks (mkdocs, Sphinx) add a "¶" link per heading; drop them.
			if (!href || !label || label === "¶" || label === "#") return label === "¶" || label === "#" ? "" : content;
			try {
				return `[${content}](${new URL(href, url).href})`;
			} catch {
				return content;
			}
		},
	});
	const markdown = turndown
		.turndown(root)
		.replace(/\n{3,}/g, "\n\n")
		.trim();
	return { title, markdown, readable };
}

export default function web(pi: ExtensionAPI) {
	pi.registerTool({
		name: "web_search",
		label: "Web search",
		description: `Search the web through the private SearXNG instance on ${SEARXNG_URL} (no API key, no quota). Returns ranked results with title, URL and snippet. Follow up with web_fetch on a result URL to read the page.`,
		promptSnippet: "Search the web (SearXNG, no key needed); returns titles, URLs and snippets",
		promptGuidelines: [
			"Use web_search for anything that depends on a version, a date, an API surface or an exact error message instead of answering from memory; then read the page with web_fetch before citing it",
		],
		parameters: Type.Object({
			query: Type.String({ description: "Search query. Use specific terms, version numbers and error text; quote exact phrases." }),
			max_results: Type.Optional(Type.Integer({ minimum: 1, maximum: 20, description: "Results to return, default 8" })),
			time_range: Type.Optional(
				Type.Union([Type.Literal("day"), Type.Literal("week"), Type.Literal("month"), Type.Literal("year")], {
					description: "Only results from this period",
				}),
			),
		}),
		async execute(_toolCallId, params, signal) {
			const max = params.max_results ?? 8;
			const url = new URL(`${SEARXNG_URL}/search`);
			url.searchParams.set("q", params.query);
			url.searchParams.set("format", "json");
			url.searchParams.set("language", "en");
			if (params.time_range) url.searchParams.set("time_range", params.time_range);
			const t0 = performance.now();
			let data: SearxResponse;
			try {
				const res = await fetch(url, {
					headers: { "user-agent": USER_AGENT, accept: "application/json" },
					signal: AbortSignal.any([signal, AbortSignal.timeout(FETCH_TIMEOUT_MS)]),
				});
				if (!res.ok) throw new Error(`SearXNG answered HTTP ${res.status}. Check that the searxng container is up on vllm: /vllm.`);
				data = (await res.json()) as SearxResponse;
			} catch (err) {
				const message = err instanceof Error ? (err as any).cause?.code ?? err.message : String(err);
				throw new Error(`web_search failed: ${message}. SearXNG runs on ${SEARXNG_URL}; is Tailscale up and the searxng container running?`);
			}
			const seconds = (performance.now() - t0) / 1000;
			const results = (data.results ?? []).slice(0, max);
			record({ type: "web_search", results: results.length, total: data.results?.length ?? 0, seconds });

			const lines: string[] = [];
			for (const answer of data.answers ?? []) {
				const text = typeof answer === "string" ? answer : answer.answer;
				if (text) lines.push(`Answer: ${clip(text, 400)}`);
			}
			for (const box of (data.infoboxes ?? []).slice(0, 1)) {
				if (box.content) lines.push(`${box.infobox ?? "Infobox"}: ${clip(box.content, 400)}`);
			}
			if (lines.length) lines.push("");
			if (results.length === 0) {
				lines.push(`No results for "${params.query}".`);
				if (data.suggestions?.length) lines.push(`Suggestions: ${data.suggestions.slice(0, 5).join(", ")}`);
			}
			results.forEach((r, i) => {
				const engines = r.engines?.length ? r.engines.join(", ") : (r.engine ?? "");
				const date = r.publishedDate ? ` (${r.publishedDate.slice(0, 10)})` : "";
				lines.push(`${i + 1}. ${clip(r.title ?? "(untitled)", 120)}${date}`);
				lines.push(`   ${r.url ?? ""}`);
				if (r.content) lines.push(`   ${clip(r.content, 300)}`);
				if (engines) lines.push(`   via ${engines}`);
			});
			const { text } = budget(lines.join("\n"), "Ask for fewer results.");
			return {
				content: [{ type: "text", text }],
				details: { query: params.query, count: results.length, seconds },
			};
		},
	});

	pi.registerTool({
		name: "web_fetch",
		label: "Web fetch",
		description: `Fetch a URL and return its main content as markdown (HTML is reduced with Readability; text, JSON and markdown come back as-is; GitHub blob URLs are fetched raw). Output is cut to ${formatSize(MAX_BYTES)} or ${MAX_LINES} lines, so fetch specific pages rather than index pages. PDFs and binaries are not supported.`,
		promptSnippet: "Fetch a URL as markdown (article text, GitHub files raw)",
		promptGuidelines: ["Use web_fetch on a specific page, not a site index; its output is capped, so pick the page that holds the answer"],
		parameters: Type.Object({
			url: Type.String({ description: "Absolute http(s) URL" }),
		}),
		async execute(_toolCallId, params, signal) {
			const target = rewriteUrl(params.url.trim());
			if (!/^https?:\/\//i.test(target)) throw new Error("web_fetch needs an absolute http(s) URL");
			const t0 = performance.now();
			let res: Response;
			try {
				res = await fetch(target, {
					headers: { "user-agent": USER_AGENT, accept: "text/html,application/xhtml+xml,text/plain,application/json,text/markdown;q=0.9,*/*;q=0.5" },
					redirect: "follow",
					signal: AbortSignal.any([signal, AbortSignal.timeout(FETCH_TIMEOUT_MS)]),
				});
			} catch (err) {
				const message = err instanceof Error ? (err as any).cause?.code ?? err.message : String(err);
				throw new Error(`web_fetch failed for ${target}: ${message}`);
			}
			if (!res.ok) throw new Error(`web_fetch: ${target} answered HTTP ${res.status} ${res.statusText}`);
			const contentType = (res.headers.get("content-type") ?? "").toLowerCase();
			const body = await readBody(res);
			const seconds = (performance.now() - t0) / 1000;

			let text: string;
			let title = "";
			let readable = false;
			if (contentType.includes("html")) {
				const converted = htmlToMarkdown(body, res.url || target);
				title = converted.title;
				readable = converted.readable;
				text = `${title ? `# ${title}\n` : ""}Source: ${res.url || target}\n\n${converted.markdown}`;
			} else if (/^(text\/|application\/(json|xml|javascript|x-yaml|yaml|toml))/.test(contentType) || contentType === "") {
				text = `Source: ${res.url || target}\n\n${body}`;
			} else {
				throw new Error(`web_fetch: unsupported content type ${contentType} at ${target}`);
			}
			record({ type: "web_fetch", bytes: body.length, contentType, readable, seconds });
			const budgeted = budget(text, "Fetch a more specific page, or search within the site for the section you need.");
			return {
				content: [{ type: "text", text: budgeted.text }],
				details: { url: res.url || target, title, contentType, bytes: body.length, truncated: budgeted.truncated, readable, seconds },
			};
		},
	});
}
