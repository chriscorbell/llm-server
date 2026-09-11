#!/usr/bin/env python3
"""Measure decode speed, time to first token, prefill rate and MTP acceptance.

Client-side timing against the OpenAI-compatible endpoint, which is what the
agent client actually experiences. Reports medians over n repetitions.

Every run uses a unique random prefix so prefix caching does not silently turn a
cold measurement into a warm one. Pass --warm to measure the cached path instead.

Usage:
  ./bench.py --base-url http://vllm:8000 --prompt-tokens 512 --gen 128 -n 5

The key defaults to the llm-server entry in ~/.pi/agent/auth.json; pass --key to override.
"""
import argparse, hashlib, json, os, statistics, time, urllib.request, uuid, sys, re
from pathlib import Path

def post_stream(url, key, body, timeout=1800):
    req = urllib.request.Request(
        url + "/v1/chat/completions",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
    )
    started_at = time.time()
    t0 = time.monotonic()
    ttft = None
    chunks = 0
    completion_tokens = None
    prompt_tokens = None
    cached_tokens = None
    text = {"content": "", "reasoning": "", "tool_arguments": ""}
    finish_reason = None
    with urllib.request.urlopen(req, timeout=timeout) as r:
        for raw in r:
            line = raw.decode().strip()
            if not line.startswith("data: "):
                continue
            payload = line[6:]
            if payload == "[DONE]":
                break
            chunk = json.loads(payload)
            if chunk.get("usage"):
                completion_tokens = chunk["usage"].get("completion_tokens")
                prompt_tokens = chunk["usage"].get("prompt_tokens")
                cached_tokens = (chunk["usage"].get("prompt_tokens_details") or {}).get("cached_tokens")
            if not chunk.get("choices"):
                continue
            delta = chunk["choices"][0].get("delta", {})
            finish_reason = chunk["choices"][0].get("finish_reason") or finish_reason
            content = delta.get("content") or ""
            reasoning = delta.get("reasoning") or delta.get("reasoning_content") or ""
            arguments = "".join(c.get("function", {}).get("arguments", "") for c in delta.get("tool_calls", []))
            text["content"] += content
            text["reasoning"] += reasoning
            text["tool_arguments"] += arguments
            if content or reasoning or arguments:
                if ttft is None:
                    ttft = time.monotonic() - t0
                chunks += 1
    total = time.monotonic() - t0
    # Speculative decoding can carry several tokens in one stream chunk, so counting
    # chunks understates the rate. Trust the server's own usage count when present.
    if completion_tokens is None or prompt_tokens is None:
        raise RuntimeError("Server omitted usage token counts; stream chunks are not tokens with MTP")
    return {"started_at": started_at, "finished_at": time.time(),
            "ttft_s": ttft, "gen_tokens": completion_tokens, "total_s": total,
            "prompt_tokens": prompt_tokens, "cached_tokens": cached_tokens,
            "finish_reason": finish_reason, "stream_chunks": chunks, "text": text}

def metrics(url, key):
    """Scrape MTP acceptance from the Prometheus endpoint."""
    try:
        req = urllib.request.Request(url + "/metrics", headers={"Authorization": f"Bearer {key}"})
        text = urllib.request.urlopen(req, timeout=10).read().decode()
    except Exception:
        return {}
    out = {}
    for name, labels, value in re.findall(r"^(vllm:spec_decode_\w+_total)\{([^}]*)\}\s+([0-9.e+]+)$", text, re.M):
        position = re.search(r'position="(\d+)"', labels)
        key = name + (":" + position[1] if position else "")
        out[key] = out.get(key, 0) + float(value)
    return out

CORPUS_DIR = Path(__file__).resolve().parent.parent


def _corpus_text(kind):
    """Real text of the kind this server actually serves.

    "code" reads this repository's own sources, "prose" its own Markdown.
    Output predictability affects acceptance much more than input type. Use
    --corpus-file to freeze input across experiments and --workload for output.
    """
    if kind == "filler":
        words = ("the quick brown fox jumps over the lazy dog while counting "
                 "tokens for a benchmark run ").split()
        return " ".join(words[i % len(words)] for i in range(200_000))
    globs = ("**/*.py", "**/*.sh", "**/*.ts") if kind == "code" else ("**/*.md",)
    parts = []
    for pattern in globs:
        for path in sorted(CORPUS_DIR.glob(pattern)):
            if ".git" in path.parts or "results" in path.parts:
                continue
            try:
                parts.append(path.read_text())
            except (OSError, UnicodeDecodeError):
                continue
    if not parts:
        raise SystemExit(f"no {kind} corpus found under {CORPUS_DIR}")
    return "\n\n".join(parts)


def filler(n_tokens, kind="code", corpus=None, session_id=None):
    """About n_tokens of realistic text, with a unique prefix to defeat caching.

    Roughly 3.6 characters per token for code, which is close enough for a
    benchmark that reports the server's own token count anyway.
    """
    text = corpus if corpus is not None else _corpus_text(kind)
    want = int(n_tokens * 3.6)
    body = (text * (want // len(text) + 1))[:want]
    return f"// benchmark session {session_id or uuid.uuid4().hex}\n{body}"


CODE_TASK = """Write a complete Python 3 module implementing these utilities:
1. chunked(iterable, size): yield lists of at most size elements; reject size <= 0.
2. unique_by(items, key): preserve the first item for each hashable key.
3. merge_intervals(intervals): sort and merge overlapping or touching closed intervals.
4. flatten(value): recursively yield leaves from nested lists and tuples, preserving strings.
5. deep_merge(left, right): recursively merge dictionaries without mutating either input.
6. retry(fn, attempts, retry_on): call fn until it succeeds; re-raise the final exception.
Use only the standard library, type hints and short docstrings. Include examples in a
main block. The reference material above is unrelated context; do not copy it.
Return the implementation now, without discussing the reference material."""


def request_body(a, prefix, rep):
    instruction = "Summarise what the text above is for, in one plain paragraph."
    if a.workload in ("code", "tool"):
        instruction = CODE_TASK
    body = {
        "model": a.model,
        "messages": [{"role": "user", "content": prefix + "\n\n" + instruction}],
        "max_tokens": a.gen, "stream": True, "stream_options": {"include_usage": True},
        "temperature": 1.0 if a.thinking else 0.7,
        "top_p": 0.95 if a.thinking else 0.8, "top_k": a.top_k,
        "min_p": 0.0, "presence_penalty": 0.0 if a.thinking else 1.5,
        "repetition_penalty": 1.0, "seed": a.seed + rep,
        "chat_template_kwargs": {"enable_thinking": a.thinking, "preserve_thinking": True},
    }
    if a.thinking:
        body["reasoning_effort"] = a.effort
    if a.workload == "tool":
        body["tools"] = [{"type": "function", "function": {
            "name": "write", "description": "Write a complete UTF-8 file.",
            "parameters": {"type": "object", "properties": {
                "path": {"type": "string"}, "content": {"type": "string"}},
                "required": ["path", "content"]}}}]
        body["tool_choice"] = "auto"
        body["messages"][0]["content"] += "\nUse the write tool to save the module to utilities.py."
    return body

def pi_api_key(provider="llm-server"):
    """The server key from Pi's auth store, which is where it lives on the MacBook."""
    agent_dir = Path(os.environ.get("PI_CODING_AGENT_DIR") or Path.home() / ".pi" / "agent")
    try:
        return json.loads((agent_dir / "auth.json").read_text())[provider]["key"]
    except (OSError, KeyError, TypeError, ValueError):
        return None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="http://127.0.0.1:8000")
    ap.add_argument("--key", default=pi_api_key() or "change-me", help="defaults to the llm-server key in Pi's auth.json")
    ap.add_argument("--model", default="qwen38")
    ap.add_argument("--prompt-tokens", type=int, default=512)
    ap.add_argument("--gen", type=int, default=128)
    ap.add_argument("-n", type=int, default=5)
    ap.add_argument("--thinking", action="store_true", help="leave thinking on (default off for stable timing)")
    ap.add_argument("--warm", action="store_true", help="reuse the same prompt to measure the cached path")
    ap.add_argument("--prompt-id", help="stable prompt identifier for matched warm comparisons; requires --warm")
    ap.add_argument("--corpus-file", type=Path, help="fixed input corpus, unchanged between comparison arms")
    ap.add_argument("--workload", choices=("summary", "code", "tool"), default="summary")
    ap.add_argument("--effort", choices=("low", "medium", "xhigh"), default="xhigh")
    ap.add_argument("--seed", type=int, default=42000, help="sampling seed; incremented for each repetition")
    ap.add_argument("--top-k", type=int, default=20)
    ap.add_argument("--corpus", choices=("code", "prose", "filler"), default="code",
                    help="what kind of text to fill the prompt with")
    ap.add_argument("--json", help="write results to this path")
    a = ap.parse_args()
    if a.n < 1 or a.gen < 2 or a.prompt_tokens < 1:
        ap.error("repetitions and prompt tokens must be positive; generation must be at least two tokens")
    if a.prompt_id and not a.warm:
        ap.error("--prompt-id requires --warm; cold runs need fresh prefixes")
    corpus = a.corpus_file.read_text() if a.corpus_file else _corpus_text(a.corpus)
    if not corpus:
        ap.error("input corpus is empty")
    prompt_id = (a.prompt_id or uuid.uuid4().hex) if a.warm else None
    fixed = filler(a.prompt_tokens, corpus=corpus, session_id=prompt_id) if a.warm else None
    rows = []
    deltas = {}
    def save():
        if a.json:
            path = Path(a.json)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps({"result": result, "reps": rows}, indent=2))
    result = {"status": "in_progress", "workload": a.workload,
              "corpus_sha256": hashlib.sha256(corpus.encode()).hexdigest(), "prompt_id": prompt_id}
    for i in range(a.n + 1):  # first is a discarded warmup of the same shape
        body = request_body(a, fixed or filler(a.prompt_tokens, corpus=corpus), i)
        m0 = metrics(a.base_url, a.key)
        row = post_stream(a.base_url, a.key, body)
        row["request_sha256"] = hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()
        m1 = metrics(a.base_url, a.key)
        if i == 0:
            print("warmup complete", flush=True)
            continue
        ttft, ntok, total, prompt_tokens = (row[k] for k in ("ttft_s", "gen_tokens", "total_s", "prompt_tokens"))
        if ttft is None or ntok < 2:
            raise RuntimeError(f"rep {i}: insufficient output: {row}")
        row["decode_tok_s"] = (ntok - 1) / (total - ttft)
        # Input/TTFT is an effective cold rate, not an isolated GPU prefill kernel measurement.
        row["prefill_tok_s"] = prompt_tokens / ttft if not a.warm else None
        row["seed"] = a.seed + i
        row["spec_delta"] = {k: m1[k] - m0[k] for k in m0.keys() & m1.keys()}
        for k, value in row["spec_delta"].items():
            deltas[k] = deltas.get(k, 0) + value
        rows.append(row)
        save()
        print(f"rep {i}: input {prompt_tokens} cached {row['cached_tokens']} ttft {ttft:.2f}s "
              f"decode {row['decode_tok_s']:.1f} tok/s output {ntok} "
              f"chars answer/reason/tool {len(row['text']['content'])}/{len(row['text']['reasoning'])}/{len(row['text']['tool_arguments'])}", flush=True)

    acc = None
    da = deltas.get("vllm:spec_decode_num_accepted_tokens_total", 0)
    dd = deltas.get("vllm:spec_decode_num_draft_tokens_total", 0)
    drafts = deltas.get("vllm:spec_decode_num_drafts_total", 0)
    if dd > 0:
        acc = 100.0 * da / dd

    med = lambda k: statistics.median(r[k] for r in rows)
    result = {**result, "status": "complete",
        "prompt_tokens": med("prompt_tokens"), "prompt_tokens_target": a.prompt_tokens,
        "concurrency": 1, "gen": a.gen, "n": len(rows),
        "corpus": a.corpus, "top_k": a.top_k,
        "thinking": a.thinking, "prefix_cache_path": "warm" if a.warm else "cold",
        "effort": a.effort if a.thinking else None, "seed": a.seed,
        "ttft_s_median": round(med("ttft_s"), 3),
        "decode_tok_s_median": round(med("decode_tok_s"), 1),
        "decode_tok_s_stdev": round(statistics.stdev(r["decode_tok_s"] for r in rows), 2) if len(rows) > 1 else 0,
        "decode_tok_s_min": round(min(r["decode_tok_s"] for r in rows), 1),
        "decode_tok_s_max": round(max(r["decode_tok_s"] for r in rows), 1),
        "gen_tokens_median": med("gen_tokens"), "total_s_median": round(med("total_s"), 3),
        "cached_tokens_median": med("cached_tokens") if all(r["cached_tokens"] is not None for r in rows) else None,
        "prefill_tok_s_median": round(med("prefill_tok_s"), 1) if not a.warm else None,
        "mtp_acceptance_pct": round(acc, 1) if acc is not None else None,
        "mtp_acceptance_per_position": {k.rsplit(":", 1)[1]: round(v / drafts, 4)
            for k, v in deltas.items() if "per_pos_total:" in k and drafts > 0},
    }
    print("\n" + json.dumps(result, indent=2))
    save()

if __name__ == "__main__":
    main()
